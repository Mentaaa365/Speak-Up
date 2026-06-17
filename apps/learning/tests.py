import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse

from apps.authentication.models import Perfil
from apps.curriculum.models import Ejercicio, NivelMCER, Submodulo
from apps.learning.models import SesionEntrevista
from apps.learning.views import VocabularyLearningView
from apps.progress.models import IntentoEjercicio

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


class VocabularyLearningViewTests(TestCase):
    """WU-4: VocabularyLearningView — guards and context."""

    def setUp(self):
        self.url = reverse("learning:vocabulary")
        self.nivel = NivelMCER.objects.create(codigo="A2", orden=2, parametros_json={})
        self.submodulo = Submodulo.objects.create(
            nivel=self.nivel, tipo="vocabulario", orden=1
        )
        self.ejercicio1 = Ejercicio.objects.create(
            submodulo=self.submodulo,
            contenido_json={},
            nivel_dificultad="A2",
            texto_objetivo="appointment",
        )
        self.ejercicio2 = Ejercicio.objects.create(
            submodulo=self.submodulo,
            contenido_json={},
            nivel_dificultad="A2",
            texto_objetivo="schedule",
        )
        self.user = User.objects.create_user(
            username="vocab@example.com",
            email="vocab@example.com",
            password="x",
        )
        self.perfil = self.user.perfil
        self.perfil.nivel_mcer = self.nivel
        self.perfil.save()

    def test_guard1_no_perfil_redirects_to_login(self):
        """Perfil.DoesNotExist in view -> 302 to authentication:login.

        force_login internally triggers post_save which recreates a deleted
        Perfil (signal side-effect). To test the guard we bypass the session
        cookie path and call the view directly via RequestFactory with the
        Perfil lookup patched to raise DoesNotExist.
        """
        factory = RequestFactory()
        request = factory.get(self.url)
        request.user = self.user

        with patch(
            "apps.learning.views.Perfil.objects.select_related",
            return_value=type(
                "qs",
                (),
                {"get": staticmethod(lambda **kw: (_ for _ in ()).throw(Perfil.DoesNotExist()))},
            )(),
        ):
            response = VocabularyLearningView.as_view()(request)

        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response["Location"])

    def test_guard2_no_vocabulario_submodulo_redirects_to_dashboard(self):
        """Perfil exists but nivel has no 'vocabulario' submodulo -> 302 to progress:dashboard."""
        nivel_sin_vocab = NivelMCER.objects.create(
            codigo="B2", orden=4, parametros_json={}
        )
        self.perfil.nivel_mcer = nivel_sin_vocab
        self.perfil.save()
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("progress:dashboard"), fetch_redirect_response=False)

    def test_happy_path_context_keys_present(self):
        """200 response with all required context keys."""
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        for key in ("submodulo", "ejercicios", "ejercicios_json", "guardar_url"):
            self.assertIn(key, response.context, msg=f"Missing context key: {key}")

    def test_ejercicios_json_is_valid_json_with_id_and_texto_objetivo(self):
        """ejercicios_json is valid JSON and each entry has 'id' and 'texto_objetivo'."""
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        raw = response.context["ejercicios_json"]
        parsed = json.loads(raw)
        self.assertIsInstance(parsed, list)
        self.assertGreater(len(parsed), 0)
        for entry in parsed:
            self.assertIn("id", entry)
            self.assertIn("texto_objetivo", entry)
        textos = {e["texto_objetivo"] for e in parsed}
        self.assertIn("appointment", textos)
        self.assertIn("schedule", textos)
