from django.urls import path
from . import views
from .views import VocabularyLearningView, MusicLearningView, WritingLearningView, EvaluarEscrituraView, MiNivelRouterView

app_name = 'learning'

# 🔥 LA SOLUCIÓN: Registramos el namespace en inglés exigido por la plantilla
app_name = 'learning'

urlpatterns = [
    path('vocabulary/', views.VocabularyLearningView.as_view(), name='vocabulary'),
    # Ruta base para el submódulo de actividades musicales LRC (RF-04)
    path('music/', views.MusicLearningView.as_view(), name='music'),
    # RF-05: AI Interview routes
    path('writing/', WritingLearningView.as_view(), name='writing'),
    path('writing/evaluar/', EvaluarEscrituraView.as_view(), name='writing_evaluar'),
    path('ai-interview/', views.AiInterviewLearningView.as_view(), name='ai_interview'),
    path('ai-interview/turno/', views.TurnoEntrevistaView.as_view(), name='interview_turno'),
    path('ai-interview/finalizar/', views.FinalizarEntrevistaView.as_view(), name='interview_finalizar'),
    path('mi-nivel-smart/', MiNivelRouterView.as_view(), name='router_nivel'),
]
