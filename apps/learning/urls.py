from django.urls import path
from . import views


# 🔥 LA SOLUCIÓN: Registramos el namespace en inglés exigido por la plantilla
app_name = 'learning'

urlpatterns = [
    path('vocabulary/', views.VocabularyLearningView.as_view(), name='vocabulary'),
    # Ruta base para el submódulo de actividades musicales LRC (RF-04)
    path('music/', views.MusicLearningView.as_view(), name='music'),
    path('ai-interview/', views.AiInterviewLearningView.as_view(), name='ai_interview'),
]