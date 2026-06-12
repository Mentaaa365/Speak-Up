from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q
from django.utils import timezone


class User(AbstractUser):
    """Custom user model: AbstractUser with a unique email."""

    email = models.EmailField(unique=True)

    def __str__(self):
        return self.username


class Perfil(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil"
    )
    nivel_mcer = models.ForeignKey(
        "curriculum.NivelMCER",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="perfiles",
    )
    institucion = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Perfil de {self.usuario}"


class PasswordResetToken(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reset_tokens"
    )
    token_hash = models.CharField(max_length=64, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["usuario"],
                condition=Q(used_at__isnull=True),
                name="uq_active_reset_per_user",
            )
        ]

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"PasswordResetToken({self.usuario}, expires_at={self.expires_at})"
