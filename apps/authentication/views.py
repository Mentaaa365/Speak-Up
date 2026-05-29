from django.contrib.auth.views import LoginView
from django.views.generic import TemplateView
from django.shortcuts import redirect, render  # <-- Asegúrate de tener esta importación
from django.contrib.auth import logout
import re
from django.contrib import messages

class SpeakUpLoginView(LoginView):
    template_name = 'authentication/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        user = self.request.user
        if user.is_superuser:
            return '/progress/dashboard/'
            
        try:
            if user.perfil.nivel_mcer:
                return '/progress/dashboard/'
            return '/diagnosis/speaking/'
        except AttributeError:
            return '/progress/dashboard/'
        """try:
            if user.perfil.nivel_mcer:
                return '/progress/dashboard/'
            return '/diagnosis/speaking/'
        except AttributeError:
            return '/progress/dashboard/'"""

# VISTA DE REGISTRO ACTUALIZADA:
class SpeakUpRegisterView(TemplateView):
    template_name = 'authentication/register.html'

    def post(self, request, *args, **kwargs):
        username = request.POST.get('username', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')

        context = {
            'values': request.POST
        }

        # 🛡️ EL CANDADO DE PYTHON: Si el nombre contiene algo que no sea letras o espacios, rebota
        if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', first_name):
            messages.error(request, "Error: El nombre completo solo puede contener letras y espacios.")
            return render(request, self.template_name, context)
        # Aquí es donde capturarás los datos (request.POST.get('email'), etc.) 
        # y aplicarás el hash bcrypt para guardarlos en la base de datos relacional.
        
        # 🚀 CUMPLIMOS EL REQUERIMIENTO (HU-01 / UC1):
        # Simulamos el éxito del registro y redirigimos de inmediato al Examen de Diagnóstico
        return redirect('/progress/dashboard/')
        "return redirect('/diagnosis/speaking/')"
    

class DummyView(TemplateView):
    template_name = 'base.html'

def speakup_logout_view(request):
    """
    Termina de forma segura la sesión del usuario actual 
    y limpia las cookies del navegador.
    """
    logout(request)
    return redirect('authentication:login')