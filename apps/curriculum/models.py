from django.db import models


class NivelMCER(models.Model):
    codigo = models.CharField(max_length=2, unique=True, db_index=True)
    parametros_json = models.JSONField(default=dict)
    orden = models.IntegerField(unique=True)

    def __str__(self):
        return self.codigo


class Submodulo(models.Model):
    nivel = models.ForeignKey(
        NivelMCER, on_delete=models.CASCADE, related_name="submodulos"
    )
    tipo = models.CharField(max_length=50)
    orden = models.IntegerField()

    class Meta:
        indexes = [
            models.Index(fields=["nivel", "orden"]),
        ]


class Ejercicio(models.Model):
    submodulo = models.ForeignKey(
        Submodulo, on_delete=models.CASCADE, related_name="ejercicios"
    )
    contenido_json = models.JSONField(default=dict,blank=True)
    nivel_dificultad = models.CharField(max_length=2)
    texto_objetivo = models.TextField()
