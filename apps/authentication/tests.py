import hashlib
import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.authentication.backends import EmailBackend
from apps.authentication.forms import PasswordResetRequestForm, SetNewPasswordForm
from apps.authentication.models import PasswordResetToken, Perfil
from apps.curriculum.models import NivelMCER

User = get_user_model()


class CustomUserModelTests(TestCase):
    """Custom User(AbstractUser) with unique email."""

    def test_get_user_model_resolves_to_authentication_user(self):
        self.assertEqual(User._meta.app_label, "authentication")
        self.assertEqual(User._meta.model_name, "user")

    def test_duplicate_email_raises_integrity_error(self):
        User.objects.create_user(
            username="ana", email="ana@example.com", password="x"
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(
                    username="ana2", email="ana@example.com", password="y"
                )


class EmailBackendTests(TestCase):
    """EmailBackend.authenticate continues to work with the custom User."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="bea", email="bea@example.com", password="correct-pass"
        )
        self.backend = EmailBackend()

    def test_authenticate_returns_user_with_correct_password(self):
        authenticated = self.backend.authenticate(
            request=None, username="bea@example.com", password="correct-pass"
        )
        self.assertEqual(authenticated, self.user)

    def test_authenticate_returns_none_with_wrong_password(self):
        authenticated = self.backend.authenticate(
            request=None, username="bea@example.com", password="wrong-pass"
        )
        self.assertIsNone(authenticated)


class PerfilSignalTests(TestCase):
    """Perfil is auto-created via post_save when a User is created."""

    def test_creating_user_auto_creates_exactly_one_perfil(self):
        user = User.objects.create_user(
            username="carla", email="carla@example.com", password="x"
        )
        self.assertEqual(Perfil.objects.filter(usuario=user).count(), 1)
        perfil = Perfil.objects.get(usuario=user)
        self.assertIsNone(perfil.nivel_mcer)

    def test_existing_user_save_does_not_duplicate_perfil(self):
        user = User.objects.create_user(
            username="dani", email="dani@example.com", password="x"
        )
        self.assertEqual(Perfil.objects.filter(usuario=user).count(), 1)

        # Saving the user again (created=False) must not create a second Perfil.
        user.first_name = "Dani"
        user.save()

        self.assertEqual(Perfil.objects.filter(usuario=user).count(), 1)

    def test_perfil_nivel_mcer_set_null_on_nivel_delete(self):
        nivel = NivelMCER.objects.create(codigo="A1", orden=1)
        user = User.objects.create_user(
            username="elena", email="elena@example.com", password="x"
        )
        perfil = Perfil.objects.get(usuario=user)
        perfil.nivel_mcer = nivel
        perfil.save()

        nivel.delete()

        perfil.refresh_from_db()
        self.assertIsNone(perfil.nivel_mcer)


class LoginRedirectTests(TestCase):
    """SpeakUpLoginView redirects correctly based on profile state."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="redir@example.com",
            email="redir@example.com",
            password="ValidPass1!",
        )

    def test_new_user_redirects_to_diagnosis_welcome(self):
        response = self.client.post(
            "/authentication/login/",
            {"username": "redir@example.com", "password": "ValidPass1!"},
        )
        self.assertRedirects(
            response,
            "/diagnosis/speaking/",
            fetch_redirect_response=False,
        )

    def test_returning_user_redirects_to_dashboard(self):
        nivel = NivelMCER.objects.create(codigo="A1", orden=1)
        self.user.perfil.nivel_mcer = nivel
        self.user.perfil.save()

        response = self.client.post(
            "/authentication/login/",
            {"username": "redir@example.com", "password": "ValidPass1!"},
        )
        self.assertRedirects(
            response,
            "/progress/dashboard/",
            fetch_redirect_response=False,
        )


