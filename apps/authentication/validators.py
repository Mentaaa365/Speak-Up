# apps/authentication/validators.py
import re
from django.core.exceptions import ValidationError

class SpeakUpPasswordValidator:
    def validate(self, password, user=None):
        if len(password) < 8:
            raise ValidationError("La contraseña debe tener al menos 8 caracteres.")
        if not re.search(r'[A-Z]', password):
            raise ValidationError("Debe incluir al menos una letra mayúscula.")
        if not re.search(r'\d', password):
            raise ValidationError("Debe incluir al menos un número.")
        

    def get_help_text(self):
        return "Tu contraseña debe contener al menos 8 caracteres, una mayúscula, un número y un símbolo especial."