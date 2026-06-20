from django.core.management.base import BaseCommand

from apps.curriculum.models import Ejercicio, NivelMCER, Submodulo
from apps.question_bank.models import Question

NIVELES = [
    {"codigo": "A1", "orden": 1, "parametros_json": {"nombre_descriptivo": "Principiante (A1)"}},
    {"codigo": "A2", "orden": 2, "parametros_json": {"nombre_descriptivo": "Elemental (A2)"}},
    {"codigo": "B1", "orden": 3, "parametros_json": {"nombre_descriptivo": "Intermedio (B1)"}},
]

SUBMODULO_TIPOS = [
    ("vocabulario", 1),
    ("musica", 2),
    ("entrevista", 3),
    ("writing", 4),
]

VOCABULARY_EXERCISES = {
    "A1": [
        {
            "texto_objetivo": "apple",
            "contenido_json": {
                "imagen_url": "https://images.unsplash.com/photo-1579613832125-5d34a13ffe2a?w=400&h=300&fit=crop",
            },
        },
        {
            "texto_objetivo": "cat",
            "contenido_json": {
                "imagen_url": "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?w=400&h=300&fit=crop",
            },
        },
        {
            "texto_objetivo": "good morning",
            "contenido_json": {
                "imagen_url": "https://images.unsplash.com/photo-1470252649378-9c29740c9fa8?w=400&h=300&fit=crop",
            },
        },
    ],
    "A2": [
        {
            "texto_objetivo": "She is reading a book",
            "contenido_json": {
                "imagen_url": "https://images.unsplash.com/photo-1456513080510-7bf3a84b82f8?w=400&h=300&fit=crop",
            },
        },
        {
            "texto_objetivo": "I take the bus to school",
            "contenido_json": {
                "imagen_url": "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?w=400&h=300&fit=crop",
            },
        },
        {
            "texto_objetivo": "They are playing in the park",
            "contenido_json": {
                "imagen_url": "https://images.unsplash.com/photo-1596464716127-f2a82984de30?w=400&h=300&fit=crop",
            },
        },
    ],
    "B1": [
        {
            "texto_objetivo": "The environmental impact of urbanization has become increasingly concerning",
            "contenido_json": {},
        },
        {
            "texto_objetivo": "Despite considerable opposition the new policy was implemented successfully",
            "contenido_json": {},
        },
        {
            "texto_objetivo": "Scientists have discovered a strong correlation between sleep quality and academic performance",
            "contenido_json": {},
        },
    ],
}

MUSIC_EXERCISES = {
    "A1": [
        {
            "titulo": "Hello - Greeting Song",
            "contenido_json": {
                "audio_url": "/static/audio/hello.mp3",
                "lrc": (
                    "[00:05.00]Hello how are you\n"
                    "[00:15.00]I am fine thank you\n"
                    "[00:25.00]What is your name\n"
                    "[00:35.00]My name is John\n"
                    "[00:45.00]Nice to meet you\n"
                ),
            },
        },
    ],
    "A2": [
        {
            "titulo": "Daily Routine Song",
            "contenido_json": {
                "audio_url": "/static/audio/hello.mp3",
                "lrc": (
                    "[00:05.00]I wake up every morning at seven\n"
                    "[00:15.00]I take a shower and get dressed\n"
                    "[00:25.00]I have breakfast with my family\n"
                    "[00:35.00]Then I go to school by bus\n"
                    "[00:45.00]I study English every day\n"
                    "[00:55.00]After school I play with friends\n"
                ),
            },
        },
    ],
    "B1": [
        {
            "titulo": "Travel Dreams Song",
            "contenido_json": {
                "audio_url": "/static/audio/hello.mp3",
                "lrc": (
                    "[00:05.00]I have always wanted to travel the world\n"
                    "[00:15.00]To visit places I have only seen in pictures\n"
                    "[00:25.00]The mountains of Switzerland look beautiful\n"
                    "[00:35.00]And the beaches of Australia are amazing\n"
                    "[00:45.00]One day I will save enough money to go\n"
                    "[00:55.00]I believe that traveling teaches you about life\n"
                    "[01:05.00]Every culture has something special to offer\n"
                    "[01:15.00]And every journey begins with a single step\n"
                ),
            },
        },
    ],
}


