# apps/authentication/forms.py
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()
import re

class RegistroForm(forms.Form):
    first_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    institution = forms.CharField(max_length=100)

    def clean_first_name(self):
        nombre = self.cleaned_data.get('first_name')
        if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', nombre):
            raise forms.ValidationError('El nombre no puede contener números o símbolos.')
        return nombre

    def clean_email(self):
        correo = self.cleaned_data.get('email')
        if User.objects.filter(username=correo).exists():
            raise forms.ValidationError('Duplicado') 
        return correo

    # 🔥 NUEVO MÉTODO: Conecta tu pantalla de registro con las reglas globales
    def clean_password(self):
        password = self.cleaned_data.get('password')

        # Ejecuta AUTOMÁTICAMENTE todos los validadores definidos en settings.py
        # (incluyendo el tamaño mínimo y tus reglas de mayúsculas/símbolos)
        try:
            validate_password(password)
        except forms.ValidationError as error:
            # Si rompe cualquiera de las reglas, envía los mensajes de error directo al HTML
            raise forms.ValidationError(error.messages)

        return password


class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(label='Email address')


class SetNewPasswordForm(forms.Form):
    new_password1 = forms.CharField(widget=forms.PasswordInput, label='New password')
    new_password2 = forms.CharField(widget=forms.PasswordInput, label='Confirm password')

    def clean_new_password1(self):
        password = self.cleaned_data.get('new_password1')
        if password:
            try:
                validate_password(password)
            except forms.ValidationError as error:
                raise forms.ValidationError(error.messages)
        return password

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('new_password1')
        p2 = cleaned_data.get('new_password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Passwords do not match.')
        return cleaned_data