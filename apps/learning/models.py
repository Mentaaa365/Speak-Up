from django.db import models


class SesionEntrevista(models.Model):
    perfil = models.ForeignKey(
        "authentication.Perfil", on_delete=models.CASCADE, related_name="entrevistas"
    )
    submodulo = models.ForeignKey(
        "curriculum.Submodulo",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    transcripcion_json = models.JSONField(default=dict)
    puntaje = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    estado = models.CharField(max_length=20, default="EN_CURSO")
    iniciada_en = models.DateTimeField(auto_now_add=True)
    finalizada_en = models.DateTimeField(null=True, blank=True)