class PasswordResetTokenTests(TestCase):
    """PasswordResetToken: TTL, single-active-per-user, invalidation on use."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="fede", email="fede@example.com", password="x"
        )

    def test_expired_token_is_invalid(self):
        token = PasswordResetToken.objects.create(
            usuario=self.user,
            token_hash="a" * 64,
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        self.assertTrue(token.is_expired())

    def test_unexpired_unused_token_is_valid(self):
        token = PasswordResetToken.objects.create(
            usuario=self.user,
            token_hash="b" * 64,
            expires_at=timezone.now() + timedelta(minutes=30),
        )
        self.assertFalse(token.is_expired())

    def test_unique_constraint_blocks_second_active_token_per_user(self):
        PasswordResetToken.objects.create(
            usuario=self.user,
            token_hash="c" * 64,
            expires_at=timezone.now() + timedelta(minutes=30),
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PasswordResetToken.objects.create(
                    usuario=self.user,
                    token_hash="d" * 64,
                    expires_at=timezone.now() + timedelta(minutes=30),
                )

    def test_marking_used_allows_new_active_token(self):
        first = PasswordResetToken.objects.create(
            usuario=self.user,
            token_hash="e" * 64,
            expires_at=timezone.now() + timedelta(minutes=30),
        )
        first.used_at = timezone.now()
        first.save()

        second = PasswordResetToken.objects.create(
            usuario=self.user,
            token_hash="f" * 64,
            expires_at=timezone.now() + timedelta(minutes=30),
        )

        self.assertIsNotNone(second.pk)
        self.assertEqual(
            PasswordResetToken.objects.filter(
                usuario=self.user, used_at__isnull=True
            ).count(),
            1,
        )


class PasswordResetRequestFormTests(TestCase):
    """PasswordResetRequestForm: email field validation."""

    def test_valid_email_is_accepted(self):
        form = PasswordResetRequestForm({'email': 'student@example.com'})
        self.assertTrue(form.is_valid())

    def test_invalid_email_format_is_rejected(self):
        form = PasswordResetRequestForm({'email': 'not-an-email'})
        self.assertFalse(form.is_valid())

    def test_empty_email_is_rejected(self):
        form = PasswordResetRequestForm({'email': ''})
        self.assertFalse(form.is_valid())


class SetNewPasswordFormTests(TestCase):
    """SetNewPasswordForm: password match and strength validation."""

    VALID_PASSWORD = 'ValidPass123!'

    def test_matching_strong_passwords_are_valid(self):
        data = {'new_password1': self.VALID_PASSWORD, 'new_password2': self.VALID_PASSWORD}
        form = SetNewPasswordForm(data)
        self.assertTrue(form.is_valid())

    def test_non_matching_passwords_are_rejected(self):
        data = {'new_password1': self.VALID_PASSWORD, 'new_password2': 'DifferentPass1!'}
        form = SetNewPasswordForm(data)
        self.assertFalse(form.is_valid())

    def test_weak_password_is_rejected(self):
        data = {'new_password1': '123', 'new_password2': '123'}
        form = SetNewPasswordForm(data)
        self.assertFalse(form.is_valid())


class PasswordResetRequestViewTests(TestCase):
    """CustomPasswordResetRequestView: token creation, email sending, generic response (RF-02)."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='reset@example.com',
            email='reset@example.com',
            password='OldPass123!',
        )
        self.url = reverse('authentication:password_reset')

    def test_post_with_known_email_creates_one_active_token(self):
        self.client.post(self.url, {'email': 'reset@example.com'})
        self.assertEqual(
            PasswordResetToken.objects.filter(usuario=self.user, used_at__isnull=True).count(), 1
        )

    def test_post_with_known_email_sends_one_email(self):
        self.client.post(self.url, {'email': 'reset@example.com'})
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('reset@example.com', mail.outbox[0].to)

    def test_post_redirects_to_done_for_known_email(self):
        response = self.client.post(self.url, {'email': 'reset@example.com'})
        self.assertRedirects(
            response, reverse('authentication:password_reset_done'), fetch_redirect_response=False
        )

    def test_post_with_unknown_email_does_not_create_token(self):
        self.client.post(self.url, {'email': 'nobody@example.com'})
        self.assertEqual(PasswordResetToken.objects.count(), 0)

    def test_post_with_unknown_email_does_not_send_email(self):
        self.client.post(self.url, {'email': 'nobody@example.com'})
        self.assertEqual(len(mail.outbox), 0)

    def test_post_with_unknown_email_redirects_to_done(self):
        response = self.client.post(self.url, {'email': 'nobody@example.com'})
        self.assertRedirects(
            response, reverse('authentication:password_reset_done'), fetch_redirect_response=False
        )

    def test_new_request_invalidates_previous_active_token(self):
        self.client.post(self.url, {'email': 'reset@example.com'})
        first_token = PasswordResetToken.objects.get(usuario=self.user)
        self.client.post(self.url, {'email': 'reset@example.com'})
        first_token.refresh_from_db()
        self.assertIsNotNone(first_token.used_at)
        self.assertEqual(
            PasswordResetToken.objects.filter(usuario=self.user, used_at__isnull=True).count(), 1
        )


