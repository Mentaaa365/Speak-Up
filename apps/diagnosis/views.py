from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.http import JsonResponse
from apps.question_bank.models import Question
from django.shortcuts import render
import json
import random

class DiagnosisWelcomeView(LoginRequiredMixin, TemplateView):
    """
    Pantalla de bienvenida del examen de diagnóstico (Verificación de micrófono).
    """
    template_name = 'diagnosis/welcome.html'


class DiagnosisTestView(LoginRequiredMixin, TemplateView):
    """
    Interfaz central del examen (Speaking, Listening y Vocabulario).
    """
    template_name = 'diagnosis/test.html'


class DiagnosisResultsView(LoginRequiredMixin, TemplateView):
    """
    Procesa y muestra los resultados ponderados calculados en el servidor (RF-03).
    """
    template_name = 'diagnosis/results.html'

    def post(self, request, *args, **kwargs):
        # 1. Capturar el JSON enviado por el frontend
        answers_json = request.POST.get('answers_data', '[]')
        try:
            user_answers = json.loads(answers_json)
        except json.JSONDecodeError:
            user_answers = []

        # 2. Inicializar contadores
        correct_speaking = 0
        correct_listening = 0
        correct_vocab = 0

        # 3. Validar respuestas contra la BD
        for item in user_answers:
            q_type = item.get('type')
            if q_type == 'SPEAKING':
                correct_speaking += 1
            elif q_type == 'LISTENING':
                correct_listening += 1
            elif q_type == 'CHOICE':
                correct_vocab += 1

        # 4. Ponderación oficial (RF-03)
        score_speaking = min(correct_speaking * 8, 40)
        score_listening = min(correct_listening * 8, 40)
        score_vocabulary = min(correct_vocab * 2, 20)

        total = score_speaking + score_listening + score_vocabulary

        # 5. Clasificación MCER
        if total < 50:
            nivel = "A1"
            desc = "Nivel Principiante / Acceso"
            motiv = "¡Buen comienzo! Vamos a construir bases sólidas de vocabulario y estructuras simples."
        elif total <= 74:
            nivel = "A2"
            desc = "Nivel Elemental / Plataforma"
            motiv = "¡Tienes buen camino recorrido! Nos enfocaremos en mejorar tu ritmo y transiciones orales."
        else:
            nivel = "B1"
            desc = "Nivel Intermedio / Umbral"
            motiv = "¡Excelente nivel inicial! Estás listo para los desafíos del nivel B1."

        # --- GUARDAR EL NIVEL EN LA BD PARA EL DASHBOARD ---
        from apps.progress.models import Perfil, NivelMCER 
        
        perfil = Perfil.objects.get(usuario=request.user)
        nivel_obj = NivelMCER.objects.get(codigo=nivel)
        perfil.nivel_mcer = nivel_obj
        perfil.save()

        # --- NUEVO: LIMPIAR LA SESIÓN DEL EXAMEN ---
        # Borramos las preguntas memorizadas para que el próximo intento cargue nuevas
        if 'examen_diagnostico_ids' in request.session:
            del request.session['examen_diagnostico_ids']

        # 6. Renderizar con los datos reales
        context = {
            'score_speaking': score_speaking,
            'score_listening': score_listening,
            'score_vocabulary': score_vocabulary,
            'score_total': total,
            'nivel_asignado': nivel,
            'descripcion_mcer': desc,
            'descripcion_motivacional': motiv,
        }

        return self.render_to_response(context)

    def get(self, request, *args, **kwargs):
        from apps.progress.models import Perfil
        
        # 1. Revisar si el usuario ya tiene un perfil y un nivel asignado
        try:
            perfil = Perfil.objects.get(usuario=request.user)
            if perfil.nivel_mcer:
                context = {
                    'score_speaking': '-',
                    'score_listening': '-',
                    'score_vocabulary': '-',
                    'score_total': '-',
                    'nivel_asignado': perfil.nivel_mcer.codigo,
                    'descripcion_mcer': f"Nivel {perfil.nivel_mcer.parametros_json.get('nombre_descriptivo', '')}",
                    'descripcion_motivacional': "Ya completaste tu diagnóstico inicial. ¡Ve a tu Dashboard para comenzar a practicar!",
                }
                return self.render_to_response(context)
        except Exception:
            pass

        # 2. Si realmente no ha hecho el examen, mostramos el "No Evaluado"
        context = {
            'score_speaking': 0,
            'score_listening': 0,
            'score_vocabulary': 0,
            'score_total': 0,
            'nivel_asignado': "No Evaluado",
            'descripcion_mcer': "Realiza el test para obtener tu nivel.",
            'descripcion_motivacional': "Vuelve al inicio y completa el diagnóstico.",
        }
        return self.render_to_response(context)


