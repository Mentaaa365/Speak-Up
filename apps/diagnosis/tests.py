import inspect
import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.authentication.models import Perfil
from apps.curriculum.models import NivelMCER
from apps.diagnosis import views
from apps.question_bank.models import Question

User = get_user_model()


class DiagnosisBankContextFilterTests(TestCase):
    """API must only serve bank_context='DIAGNOSTIC' questions (RF-03)."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="bank@example.com", email="bank@example.com", password="x"
        )
        self.client.force_login(self.user)

    def test_exercise_questions_are_excluded_from_diagnostic_api(self):
        Question.objects.create(
            level="A1", question_type="CHOICE",
            bank_context="DIAGNOSTIC", text="Diagnostic question"
        )
        Question.objects.create(
            level="A1", question_type="CHOICE",
            bank_context="EXERCISE", text="Exercise question"
        )

        response = self.client.get(reverse("diagnosis:api_get_questions"))
        texts = [q["text"] for q in response.json()["questions"]]

        self.assertIn("Diagnostic question", texts)
        self.assertNotIn("Exercise question", texts)

    def test_promotion_exam_questions_are_excluded_from_diagnostic_api(self):
        Question.objects.create(
            level="B1", question_type="CHOICE",
            bank_context="DIAGNOSTIC", text="Diagnostic B1 question"
        )
        Question.objects.create(
            level="B1", question_type="CHOICE",
            bank_context="PROMOTION_EXAM", text="Promotion exam question"
        )

        response = self.client.get(reverse("diagnosis:api_get_questions"))
        texts = [q["text"] for q in response.json()["questions"]]

        self.assertIn("Diagnostic B1 question", texts)
        self.assertNotIn("Promotion exam question", texts)


class DiagnosisModuleIndependenceTests(TestCase):
    """diagnosis must not import from apps.progress (RF-08 module independence)."""

    def test_views_source_has_no_progress_imports(self):
        source = inspect.getsource(views)
        self.assertNotIn("from apps.progress", source)
        self.assertNotIn("import apps.progress", source)


class DiagnosisResultsPersistsNivelMcerTests(TestCase):
    """Completing the diagnosis flow assigns Perfil.nivel_mcer via curriculum.NivelMCER."""

    def setUp(self):
        self.nivel_a1 = NivelMCER.objects.create(codigo="A1", orden=1)
        self.user = User.objects.create_user(
            username="gabi", email="gabi@example.com", password="x"
        )
        self.client.force_login(self.user)

    def test_post_results_assigns_nivel_mcer_to_perfil(self):
        response = self.client.post(
            reverse("diagnosis:results"),
            {"answers_data": json.dumps([])},
        )

        self.assertEqual(response.status_code, 200)

        perfil = Perfil.objects.get(usuario=self.user)
        self.assertEqual(perfil.nivel_mcer, self.nivel_a1)


# ──────────────────────────────────────────────────────────────────────────────
#  H2 — DiagnosisAttempt model tests
# ──────────────────────────────────────────────────────────────────────────────

class DiagnosisAttemptModelTests(TestCase):
    """DiagnosisAttempt creates correctly with all fields and correct FK relations."""

    def setUp(self):
        self.nivel = NivelMCER.objects.create(codigo="A1", orden=1)
        self.user = User.objects.create_user(
            username="modeltest@example.com",
            email="modeltest@example.com",
            password="x",
        )
        self.perfil = Perfil.objects.get(usuario=self.user)

    def test_create_with_all_fields(self):
        from apps.diagnosis.models import DiagnosisAttempt
        attempt = DiagnosisAttempt.objects.create(
            perfil=self.perfil,
            nivel_resultado=self.nivel,
            score_speaking=40,
            score_listening=35,
            score_vocab=15,
            score_writing=10,
            score_total=100,
        )
        self.assertEqual(attempt.perfil, self.perfil)
        self.assertEqual(attempt.nivel_resultado, self.nivel)
        self.assertEqual(attempt.score_total, 100)
        self.assertIsNotNone(attempt.fecha)

    def test_fk_to_perfil_via_related_name(self):
        from apps.diagnosis.models import DiagnosisAttempt
        DiagnosisAttempt.objects.create(
            perfil=self.perfil,
            nivel_resultado=self.nivel,
            score_speaking=40,
            score_listening=35,
            score_vocab=15,
            score_writing=10,
            score_total=100,
        )
        self.assertEqual(self.perfil.diagnosis_attempts.count(), 1)

    def test_fk_to_nivel_mcer_via_related_name(self):
        from apps.diagnosis.models import DiagnosisAttempt
        DiagnosisAttempt.objects.create(
            perfil=self.perfil,
            nivel_resultado=self.nivel,
            score_speaking=40,
            score_listening=35,
            score_vocab=15,
            score_writing=10,
            score_total=100,
        )
        self.assertEqual(self.nivel.diagnosis_attempts.count(), 1)

    def test_ordering_by_fecha_descending(self):
        from apps.diagnosis.models import DiagnosisAttempt
        first = DiagnosisAttempt.objects.create(
            perfil=self.perfil,
            nivel_resultado=self.nivel,
            score_speaking=10,
            score_listening=10,
            score_vocab=10,
            score_writing=10,
            score_total=40,
        )
        second = DiagnosisAttempt.objects.create(
            perfil=self.perfil,
            nivel_resultado=self.nivel,
            score_speaking=20,
            score_listening=20,
            score_vocab=20,
            score_writing=20,
            score_total=80,
        )
        attempts = list(DiagnosisAttempt.objects.filter(perfil=self.perfil))
        # second was created later, so it should come first with -fecha ordering
        self.assertEqual(attempts[0].pk, second.pk)
        self.assertEqual(attempts[1].pk, first.pk)


# ──────────────────────────────────────────────────────────────────────────────
#  H2 — Cooldown guard on DiagnosisWelcomeView
# ──────────────────────────────────────────────────────────────────────────────

class DiagnosisCooldownGuardTests(TestCase):
    """DiagnosisWelcomeView enforces a 30-day cooldown when nivel_mcer is set."""

    def setUp(self):
        self.nivel = NivelMCER.objects.create(codigo="A1", orden=1)
        self.url = reverse("diagnosis:welcome")

    def _make_user(self, username):
        return User.objects.create_user(
            username=username, email=username, password="x"
        )

    def test_no_perfil_returns_200(self):
        user = self._make_user("noperfil@example.com")
        # force_login first to flush signal-triggered Perfil save, then delete
        self.client.force_login(user)
        Perfil.objects.filter(usuario=user).delete()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_perfil_without_nivel_mcer_returns_200(self):
        user = self._make_user("nonivel@example.com")
        # Perfil exists but nivel_mcer is None (default) — order does not matter here
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_perfil_with_nivel_and_fecha_today_redirects(self):
        user = self._make_user("today@example.com")
        # force_login BEFORE modifying Perfil to avoid signal overwriting saved values
        self.client.force_login(user)
        perfil = Perfil.objects.get(usuario=user)
        perfil.nivel_mcer = self.nivel
        perfil.fecha_ultimo_diagnostico = timezone.now()
        perfil.save()
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse("progress:dashboard"), fetch_redirect_response=False)

    def test_perfil_with_nivel_and_fecha_29_days_ago_redirects(self):
        user = self._make_user("day29@example.com")
        # force_login BEFORE modifying Perfil to avoid signal overwriting saved values
        self.client.force_login(user)
        perfil = Perfil.objects.get(usuario=user)
        perfil.nivel_mcer = self.nivel
        perfil.fecha_ultimo_diagnostico = timezone.now() - timedelta(days=29)
        perfil.save()
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse("progress:dashboard"), fetch_redirect_response=False)

    def test_perfil_with_nivel_and_fecha_31_days_ago_returns_200(self):
        user = self._make_user("day31@example.com")
        # force_login BEFORE modifying Perfil to avoid signal overwriting saved values
        self.client.force_login(user)
        perfil = Perfil.objects.get(usuario=user)
        perfil.nivel_mcer = self.nivel
        perfil.fecha_ultimo_diagnostico = timezone.now() - timedelta(days=31)
        perfil.save()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_perfil_with_nivel_but_no_fecha_returns_200(self):
        user = self._make_user("nofecha@example.com")
        # force_login BEFORE modifying Perfil to avoid signal overwriting saved values
        self.client.force_login(user)
        perfil = Perfil.objects.get(usuario=user)
        perfil.nivel_mcer = self.nivel
        perfil.fecha_ultimo_diagnostico = None
        perfil.save()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)


# ──────────────────────────────────────────────────────────────────────────────
#  H2 — DiagnosisAttempt created on DiagnosisResultsView.post()
# ──────────────────────────────────────────────────────────────────────────────

class DiagnosisAttemptCreatedOnResultsTests(TestCase):
    """After a successful results POST, a DiagnosisAttempt is recorded."""

    def setUp(self):
        self.nivel_a1 = NivelMCER.objects.create(codigo="A1", orden=1)
        self.user = User.objects.create_user(
            username="resultstest@example.com",
            email="resultstest@example.com",
            password="x",
        )
        self.client.force_login(self.user)

    def test_post_creates_diagnosis_attempt(self):
        from apps.diagnosis.models import DiagnosisAttempt
        self.client.post(
            reverse("diagnosis:results"),
            {"answers_data": json.dumps([])},
        )
        self.assertEqual(DiagnosisAttempt.objects.filter(
            perfil__usuario=self.user
        ).count(), 1)

    def test_post_sets_fecha_ultimo_diagnostico(self):
        self.client.post(
            reverse("diagnosis:results"),
            {"answers_data": json.dumps([])},
        )
        perfil = Perfil.objects.get(usuario=self.user)
        self.assertIsNotNone(perfil.fecha_ultimo_diagnostico)

    def test_post_updates_nivel_mcer(self):
        self.client.post(
            reverse("diagnosis:results"),
            {"answers_data": json.dumps([])},
        )
        perfil = Perfil.objects.get(usuario=self.user)
        self.assertEqual(perfil.nivel_mcer, self.nivel_a1)


# ──────────────────────────────────────────────────────────────────────────────
#  H2 — DiagnosisAttempt history exposed in ProgressDetailView context
# ──────────────────────────────────────────────────────────────────────────────

class DiagnosisHistoryInProgressDetailTests(TestCase):
    """ProgressDetailView.get_context_data() includes diagnosis_attempts."""

    def setUp(self):
        self.nivel = NivelMCER.objects.create(codigo="A1", orden=1)
        self.user = User.objects.create_user(
            username="progresstest@example.com",
            email="progresstest@example.com",
            password="x",
        )
        # force_login BEFORE saving perfil to avoid signal overwriting nivel_mcer
        self.client.force_login(self.user)
        self.perfil = Perfil.objects.get(usuario=self.user)
        self.perfil.nivel_mcer = self.nivel
        self.perfil.save()

    def test_context_has_diagnosis_attempts_key(self):
        response = self.client.get(reverse("progress:detail"))
        self.assertIn("diagnosis_attempts", response.context)

    def test_diagnosis_attempts_contains_user_attempts(self):
        from apps.diagnosis.models import DiagnosisAttempt
        attempt = DiagnosisAttempt.objects.create(
            perfil=self.perfil,
            nivel_resultado=self.nivel,
            score_speaking=30,
            score_listening=25,
            score_vocab=10,
            score_writing=5,
            score_total=70,
        )
        response = self.client.get(reverse("progress:detail"))
        attempts_in_ctx = list(response.context["diagnosis_attempts"])
        self.assertIn(attempt, attempts_in_ctx)

    def test_diagnosis_attempts_ordered_by_fecha_desc(self):
        from apps.diagnosis.models import DiagnosisAttempt
        first = DiagnosisAttempt.objects.create(
            perfil=self.perfil,
            nivel_resultado=self.nivel,
            score_speaking=10,
            score_listening=10,
            score_vocab=10,
            score_writing=10,
            score_total=40,
        )
        second = DiagnosisAttempt.objects.create(
            perfil=self.perfil,
            nivel_resultado=self.nivel,
            score_speaking=20,
            score_listening=20,
            score_vocab=20,
            score_writing=20,
            score_total=80,
        )
        response = self.client.get(reverse("progress:detail"))
        attempts_in_ctx = list(response.context["diagnosis_attempts"])
        self.assertEqual(attempts_in_ctx[0].pk, second.pk)
        self.assertEqual(attempts_in_ctx[1].pk, first.pk)
