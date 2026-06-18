import uuid

from django.db import models


class ExamenIntento(models.Model):
    TIPO_CHOICES = [
        ("DIAGNOSTICO", "Diagnóstico"),
        ("PROMOCION", "Promoción"),
        ("CERTIFICACION", "Certificación"),
    ]

    perfil = models.ForeignKey(
        "authentication.Perfil", on_delete=models.CASCADE, related_name="examenes"
    )
    tipo = models.CharField(max_length=15, choices=TIPO_CHOICES, db_index=True)
    nivel_objetivo = models.ForeignKey(
        "curriculum.NivelMCER",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    puntaje = models.DecimalField(max_digits=5, decimal_places=2)
    aprobado = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)
    detalle_json = models.JSONField(default=dict)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["perfil", "tipo"]),
        ]


class Certificado(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    examen = models.OneToOneField(
        "exams.ExamenIntento", on_delete=models.PROTECT, related_name="certificado"
    )
    codigo_hash = models.CharField(max_length=64, unique=True, db_index=True)
    nivel = models.ForeignKey("curriculum.NivelMCER", on_delete=models.PROTECT)
    emitido_en = models.DateTimeField(auto_now_add=True)