WRITING_EXERCISES = {
    "A1": [
        "Describe your family in 2-3 simple sentences.",
        "Write about what you do every day.",
    ],
    "A2": [
        "Describe your last vacation. Where did you go and what did you do?",
        "Write about your favorite hobby and explain why you enjoy it.",
    ],
    "B1": [
        "Write an essay about the advantages and disadvantages of social media for students.",
        "Describe a challenge you overcame and explain what you learned from the experience.",
    ],
}

WRITING_QUESTIONS = {
    "A1": [
        "Write 2-3 sentences introducing yourself: your name, age, and where you live.",
        "Describe your favorite food in simple sentences.",
    ],
    "A2": [
        "Write a short paragraph about your best friend and what you like to do together.",
        "Describe what you did last weekend in 3-5 sentences.",
    ],
    "B1": [
        "Write a paragraph explaining why learning English is important for your future.",
        "Describe a place you would like to visit and explain why it interests you.",
    ],
}


class Command(BaseCommand):
    help = "Seed NivelMCER, Submodulos, Ejercicios, and WRITING questions for all levels"

    def handle(self, *args, **options):
        created_niveles = 0
        created_submodulos = 0
        created_ejercicios = 0
        created_questions = 0

        for nivel_data in NIVELES:
            nivel, created = NivelMCER.objects.get_or_create(
                codigo=nivel_data["codigo"],
                defaults={
                    "orden": nivel_data["orden"],
                    "parametros_json": nivel_data["parametros_json"],
                },
            )
            if created:
                created_niveles += 1

            for tipo, orden in SUBMODULO_TIPOS:
                _, sub_created = Submodulo.objects.get_or_create(
                    nivel=nivel,
                    tipo=tipo,
                    defaults={"orden": orden},
                )
                if sub_created:
                    created_submodulos += 1

            vocab_sub = Submodulo.objects.get(nivel=nivel, tipo="vocabulario")
            for exercise in VOCABULARY_EXERCISES.get(nivel_data["codigo"], []):
                _, ej_created = Ejercicio.objects.get_or_create(
                    submodulo=vocab_sub,
                    texto_objetivo=exercise["texto_objetivo"],
                    defaults={
                        "nivel_dificultad": nivel_data["codigo"],
                        "contenido_json": exercise["contenido_json"],
                    },
                )
                if ej_created:
                    created_ejercicios += 1

            musica_sub = Submodulo.objects.get(nivel=nivel, tipo="musica")
            for exercise in MUSIC_EXERCISES.get(nivel_data["codigo"], []):
                _, ej_created = Ejercicio.objects.get_or_create(
                    submodulo=musica_sub,
                    texto_objetivo=exercise["titulo"],
                    defaults={
                        "nivel_dificultad": nivel_data["codigo"],
                        "contenido_json": exercise["contenido_json"],
                    },
                )
                if ej_created:
                    created_ejercicios += 1

            writing_sub = Submodulo.objects.get(nivel=nivel, tipo="writing")
            for prompt in WRITING_EXERCISES.get(nivel_data["codigo"], []):
                _, ej_created = Ejercicio.objects.get_or_create(
                    submodulo=writing_sub,
                    texto_objetivo=prompt,
                    defaults={
                        "nivel_dificultad": nivel_data["codigo"],
                        "contenido_json": {},
                    },
                )
                if ej_created:
                    created_ejercicios += 1

            for prompt in WRITING_QUESTIONS.get(nivel_data["codigo"], []):
                for bank_ctx in ("DIAGNOSTIC", "PROMOTION_EXAM"):
                    _, q_created = Question.objects.get_or_create(
                        level=nivel_data["codigo"],
                        question_type="WRITING",
                        bank_context=bank_ctx,
                        text=prompt,
                    )
                    if q_created:
                        created_questions += 1

        self.stdout.write(self.style.SUCCESS(
            f"Seed complete: {created_niveles} niveles, "
            f"{created_submodulos} submodulos, "
            f"{created_ejercicios} ejercicios, "
            f"{created_questions} questions created"
        ))
        self.stdout.write(
            f"Totals: {NivelMCER.objects.count()} niveles, "
            f"{Submodulo.objects.count()} submodulos, "
            f"{Ejercicio.objects.count()} ejercicios, "
            f"{Question.objects.filter(question_type='WRITING').count()} writing questions"
        )