class PasswordResetConfirmViewTests(TestCase):
    """CustomPasswordResetConfirmView: token validation and password update (RF-02)."""

    VALID_PASSWORD = 'NewPass123!'

    def setUp(self):
        self.user = User.objects.create_user(
            username='confirm@example.com',
            email='confirm@example.com',
            password='OldPass123!',
        )
        self.raw_token = uuid.uuid4().hex
        token_hash = hashlib.sha256(self.raw_token.encode()).hexdigest()
        self.token_obj = PasswordResetToken.objects.create(
            usuario=self.user,
            token_hash=token_hash,
            expires_at=timezone.now() + timedelta(minutes=30),
        )
        self.confirm_url = reverse(
            'authentication:password_reset_confirm', kwargs={'token': self.raw_token}
        )

    def test_get_with_valid_token_shows_form(self):
        response = self.client.get(self.confirm_url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['validlink'])
        self.assertIsNotNone(response.context['form'])

    def test_get_with_expired_token_shows_invalid_link(self):
        self.token_obj.expires_at = timezone.now() - timedelta(minutes=1)
        self.token_obj.save()
        response = self.client.get(self.confirm_url)
        self.assertFalse(response.context['validlink'])

    def test_get_with_used_token_shows_invalid_link(self):
        self.token_obj.used_at = timezone.now()
        self.token_obj.save()
        response = self.client.get(self.confirm_url)
        self.assertFalse(response.context['validlink'])

    def test_get_with_unknown_token_shows_invalid_link(self):
        unknown_url = reverse(
            'authentication:password_reset_confirm', kwargs={'token': '0' * 32}
        )
        response = self.client.get(unknown_url)
        self.assertFalse(response.context['validlink'])

    def test_post_updates_password_and_marks_token_used(self):
        self.client.post(
            self.confirm_url,
            {'new_password1': self.VALID_PASSWORD, 'new_password2': self.VALID_PASSWORD},
        )
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.VALID_PASSWORD))
        self.token_obj.refresh_from_db()
        self.assertIsNotNone(self.token_obj.used_at)

    def test_post_redirects_to_complete(self):
        response = self.client.post(
            self.confirm_url,
            {'new_password1': self.VALID_PASSWORD, 'new_password2': self.VALID_PASSWORD},
        )
        self.assertRedirects(
            response, reverse('authentication:password_reset_complete'), fetch_redirect_response=False
        )

    def test_post_with_mismatched_passwords_does_not_mark_token_used(self):
        self.client.post(
            self.confirm_url,
            {'new_password1': self.VALID_PASSWORD, 'new_password2': 'DifferentPass1!'},
        )
        self.token_obj.refresh_from_db()
        self.assertIsNone(self.token_obj.used_at)
