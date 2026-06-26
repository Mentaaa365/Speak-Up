import json
import logging
import random

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import TemplateView

from apps.learning.writing_evaluator import AIEvaluationError, AIWritingEvaluator
from apps.question_bank.models import Option, Question
from apps.shared.scoring import (
    LISTENING_MAX, MCER_THRESHOLD_A2, MCER_THRESHOLD_B1,
    SPEAKING_MAX, VOCABULARY_MAX, WRITING_MAX,
)
from apps.shared.utils import _similitud

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  UC2 — Pantalla de bienvenida / verificación de micrófono
# ─────────────────────────────────────────────
class DiagnosisWelcomeView(LoginRequiredMixin, TemplateView):
    template_name = 'diagnosis/welcome.html'

    def dispatch(self, request, *args, **kwargs):
        from django.conf import settings
        from django.utils import timezone
        from datetime import timedelta
        from apps.authentication.models import Perfil
        try:
            perfil = Perfil.objects.get(usuario=request.user)
            if perfil.nivel_mcer:
                cooldown_days = getattr(settings, 'DIAGNOSIS_COOLDOWN_DAYS', 30)
                if perfil.fecha_ultimo_diagnostico:
                    elapsed = timezone.now() - perfil.fecha_ultimo_diagnostico
                    if elapsed.days < cooldown_days:
                        days_left = cooldown_days - elapsed.days
                        from django.contrib import messages
                        messages.warning(
                            request,
                            f"You can retake the diagnostic in {days_left} day{'s' if days_left != 1 else ''}."
                        )
                        return redirect('progress:dashboard')
                else:
                    # Has level but no fecha → first diagnosis was before this feature.
                    # Allow retake (no cooldown data).
                    pass
        except Perfil.DoesNotExist:
            pass
        return super().dispatch(request, *args, **kwargs)


class DiagnosisTestView(LoginRequiredMixin, TemplateView):
    template_name = 'diagnosis/test.html'

    def dispatch(self, request, *args, **kwargs):
        from django.conf import settings
        from django.utils import timezone
        from datetime import timedelta
        from apps.authentication.models import Perfil
        try:
            perfil = Perfil.objects.get(usuario=request.user)
            if perfil.nivel_mcer:
                cooldown_days = getattr(settings, 'DIAGNOSIS_COOLDOWN_DAYS', 30)
                if perfil.fecha_ultimo_diagnostico:
                    elapsed = timezone.now() - perfil.fecha_ultimo_diagnostico
                    if elapsed.days < cooldown_days:
                        days_left = cooldown_days - elapsed.days
                        from django.contrib import messages
                        messages.warning(
                            request,
                            f"You can retake the diagnostic in {days_left} day{'s' if days_left != 1 else ''}."
                        )
                        return redirect('progress:dashboard')
                else:
                    # Has level but no fecha → first diagnosis was before this feature.
                    # Allow retake (no cooldown data).
                    pass
        except Perfil.DoesNotExist:
            pass
        return super().dispatch(request, *args, **kwargs)


