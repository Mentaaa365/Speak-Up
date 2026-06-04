# apps/authentication/urls.py
from django.urls import path
from django.urls import reverse_lazy
from django.contrib.auth import views as auth_views
from . import views

app_name = 'authentication'

urlpatterns = [
    path('login/', views.SpeakUpLoginView.as_view(), name='login'),
    path('register/', views.SpeakUpRegisterView.as_view(), name='register'),
    path('logout/', views.speakup_logout_view, name='logout'),

    # 🔥 HU-02: FLUJO SEGURO DE RECUPERACIÓN DE CONTRASEÑA
    # 1. Formulario de solicitud (Introduce tu correo)
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='authentication/password_reset_form.html',
             # Correo en texto plano (Respaldo)
             email_template_name='authentication/password_reset_email.html',
             # 🔥 LA CLAVE: Correo con maquetación HTML gráfica (Prioridad)
             html_email_template_name='authentication/password_reset_email.html',
             success_url=reverse_lazy('authentication:password_reset_done')
         ), 
         name='password_reset'),

    # 2. Confirmación de envío ("Te hemos enviado un correo")
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='authentication/password_reset_done.html'
         ), 
         name='password_reset_done'),

    # 3. Formulario para ingresar la nueva clave (Validación asíncrona de Token temporal)
    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='authentication/password_reset_confirm.html',
             success_url=reverse_lazy('authentication:password_reset_complete')
         ), 
         name='password_reset_confirm'),

    # 4. Éxito final ("Contraseña cambiada con éxito")
    path('password-reset/complete/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='authentication/password_reset_complete.html'
         ), 
         name='password_reset_complete'),
]