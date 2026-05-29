from django.urls import path
from . import views

# 🔥 LA SOLUCIÓN: Registramos el namespace en inglés exigido por la plantilla
app_name = 'learning'

urlpatterns = [
    # Ruta base para el submódulo de actividades musicales LRC (RF-04)
    path('music/', views.MusicLearningView.as_view(), name='music'),
]