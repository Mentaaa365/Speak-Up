# apps/authentication/forms.py
from django import forms
from django.contrib.auth.models import User
# 🔥 IMPORTANTE: Importa la función encargada de ejecutar los validadores de settings.py
from django.contrib.auth.password_validation import validate_password 
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