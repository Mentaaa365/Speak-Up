# apps/authentication/backends.py
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

class EmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        try:
            # Tratamos el 'username' que llega de tu HTML como si fuera el email
            user = UserModel.objects.get(email=username)
        except UserModel.DoesNotExist:
            return None
        
        if user.check_password(password):
            return user
        return None