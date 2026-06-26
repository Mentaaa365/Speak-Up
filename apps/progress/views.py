from decimal import Decimal, InvalidOperation
import json

from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View

from apps.authentication.models import Perfil
from apps.curriculum.models import NivelMCER, Submodulo, Ejercicio
from apps.exams.models import ExamenIntento
from apps.progress.models import IntentoEjercicio
from apps.learning.models import SesionEntrevista
from apps.learning.prosody_evaluator import ProsodyEvaluator
from apps.learning.writing_evaluator import AIEvaluationError
from apps.shared.utils import (
    _parse_lrc_lines,
    _score_musica,
    _score_musica_ponderado,
    _score_palabra_por_palabra,
    _submodulo_completado,
)




# ─────────────────────────────────────────────────────────────────────────────
#  HU-07  RF-07 — Dashboard principal
# ─────────────────────────────────────────────────────────────────────────────

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'progress/dashboard.html'

    def get(self, request, *args, **kwargs):
        # ✅ CORRECCIÓN 1: en vez de lanzar ValueError (→ 500),
        #    redirigimos elegantemente al diagnóstico si no hay nivel.
        try:
            perfil = Perfil.objects.get(usuario=request.user)
        except Perfil.DoesNotExist:
            return redirect('diagnosis:welcome')

        if not perfil.nivel_mcer:
            return redirect('diagnosis:welcome')

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        perfil       = Perfil.objects.get(usuario=self.request.user)
        nivel_activo = perfil.nivel_mcer  # Garantizado no-nulo gracias al get()

        # ── Barra 1: Progreso Global del Sistema ─────────────────────────────
        # Cuenta TODAS las actividades superadas del sistema (no solo del nivel activo)
        total_ejercicios    = Ejercicio.objects.count()
        ejercicios_exitosos = IntentoEjercicio.objects.filter(
            perfil=perfil,
            puntaje__gte=80,
            activo=True,
        ).count()

        context['global_progress'] = (
            int((ejercicios_exitosos / total_ejercicios) * 100)
            if total_ejercicios > 0 else 0
        )

        # ── Barra 2: Niveles MCER con estado real ────────────────────────────
        # ✅ CORRECCIÓN 2: sub_completados calculado desde la BD, no hardcodeado.
        #    Mientras los submódulos/ejercicios no existan en la BD el valor será 0,
        #    pero nunca mentirá al mostrar "1 de 3" de forma fija.
        niveles_db   = NivelMCER.objects.all().order_by('orden')
        niveles_data = []

        for nivel in niveles_db:
            if nivel.orden < nivel_activo.orden:
                estado          = 'completado'
                sub_completados = nivel.submodulos.count()   # todos los suyos
                progreso        = 100

            elif nivel.orden == nivel_activo.orden:
                estado          = 'activo'
                sub_completados = sum(1 for sub in nivel.submodulos.all() if _submodulo_completado(perfil, sub))
                total_subs      = nivel.submodulos.count()
                progreso        = (
                    int((sub_completados / total_subs) * 100)
                    if total_subs > 0 else 0
                )

            else:
                estado          = 'bloqueado'
                sub_completados = 0
                progreso        = 0

            niveles_data.append({
                'codigo':          nivel.codigo,
                'nombre':          nivel.parametros_json.get('nombre_descriptivo', 'Nivel'),
                'estado':          estado,
                'sub_completados': sub_completados,
                'total_subs':      nivel.submodulos.count(),
                'progreso':        progreso,
            })

        context['niveles']       = niveles_data
        context['nivel_activo']  = nivel_activo   # ✅ CORRECCIÓN 3: disponible en template
                                                   #    para la sidebar ("Nivel A2 activo")

        # ── Barra 3: Submódulos del nivel activo ─────────────────────────────
        # ✅ CORRECCIÓN 4: datos reales desde BD en vez de lista hardcodeada.
        #    Si la BD todavía no tiene submódulos, muestra lista vacía sin romper.
        # ── Barra 3: Submódulos del nivel activo ─────────────────────────────
        TIPO_A_NOMBRE = {
            'vocabulario': ('Vocabulary and Reading',  '📖', reverse_lazy('learning:vocabulary')),
            'musica':      ('Music Activities (LRC)',  '🎵', reverse_lazy('learning:music')),
            'entrevista':  ('AI Oral Interviews',      '🤖', reverse_lazy('learning:ai_interview')),
            'writing':     ('AI Writing',              '✍️', reverse_lazy('learning:writing')),
        }
        submodulos_data = []

        # 🔥 VARIABLE NUEVA: Iniciamos asumiendo que el "anterior" está listo para abrir el primero
        submodulo_anterior_completado = True

        for submodulo in nivel_activo.submodulos.all().order_by('orden'):
            nombre, icono, url = TIPO_A_NOMBRE.get(
                submodulo.tipo,
                (submodulo.tipo.capitalize(), '📌', '#')
            )

            if submodulo.tipo == 'entrevista':
                aprobadas = SesionEntrevista.objects.filter(
                    perfil=perfil,
                    submodulo=submodulo,
                    estado='COMPLETADA',
                    puntaje__gte=80,
                ).count()
                completado   = aprobadas >= 1
                progreso_sub = 100 if completado else 0
            else:
                total_ej  = submodulo.ejercicios.count()
                aprobados = IntentoEjercicio.objects.filter(
                    perfil=perfil,
                    ejercicio__submodulo=submodulo,
                    puntaje__gte=80,
                    activo=True,
                ).count()
                progreso_sub = int((aprobados / total_ej) * 100) if total_ej > 0 else 0
                completado   = total_ej > 0 and aprobados >= total_ej

            if completado:
                estado  = 'completado'
                detalle = 'Completed at 100%.'
            elif submodulo_anterior_completado:
                estado  = 'activo'
                if submodulo.tipo == 'entrevista':
                    detalle = 'Complete 1 AI oral interview.'
                else:
                    detalle = f'{aprobados} of {total_ej} exercises passed.'
            else:
                estado  = 'bloqueado'
                detalle = 'Complete the previous submodule to unlock.'

            submodulo_anterior_completado = completado

            submodulos_data.append({
                'nombre':   nombre,
                'icono':    icono,
                'estado':   estado,
                'progreso': progreso_sub,
                'detalle':  detalle,
                'url':      url,
            })

        context['submodulos'] = submodulos_data

        # ── Examen de promoción ───────────────────────────────────────────────
        # ✅ CORRECCIÓN 5: título dinámico correcto según nivel activo y siguiente
        try:
            nivel_siguiente = NivelMCER.objects.get(orden=nivel_activo.orden + 1)
            titulo_examen   = f"Examen de Promoción {nivel_activo.codigo} → {nivel_siguiente.codigo}"
        except NivelMCER.DoesNotExist:
            titulo_examen   = f"Examen de Certificación {nivel_activo.codigo}"

        # El examen está disponible solo si los 3 submódulos del nivel activo
        # están completados (todos con puntaje >= 80, activo=True)
        total_subs_activo = nivel_activo.submodulos.count()
        subs_completados  = sum(1 for sub in nivel_activo.submodulos.all() if _submodulo_completado(perfil, sub))
        examen_disponible = total_subs_activo > 0 and subs_completados >= total_subs_activo

        intentos_usados = ExamenIntento.objects.filter(
            perfil=perfil,
            nivel_objetivo=nivel_activo,
            tipo__in=['PROMOCION', 'CERTIFICACION'],
        ).count()

        context['examen'] = {
            'disponible':         examen_disponible,
            'intentos_restantes': max(0, 2 - intentos_usados),
            'titulo':             titulo_examen,
            'url':                reverse_lazy('exams:start'),
        }

        return context


