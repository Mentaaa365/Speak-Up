from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

class CertificateView(LoginRequiredMixin, TemplateView):
    """
    Muestra la plantilla del certificado B1.
    """
    template_name = 'exams/certificate.html'