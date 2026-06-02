import uuid
from django.db import models
from django.contrib.auth.models import User

class NivelMCER(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo = models.CharField(max_length=2, unique=True)
    parametros_json = models.JSONField(default=dict)
    orden = models.IntegerField(unique=True)

    def __str__(self):
        return self.codigo

class Submodulo(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nivel = models.ForeignKey(NivelMCER, on_delete=models.CASCADE, related_name='submodulos')
    tipo = models.CharField(max_length=50)
    orden = models.IntegerField()

class Perfil(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    nivel_mcer = models.ForeignKey(NivelMCER, on_delete=models.SET_NULL, null=True, blank=True)
    institucion = models.CharField(max_length=255, blank=True, null=True)

class Ejercicio(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submodulo = models.ForeignKey(Submodulo, on_delete=models.CASCADE, related_name='ejercicios')
    contenido_json = models.JSONField(default=dict)
    nivel_dificultad = models.CharField(max_length=2)

class ProgresoPorEjercicio(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    perfil = models.ForeignKey(Perfil, on_delete=models.CASCADE, related_name='progresos')
    ejercicio = models.ForeignKey(Ejercicio, on_delete=models.CASCADE)
    puntaje = models.DecimalField(max_digits=5, decimal_places=2)
    activo = models.BooleanField(default=True)
    fecha_completado = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('perfil', 'ejercicio')