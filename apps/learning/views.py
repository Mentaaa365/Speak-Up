import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from apps.authentication.models import Perfil
from apps.curriculum.models import Ejercicio, Submodulo
from apps.learning.models import SesionEntrevista


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


class AiInterviewLearningView(LoginRequiredMixin, View):
    """
    HU-05 / RF-05: AI oral interview session view.

    Guard 1: no Perfil row for the user -> redirect to authentication:login.
    Guard 2: active nivel has no 'entrevista' Submodulo -> redirect to progress:dashboard.

    On GET: abandons any prior EN_CURSO session (append-only audit trail),
    creates a fresh EN_CURSO session, and renders the interview template
    with level-specific parameters.
    """

    template_name = 'learning/ai_interview.html'

    # Level-specific parameters
    _TTS_RATE = {'A1': 0.85, 'A2': 1.0, 'B1': 1.0}
    _TIEMPO_RESPUESTA = {'A1': 45, 'A2': 30, 'B1': 60}

    def get(self, request, *args, **kwargs):
        # Guard 1: Perfil must exist for this user
        try:
            perfil = Perfil.objects.select_related('nivel_mcer').get(usuario=request.user)
        except Perfil.DoesNotExist:
            return redirect('authentication:login')

        # Guard 2: nivel must have an 'entrevista' submodulo
        submodulo = Submodulo.objects.filter(
            nivel=perfil.nivel_mcer, tipo='entrevista'
        ).first()
        if submodulo is None:
            return redirect('progress:dashboard')

        # Abandon any prior EN_CURSO session (append-only: never delete rows)
        SesionEntrevista.objects.filter(
            perfil=perfil, submodulo=submodulo, estado='EN_CURSO'
        ).update(estado='ABANDONADA')

        # Create a fresh EN_CURSO session
        sesion = SesionEntrevista.objects.create(
            perfil=perfil,
            submodulo=submodulo,
            estado='EN_CURSO',
        )

        nivel_codigo = perfil.nivel_mcer.codigo

        context = {
            'submodulo': submodulo,
            'nivel': perfil.nivel_mcer,
            'sesion_id': sesion.pk,
            'nivel_codigo': nivel_codigo,
            'tts_rate': self._TTS_RATE.get(nivel_codigo, 1.0),
            'tiempo_respuesta': self._TIEMPO_RESPUESTA.get(nivel_codigo, 45),
            'turno_url': reverse('learning:interview_turno'),
            'finalizar_url': reverse('learning:interview_finalizar'),
        }
        return render(request, self.template_name, context)


class TurnoEntrevistaView(LoginRequiredMixin, View):
    """
    WU-5b stub: POST /learning/ai-interview/turno/
    Returns 501 until WU-5b implements the full turn logic.
    """

    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        return JsonResponse({'error': 'not_implemented'}, status=501)


class FinalizarEntrevistaView(LoginRequiredMixin, View):
    """
    WU-5b stub: POST /learning/ai-interview/finalizar/
    Returns 501 until WU-5b implements the full finalize logic.
    """

    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        return JsonResponse({'error': 'not_implemented'}, status=501)
