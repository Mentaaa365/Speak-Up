import hashlib
import json
import random
import uuid
from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import TemplateView

from apps.authentication.models import Perfil
from apps.curriculum.models import NivelMCER
from apps.exams.models import Certificado, ExamenIntento
from apps.learning.models import SesionEntrevista
from apps.progress.models import IntentoEjercicio
from apps.question_bank.models import Option, Question
from apps.shared.utils import _similitud


class ExamStartView(LoginRequiredMixin, View):
    template_name = 'exams/exam.html'

    def get(self, request, *args, **kwargs):
        # Guard 1: profile must exist and have a nivel assigned
        try:
            perfil = Perfil.objects.get(usuario=request.user)
        except Perfil.DoesNotExist:
            return redirect(reverse_lazy('diagnosis:welcome'))

        if not perfil.nivel_mcer:
            return redirect(reverse_lazy('diagnosis:welcome'))

        nivel_activo = perfil.nivel_mcer

        # Guard 2: already has a Certificado (B1 passed) → show it
        if Certificado.objects.filter(examen__perfil=perfil).exists():
            return redirect(reverse_lazy('exams:certificate'))

        # Guard 3: already has an approved attempt for this nivel → already promoted
        if ExamenIntento.objects.filter(
            perfil=perfil,
            nivel_objetivo=nivel_activo,
            tipo__in=['PROMOCION', 'CERTIFICACION'],
            aprobado=True,
        ).exists():
            return redirect(reverse_lazy('progress:dashboard'))

        # Guard 4: attempt limit (2) reached — count only active attempts
        active_count = ExamenIntento.objects.filter(
            perfil=perfil,
            nivel_objetivo=nivel_activo,
            tipo__in=['PROMOCION', 'CERTIFICACION'],
            activo=True,
        ).count()
        if active_count >= 2:
            return render(request, self.template_name, {
                'error': 'Has agotado tus 2 intentos para este nivel.',
            })
        intentos_restantes = 2 - active_count
        is_ultimo_intento = (active_count == 1)

        # Guard 5: bank must have enough questions for this nivel
        bank = Question.objects.filter(
            bank_context='PROMOTION_EXAM',
            level=nivel_activo.codigo,
        )
        if (
            bank.filter(question_type='SPEAKING').count() < 5
            or bank.filter(question_type='LISTENING').count() < 5
            or bank.filter(question_type='CHOICE').count() < 10
        ):
            return render(request, self.template_name, {
                'error': 'Este examen aún no tiene preguntas configuradas. Inténtalo más tarde.',
            })

        # Determine tipo: CERTIFICACION when no next nivel exists
        nivel_siguiente = NivelMCER.objects.filter(
            orden__gt=nivel_activo.orden
        ).order_by('orden').first()
        tipo = 'CERTIFICACION' if nivel_siguiente is None else 'PROMOCION'

        # Question selection — session-cached so reloads don't reshuffle
        preguntas_ids = request.session.get('examen_promocion_ids')
        if not preguntas_ids:
            seleccion = []
            for q_type, cantidad in [('SPEAKING', 5), ('LISTENING', 5), ('CHOICE', 10)]:
                grupo = list(
                    Question.objects.filter(
                        bank_context='PROMOTION_EXAM',
                        level=nivel_activo.codigo,
                        question_type=q_type,
                    ).order_by('?')[:cantidad]
                )
                seleccion.extend(grupo)
            random.shuffle(seleccion)
            preguntas_ids = [str(q.id) for q in seleccion]
            request.session['examen_promocion_ids'] = preguntas_ids
            preguntas_seleccionadas = seleccion
        else:
            preguntas_seleccionadas = []
            for p_id in preguntas_ids:
                try:
                    preguntas_seleccionadas.append(Question.objects.get(id=p_id))
                except Question.DoesNotExist:
                    continue

        preguntas_payload = [{
            'id': str(q.id),
            'type': q.question_type,
            'text': q.text,
            'audioText': q.audio_text or '',
            'targetPhrase': q.target_phrase or '',
            'options': [{'id': str(o.id), 'text': o.text} for o in q.options.all()]
                        if q.question_type in ('CHOICE', 'LISTENING') else [],
        } for q in preguntas_seleccionadas]

        return render(request, self.template_name, {
            'nivel_activo': nivel_activo,
            'nivel_siguiente': nivel_siguiente,
            'tipo': tipo,
            'preguntas': preguntas_seleccionadas,
            'preguntas_json': json.dumps(preguntas_payload),
            'intentos_restantes': intentos_restantes,
            'is_ultimo_intento': is_ultimo_intento,
        })

    def post(self, request, *args, **kwargs):
        try:
            perfil = Perfil.objects.get(usuario=request.user)
        except Perfil.DoesNotExist:
            return redirect(reverse_lazy('diagnosis:welcome'))

        nivel_activo = perfil.nivel_mcer
        if not nivel_activo:
            return redirect(reverse_lazy('diagnosis:welcome'))

        nivel_siguiente = NivelMCER.objects.filter(
            orden__gt=nivel_activo.orden
        ).order_by('orden').first()
        tipo = 'CERTIFICACION' if nivel_siguiente is None else 'PROMOCION'

        try:
            user_answers = json.loads(request.POST.get('answers_data', '[]'))
        except json.JSONDecodeError:
            user_answers = []

        correct_speaking = 0
        correct_listening = 0
        correct_choice = 0

        for item in user_answers:
            q_type = item.get('type', '')
            answer = item.get('answer', '')
            target = item.get('targetPhrase', '')
            option_id = item.get('optionId', '')

            if q_type == 'SPEAKING':
                if target and _similitud(answer, target) >= 0.55:
                    correct_speaking += 1
            elif q_type in ('LISTENING', 'CHOICE'):
                if option_id:
                    try:
                        opt = Option.objects.get(id=option_id)
                        if opt.is_correct:
                            if q_type == 'LISTENING':
                                correct_listening += 1
                            else:
                                correct_choice += 1
                    except Option.DoesNotExist:
                        pass

        puntaje = Decimal(
            min(correct_speaking * 8, 40)
            + min(correct_listening * 8, 40)
            + min(correct_choice * 2, 20)
        )
        aprobado = puntaje >= Decimal('80')

        score_speaking = min(correct_speaking * 8, 40)
        score_listening = min(correct_listening * 8, 40)
        score_choice = min(correct_choice * 2, 20)

        intento = ExamenIntento.objects.create(
            perfil=perfil,
            tipo=tipo,
            nivel_objetivo=nivel_activo,
            puntaje=puntaje,
            aprobado=aprobado,
        )

        reset_realizado = False

        if aprobado:
            if tipo == 'PROMOCION' and nivel_siguiente:
                perfil.nivel_mcer = nivel_siguiente
                perfil.save()
            elif tipo == 'CERTIFICACION':
                Certificado.objects.create(
                    examen=intento,
                    codigo_hash=hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest(),
                    nivel=nivel_activo,
                )
        else:
            # Check if soft reset is needed (2 active failed attempts)
            active_count = ExamenIntento.objects.filter(
                perfil=perfil,
                nivel_objetivo=nivel_activo,
                tipo__in=['PROMOCION', 'CERTIFICACION'],
                activo=True,
            ).count()

            if active_count >= 2:
                with transaction.atomic():
                    IntentoEjercicio.objects.filter(
                        perfil=perfil,
                        ejercicio__submodulo__nivel=nivel_activo,
                        activo=True,
                    ).update(activo=False)

                    SesionEntrevista.objects.filter(
                        perfil=perfil,
                        submodulo__nivel=nivel_activo,
                        estado='COMPLETADA',
                    ).update(estado='ABANDONADA')

                    ExamenIntento.objects.filter(
                        perfil=perfil,
                        nivel_objetivo=nivel_activo,
                        tipo__in=['PROMOCION', 'CERTIFICACION'],
                        activo=True,
                    ).update(activo=False)

                reset_realizado = True

        request.session.pop('examen_promocion_ids', None)

        # Compute intentos_restantes AFTER potential reset
        post_active_count = ExamenIntento.objects.filter(
            perfil=perfil,
            nivel_objetivo=nivel_activo,
            tipo__in=['PROMOCION', 'CERTIFICACION'],
            activo=True,
        ).count()
        intentos_restantes = 2 - post_active_count

        return render(request, self.template_name, {
            'resultado': True,
            'aprobado': aprobado,
            'puntaje': puntaje,
            'score_speaking': score_speaking,
            'score_listening': score_listening,
            'score_choice': score_choice,
            'tipo': tipo,
            'nivel_activo': nivel_activo,
            'nivel_siguiente': nivel_siguiente,
            'intentos_restantes': intentos_restantes,
            'reset_realizado': reset_realizado,
        })


class CertificateView(LoginRequiredMixin, View):
    template_name = 'exams/certificate.html'

    def get(self, request, *args, **kwargs):
        try:
            perfil = Perfil.objects.get(usuario=request.user)
        except Perfil.DoesNotExist:
            return redirect(reverse_lazy('progress:dashboard'))

        try:
            certificado = Certificado.objects.get(examen__perfil=perfil)
        except Certificado.DoesNotExist:
            return redirect(reverse_lazy('progress:dashboard'))

        return render(request, self.template_name, {
            'certificado': certificado,
            'nivel': certificado.nivel,
            'emitido_en': certificado.emitido_en,
            'puntaje': certificado.examen.puntaje,
        })
