import os
import django
import csv

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'speakup_config.settings')
django.setup()

from apps.question_bank.models import Question, Option

def cargar_desde_csv():
    print("Iniciando lectura del archivo CSV...")
    
    # Ruta al archivo que acabamos de crear
    ruta_csv = 'preguntas.csv'
    
    with open(ruta_csv, newline='', encoding='utf-8') as archivo:
        lector = csv.DictReader(archivo)
        contador = 0
        
        for fila in lector:
            # 1. Creamos la pregunta
            q = Question.objects.create(
                level=fila['level'],
                question_type=fila['type'],
                text=fila['text'],
                audio_text=fila['audio_text'] if fila['audio_text'] else None,
                target_phrase=fila['target_phrase'] if fila['target_phrase'] else None
            )
            
            # 2. Si NO es de tipo SPEAKING, le creamos sus 4 opciones
            if fila['type'] in ['CHOICE', 'LISTENING']:
                correcta_idx = int(fila['correct_opt'])
                
                opciones = [
                    fila['opt1'],
                    fila['opt2'],
                    fila['opt3'],
                    fila['opt4']
                ]
                
                for i, texto_opcion in enumerate(opciones, start=1):
                    Option.objects.create(
                        question=q,
                        text=texto_opcion,
                        is_correct=(i == correcta_idx)
                    )
            contador += 1
            
    print(f"¡Éxito! Se inyectaron {contador} preguntas en la base de datos de forma automática.")

if __name__ == '__main__':
    # Limpiamos la base de datos antes de cargar para evitar duplicados si corres el script varias veces
    print("Limpiando banco de preguntas actual...")
    Question.objects.all().delete()
    
    cargar_desde_csv()