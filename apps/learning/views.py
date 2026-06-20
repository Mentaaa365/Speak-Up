import json
from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from apps.authentication.models import Perfil
from apps.curriculum.models import Ejercicio, Submodulo
from apps.learning.ai_client import AIInterviewClient
from apps.learning.models import SesionEntrevista
from apps.learning.writing_evaluator import AIEvaluationError, AIWritingEvaluator
from apps.progress.models import IntentoEjercicio
from apps.shared.utils import _submodulo_completado



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


class MusicLearningView(LoginRequiredMixin, View):
    template_name = 'learning/music.html'

    _PLAYBACK_RATE = {'A1': 0.85, 'A2': 1.0, 'B1': 1.0}

    def get(self, request, *args, **kwargs):
        # 1. Obtenemos el perfil del usuario actual
        try:
            perfil = Perfil.objects.select_related('nivel_mcer').get(usuario=request.user)
        except Perfil.DoesNotExist:
            return redirect('authentication:login')

        # 2. Buscamos el submódulo de tipo 'musica' para su nivel
        submodulo = Submodulo.objects.filter(
            nivel=perfil.nivel_mcer, 
            tipo='musica'
        ).first()

        # Si no existe el submódulo, redirigimos al dashboard
        if submodulo is None:
            return redirect('progress:dashboard')

        # 3. Extraemos los ejercicios vinculados al submódulo
        ejercicios_qs = submodulo.ejercicios.all()
        canciones_data = []

        for e in ejercicios_qs:
            # Manejamos el contenido_json (asumiendo que viene como diccionario o string)
            contenido = e.contenido_json
            if isinstance(contenido, str):
                try:
                    contenido = json.loads(contenido)
                except json.JSONDecodeError:
                    contenido = {}
            
            canciones_data.append({
                'id': e.pk,
                'titulo': e.texto_objetivo,
                'config': contenido
            })

        nivel_codigo = perfil.nivel_mcer.codigo

        context = {
            'submodulo': submodulo,
            'canciones_json': json.dumps(canciones_data),
            'nivel_codigo': nivel_codigo,
            'playback_rate': self._PLAYBACK_RATE.get(nivel_codigo, 1.0),
        }
        return render(request, self.template_name, context)


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
    WU-5b: POST /learning/ai-interview/turno/

    Accepts a JSON body with sesion_id, transcripcion, and historial.
    Verifies session ownership and state, then calls AIInterviewClient
    to produce the agent's next utterance. Persists the updated historial
    to the session and returns it alongside the agent's response.
    """

    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        try:
            body = json.loads(request.body)
        except (ValueError, TypeError):
            return JsonResponse({'error': 'invalid_payload'}, status=400)

        sesion_id = body.get('sesion_id')
        transcripcion = body.get('transcripcion', '').strip()
        historial = body.get('historial', [])

        # Both sesion_id and transcripcion are required (empty transcripcion only
        # allowed on the first turn where historial is also empty).
        if not sesion_id:
            return JsonResponse({'error': 'invalid_payload'}, status=400)

        # Fetch session and verify ownership
        try:
            sesion = SesionEntrevista.objects.select_related(
                'perfil', 'submodulo__nivel'
            ).get(pk=sesion_id)
        except SesionEntrevista.DoesNotExist:
            return JsonResponse({'error': 'not_found'}, status=404)

        perfil = Perfil.objects.get(usuario=request.user)
        if sesion.perfil != perfil:
            return JsonResponse({'error': 'forbidden'}, status=403)

        if sesion.estado != 'EN_CURSO':
            return JsonResponse({'error': 'session_not_active'}, status=409)

        nivel_codigo = sesion.submodulo.nivel.codigo
        client = AIInterviewClient()

        # First turn: start_session; subsequent turns: next_turn_for
        if not historial:
            respuesta_agente = client.start_session(nivel_codigo)
        else:
            respuesta_agente = client.next_turn_for(nivel_codigo, historial, transcripcion)

        # Build the updated historial
        nuevo_historial = list(historial)
        if historial:
            # Append student response only after the first turn
            nuevo_historial.append({'role': 'user', 'content': transcripcion})
        nuevo_historial.append({'role': 'assistant', 'content': respuesta_agente})

        # Persist partial historial to DB
        sesion.transcripcion_json = nuevo_historial
        sesion.save(update_fields=['transcripcion_json'])

        return JsonResponse({'respuesta': respuesta_agente, 'historial': nuevo_historial})


class FinalizarEntrevistaView(LoginRequiredMixin, View):
    """
    WU-5b: POST /learning/ai-interview/finalizar/

    Accepts a JSON body with sesion_id. Verifies session ownership and state,
    calls AIInterviewClient.evaluate_session on the persisted transcript, marks
    the session COMPLETADA with the resulting score, and returns evaluation
    results along with the submodulo completion flag.
    """

    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        try:
            body = json.loads(request.body)
        except (ValueError, TypeError):
            return JsonResponse({'error': 'invalid_payload'}, status=400)

        sesion_id = body.get('sesion_id')

        if not sesion_id:
            return JsonResponse({'error': 'invalid_payload'}, status=400)

        try:
            sesion = SesionEntrevista.objects.select_related(
                'perfil__nivel_mcer', 'submodulo'
            ).get(pk=sesion_id)
        except SesionEntrevista.DoesNotExist:
            return JsonResponse({'error': 'not_found'}, status=404)

        perfil = Perfil.objects.select_related('nivel_mcer').get(usuario=request.user)
        if sesion.perfil != perfil:
            return JsonResponse({'error': 'forbidden'}, status=403)

        if sesion.estado != 'EN_CURSO':
            return JsonResponse({'error': 'session_not_active'}, status=409)

        historial = sesion.transcripcion_json or []
        if not historial:
            return JsonResponse({'error': 'empty_session'}, status=400)

        nivel_codigo = perfil.nivel_mcer.codigo
        client = AIInterviewClient()

        try:
            resultado = client.evaluate_session(nivel_codigo, historial)
        except AIEvaluationError:
            return JsonResponse({'error': 'evaluation_failed'}, status=502)

        puntaje = Decimal(str(resultado['puntaje_global']))
        aprobado = puntaje >= 80

        sesion.puntaje = puntaje
        sesion.estado = 'COMPLETADA'
        sesion.finalizada_en = timezone.now()
        sesion.save(update_fields=['puntaje', 'estado', 'finalizada_en'])

        submodulo_completado = _submodulo_completado(perfil, sesion.submodulo)

        return JsonResponse({
            'aprobado': aprobado,
            'puntaje': str(puntaje),
            'scores': resultado['scores'],
            'submodulo_completado': submodulo_completado,
        })
    

class WritingLearningView(LoginRequiredMixin, View):
    template_name = 'learning/writing.html'

    def get(self, request, *args, **kwargs):
        try:
            perfil = Perfil.objects.select_related('nivel_mcer').get(usuario=request.user)
        except Perfil.DoesNotExist:
            return redirect('authentication:login')

        submodulo = Submodulo.objects.filter(
            nivel=perfil.nivel_mcer, tipo='writing'
        ).first()
        if submodulo is None:
            return redirect('progress:dashboard')

        ejercicios_qs = submodulo.ejercicios.all()

        context = {
            'submodulo': submodulo,
            'ejercicios_json': json.dumps([
                {'id': e.pk, 'prompt': e.texto_objetivo}
                for e in ejercicios_qs
            ]),
            'nivel_codigo': perfil.nivel_mcer.codigo,
        }
        return render(request, self.template_name, context)


class EvaluarEscrituraView(LoginRequiredMixin, View):
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        try:
            body = json.loads(request.body)
        except (ValueError, TypeError):
            return JsonResponse({'error': 'invalid_payload'}, status=400)

        ejercicio_id = body.get('ejercicio_id')
        texto = (body.get('texto') or '').strip()

        if not ejercicio_id or not texto:
            return JsonResponse({'error': 'invalid_payload'}, status=400)

        perfil = Perfil.objects.select_related('nivel_mcer').get(usuario=request.user)
        ejercicio = Ejercicio.objects.select_related('submodulo__nivel').filter(pk=ejercicio_id).first()

        if ejercicio is None:
            return JsonResponse({'error': 'not_found'}, status=404)
        if ejercicio.submodulo.nivel != perfil.nivel_mcer:
            return JsonResponse({'error': 'level_mismatch'}, status=403)

        IntentoEjercicio.objects.filter(
            perfil=perfil, ejercicio=ejercicio, activo=True
        ).update(activo=False)

        try:
            evaluator = AIWritingEvaluator()
            result = evaluator.evaluate(texto, perfil.nivel_mcer.codigo, ejercicio.texto_objetivo)
            puntaje = result['score']
            intento = IntentoEjercicio.objects.create(
                perfil=perfil, ejercicio=ejercicio,
                puntaje=puntaje, activo=True, transcripcion=texto,
            )
            completado = _submodulo_completado(perfil, ejercicio.submodulo)
            return JsonResponse({
                'pending': False,
                'aprobado': puntaje >= 80,
                'puntaje': puntaje,
                'grammar': result['grammar'],
                'coherence': result['coherence'],
                'vocabulary': result['vocabulary'],
                'suggestions': result['suggestions'],
                'submodulo_completado': completado,
            })
        except AIEvaluationError:
            IntentoEjercicio.objects.create(
                perfil=perfil, ejercicio=ejercicio,
                puntaje=None, activo=True, transcripcion=texto,
            )
            return JsonResponse({
                'pending': True,
                'aprobado': False,
                'puntaje': 0,
                'suggestions': 'Evaluación pendiente. Puedes reintentar más tarde.',
                'submodulo_completado': False,
            })


class MiNivelRouterView(LoginRequiredMixin, View):
    _TIPO_TO_URL = {
        'vocabulario': 'learning:vocabulary',
        'musica': 'learning:music',
        'entrevista': 'learning:ai_interview',
        'writing': 'learning:writing',
    }

    def get(self, request, *args, **kwargs):
        perfil = request.user.perfil

        for sub in perfil.nivel_mcer.submodulos.all().order_by('orden'):
            if not _submodulo_completado(perfil, sub):
                url_name = self._TIPO_TO_URL.get(sub.tipo)
                if url_name:
                    return redirect(url_name)

        return redirect('progress:dashboard')