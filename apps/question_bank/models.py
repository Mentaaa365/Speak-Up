from django.db import models
from django.db import models

class Question(models.Model):
    """
    Entidad central del Banco de Preguntas.
    Sirve tanto para el Test Diagnóstico como para los módulos A1, A2 y B1.
    """
    LEVEL_CHOICES = [
        ('DIAG', 'Test Diagnóstico'),
        ('A1', 'Nivel A1: Principiante'),
        ('A2', 'Nivel A2: Elemental'),
        ('B1', 'Nivel B1: Intermedio'),
    ]

    TYPE_CHOICES = [
        ('CHOICE', 'Gramática/Vocabulario (Opción Múltiple)'),
        ('LISTENING', 'Comprensión Auditiva (Motor TTS)'),
        ('SPEAKING', 'Pronunciación (Motor STT)'),
    ]

    level = models.CharField(
        max_length=4, 
        choices=LEVEL_CHOICES, 
        verbose_name="Nivel al que pertenece"
    )
    question_type = models.CharField(
        max_length=15, 
        choices=TYPE_CHOICES, 
        verbose_name="Tipo de Pregunta"
    )
    text = models.TextField(
        verbose_name="Texto de la pregunta (Se permite HTML para negritas o saltos de línea)"
    )

    # --- CAMPOS PARA LOS MOTORES DE VOZ (Opcionales) ---
    audio_text = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        verbose_name="Texto oculto que leerá el navegador (Para Listening)",
        help_text="Solo llenar si el tipo es Comprensión Auditiva."
    )
    target_phrase = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        verbose_name="Frase exacta a evaluar (Para Speaking)",
        help_text="Solo llenar si el tipo es Pronunciación."
    )

    class Meta:
        verbose_name = "Pregunta"
        verbose_name_plural = "Banco de Preguntas"
        ordering = ['level', 'question_type']

    def __str__(self):
        return f"[{self.level}] {self.get_question_type_display()} - {self.text[:40]}..."


class Option(models.Model):
    """
    Opciones de respuesta para las preguntas de tipo CHOICE o LISTENING.
    """
    question = models.ForeignKey(
        Question, 
        on_delete=models.CASCADE, 
        related_name='options',
        verbose_name="Pregunta asociada"
    )
    text = models.CharField(
        max_length=200, 
        verbose_name="Texto de la opción"
    )
    is_correct = models.BooleanField(
        default=False, 
        verbose_name="¿Es la respuesta correcta?"
    )

    class Meta:
        verbose_name = "Opción"
        verbose_name_plural = "Opciones"

    def __str__(self):
        return f"{self.text} ({'Correcta' if self.is_correct else 'Incorrecta'})"
