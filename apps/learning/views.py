from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render

class VocabularyLearningView(LoginRequiredMixin, TemplateView):
    """
    HU-04 / RF-04: Gestiona de forma parametrizada los submódulos de Vocabulario y Lectura.
    Evalúa precisión fonética usando STT y resalta los errores.
    """
    template_name = 'learning/vocabulary.html'

class MusicLearningView(LoginRequiredMixin, TemplateView):
    """
    HU-04 / RF-04: Gestiona de forma parametrizada las actividades musicales
    con reproducción de letra sincronizada (LRC) y pausas automáticas.
    """
    template_name = 'learning/music.html'

class AiInterviewLearningView(LoginRequiredMixin, TemplateView):
    """
    HU-05 / RF-05: Administra las sesiones de conversación oral con el agente IA.
    Carga dinámicamente los parámetros de complejidad, tiempos de respuesta y transcripción.
    """
    template_name = 'learning/ai_interview.html'