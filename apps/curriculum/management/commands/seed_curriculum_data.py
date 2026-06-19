from django.core.management.base import BaseCommand

from apps.curriculum.models import Ejercicio, NivelMCER, Submodulo

NIVELES = [
    {"codigo": "A1", "orden": 1, "parametros_json": {"nombre_descriptivo": "Principiante (A1)"}},
    {"codigo": "A2", "orden": 2, "parametros_json": {"nombre_descriptivo": "Elemental (A2)"}},
    {"codigo": "B1", "orden": 3, "parametros_json": {"nombre_descriptivo": "Intermedio (B1)"}},
]

SUBMODULO_TIPOS = [
    ("vocabulario", 1),
    ("musica", 2),
    ("entrevista", 3),
]

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


class Command(BaseCommand):
    help = "Seed NivelMCER, Submodulos, and music Ejercicios for all levels"

    def handle(self, *args, **options):
        created_niveles = 0
        created_submodulos = 0
        created_ejercicios = 0

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

        self.stdout.write(self.style.SUCCESS(
            f"Seed complete: {created_niveles} niveles, "
            f"{created_submodulos} submodulos, "
            f"{created_ejercicios} ejercicios created"
        ))
        self.stdout.write(
            f"Totals: {NivelMCER.objects.count()} niveles, "
            f"{Submodulo.objects.count()} submodulos, "
            f"{Ejercicio.objects.filter(submodulo__tipo='musica').count()} music ejercicios"
        )