# ─────────────────────────────────────────────────────────────────────────────
#  HU-07  RF-07 — Desglose analítico (3 barras independientes)
# ─────────────────────────────────────────────────────────────────────────────

class ProgressDetailView(LoginRequiredMixin, TemplateView):
    """
    Muestra el desglose analítico con las 3 barras de progreso independientes (RF-07).
    """
    template_name = 'progress/progress_detail.html'

    def get(self, request, *args, **kwargs):
        # Misma protección que DashboardView
        try:
            perfil = Perfil.objects.get(usuario=request.user)
        except Perfil.DoesNotExist:
            return redirect('diagnosis:welcome')

        if not perfil.nivel_mcer:
            return redirect('diagnosis:welcome')

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        perfil       = Perfil.objects.get(usuario=self.request.user)
        nivel_activo = perfil.nivel_mcer

        # ── Barra 1: Global ───────────────────────────────────────────────────
        total_ejercicios    = Ejercicio.objects.count()
        ejercicios_exitosos = IntentoEjercicio.objects.filter(
            perfil=perfil, puntaje__gte=80, activo=True
        ).count()

        context['global_progress'] = (
            int((ejercicios_exitosos / total_ejercicios) * 100)
            if total_ejercicios > 0 else 0
        )
        context['ejercicios_exitosos'] = ejercicios_exitosos
        context['total_ejercicios']    = total_ejercicios

        from apps.learning.models import SesionEntrevista
        context['entrevistas_completadas'] = SesionEntrevista.objects.filter(
            perfil=perfil, estado='COMPLETADA', puntaje__gte=80,
        ).count()
        context['niveles_completados'] = NivelMCER.objects.filter(
            orden__lt=nivel_activo.orden,
        ).count()
        context['total_niveles'] = NivelMCER.objects.count()

        # ── Barra 2: Por nivel MCER ───────────────────────────────────────────
        niveles_db   = NivelMCER.objects.all().order_by('orden')
        niveles_data = []

        for nivel in niveles_db:
            total_subs      = nivel.submodulos.count()
            sub_completados = sum(1 for sub in nivel.submodulos.all() if _submodulo_completado(perfil, sub))

            if nivel.orden < nivel_activo.orden:
                estado   = 'completado'
                progreso = 100
            elif nivel.orden == nivel_activo.orden:
                estado   = 'activo'
                progreso = int((sub_completados / total_subs) * 100) if total_subs > 0 else 0
            else:
                estado   = 'bloqueado'
                progreso = 0

            niveles_data.append({
                'codigo':          nivel.codigo,
                'nombre':          nivel.parametros_json.get('nombre_descriptivo', 'Nivel'),
                'estado':          estado,
                'sub_completados': sub_completados,
                'total_subs':      total_subs,
                'progreso':        progreso,
            })

        context['niveles']      = niveles_data
        context['nivel_activo'] = nivel_activo

        # ── Barra 3: Por submódulo del nivel activo ───────────────────────────
        TIPO_A_NOMBRE = {
            'vocabulario': ('Vocabulary and Reading',  '📖'),
            'musica':      ('Music Activities (LRC)',  '🎵'),
            'entrevista':  ('AI Oral Interviews',      '🤖'),
            'writing':     ('AI Writing',              '✍️'),
        }
        submodulos_data = []

        for submodulo in nivel_activo.submodulos.all().order_by('orden'):
            total_ej  = submodulo.ejercicios.count()
            aprobados = IntentoEjercicio.objects.filter(
                perfil=perfil,
                ejercicio__submodulo=submodulo,
                puntaje__gte=80,
                activo=True,
            ).count()

            nombre, icono = TIPO_A_NOMBRE.get(
                submodulo.tipo,
                (submodulo.tipo.capitalize(), '📌')
            )
            submodulos_data.append({
                'nombre':      nombre,
                'icono':       icono,
                'aprobados':   aprobados,
                'total':       total_ej,
                'progreso':    int((aprobados / total_ej) * 100) if total_ej > 0 else 0,
                'completado':  total_ej > 0 and aprobados >= total_ej,
            })

        context['submodulos'] = submodulos_data

        from apps.diagnosis.models import DiagnosisAttempt
        context['diagnosis_attempts'] = DiagnosisAttempt.objects.filter(
            perfil=perfil
        ).select_related('nivel_resultado').order_by('-fecha')

        return context


