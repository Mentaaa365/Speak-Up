from django.contrib.auth.views import LoginView
from django.views.generic import TemplateView
from django.shortcuts import redirect, render
from django.contrib.auth import logout
from django.contrib.auth.models import User  # <-- Importación vital para que funcione el registro
from django.urls import reverse_lazy         # <-- Importación recomendada para redirecciones en LoginView
import re
from django.contrib import messages


class SpeakUpLoginView(LoginView):
    template_name = 'authentication/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        user = self.request.user
        
        # 1. Evaluamos si el perfil existe y si ya tiene un nivel asignado
        if hasattr(user, 'perfil') and user.perfil.nivel_mcer is not None:
            return reverse_lazy('progress:dashboard')
        
        # 2. Si es un usuario nuevo, lo enviamos al examen. 
        # La ruta correcta es 'diagnosis:welcome' o 'diagnosis:test_run' (Nunca 'test' a secas)
        return reverse_lazy('diagnosis:test_run')

# VISTA DE REGISTRO ACTUALIZADA:
class SpeakUpRegisterView(TemplateView):
    template_name = 'authentication/register.html'
    
    def post(self, request, *args, **kwargs):
        # 1. Cambiamos 'name' por 'first_name' para que coincida exactamente con tu HTML
        nombre = request.POST.get('first_name')
        correo = request.POST.get('email')
        contrasena = request.POST.get('password')
        institucion = request.POST.get('institution') # Capturamos la institución del HTML

        # 2. Validar que el nombre no tenga números
        if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', nombre):
            messages.error(request, 'El nombre no puede contener números o símbolos.')
            return render(request, self.template_name)

        # 3. Validar si el correo ya existe
        if User.objects.filter(username=correo).exists():
            # Pasamos la variable que tu HTML necesita para mostrar el cuadro amarillo
            return render(request, self.template_name, {'error_correo_duplicado': True})

        # 4. CREACIÓN ENCRIPTADA 
        nuevo_usuario = User.objects.create_user(
            username=correo,
            email=correo,
            password=contrasena,
            first_name=nombre
        )
        
        # 5. Guardar la institución en el Perfil
        # (El perfil ya fue creado milisegundos atrás por las señales de models.py)
        nuevo_usuario.perfil.institucion = institucion
        nuevo_usuario.perfil.save()

        # 6. Redirigir al usuario al login
        messages.success(request, '¡Registro exitoso! Por favor, inicia sesión.')
        return redirect('authentication:login')

class DummyView(TemplateView):
    template_name = 'base.html'

def speakup_logout_view(request):
    """
    Termina de forma segura la sesión del usuario actual 
    y limpia las cookies del navegador.
    """
    logout(request)
    return redirect('authentication:login')