from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.http import JsonResponse
from apps.question_bank.models import Question
import random
from django.shortcuts import render
import json

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


import json
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

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
        # Como MVP temporal, contaremos los tipos de pregunta recibidos. 
        # Luego deberás comparar 'answer' con la respuesta correcta en SQL Server.
        for item in user_answers:
            q_type = item.get('type')
            if q_type == 'SPEAKING':
                correct_speaking += 1
            elif q_type == 'LISTENING':
                correct_listening += 1
            elif q_type == 'CHOICE':
                correct_vocab += 1

        # 4. Ponderación oficial (RF-03)
        # Speaking (5 ítems) = 40% -> 8% c/u
        # Listening (5 ítems) = 40% -> 8% c/u
        # Vocabulario (10 ítems) = 20% -> 2% c/u
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

        # --- NUEVO: GUARDAR EL NIVEL EN LA BD PARA EL DASHBOARD ---
        # (Asegúrate de importar Perfil y NivelMCER al inicio de tu views.py)
        # --- GUARDAR EL NIVEL EN LA BD PARA EL DASHBOARD ---
        from apps.progress.models import Perfil, NivelMCER # <-- Ruta correcta
        
        perfil = Perfil.objects.get(usuario=request.user)
        nivel_obj = NivelMCER.objects.get(codigo=nivel)
        perfil.nivel_mcer = nivel_obj
        perfil.save()
        # -----------------------------------------------------------
        # -----------------------------------------------------------

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
                # Si ya dio el examen, le mostramos su nivel histórico
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


# Agregamos esta clase para evitar choques si alguna ruta vieja todavía la busca
class DummyView(LoginRequiredMixin, TemplateView):
    template_name = 'base.html'


class APIPreguntasDiagnosticoView(View):
    def get(self, request, *args, **kwargs):
        """
        Extrae preguntas aleatorias de la BD para el examen.
        """
        # Traemos todas las preguntas y las mezclamos
        preguntas_db = list(Question.objects.all())
        random.shuffle(preguntas_db)
        
        # Seleccionamos las primeras 10
        preguntas_seleccionadas = preguntas_db[:10]
        
        questions_array = []
        for q in preguntas_seleccionadas:
            pregunta_dict = {
                'id': q.id,
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
        # 1. Recibir el JSON con las respuestas crudas del usuario (Blindaje de seguridad)
        answers_json = request.POST.get('answers_data', '[]')
        try:
            user_answers = json.loads(answers_json)
        except json.JSONDecodeError:
            user_answers = []

        # Contadores de respuestas correctas
        correct_speaking = 0
        correct_listening = 0
        correct_vocab = 0

        # 2. Evaluación en el backend contra la base de datos
        for item in user_answers:
            q_id = item.get('questionId')
            user_ans = item.get('answer', '').lower().strip()
            
            try:
                # Consulta a la base de datos (Asumiendo tu modelo BancoPregunta)
                # pregunta = BancoPregunta.objects.get(id=q_id)
                
                # SIMULACIÓN (Reemplaza esto con la validación real contra 'pregunta.contenido_json')
                # if pregunta.tipo == 'SPEAKING':
                #     target = pregunta.contenido_json.get('targetPhrase', '').lower()
                #     if target.replace('.', '') in user_ans:
                #         correct_speaking += 1
                pass 
                
            except Exception as e:
                # Manejar el error si el ID de la pregunta no existe
                continue
        
        # Para pruebas, asignamos valores fijos asumiendo que ya pasaron la validación de BD
        # Borra estas 3 líneas cuando conectes el modelo BancoPregunta
        correct_speaking = 4  # 4 de 5 correctas
        correct_listening = 3 # 3 de 5 correctas
        correct_vocab = 8     # 8 de 10 correctas

        # 3. Ponderación estricta según requerimientos RF-03 (Total = 100%)
        # Speaking: 5 ítems = 40% (Cada uno vale 8%)
        # Listening: 5 ítems = 40% (Cada uno vale 8%)
        # Vocabulario: 10 ítems = 20% (Cada uno vale 2%)
        score_speaking = correct_speaking * 8
        score_listening = correct_listening * 8
        score_vocabulary = correct_vocab * 2

        score_total = score_speaking + score_listening + score_vocabulary

        # 4. Tabla de clasificación MCER (Ajustada a RF-03)
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

        # TODO: Aquí debes hacer un UPDATE en la tabla Perfil para guardar el 'nivel_asignado' al request.user

        # 5. Empaquetamos todo y renderizamos el template
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