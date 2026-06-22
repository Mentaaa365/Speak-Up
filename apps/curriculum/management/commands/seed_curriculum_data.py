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
    ("writing", 2),
    ("musica", 3),
    ("entrevista", 4),
]

VOCABULARY_EXERCISES = {
    "A1": [
        {
            "texto_objetivo": "My name is John",
            "contenido_json": {
                "imagen_url": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&h=300&fit=crop",
            },
        },
        {
            "texto_objetivo": "I am twenty years old",
            "contenido_json": {
                "imagen_url": "https://images.unsplash.com/photo-1529333166437-7750a6dd5a70?w=400&h=300&fit=crop",
            },
        },
        {
            "texto_objetivo": "I have one sister",
            "contenido_json": {
                "imagen_url": "https://images.unsplash.com/photo-1511895426328-dc8714191300?w=400&h=300&fit=crop",
            },
        },
        {
            "texto_objetivo": "I like to eat macaroni",
            "contenido_json": {
                "imagen_url": "https://images.unsplash.com/photo-1551462147-ff29053bfc14?w=400&h=300&fit=crop",
            },
        },
        {
            "texto_objetivo": "I wake up at seven in the morning",
            "contenido_json": {
                "imagen_url": "https://images.unsplash.com/photo-1495364141860-b0d03eccd065?w=400&h=300&fit=crop",
            },
        },
        {
            "texto_objetivo": "I go to school by bus",
            "contenido_json": {
                "imagen_url": "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?w=400&h=300&fit=crop",
            },
        },
        {
            "texto_objetivo": "My favorite color is blue",
            "contenido_json": {
                "imagen_url": "https://images.unsplash.com/photo-1579546929518-9e396f3cc809?w=400&h=300&fit=crop",
            },
        },
        {
            "texto_objetivo": "I like to play with my dog",
            "contenido_json": {
                "imagen_url": "https://images.unsplash.com/photo-1587300003388-59208cc962cb?w=400&h=300&fit=crop",
            },
        },
        {
            "texto_objetivo": "Nice to meet you",
            "contenido_json": {
                "imagen_url": "https://images.unsplash.com/photo-1521791136064-7986c2920216?w=400&h=300&fit=crop",
            },
        },
        {
            "texto_objetivo": "I am from Ecuador",
            "contenido_json": {
                "imagen_url": "https://images.unsplash.com/photo-1547995886-6dc09384c6e6?w=400&h=300&fit=crop",
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
        {
            "texto_objetivo": "He is cooking dinner",
            "contenido_json": {
                "imagen_url": "https://images.unsplash.com/photo-1556910103-1c02745aae4d?w=400&h=300&fit=crop",
            },
        },
        {
            "texto_objetivo": "We went to the beach last weekend",
            "contenido_json": {
                "imagen_url": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=400&h=300&fit=crop",
            },
        },
        {
            "texto_objetivo": "The children are doing their homework",
            "contenido_json": {
                "imagen_url": "https://images.unsplash.com/photo-1503676260728-1c00da094a0b?w=400&h=300&fit=crop",
            },
        },
        {
            "texto_objetivo": "My mother works at the hospital",
            "contenido_json": {
                "imagen_url": "https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?w=400&h=300&fit=crop",
            },
        },
        {
            "texto_objetivo": "I usually wake up at seven",
            "contenido_json": {
                "imagen_url": "https://images.unsplash.com/photo-1495364141860-b0d03eccd065?w=400&h=300&fit=crop",
            },
        },
        {
            "texto_objetivo": "She is wearing a red dress",
            "contenido_json": {
                "imagen_url": "https://images.unsplash.com/photo-1595777457583-95e059d581b8?w=400&h=300&fit=crop",
            },
        },
        {
            "texto_objetivo": "The dog is running in the garden",
            "contenido_json": {
                "imagen_url": "https://images.unsplash.com/photo-1530281700549-e82e7bf110d6?w=400&h=300&fit=crop",
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
        {
            "texto_objetivo": "The government should invest more in renewable energy sources",
            "contenido_json": {},
        },
        {
            "texto_objetivo": "Many students struggle to balance their academic and social lives",
            "contenido_json": {},
        },
        {
            "texto_objetivo": "Technological advancements have completely transformed the way we communicate",
            "contenido_json": {},
        },
        {
            "texto_objetivo": "It is essential that every citizen understands their rights and responsibilities",
            "contenido_json": {},
        },
        {
            "texto_objetivo": "The research findings suggest that regular exercise improves mental health",
            "contenido_json": {},
        },
        {
            "texto_objetivo": "Although the project was challenging we managed to finish it on time",
            "contenido_json": {},
        },
        {
            "texto_objetivo": "Climate change remains one of the most pressing issues of our generation",
            "contenido_json": {},
        },
    ],
}

MUSIC_EXERCISES = {
    "A1": [
        {
            "titulo": "You Are My Sunshine",
            "contenido_json": {
                "audio_url": "/static/audio/you_are_my_sunshine.mp3",
                "lrc": (
                    "[00:05.00]You are my sunshine my only sunshine\n"
                    "[00:12.00]You make me happy when skies are gray\n"
                    "[00:19.00]You will never know dear how much I love you\n"
                    "[00:26.00]Please do not take my sunshine away\n"
                ),
            },
        },
    ],
    "A2": [
        {
            "titulo": "Count On Me - Bruno Mars",
            "contenido_json": {
                "audio_url": "/static/audio/count_on_me.mp3",
                "lrc": (
                    "[00:15.00]If you ever find yourself stuck in the middle of the sea\n"
                    "[00:22.00]I will sail the world to find you\n"
                    "[00:27.00]If you ever find yourself lost in the dark and you cannot see\n"
                    "[00:34.00]I will be the light to guide you\n"
                    "[00:40.00]We find out what we are made of\n"
                    "[00:44.00]When we are called to help our friends in need\n"
                    "[00:50.00]You can count on me like one two three\n"
                    "[00:55.00]I will be there\n"
                ),
            },
        },
    ],
    "B1": [
        {
            "titulo": "Hello - Adele",
            "contenido_json": {
                "audio_url": "/static/audio/hello.mp3",
                "lrc": (
                    "[00:05.00]Hello it is me\n"
                    "[00:10.00]I was wondering if after all these years you would like to meet\n"
                    "[00:18.00]To go over everything\n"
                    "[00:22.00]They say that time is supposed to heal you\n"
                    "[00:26.00]But I have not done much healing\n"
                    "[00:32.00]Hello can you hear me\n"
                    "[00:38.00]I am in California dreaming about who we used to be\n"
                    "[00:46.00]When we were younger and free\n"
                ),
            },
        },
    ],
}


WRITING_EXERCISES = {
    "A1": [
        "Describe your family in 2-3 simple sentences.",
        "Write about what you do every day.",
        "Write 3 sentences about your favorite animal.",
        "Describe what you eat for breakfast.",
        "Write about your best friend.",
        "Describe the weather today in 2 sentences.",
        "Write about your favorite sport.",
    ],
    "A2": [
        "Describe your last vacation. Where did you go and what did you do?",
        "Write about your favorite hobby and explain why you enjoy it.",
        "Write a short email to a friend inviting them to your birthday party.",
        "Describe your dream job and why you would like it.",
        "Compare your city now to how it was five years ago.",
        "Write about a movie you saw recently and whether you liked it.",
        "Explain what you usually do on a rainy weekend.",
    ],
    "B1": [
        "Write an essay about the advantages and disadvantages of social media for students.",
        "Describe a challenge you overcame and explain what you learned from the experience.",
        "Discuss whether students should have less homework and why.",
        "Write about how technology will change education in the next ten years.",
        "Explain why learning a second language is important for your future.",
        "Write a review of a restaurant or cafe you visited recently.",
        "Discuss the pros and cons of living in a big city versus the countryside.",
    ],
}

WRITING_QUESTIONS = {
    "A1": [
        "Write 2-3 sentences introducing yourself: your name, age, and where you live.",
        "Describe your favorite food in simple sentences.",
        "Write about your family. How many brothers or sisters do you have?",
        "Describe your daily routine in 3 simple sentences.",
        "Write about your favorite animal and why you like it.",
    ],
    "A2": [
        "Write a short paragraph about your best friend and what you like to do together.",
        "Describe what you did last weekend in 3-5 sentences.",
        "Write about your favorite holiday and how you celebrate it.",
        "Describe your school or university. What do you study and what do you enjoy?",
        "Write a short email to a friend telling them about a movie you watched recently.",
    ],
    "B1": [
        "Write a paragraph explaining why learning English is important for your future.",
        "Describe a place you would like to visit and explain why it interests you.",
        "Write about the advantages and disadvantages of using social media.",
        "Describe a person you admire and explain why they inspire you.",
        "Write about how technology has changed the way people communicate.",
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
