from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

class MusicLearningView(LoginRequiredMixin, TemplateView):
    """
    HU-04 / RF-04: Gestiona de forma parametrizada las actividades musicales
    con reproducción de letra sincronizada (LRC) y pausas automáticas.
    """
    template_name = 'learning/music.html'