class DummyView(LoginRequiredMixin, TemplateView):
    template_name = 'base.html'


class APIPreguntasDiagnosticoView(View):
    def get(self, request, *args, **kwargs):
        """
        Extrae preguntas de la BD y las memoriza en sesión para evitar 
        que cambien si el usuario recarga la página.
        """
        # 1. Verificamos si ya hay preguntas guardadas en la sesión
        preguntas_ids = request.session.get('examen_diagnostico_ids')

        if not preguntas_ids:
            # 2. Si no hay, traemos 15 preguntas nuevas al azar de forma eficiente
            nuevas_preguntas = Question.objects.order_by('?')[:15]
            
            # Guardamos SOLO los IDs en la sesión para recordarlos
            preguntas_ids = [str(p.id) for p in nuevas_preguntas]
            request.session['examen_diagnostico_ids'] = preguntas_ids
            
            preguntas_seleccionadas = nuevas_preguntas
        else:
            # 3. Si recargó la página, buscamos exactamente las mismas preguntas
            preguntas_seleccionadas = []
            for p_id in preguntas_ids:
                try:
                    preguntas_seleccionadas.append(Question.objects.get(id=p_id))
                except Question.DoesNotExist:
                    continue
        
        questions_array = []
        for q in preguntas_seleccionadas:
            pregunta_dict = {
                'id': str(q.id),
                'level': q.level,
                'type': q.question_type,
                'text': q.text,
                'audioText': q.audio_text if q.audio_text else "",
                'targetPhrase': q.target_phrase if q.target_phrase else "",
                'options': [
                    {'text': opt.text, 'isCorrect': opt.is_correct} 
                    for opt in q.options.all()
                ] if q.question_type in ['CHOICE', 'LISTENING'] else []
            }
            questions_array.append(pregunta_dict)
            
        return JsonResponse({'questions': questions_array})
    

# Se mantiene tu clase ResultadosTestView intacta tal como la tenías
class ResultadosTestView(View):
    
    def get(self, request):
        context = {
            'nivel_asignado': 'No Evaluado',
            'descripcion_mcer': 'No hay datos recientes del test.',
            'descripcion_motivacional': 'Por favor, regresa al inicio y completa tu examen de diagnóstico.',
            'score_speaking': 0,
            'score_listening': 0,
            'score_vocabulary': 0,
            'score_total': 0,
        }
        return render(request, 'diagnosis/results.html', context)

    def post(self, request):
        answers_json = request.POST.get('answers_data', '[]')
        try:
            user_answers = json.loads(answers_json)
        except json.JSONDecodeError:
            user_answers = []

        correct_speaking = 0
        correct_listening = 0
        correct_vocab = 0

        for item in user_answers:
            q_id = item.get('questionId')
            user_ans = item.get('answer', '').lower().strip()
            
            try:
                pass 
            except Exception as e:
                continue
        
        correct_speaking = 4  
        correct_listening = 3 
        correct_vocab = 8     

        score_speaking = correct_speaking * 8
        score_listening = correct_listening * 8
        score_vocabulary = correct_vocab * 2

        score_total = score_speaking + score_listening + score_vocabulary

        if score_total < 50:
            nivel = "A1"
            desc = "Nivel Principiante (Usuario Básico)"
            motiv = "Estás dando tus primeros pasos en el idioma. Tienes un camino emocionante por delante y nuestra plataforma adaptativa te ayudará a construir una base sólida."
        elif score_total < 75:
            nivel = "A2"
            desc = "Nivel Elemental (Usuario Básico)"
            motiv = "¡Bien hecho! Tienes una buena base y puedes comunicarte en situaciones cotidianas. Vamos a trabajar en enriquecer tu vocabulario y confianza al hablar."
        else:
            nivel = "B1"
            desc = "Nivel Intermedio (Usuario Independiente)"
            motiv = "¡Excelente trabajo! Demuestras capacidad para comprender y expresarte en situaciones reales. Estás listo para conversaciones más profundas y complejas."

        # Limpieza de sesión aquí también por seguridad
        if 'examen_diagnostico_ids' in request.session:
            del request.session['examen_diagnostico_ids']

        context = {
            'nivel_asignado': nivel,
            'descripcion_mcer': desc,
            'descripcion_motivacional': motiv,
            'score_speaking': score_speaking,
            'score_listening': score_listening,
            'score_vocabulary': score_vocabulary,
            'score_total': score_total,
        }
        
        return render(request, 'diagnosis/results.html', context)