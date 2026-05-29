from django.views.generic import TemplateView

class DashboardView(TemplateView):
    # Ruta del template actualizada
    template_name = 'progress/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        class MockUser:
            is_authenticated = True
            first_name = "María"
            last_name = "García"
            class Perfil:
                nivel_mcer = "A2"
            perfil = Perfil()
            
        if not self.request.user.is_authenticated:
            context['user'] = MockUser()

        context['porcentaje_global'] = 33
        context['stats'] = {
            'submodulos_completados': 3,
            'sesiones_ia': 3,
            'canciones': 6,
            'examenes_aprobados': 1
        }

        context['niveles'] = [
            # ... (Copia aquí la misma lista de 'niveles' con los datos mock de la respuesta anterior) ...
        ]
        return context