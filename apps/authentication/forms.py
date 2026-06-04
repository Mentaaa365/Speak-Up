# apps/authentication/forms.py
from django import forms
from django.contrib.auth.models import User
import re

class RegistroForm(forms.Form):
    # Usamos los mismos nombres (name attributes) que tienes en tu HTML
    first_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    institution = forms.CharField(max_length=100)

    def clean_first_name(self):
        nombre = self.cleaned_data.get('first_name')
        # Replicamos tu validación Regex exacta
        if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', nombre):
            raise forms.ValidationError('El nombre no puede contener números o símbolos.')
        return nombre

    def clean_email(self):
        correo = self.cleaned_data.get('email')
        # Replicamos tu validación de correo duplicado
        if User.objects.filter(username=correo).exists():
            raise forms.ValidationError('Duplicado') # La palabra clave para capturarla en la vista
        return correo