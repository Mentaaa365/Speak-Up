import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from apps.authentication.models import Perfil
from apps.curriculum.models import Ejercicio, Submodulo


class VocabularyLearningView(LoginRequiredMixin, View):
    """
    HU-04 / RF-04: Vocabulary submodule view.

    Guard 1: no Perfil row for the user -> redirect to login.
    Guard 2: active nivel has no 'vocabulario' Submodulo -> redirect to dashboard.
    """

    template_name = 'learning/vocabulary.html'

    def get(self, request, *args, **kwargs):
        try:
            perfil = Perfil.objects.select_related('nivel_mcer').get(usuario=request.user)
        except Perfil.DoesNotExist:
            return redirect('authentication:login')

        submodulo = (
            Submodulo.objects
            .filter(nivel=perfil.nivel_mcer, tipo='vocabulario')
            .first()
        )
        if submodulo is None:
            return redirect('progress:dashboard')

        ejercicios_qs = submodulo.ejercicios.all()

        context = {
            'submodulo': submodulo,
            'ejercicios': ejercicios_qs,
            'ejercicios_json': json.dumps([
                {'id': e.pk, 'texto_objetivo': e.texto_objetivo}
                for e in ejercicios_qs
            ]),
            'guardar_url': reverse('progress:guardar_ejercicio'),
        }
        return render(request, self.template_name, context)


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
