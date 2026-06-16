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

    # RF-02: Custom password reset flow using PasswordResetToken (SHA-256, 30 min TTL)
    path('password-reset/',
         views.CustomPasswordResetRequestView.as_view(),
         name='password_reset'),

    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='authentication/password_reset_done.html'
         ),
         name='password_reset_done'),

    path('password-reset-confirm/<str:token>/',
         views.CustomPasswordResetConfirmView.as_view(),
         name='password_reset_confirm'),

    path('password-reset/complete/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='authentication/password_reset_complete.html'
         ),
         name='password_reset_complete'),
]