# ─────────────────────────────────────────────
#  API — Preguntas del diagnóstico (memorizadas en sesión)
# ─────────────────────────────────────────────
class APIPreguntasDiagnosticoView(LoginRequiredMixin, View):
    """
    Extrae preguntas de la BD y las memoriza en sesión para que no cambien
    si el usuario recarga la página (RNF-03).
    Retorna id, texto, tipo, audioText, targetPhrase y opciones con su id.
    """
    def get(self, request, *args, **kwargs):
        """
        Selecciona 25 preguntas distribuidas por nivel (no 15 al azar del banco total)
        para garantizar cobertura A1/A2/B1 y una clasificación MCER confiable.

        Distribución:
            A1 →  8 preguntas (3 CHOICE + 3 LISTENING + 2 SPEAKING)
            A2 →  8 preguntas (3 CHOICE + 3 LISTENING + 2 SPEAKING)
            B1 →  9 preguntas (4 CHOICE + 3 LISTENING + 2 SPEAKING)
            Total: 25 preguntas
        """
        preguntas_ids = request.session.get('examen_diagnostico_ids')

        if not preguntas_ids:
            seleccion = []

            DISTRIBUCION = [
                ('A1', 'CHOICE',    2),
                ('A1', 'LISTENING', 2),
                ('A1', 'SPEAKING',  1),
                ('A1', 'WRITING',   1),
                ('A2', 'CHOICE',    2),
                ('A2', 'LISTENING', 2),
                ('A2', 'SPEAKING',  2),
                ('A2', 'WRITING',   2),
                ('B1', 'CHOICE',    1),
                ('B1', 'LISTENING', 1),
                ('B1', 'SPEAKING',  2),
                ('B1', 'WRITING',   2),
            ]

            for level, q_type, cantidad in DISTRIBUCION:
                grupo = list(
                    Question.objects.filter(
                        level=level,
                        question_type=q_type,
                        bank_context='DIAGNOSTIC',
                    ).order_by('?')[:cantidad]
                )
                seleccion.extend(grupo)

            random.shuffle(seleccion)

            preguntas_ids = [str(p.id) for p in seleccion]
            request.session['examen_diagnostico_ids'] = preguntas_ids
            preguntas_seleccionadas = seleccion

        else:
            preguntas_seleccionadas = []
            for p_id in preguntas_ids:
                try:
                    preguntas_seleccionadas.append(Question.objects.get(id=p_id))
                except Question.DoesNotExist:
                    continue

        questions_array = []
        for q in preguntas_seleccionadas:
            pregunta_dict = {
                'id':           str(q.id),
                'level':        q.level,
                'type':         q.question_type,
                'text':         q.text,
                'audioText':    q.audio_text    or '',
                'targetPhrase': q.target_phrase or '',
                'options': [
                    {'id': str(opt.id), 'text': opt.text}
                    for opt in q.options.all()
                ] if q.question_type in ('CHOICE', 'LISTENING') else [],
            }
            questions_array.append(pregunta_dict)

        return JsonResponse({'questions': questions_array})
    

