from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin  # <-- Esta es la línea que falta
from apps.progress.models import Perfil, NivelMCER, Ejercicio, ProgresoPorEjercicio

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'progress/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 1. Traer datos reales
        perfil = Perfil.objects.get(usuario=self.request.user)
        nivel_activo = perfil.nivel_mcer
        
        # Si no hay nivel, significa que no ha hecho el examen
        if not nivel_activo:
            raise ValueError("¡No tienes un nivel asignado! Vuelve a hacer el examen de diagnóstico.")

        # 2. Calcular porcentajes reales
        total_ejercicios = Ejercicio.objects.count()
        ejercicios_exitosos = ProgresoPorEjercicio.objects.filter(
            perfil=perfil, puntaje__gte=80, activo=True
        ).count()
        
        context['global_progress'] = int((ejercicios_exitosos / total_ejercicios) * 100) if total_ejercicios > 0 else 0

        # 3. Calcular los candados de los Niveles
        niveles_db = NivelMCER.objects.all().order_by('orden')
        niveles_data = []
        
        for nivel in niveles_db:
            if nivel.orden < nivel_activo.orden:
                estado = 'completado'
                sub_completados = 3
                progreso = 100
            elif nivel.orden == nivel_activo.orden:
                estado = 'activo'
                sub_completados = 1 
                progreso = 33
            else:
                estado = 'bloqueado'
                sub_completados = 0
                progreso = 0

            niveles_data.append({
                'codigo': nivel.codigo,
                'nombre': nivel.parametros_json.get('nombre_descriptivo', 'Nivel'),
                'estado': estado,
                'sub_completados': sub_completados,
                'progreso': progreso
            })

        context['niveles'] = niveles_data
        
        # 4. Estos los dejamos estáticos por ahora hasta que hagamos los ejercicios
        context['submodulos'] = [
            {'nombre': 'Vocabulario y Lectura', 'icono': '📖', 'estado': 'completado', 'progreso': 100, 'detalle': 'Completado al 100% con éxito.', 'url': '#'},
            {'nombre': 'Actividades Musicales (LRC)', 'icono': '🎵', 'estado': 'activo', 'progreso': 66, 'detalle': '4 de 6 canciones superadas.', 'url': '/learning/music/'},
            {'nombre': 'Entrevistas Orales con IA', 'icono': '🤖', 'estado': 'bloqueado', 'progreso': 0, 'detalle': 'Requiere ≥80% en Vocabulario.', 'url': '#'}
        ]
        context['examen'] = {
            'disponible': False,
            'intentos_restantes': 2,
            'titulo': f"Examen de Promoción {nivel_activo.codigo} → B1"
        }

        return context
    

class ProgressDetailView(LoginRequiredMixin, TemplateView):
    """
    Muestra el desglose analítico con las 3 barras de progreso independientes (RF-07).
    """
    template_name = 'progress/progress_detail.html'