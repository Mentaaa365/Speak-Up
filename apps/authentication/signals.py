from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.authentication.models import Perfil


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def manejar_perfil_usuario(sender, instance, created, **kwargs):
    if created:
        # Si el usuario es nuevo, se crea el perfil
        Perfil.objects.create(usuario=instance)
    else:
        # Si el usuario ya existe (ej. al hacer login), solo guarda si tiene perfil
        if hasattr(instance, "perfil"):
            instance.perfil.save()
