from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import TemplateView

from apps.authentication.models import Perfil
from apps.exams.models import Certificado, ExamenIntento
from apps.question_bank.models import Question


class ExamStartView(LoginRequiredMixin, View):
    template_name = 'exams/exam.html'

    def get(self, request, *args, **kwargs):
        # Guard 1: profile must exist and have a nivel assigned
        try:
            perfil = Perfil.objects.get(usuario=request.user)
        except Perfil.DoesNotExist:
            return redirect(reverse_lazy('diagnosis:welcome'))

        if not perfil.nivel_mcer:
            return redirect(reverse_lazy('diagnosis:welcome'))

        nivel_activo = perfil.nivel_mcer

        # Guard 2: already has a Certificado (B1 passed) → show it
        if Certificado.objects.filter(examen__perfil=perfil).exists():
            return redirect(reverse_lazy('exams:certificate'))

        # Guard 3: already has an approved attempt for this nivel → already promoted
        if ExamenIntento.objects.filter(
            perfil=perfil,
            nivel_objetivo=nivel_activo,
            tipo__in=['PROMOCION', 'CERTIFICACION'],
            aprobado=True,
        ).exists():
            return redirect(reverse_lazy('progress:dashboard'))

        # Guard 4: attempt limit (2) reached
        intentos_usados = ExamenIntento.objects.filter(
            perfil=perfil,
            nivel_objetivo=nivel_activo,
            tipo__in=['PROMOCION', 'CERTIFICACION'],
        ).count()
        if intentos_usados >= 2:
            return render(request, self.template_name, {
                'error': 'Has agotado tus 2 intentos para este nivel.',
            })

        # Guard 5: bank must have enough questions for this nivel
        bank = Question.objects.filter(
            bank_context='PROMOTION_EXAM',
            level=nivel_activo.codigo,
        )
        if (
            bank.filter(question_type='SPEAKING').count() < 5
            or bank.filter(question_type='LISTENING').count() < 5
            or bank.filter(question_type='CHOICE').count() < 10
        ):
            return render(request, self.template_name, {
                'error': 'Este examen aún no tiene preguntas configuradas. Inténtalo más tarde.',
            })

        # All guards pass — stub until PR B wires up question delivery
        return render(request, self.template_name, {
            'nivel_activo': nivel_activo,
        })


class CertificateView(LoginRequiredMixin, TemplateView):
    """
    Muestra la plantilla del certificado B1.
    """
    template_name = 'exams/certificate.html'
