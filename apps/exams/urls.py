from django.urls import path
from . import views

app_name = 'exams'

urlpatterns = [
    path('certificado/', views.CertificateView.as_view(), name='certificate'),
]