# ─────────────────────────────────────────────
#  UC3 — Procesamiento y resultados del diagnóstico
# ─────────────────────────────────────────────
class DiagnosisResultsView(LoginRequiredMixin, TemplateView):
    """
    Procesa y muestra los resultados ponderados calculados en el servidor (RF-03).
    Ponderación: Speaking 40 % | Listening 40 % | Vocabulario 20 %
    """
    template_name = 'diagnosis/results.html'

    def post(self, request, *args, **kwargs):
        try:
            user_answers = json.loads(request.POST.get('answers_data', '[]'))
        except json.JSONDecodeError:
            user_answers = []

        correct_speaking = 0
        correct_listening = 0
        correct_vocab = 0
        total_speaking = 0
        total_listening = 0
        total_vocab = 0
        writing_items = []

        for item in user_answers:
            q_type = item.get('type', '')
            answer = item.get('answer', '')
            option_id = item.get('optionId', '')
            target = item.get('targetPhrase', '')

            if q_type == 'SPEAKING':
                total_speaking += 1
                if target and _similitud(answer, target) >= 0.55:
                    correct_speaking += 1

            elif q_type == 'LISTENING':
                total_listening += 1
                if option_id:
                    try:
                        if Option.objects.get(id=option_id).is_correct:
                            correct_listening += 1
                    except Option.DoesNotExist:
                        pass

            elif q_type == 'CHOICE':
                total_vocab += 1
                if option_id:
                    try:
                        if Option.objects.get(id=option_id).is_correct:
                            correct_vocab += 1
                    except Option.DoesNotExist:
                        pass

            elif q_type == 'WRITING':
                q_id = item.get('questionId', '')
                try:
                    q_obj = Question.objects.get(id=q_id)
                    writing_items.append({'text': answer, 'prompt': q_obj.text, 'level': q_obj.level})
                except Question.DoesNotExist:
                    writing_items.append({'text': answer, 'prompt': '', 'level': ''})

        score_speaking = round(correct_speaking / total_speaking * SPEAKING_MAX) if total_speaking else 0
        score_listening = round(correct_listening / total_listening * LISTENING_MAX) if total_listening else 0
        score_vocab = round(correct_vocab / total_vocab * VOCABULARY_MAX) if total_vocab else 0

        writing_pending = False
        score_writing = 0
        if writing_items:
            nivel_guess = writing_items[0].get('level', 'A1') or 'A1'
            batch_payload = [{'text': it['text'], 'prompt': it['prompt']} for it in writing_items]
            evaluator = AIWritingEvaluator()
            for attempt in range(2):
                try:
                    results = evaluator.evaluate_batch(batch_payload, nivel_guess)
                    avg = round(sum(r['score'] for r in results) / len(results))
                    score_writing = round(avg / 100 * WRITING_MAX)
                    break
                except AIEvaluationError:
                    if attempt == 0:
                        logger.warning("Writing evaluation failed, retrying once")
                    else:
                        logger.warning("Writing evaluation failed on retry")
                        writing_pending = True
                        score_writing = 0

        total = score_speaking + score_listening + score_vocab + score_writing

        if total < MCER_THRESHOLD_A2:
            nivel = 'A1'
            desc = 'Beginner Level / Access'
            motiv = 'Great start! We will focus on building solid vocabulary foundations and simple structures.'
        elif total < MCER_THRESHOLD_B1:
            nivel = 'A2'
            desc = 'Elementary Level / Waystage'
            motiv = 'Good progress! We will focus on improving your rhythm and oral transitions.'
        else:
            nivel = 'B1'
            desc = 'Intermediate Level / Threshold'
            motiv = 'Excellent starting level! You are ready for the B1 challenges.'

        from apps.authentication.models import Perfil
        from apps.curriculum.models import NivelMCER
        from apps.diagnosis.models import DiagnosisAttempt
        from django.utils import timezone
        try:
            perfil = Perfil.objects.get(usuario=request.user)
            nivel_obj = NivelMCER.objects.get(codigo=nivel)
            perfil.nivel_mcer = nivel_obj
            perfil.fecha_ultimo_diagnostico = timezone.now()
            perfil.save(update_fields=['nivel_mcer', 'fecha_ultimo_diagnostico'])
            DiagnosisAttempt.objects.create(
                perfil=perfil,
                nivel_resultado=nivel_obj,
                score_speaking=score_speaking,
                score_listening=score_listening,
                score_vocab=score_vocab,
                score_writing=score_writing,
                score_total=total,
            )
        except Exception:
            pass

        request.session.pop('examen_diagnostico_ids', None)

        context = {
            'score_speaking': score_speaking,
            'score_listening': score_listening,
            'score_vocabulary': score_vocab,
            'score_writing': score_writing,
            'score_total': total,
            'writing_pending': writing_pending,
            'nivel_asignado': nivel,
            'descripcion_mcer': desc,
            'descripcion_motivacional': motiv,
        }
        return self.render_to_response(context)

    # ── GET: muestra resultados si el usuario ya tiene nivel asignado ──
    def get(self, request, *args, **kwargs):
        from apps.authentication.models import Perfil

        try:
            perfil = Perfil.objects.get(usuario=request.user)
            if perfil.nivel_mcer:
                nombre = perfil.nivel_mcer.parametros_json.get('nombre_descriptivo', '')
                context = {
                    'score_speaking':         '-',
                    'score_listening':        '-',
                    'score_vocabulary':       '-',
                    'score_writing':          '-',
                    'score_total':            '-',
                    'nivel_asignado':         perfil.nivel_mcer.codigo,
                    'descripcion_mcer':       f'Level {nombre}' if nombre else f'Level {perfil.nivel_mcer.codigo}',
                    'descripcion_motivacional': 'You already have your diagnosis! Go to your Dashboard to start practicing.',
                }
                return self.render_to_response(context)
        except Exception:
            pass

        context = {
            'score_speaking':         0,
            'score_listening':        0,
            'score_vocabulary':       0,
            'score_writing':          0,
            'score_total':            0,
            'nivel_asignado':         'Not Evaluated',
            'descripcion_mcer':       'Complete the diagnostic test to get your level.',
            'descripcion_motivacional': 'Go back and complete the diagnostic test.',
        }
        return self.render_to_response(context)


# ─────────────────────────────────────────────
#  Vista auxiliar (mantenla si la usas en urls.py)
# ─────────────────────────────────────────────
class DummyView(LoginRequiredMixin, TemplateView):
    template_name = 'base.html'

# ResultadosTestView fue eliminada — era una versión de prueba con
# valores hardcodeados (correct_speaking = 4, etc.) que ya no se necesita.
# Si está referenciada en urls.py, elimina esa ruta también.