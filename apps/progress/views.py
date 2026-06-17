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
from apps.shared.utils import _submodulo_completado




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
        TIPO_A_NOMBRE = {
            'vocabulario': ('Vocabulario y Lectura',       '📖', reverse_lazy('learning:vocabulary')),
            'musica':      ('Actividades Musicales (LRC)', '🎵', reverse_lazy('learning:music')),
            'entrevista':  ('Entrevistas Orales con IA',   '🤖', '#'),
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

            progreso_sub = int((aprobados / total_ej) * 100) if total_ej > 0 else 0
            completado   = total_ej > 0 and aprobados >= total_ej

            nombre, icono, url = TIPO_A_NOMBRE.get(
                submodulo.tipo,
                (submodulo.tipo.capitalize(), '📌', '#')
            )

            if completado:
                estado  = 'completado'
                detalle = f'Completado al 100% con éxito.'
            elif progreso_sub > 0:
                estado  = 'activo'
                detalle = f'{aprobados} de {total_ej} ejercicios superados.'
            else:
                estado  = 'bloqueado'
                detalle = 'Completa el submódulo anterior para desbloquear.'

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
            'vocabulario': ('Vocabulario y Lectura',       '📖'),
            'musica':      ('Actividades Musicales (LRC)', '🎵'),
            'entrevista':  ('Entrevistas Orales con IA',   '🤖'),
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
            puntaje = Decimal(str(body['puntaje']))
        except (json.JSONDecodeError, KeyError, InvalidOperation):
            return JsonResponse({'error': 'invalid_payload'}, status=400)

        perfil = Perfil.objects.select_related('nivel_mcer').get(usuario=request.user)
        ejercicio = (Ejercicio.objects
                     .select_related('submodulo__nivel')
                     .filter(pk=ejercicio_id).first())
        if ejercicio is None:
            return JsonResponse({'error': 'not_found'}, status=404)
        if ejercicio.submodulo.nivel != perfil.nivel_mcer:
            return JsonResponse({'error': 'level_mismatch'}, status=403)

        IntentoEjercicio.objects.filter(
            perfil=perfil, ejercicio=ejercicio, activo=True
        ).update(activo=False)
        IntentoEjercicio.objects.create(
            perfil=perfil, ejercicio=ejercicio, puntaje=puntaje,
            activo=True, transcripcion=body.get('transcripcion'),
        )
        completado = _submodulo_completado(perfil, ejercicio.submodulo)
        return JsonResponse({
            'aprobado': puntaje >= 80,
            'puntaje': str(puntaje.quantize(Decimal('0.01'))),
            'submodulo_completado': completado,
        })