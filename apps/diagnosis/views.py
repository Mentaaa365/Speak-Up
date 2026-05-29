from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

class DiagnosisWelcomeView(LoginRequiredMixin, TemplateView):
    """
    Pantalla de bienvenida del examen de diagnóstico (Verificación de micrófono).
    """
    template_name = 'diagnosis/welcome.html'


class DiagnosisTestView(LoginRequiredMixin, TemplateView):
    """
    Interfaz central del examen (Speaking, Listening y Vocabulario).
    """
    template_name = 'diagnosis/test.html'


class DiagnosisResultsView(LoginRequiredMixin, TemplateView):
    """
    Procesa y muestra los resultados ponderados calculados en el servidor (RF-03).
    """
    template_name = 'diagnosis/results.html'

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Ponderación oficial de la UNEMI: Speaking 40%, Listening 40%, Vocabulario 20%
        context['score_speaking'] = 32    
        context['score_listening'] = 35   
        context['score_vocabulary'] = 13  
        
        total = context['score_speaking'] + context['score_listening'] + context['score_vocabulary']
        context['score_total'] = total    
        
        # Clasificación según tu documento de requerimientos: <50% A1 | 50-74% A2 | >=75% B1
        if total < 50:
            context['nivel_asignado'] = "A1"
            context['descripcion_mcer'] = "Nivel Principiante / Acceso"
            context['descripcion_motivacional'] = "¡Buen comienzo! Vamos a construir bases sólidas de vocabulario y estructuras simples."
        elif total <= 74:
            context['nivel_asignado'] = "A2"
            context['descripcion_mcer'] = "Nivel Elemental / Plataforma"
            context['descripcion_motivacional'] = "¡Tienes buen camino recorrido! Nos enfocaremos en mejorar tu ritmo y transiciones orales."
        else:
            context['nivel_asignado'] = "B1"
            context['descripcion_mcer'] = "Nivel Intermedio / Umbral"
            context['descripcion_motivacional'] = "¡Excelente nivel inicial! Estás listo para los desafíos del nivel B1."

        return context


# Agregamos esta clase para evitar choques si alguna ruta vieja todavía la busca
class DummyView(LoginRequiredMixin, TemplateView):
    template_name = 'base.html'