# ─────────────────────────────────────────────────────────────────────────────
#  RF-04 — Vocabulary exercise attempt endpoint
# ─────────────────────────────────────────────────────────────────────────────

class GuardarEjercicioView(LoginRequiredMixin, View):
    http_method_names = ['post']  # GET -> 405 automatically

    def post(self, request, *args, **kwargs):
        try:
            body = json.loads(request.body)
            ejercicio_id = body['ejercicio_id']
        except (json.JSONDecodeError, KeyError):
            return JsonResponse({'error': 'invalid_payload'}, status=400)

        perfil = Perfil.objects.select_related('nivel_mcer').get(usuario=request.user)
        ejercicio = (Ejercicio.objects
                     .select_related('submodulo__nivel')
                     .filter(pk=ejercicio_id).first())
        if ejercicio is None:
            return JsonResponse({'error': 'not_found'}, status=404)
        if ejercicio.submodulo.nivel != perfil.nivel_mcer:
            return JsonResponse({'error': 'level_mismatch'}, status=403)

        tipo = ejercicio.submodulo.tipo
        transcripcion = body.get('transcripcion')

        if tipo == 'vocabulario':
            if not transcripcion or not transcripcion.strip():
                return JsonResponse({'error': 'transcripcion_required'}, status=400)
            puntaje = Decimal(
                _score_palabra_por_palabra(transcripcion, ejercicio.texto_objetivo)
            )

        elif tipo == 'musica':
            line_transcriptions = body.get('line_transcriptions')
            if not isinstance(line_transcriptions, dict) or not line_transcriptions:
                return JsonResponse({'error': 'line_transcriptions_required'}, status=400)
            lrc_text = (ejercicio.contenido_json or {}).get('lrc', '')
            precision = _score_musica(line_transcriptions, lrc_text)
            nivel_codigo = perfil.nivel_mcer.codigo

            ai_scores = None
            if nivel_codigo in ('A2', 'B1'):
                try:
                    evaluator = ProsodyEvaluator()
                    lrc_lines = _parse_lrc_lines(lrc_text)
                    ai_scores = evaluator.evaluate(line_transcriptions, lrc_lines, nivel_codigo)
                except (AIEvaluationError, EnvironmentError):
                    ai_scores = None

            puntaje = Decimal(_score_musica_ponderado(precision, nivel_codigo, ai_scores))
            transcripcion = json.dumps(line_transcriptions)

        else:
            try:
                puntaje = Decimal(str(body['puntaje']))
            except (KeyError, InvalidOperation):
                return JsonResponse({'error': 'invalid_payload'}, status=400)

        IntentoEjercicio.objects.filter(
            perfil=perfil, ejercicio=ejercicio, activo=True
        ).update(activo=False)
        IntentoEjercicio.objects.create(
            perfil=perfil, ejercicio=ejercicio, puntaje=puntaje,
            activo=True, transcripcion=transcripcion,
        )
        completado = _submodulo_completado(perfil, ejercicio.submodulo)
        return JsonResponse({
            'aprobado': puntaje >= 80,
            'puntaje': str(puntaje.quantize(Decimal('0.01'))),
            'submodulo_completado': completado,
        })