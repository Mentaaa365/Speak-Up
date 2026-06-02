from django.urls import path
from . import views
from .views import APIPreguntasDiagnosticoView, DiagnosisResultsView


# 1. Asegúrate de que el namespace esté en inglés y con comillas
app_name = 'diagnosis'

# 2. 🔥 LA SOLUCIÓN: Debe ser exactamente 'urlpatterns' (sin guiones bajos, en minúsculas y como una lista [])
urlpatterns = [
    # Pantalla de bienvenida y verificación de micrófono
    path('speaking/', views.DiagnosisWelcomeView.as_view(), name='welcome'),
    
    # Pantalla central del examen interactivo
    path('test/', views.DiagnosisTestView.as_view(), name='test_run'),
    
    # Marcador para la pantalla de resultados finales
    path('results/', DiagnosisResultsView.as_view(), name='results'),

    path('api/get-questions/', APIPreguntasDiagnosticoView.as_view(), name='api_get_questions'),
]
