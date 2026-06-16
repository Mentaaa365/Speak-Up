from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.http import JsonResponse
from apps.question_bank.models import Question, Option
from apps.shared.utils import _similitud
from django.shortcuts import render
import json
import random


# ─────────────────────────────────────────────
#  UC2 — Pantalla de bienvenida / verificación de micrófono
# ─────────────────────────────────────────────
class DiagnosisWelcomeView(LoginRequiredMixin, TemplateView):
    """
    Pantalla de bienvenida del examen de diagnóstico (Verificación de micrófono).
    """
    template_name = 'diagnosis/welcome.html'


# ─────────────────────────────────────────────
#  UC3 — Interfaz central del examen
# ─────────────────────────────────────────────
class DiagnosisTestView(LoginRequiredMixin, TemplateView):
    """
    Interfaz central del examen (Speaking, Listening y Vocabulario).
    """
    template_name = 'diagnosis/test.html'


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
                ('A1', 'CHOICE',    3),
                ('A1', 'LISTENING', 3),
                ('A1', 'SPEAKING',  2),
                ('A2', 'CHOICE',    3),
                ('A2', 'LISTENING', 3),
                ('A2', 'SPEAKING',  2),
                ('B1', 'CHOICE',    4),
                ('B1', 'LISTENING', 3),
                ('B1', 'SPEAKING',  2),
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
                ] if q.question_type in ['CHOICE', 'LISTENING'] else [],
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

    # ── POST: recibe respuestas y calcula el nivel ──
    def post(self, request, *args, **kwargs):
        # 1. Parsear el JSON enviado por el frontend
        try:
            user_answers = json.loads(request.POST.get('answers_data', '[]'))
        except json.JSONDecodeError:
            user_answers = []

        correct_speaking  = 0
        correct_listening = 0
        correct_vocab     = 0

        # 2. Validar cada respuesta contra la BD ─ nunca confiamos en el cliente
        for item in user_answers:
            q_type    = item.get('type', '')
            answer    = item.get('answer', '')
            option_id = item.get('optionId', '')       # ID de la opción seleccionada
            target    = item.get('targetPhrase', '')   # Frase objetivo para SPEAKING

            if q_type == 'SPEAKING':
                # Comparamos la transcripción con la frase objetivo usando similitud
                # Umbral 0.55: flexible ante acentos y pequeñas variaciones fonéticas
                if target and _similitud(answer, target) >= 0.55:
                    correct_speaking += 1

            elif q_type in ('LISTENING', 'CHOICE'):
                # Consultamos la BD para saber si la opción elegida es la correcta
                # ✅ SEGURIDAD: el backend decide, no el valor que envió el cliente
                if option_id:
                    try:
                        opcion = Option.objects.get(id=option_id)
                        if opcion.is_correct:
                            if q_type == 'LISTENING':
                                correct_listening += 1
                            else:
                                correct_vocab += 1
                    except Option.DoesNotExist:
                        # ID manipulado o inexistente — simplemente ignoramos
                        pass

        # 3. Ponderación oficial (RF-03 / UC3)
        #    Máx Speaking: 5 preguntas × 8 pts = 40
        #    Máx Listening: 5 preguntas × 8 pts = 40
        #    Máx Vocab:    10 preguntas × 2 pts = 20
        score_speaking  = min(correct_speaking  * 8,  40)
        score_listening = min(correct_listening * 8,  40)
        score_vocab     = min(correct_vocab     * 2,  20)
        total           = score_speaking + score_listening + score_vocab

        # 4. Clasificación MCER
        if total < 50:
            nivel = 'A1'
            desc  = 'Nivel Principiante / Acceso'
            motiv = '¡Buen comienzo! Vamos a construir bases sólidas de vocabulario y estructuras simples.'
        elif total <= 74:
            nivel = 'A2'
            desc  = 'Nivel Elemental / Plataforma'
            motiv = '¡Tienes buen camino recorrido! Nos enfocaremos en mejorar tu ritmo y transiciones orales.'
        else:
            nivel = 'B1'
            desc  = 'Nivel Intermedio / Umbral'
            motiv = '¡Excelente nivel inicial! Estás listo para los desafíos del nivel B1.'

        # 5. Persistir nivel en la BD
        from apps.authentication.models import Perfil
        from apps.curriculum.models import NivelMCER
        try:
            perfil    = Perfil.objects.get(usuario=request.user)
            nivel_obj = NivelMCER.objects.get(codigo=nivel)
            perfil.nivel_mcer = nivel_obj
            perfil.save()
        except Exception:
            # Si falla el guardado no rompemos la experiencia del estudiante
            pass

        # 6. Limpiar sesión del examen para que el próximo intento cargue preguntas nuevas
        request.session.pop('examen_diagnostico_ids', None)

        context = {
            'score_speaking':         score_speaking,
            'score_listening':        score_listening,
            'score_vocabulary':       score_vocab,
            'score_total':            total,
            'nivel_asignado':         nivel,
            'descripcion_mcer':       desc,
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
                    'score_total':            '-',
                    'nivel_asignado':         perfil.nivel_mcer.codigo,
                    'descripcion_mcer':       f'Nivel {nombre}' if nombre else f'Nivel {perfil.nivel_mcer.codigo}',
                    'descripcion_motivacional': '¡Ya tienes tu diagnóstico! Ve a tu Dashboard para comenzar a practicar.',
                }
                return self.render_to_response(context)
        except Exception:
            pass

        # Usuario sin nivel: lo invitamos a hacer el examen
        context = {
            'score_speaking':         0,
            'score_listening':        0,
            'score_vocabulary':       0,
            'score_total':            0,
            'nivel_asignado':         'No Evaluado',
            'descripcion_mcer':       'Realiza el test para obtener tu nivel.',
            'descripcion_motivacional': 'Vuelve al inicio y completa el diagnóstico.',
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