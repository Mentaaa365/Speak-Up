from django.contrib.auth.views import LoginView
from django.views.generic import TemplateView
from django.shortcuts import redirect, render
from django.contrib.auth import logout
from django.contrib.auth import get_user_model
User = get_user_model()
from django.urls import reverse_lazy      # <-- Importación recomendada para redirecciones en LoginView
from django.contrib import messages
from .forms import RegistroForm
from django.db import transaction

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
        return reverse_lazy('diagnosis:welcome')

# VISTA DE REGISTRO ACTUALIZADA:
class SpeakUpRegisterView(TemplateView):
    template_name = 'authentication/register.html'

    def post(self, request, *args, **kwargs):
        form = RegistroForm(request.POST)

        if form.is_valid():
            nombre = form.cleaned_data['first_name']
            correo = form.cleaned_data['email']
            contrasena = form.cleaned_data['password']
            institucion = form.cleaned_data['institution']

            try:
                # 2. Envolvemos la creación en una transacción atómica
                with transaction.atomic():
                    nuevo_usuario = User.objects.create_user(
                        username=correo,
                        email=correo,
                        password=contrasena,
                        first_name=nombre
                    )
                    
                    nuevo_usuario.perfil.institucion = institucion
                    nuevo_usuario.perfil.save()

                # Si todo sale bien dentro del bloque `with`, redirigimos:
                messages.success(request, '¡Registro exitoso! Por favor, inicia sesión.')
                return redirect('authentication:login')

            except Exception as e:
                # Si algo falla en la base de datos, entra aquí y deshace la creación
                messages.error(request, 'Ocurrió un error en el servidor al guardar tu cuenta. Intenta de nuevo.')
                return render(request, self.template_name)
                
        else:
            contexto = {}
            
            if 'first_name' in form.errors:
                messages.error(request, form.errors['first_name'][0])
                
            if 'email' in form.errors:
                contexto['error_correo_duplicado'] = True

            return render(request, self.template_name, contexto)

class DummyView(TemplateView):
    template_name = 'base.html'

def speakup_logout_view(request):
    
    logout(request)
    return redirect('authentication:login')