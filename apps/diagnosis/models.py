from django.db import models


class DiagnosisAttempt(models.Model):
    perfil = models.ForeignKey(
        'authentication.Perfil', on_delete=models.CASCADE,
        related_name='diagnosis_attempts'
    )
    fecha = models.DateTimeField(auto_now_add=True)
    nivel_resultado = models.ForeignKey(
        'curriculum.NivelMCER', on_delete=models.PROTECT,
        related_name='diagnosis_attempts'
    )
    score_speaking  = models.DecimalField(max_digits=5, decimal_places=2)
    score_listening = models.DecimalField(max_digits=5, decimal_places=2)
    score_vocab     = models.DecimalField(max_digits=5, decimal_places=2)
    score_writing   = models.DecimalField(max_digits=5, decimal_places=2)
    score_total     = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        ordering = ['-fecha']

    def __str__(self):
        return f"DiagnosisAttempt({self.perfil}, {self.nivel_resultado}, {self.fecha})"
