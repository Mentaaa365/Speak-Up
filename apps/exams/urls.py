from django.urls import path
from . import views

app_name = 'exams'

urlpatterns = [
    path('start/', views.ExamStartView.as_view(), name='start'),
    path('certificado/', views.CertificateView.as_view(), name='certificate'),
]
