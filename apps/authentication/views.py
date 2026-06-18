import hashlib
import uuid
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model, logout
from django.contrib.auth.views import LoginView
from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from .forms import PasswordResetRequestForm, RegistroForm, SetNewPasswordForm
from .models import PasswordResetToken

User = get_user_model()

class SpeakUpLoginView(LoginView):
    template_name = 'authentication/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        user = self.request.user
        
        # 1. Evaluamos si el perfil existe y si ya tiene un nivel asignado
        if hasattr(user, 'perfil') and user.perfil.nivel_mcer is not None:
            return reverse_lazy('progress:dashboard')
        
        # 2. Si es un usuario nuevo, lo enviamos al examen. 
        # La ruta correcta es 'diagnosis:welcome' o 'diagnosis:test_run' (Nunca 'test' a secas)
        return reverse_lazy('diagnosis:welcome')

# VISTA DE REGISTRO ACTUALIZADA:
class SpeakUpRegisterView(TemplateView):
    template_name = 'authentication/register.html'

    def post(self, request, *args, **kwargs):
        form = RegistroForm(request.POST)

        if form.is_valid():
            nombre = form.cleaned_data['first_name']
            correo = form.cleaned_data['email']
            contrasena = form.cleaned_data['password']
            institucion = form.cleaned_data['institution']

            try:
                # 2. Envolvemos la creación en una transacción atómica
                with transaction.atomic():
                    nuevo_usuario = User.objects.create_user(
                        username=correo,
                        email=correo,
                        password=contrasena,
                        first_name=nombre
                    )
                    
                    nuevo_usuario.perfil.institucion = institucion
                    nuevo_usuario.perfil.save()

                # Si todo sale bien dentro del bloque `with`, redirigimos:
                messages.success(request, '¡Registro exitoso! Por favor, inicia sesión.')
                return redirect('authentication:login')

            except Exception as e:
                # Si algo falla en la base de datos, entra aquí y deshace la creación
                messages.error(request, 'Ocurrió un error en el servidor al guardar tu cuenta. Intenta de nuevo.')
                return render(request, self.template_name)
                
        else:
            contexto = {}
            
            if 'first_name' in form.errors:
                messages.error(request, form.errors['first_name'][0])
                
            if 'email' in form.errors:
                contexto['error_correo_duplicado'] = True

            if 'password' in form.errors:
                for error in form.errors['password']:
                    messages.error(request, error)

            return render(request, self.template_name, contexto)

class DummyView(TemplateView):
    template_name = 'base.html'


def speakup_logout_view(request):
    logout(request)
    return redirect('authentication:login')


class CustomPasswordResetRequestView(View):
    template_name = 'authentication/password_reset_form.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, {'form': PasswordResetRequestForm()})

    def post(self, request, *args, **kwargs):
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
                PasswordResetToken.objects.filter(
                    usuario=user, used_at__isnull=True
                ).update(used_at=timezone.now())
                raw_token = uuid.uuid4().hex
                token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
                PasswordResetToken.objects.create(
                    usuario=user,
                    token_hash=token_hash,
                    expires_at=timezone.now() + timedelta(minutes=30),
                )
                reset_url = request.build_absolute_uri(
                    reverse('authentication:password_reset_confirm', kwargs={'token': raw_token})
                )
                send_mail(
                    subject='Restablecer contraseña - SpeakUp',
                    message=reset_url,
                    from_email=None,
                    recipient_list=[email],
                    html_message=render_to_string(
                        'authentication/password_reset_email.html',
                        {'reset_url': reset_url, 'user': user},
                    ),
                )
            except User.DoesNotExist:
                pass
        return redirect(reverse_lazy('authentication:password_reset_done'))


class CustomPasswordResetConfirmView(View):
    template_name = 'authentication/password_reset_confirm.html'

    def _get_valid_token(self, raw_token):
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        try:
            token = PasswordResetToken.objects.get(token_hash=token_hash, used_at__isnull=True)
            return None if token.is_expired() else token
        except PasswordResetToken.DoesNotExist:
            return None

    def get(self, request, token, *args, **kwargs):
        valid_token = self._get_valid_token(token)
        return render(request, self.template_name, {
            'validlink': valid_token is not None,
            'form': SetNewPasswordForm() if valid_token else None,
        })

    def post(self, request, token, *args, **kwargs):
        valid_token = self._get_valid_token(token)
        if not valid_token:
            return render(request, self.template_name, {'validlink': False})
        form = SetNewPasswordForm(request.POST)
        if form.is_valid():
            valid_token.usuario.set_password(form.cleaned_data['new_password1'])
            valid_token.usuario.save()
            valid_token.used_at = timezone.now()
            valid_token.save()
            return redirect(reverse_lazy('authentication:password_reset_complete'))
        return render(request, self.template_name, {'validlink': True, 'form': form})