"""
poblar_bd.py — Script de carga del banco de preguntas desde preguntas.csv

Uso:
    python poblar_bd.py            → carga sin borrar (idempotente con get_or_create)
    python poblar_bd.py --reset    → borra TODO el banco antes de cargar

El CSV debe estar en la raíz del proyecto con estas columnas:
    level, type, text, audio_text, target_phrase,
    opt1, opt2, opt3, opt4, correct_opt
"""

import os
import sys
import csv
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'speakup_config.settings')
django.setup()

from apps.question_bank.models import Question, Option

# ─────────────────────────────────────────────
#  Valores válidos (según models.py)
# ─────────────────────────────────────────────
LEVELS_VALIDOS = {'DIAG', 'A1', 'A2', 'B1'}
TYPES_VALIDOS  = {'CHOICE', 'LISTENING', 'SPEAKING','WRITING'}
RUTA_CSV       = os.path.join(os.path.dirname(__file__), 'preguntas.csv')


def cargar_desde_csv():
    print(f"📂 Leyendo: {RUTA_CSV}\n")

    # ✅ CORRECCIÓN 1: verificar que el archivo existe antes de abrirlo
    if not os.path.exists(RUTA_CSV):
        print(f"❌ No se encontró el archivo: {RUTA_CSV}")
        sys.exit(1)

    cargadas   = 0
    omitidas   = 0
    errores    = []

    with open(RUTA_CSV, newline='', encoding='utf-8') as archivo:
        lector = csv.DictReader(archivo)

        # ✅ CORRECCIÓN 2: verificar que el CSV tiene las columnas esperadas
        columnas_requeridas = {'level','type','text','audio_text',
                               'target_phrase','opt1','opt2','opt3','opt4','correct_opt'}
        if not columnas_requeridas.issubset(set(lector.fieldnames or [])):
            faltantes = columnas_requeridas - set(lector.fieldnames or [])
            print(f"❌ CSV con columnas faltantes: {faltantes}")
            sys.exit(1)

        for num_fila, fila in enumerate(lector, start=2):

            # ── Validar campos obligatorios ──────────────────────────────────
            level = fila['level'].strip()
            tipo  = fila['type'].strip()
            texto = fila['text'].strip()

            # ✅ CORRECCIÓN 3: validar valores contra las choices del modelo
            if level not in LEVELS_VALIDOS:
                errores.append(f"Fila {num_fila}: level inválido '{level}' — omitida.")
                omitidas += 1
                continue

            if tipo not in TYPES_VALIDOS:
                errores.append(f"Fila {num_fila}: type inválido '{tipo}' — omitida.")
                omitidas += 1
                continue

            if not texto:
                errores.append(f"Fila {num_fila}: text vacío — omitida.")
                omitidas += 1
                continue

            # ✅ CORRECCIÓN 4: usar get_or_create para evitar duplicados
            #    si el script se corre dos veces sin --reset
            q, creada = Question.objects.get_or_create(
                level=level,
                question_type=tipo,
                text=texto,
                defaults={
                    'audio_text':   fila['audio_text'].strip()   or None,
                    'target_phrase': fila['target_phrase'].strip() or None,
                }
            )

            if not creada:
                # La pregunta ya existía, no duplicamos
                omitidas += 1
                continue

            # ── Crear opciones solo para CHOICE y LISTENING ──────────────────
            if tipo in ('CHOICE', 'LISTENING'):

                # ✅ CORRECCIÓN 5: validar correct_opt antes de usarlo
                try:
                    correcta_idx = int(fila['correct_opt'].strip())
                    if correcta_idx < 1 or correcta_idx > 4:
                        raise ValueError
                except ValueError:
                    errores.append(
                        f"Fila {num_fila}: correct_opt inválido "
                        f"'{fila['correct_opt']}' (debe ser 1-4) — pregunta creada sin opciones."
                    )
                    cargadas += 1
                    continue

                opciones_textos = [
                    fila['opt1'].strip(),
                    fila['opt2'].strip(),
                    fila['opt3'].strip(),
                    fila['opt4'].strip(),
                ]

                # ✅ CORRECCIÓN 6: verificar que ninguna opción esté vacía
                opciones_vacias = [i+1 for i, t in enumerate(opciones_textos) if not t]
                if opciones_vacias:
                    errores.append(
                        f"Fila {num_fila}: opt{opciones_vacias} vacía(s) — "
                        f"pregunta creada sin opciones."
                    )
                    cargadas += 1
                    continue

                # ✅ CORRECCIÓN 7: bulk_create para insertar las 4 opciones en
                #    una sola query en vez de 4 queries separadas
                Option.objects.bulk_create([
                    Option(
                        question=q,
                        text=texto_opcion,
                        is_correct=(i == correcta_idx),
                    )
                    for i, texto_opcion in enumerate(opciones_textos, start=1)
                ])

            cargadas += 1

    # ── Reporte final ─────────────────────────────────────────────────────────
    print(f"✅ Preguntas cargadas:  {cargadas}")
    print(f"⏭️  Omitidas/duplicadas: {omitidas}")

    if errores:
        print(f"\n⚠️  {len(errores)} advertencia(s):")
        for e in errores:
            print(f"   · {e}")
    else:
        print("\n🎉 Sin errores ni advertencias.")


# ─────────────────────────────────────────────
#  Punto de entrada
# ─────────────────────────────────────────────
if __name__ == '__main__':

    # ✅ CORRECCIÓN 8: --reset requiere confirmación explícita para no
    #    destruir datos de producción por accidente
    if '--reset' in sys.argv:
        total = Question.objects.count()
        confirmacion = input(
            f"⚠️  ¿Seguro que deseas borrar las {total} preguntas existentes? (escribe 'si' para confirmar): "
        )
        if confirmacion.strip().lower() != 'si':
            print("Operación cancelada.")
            sys.exit(0)
        print("🗑️  Limpiando banco de preguntas...")
        Question.objects.all().delete()
        print("   Banco vaciado.\n")
    else:
        print("ℹ️  Modo seguro: cargando sin borrar datos existentes.")
        print("   (Usa --reset para vaciar el banco antes de cargar)\n")

    cargar_desde_csv()