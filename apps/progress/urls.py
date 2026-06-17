from django.urls import path
from . import views

app_name = 'progress'

urlpatterns = [
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('detail/', views.ProgressDetailView.as_view(), name='detail'),
    path('guardar-ejercicio/', views.GuardarEjercicioView.as_view(), name='guardar_ejercicio'),
]