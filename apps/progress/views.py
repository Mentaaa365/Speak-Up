from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from apps.progress.models import Perfil, NivelMCER, Submodulo, Ejercicio, ProgresoPorEjercicio


# ─────────────────────────────────────────────────────────────────────────────
#  UTILIDAD INTERNA
# ─────────────────────────────────────────────────────────────────────────────

def _calcular_submodulos_completados(perfil, nivel):
    """
    Devuelve cuántos submódulos del nivel dado están completados por el perfil.
    Un submódulo se considera completado cuando TODOS sus ejercicios tienen
    puntaje >= 80 y activo=True.
    """
    completados = 0
    for submodulo in nivel.submodulos.all():
        total_ej = submodulo.ejercicios.count()
        if total_ej == 0:
            continue
        aprobados = ProgresoPorEjercicio.objects.filter(
            perfil=perfil,
            ejercicio__submodulo=submodulo,
            puntaje__gte=80,
            activo=True,
        ).count()
        if aprobados >= total_ej:
            completados += 1
    return completados


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
        ejercicios_exitosos = ProgresoPorEjercicio.objects.filter(
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
                sub_completados = _calcular_submodulos_completados(perfil, nivel)
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
            'vocabulario': ('Vocabulario y Lectura',        '📖', '/learning/vocabulary/'),
            'musica':      ('Actividades Musicales (LRC)',  '🎵', '/learning/music/'),
            'entrevista':  ('Entrevistas Orales con IA',    '🤖', '#'),
        }
        submodulos_data = []

        for submodulo in nivel_activo.submodulos.all().order_by('orden'):
            total_ej  = submodulo.ejercicios.count()
            aprobados = ProgresoPorEjercicio.objects.filter(
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
        subs_completados  = _calcular_submodulos_completados(perfil, nivel_activo)
        examen_disponible = total_subs_activo > 0 and subs_completados >= total_subs_activo

        context['examen'] = {
            'disponible':         examen_disponible,
            'intentos_restantes': 2,         # TODO: conectar con modelo ExamenIntento (HU-06)
            'titulo':             titulo_examen,
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
        ejercicios_exitosos = ProgresoPorEjercicio.objects.filter(
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
            sub_completados = _calcular_submodulos_completados(perfil, nivel)

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
            aprobados = ProgresoPorEjercicio.objects.filter(
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