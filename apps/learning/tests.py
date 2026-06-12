from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.authentication.models import Perfil
from apps.curriculum.models import NivelMCER, Submodulo
from apps.learning.models import SesionEntrevista

User = get_user_model()


class SesionEntrevistaTests(TestCase):
    """SesionEntrevista persists FKs, defaults, and JSON round-trip."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="lucia", email="lucia@example.com", password="x"
        )
        self.perfil = Perfil.objects.get(usuario=self.user)
        self.nivel = NivelMCER.objects.create(codigo="B1", orden=3)
        self.submodulo = Submodulo.objects.create(
            nivel=self.nivel, tipo="entrevista", orden=1
        )

    def test_fk_to_perfil_and_submodulo_persists(self):
        sesion = SesionEntrevista.objects.create(
            perfil=self.perfil,
            submodulo=self.submodulo,
        )

        sesion.refresh_from_db()
        self.assertEqual(sesion.perfil, self.perfil)
        self.assertEqual(sesion.submodulo, self.submodulo)

    def test_estado_defaults_to_en_curso(self):
        sesion = SesionEntrevista.objects.create(
            perfil=self.perfil,
            submodulo=self.submodulo,
        )

        sesion.refresh_from_db()
        self.assertEqual(sesion.estado, "EN_CURSO")

    def test_transcripcion_json_round_trips_dict(self):
        data = {"turns": [{"role": "user", "text": "Hello"}]}
        sesion = SesionEntrevista.objects.create(
            perfil=self.perfil,
            submodulo=self.submodulo,
            transcripcion_json=data,
        )

        sesion.refresh_from_db()
        self.assertEqual(sesion.transcripcion_json, data)

    def test_session_retrievable_with_recorded_puntaje(self):
        SesionEntrevista.objects.create(
            perfil=self.perfil,
            submodulo=self.submodulo,
            puntaje=Decimal("82.50"),
            estado="FINALIZADA",
        )

        sesiones = SesionEntrevista.objects.filter(
            perfil=self.perfil, submodulo=self.submodulo
        )
        self.assertEqual(sesiones.count(), 1)
        self.assertEqual(sesiones.first().puntaje, Decimal("82.50"))
