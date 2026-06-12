from django.db import models


class IntentoEjercicio(models.Model):
    perfil = models.ForeignKey(
        "authentication.Perfil", on_delete=models.CASCADE, related_name="intentos"
    )
    ejercicio = models.ForeignKey(
        "curriculum.Ejercicio", on_delete=models.CASCADE, related_name="intentos"
    )
    puntaje = models.DecimalField(max_digits=5, decimal_places=2)
    activo = models.BooleanField(default=True)
    fecha_completado = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["perfil", "ejercicio", "activo"],
                name="ix_intento_perfil_ej_activo",
            ),
        ]
