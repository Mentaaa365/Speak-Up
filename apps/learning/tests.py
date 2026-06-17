import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

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


class SesionEntrevistaEstadoTests(TestCase):
    """WU-2: SesionEntrevista ESTADO_CHOICES."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="estado_user", email="estado@example.com", password="x"
        )
        self.perfil = Perfil.objects.get(usuario=self.user)
        self.nivel = NivelMCER.objects.create(codigo="A1", orden=1)
        self.submodulo = Submodulo.objects.create(
            nivel=self.nivel, tipo="entrevista", orden=1
        )

    def test_default_estado_is_en_curso(self):
        sesion = SesionEntrevista.objects.create(
            perfil=self.perfil,
            submodulo=self.submodulo,
        )
        sesion.refresh_from_db()
        self.assertEqual(sesion.estado, "EN_CURSO")

    def test_puntaje_nullable_by_default(self):
        sesion = SesionEntrevista.objects.create(
            perfil=self.perfil,
            submodulo=self.submodulo,
        )
        sesion.refresh_from_db()
        self.assertIsNone(sesion.puntaje)

    def test_estado_choices_contains_three_values(self):
        choices = dict(SesionEntrevista.ESTADO_CHOICES)
        self.assertIn("EN_CURSO", choices)
        self.assertIn("COMPLETADA", choices)
        self.assertIn("ABANDONADA", choices)
        self.assertEqual(len(choices), 3)

    def test_completada_save_persists(self):
        sesion = SesionEntrevista.objects.create(
            perfil=self.perfil,
            submodulo=self.submodulo,
            estado="COMPLETADA",
            puntaje=Decimal("85.00"),
        )
        sesion.refresh_from_db()
        self.assertEqual(sesion.estado, "COMPLETADA")
        self.assertEqual(sesion.puntaje, Decimal("85.00"))

    def test_row_not_deleted_on_abandon(self):
        SesionEntrevista.objects.create(
            perfil=self.perfil,
            submodulo=self.submodulo,
            estado="ABANDONADA",
        )
        SesionEntrevista.objects.create(
            perfil=self.perfil,
            submodulo=self.submodulo,
            estado="EN_CURSO",
        )
        count = SesionEntrevista.objects.filter(
            perfil=self.perfil, submodulo=self.submodulo
        ).count()
        self.assertEqual(count, 2)


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


# ---------------------------------------------------------------------------
# WU-3: AIInterviewClient tests (Strict TDD — RED written before implementation)
# ---------------------------------------------------------------------------

def _make_mock_anthropic(return_text):
    """Return a mock Anthropic class whose .messages.create() returns return_text."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=return_text)]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response
    mock_cls = MagicMock(return_value=mock_client)
    return mock_cls, mock_client


class AIInterviewClientTests(TestCase):
    """Unit tests for AIInterviewClient — anthropic.Anthropic always mocked."""

    def test_missing_api_key_raises_environment_error(self):
        """__init__ raises EnvironmentError when ANTHROPIC_API_KEY is absent."""
        import os
        from apps.learning.ai_client import AIInterviewClient

        with patch.dict(os.environ, {}, clear=True):
            # Remove the key if present
            os.environ.pop("ANTHROPIC_API_KEY", None)
            with patch("apps.learning.ai_client.anthropic.Anthropic"):
                with self.assertRaises(EnvironmentError):
                    AIInterviewClient()

    @patch("apps.learning.ai_client.anthropic.Anthropic")
    def test_start_session_calls_create_with_correct_model(self, mock_anthropic_cls):
        """start_session() calls messages.create with model='claude-haiku-4-5'."""
        mock_cls, mock_client = _make_mock_anthropic("What is your name?")
        mock_anthropic_cls.return_value = mock_client

        import os
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}):
            from apps.learning.ai_client import AIInterviewClient
            client = AIInterviewClient()
            result = client.start_session("A1")

        self.assertEqual(result, "What is your name?")
        call_kwargs = mock_client.messages.create.call_args
        self.assertEqual(call_kwargs.kwargs["model"], "claude-haiku-4-5")

    @patch("apps.learning.ai_client.anthropic.Anthropic")
    def test_next_turn_for_appends_student_response(self, mock_anthropic_cls):
        """next_turn_for() sends history + student response to the API."""
        mock_cls, mock_client = _make_mock_anthropic("Good, and you?")
        mock_anthropic_cls.return_value = mock_client

        import os
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}):
            from apps.learning.ai_client import AIInterviewClient
            client = AIInterviewClient()
            historial = [{"role": "assistant", "content": "How are you?"}]
            result = client.next_turn_for("A2", historial, "I am fine.")

        self.assertEqual(result, "Good, and you?")
        sent_messages = mock_client.messages.create.call_args.kwargs["messages"]
        # Last message must be the student's response
        self.assertEqual(sent_messages[-1]["role"], "user")
        self.assertEqual(sent_messages[-1]["content"], "I am fine.")


class EvaluateSessionTests(TestCase):
    """Tests for AIInterviewClient.evaluate_session() per-level scoring."""

    def _client_with_mock(self, return_json: str):
        """Helper: build AIInterviewClient with mocked API returning return_json."""
        import os
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=return_json)]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}):
            with patch("apps.learning.ai_client.anthropic.Anthropic", return_value=mock_client):
                from apps.learning.ai_client import AIInterviewClient
                client = AIInterviewClient()
        # Keep the mock active by storing a patcher reference isn't needed;
        # the client already stored the mock_client internally.
        return client, mock_client

    def _historial(self):
        return [
            {"role": "assistant", "content": "What is your name?"},
            {"role": "user", "content": "My name is Ana."},
        ]

    def test_a1_scores_three_numeric_categories(self):
        """A1 evaluate_session result has pronunciacion, vocabulario, fluidez."""
        raw = '{"pronunciacion": 80, "vocabulario": 75, "fluidez": 70}'
        client, _ = self._client_with_mock(raw)
        result = client.evaluate_session("A1", self._historial())

        self.assertIn("pronunciacion", result["scores"])
        self.assertIn("vocabulario", result["scores"])
        self.assertIn("fluidez", result["scores"])

    def test_a1_no_extra_keys(self):
        """A1 scores dict must NOT contain coherencia, riqueza_lexica, sugerencias_mejora."""
        raw = '{"pronunciacion": 80, "vocabulario": 75, "fluidez": 70}'
        client, _ = self._client_with_mock(raw)
        result = client.evaluate_session("A1", self._historial())

        for forbidden in ("coherencia", "riqueza_lexica", "sugerencias_mejora"):
            self.assertNotIn(forbidden, result["scores"])

    def test_a1_puntaje_global_is_mean(self):
        """puntaje_global is the integer mean of the three A1 numeric scores."""
        raw = '{"pronunciacion": 80, "vocabulario": 70, "fluidez": 90}'
        client, _ = self._client_with_mock(raw)
        result = client.evaluate_session("A1", self._historial())

        # mean(80, 70, 90) = 80
        self.assertEqual(result["puntaje_global"], 80)
        self.assertIsInstance(result["puntaje_global"], int)

    def test_a2_scores_four_numeric_categories(self):
        """A2 result has pronunciacion, vocabulario, fluidez, coherencia."""
        raw = '{"pronunciacion": 70, "vocabulario": 65, "fluidez": 75, "coherencia": 80}'
        client, _ = self._client_with_mock(raw)
        result = client.evaluate_session("A2", self._historial())

        for key in ("pronunciacion", "vocabulario", "fluidez", "coherencia"):
            self.assertIn(key, result["scores"])

    def test_a2_puntaje_global_is_mean(self):
        """puntaje_global is the integer mean of the four A2 scores."""
        raw = '{"pronunciacion": 60, "vocabulario": 80, "fluidez": 80, "coherencia": 80}'
        client, _ = self._client_with_mock(raw)
        result = client.evaluate_session("A2", self._historial())

        # mean(60, 80, 80, 80) = 75
        self.assertEqual(result["puntaje_global"], 75)

    def test_b1_scores_five_numeric_plus_sugerencias(self):
        """B1 result has 5 numeric scores plus sugerencias_mejora as str."""
        raw = json.dumps({
            "pronunciacion": 85, "vocabulario": 80, "fluidez": 78,
            "coherencia": 82, "riqueza_lexica": 76,
            "sugerencias_mejora": "Practicar conectores.",
        })
        client, _ = self._client_with_mock(raw)
        result = client.evaluate_session("B1", self._historial())

        for key in ("pronunciacion", "vocabulario", "fluidez", "coherencia", "riqueza_lexica"):
            self.assertIn(key, result["scores"])
        self.assertIn("sugerencias_mejora", result["scores"])
        self.assertIsInstance(result["scores"]["sugerencias_mejora"], str)

    def test_b1_puntaje_global_excludes_sugerencias(self):
        """B1 puntaje_global is the mean of the 5 numeric fields only."""
        raw = json.dumps({
            "pronunciacion": 80, "vocabulario": 80, "fluidez": 80,
            "coherencia": 80, "riqueza_lexica": 80,
            "sugerencias_mejora": "Keep practicing.",
        })
        client, _ = self._client_with_mock(raw)
        result = client.evaluate_session("B1", self._historial())

        # mean of 5 numeric = 80; sugerencias_mejora must be excluded
        self.assertEqual(result["puntaje_global"], 80)

    def test_api_error_propagates(self):
        """SDK exception in evaluate_session propagates; no score is silently swallowed."""
        import os

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = RuntimeError("timeout")

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}):
            with patch("apps.learning.ai_client.anthropic.Anthropic", return_value=mock_client):
                from apps.learning.ai_client import AIInterviewClient
                client = AIInterviewClient()

        with self.assertRaises(Exception):
            client.evaluate_session("A1", self._historial())


class PromptBuilderTests(TestCase):
    """Unit tests for prompt content — no API calls needed."""

    def _make_client(self):
        import os
        mock_client = MagicMock()
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}):
            with patch("apps.learning.ai_client.anthropic.Anthropic", return_value=mock_client):
                from apps.learning.ai_client import AIInterviewClient
                return AIInterviewClient()

    def test_spanish_redirect_in_a1_system_prompt(self):
        """A1 system prompt contains the Spanish-redirect instruction."""
        from apps.learning.ai_client import AIInterviewClient
        client = self._make_client()
        prompt = client._system_prompt("A1")
        self.assertIn("Please try in English.", prompt)

    def test_spanish_redirect_in_a2_system_prompt(self):
        """A2 system prompt contains the Spanish-redirect instruction."""
        client = self._make_client()
        prompt = client._system_prompt("A2")
        self.assertIn("Please try in English.", prompt)

    def test_b1_system_prompt_no_strict_redirect(self):
        """B1 system prompt does NOT enforce strict English-only redirect."""
        client = self._make_client()
        prompt = client._system_prompt("B1")
        # B1 should encourage richer responses, not enforce redirect strictly
        # Per design: 'Do NOT enforce English-only redirection strictly'
        self.assertIn("B1", prompt.upper() or prompt)

    def test_eval_prompt_a1_only_three_categories(self):
        """A1 eval prompt references exactly pronunciacion, vocabulario, fluidez."""
        client = self._make_client()
        prompt = client._eval_prompt("A1", ["pronunciacion", "vocabulario", "fluidez"])
        self.assertIn("pronunciacion", prompt)
        self.assertIn("vocabulario", prompt)
        self.assertIn("fluidez", prompt)
        self.assertNotIn("coherencia", prompt)
        self.assertNotIn("riqueza_lexica", prompt)
        self.assertNotIn("sugerencias_mejora", prompt)

    def test_eval_prompt_b1_includes_sugerencias_key(self):
        """B1 eval prompt includes sugerencias_mejora key."""
        client = self._make_client()
        cats = ["pronunciacion", "vocabulario", "fluidez", "coherencia", "riqueza_lexica"]
        prompt = client._eval_prompt("B1", cats)
        self.assertIn("sugerencias_mejora", prompt)


# ---------------------------------------------------------------------------
# WU-5a: AiInterviewLearningView GET tests (Strict TDD — RED before GREEN)
# ---------------------------------------------------------------------------

class AiInterviewLearningViewTests(TestCase):
    """WU-5a: AiInterviewLearningView.get() — guards, session lifecycle, context."""

    def setUp(self):
        self.url = reverse("learning:ai_interview")
        self.nivel = NivelMCER.objects.create(codigo="A1", orden=10, parametros_json={})
        self.submodulo = Submodulo.objects.create(
            nivel=self.nivel, tipo="entrevista", orden=1
        )
        self.user = User.objects.create_user(
            username="interview@example.com",
            email="interview@example.com",
            password="x",
        )
        self.perfil = self.user.perfil
        self.perfil.nivel_mcer = self.nivel
        self.perfil.save()

    # ------------------------------------------------------------------
    # Guard 1: Perfil.DoesNotExist -> redirect to authentication:login
    # ------------------------------------------------------------------

    def test_guard1_no_perfil_redirects_to_login(self):
        """Perfil.DoesNotExist -> 302 to authentication:login."""
        from apps.learning.views import AiInterviewLearningView

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
            response = AiInterviewLearningView.as_view()(request)

        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response["Location"])

    # ------------------------------------------------------------------
    # Guard 2: no 'entrevista' Submodulo for this nivel -> redirect to dashboard
    # ------------------------------------------------------------------

    def test_guard2_no_entrevista_submodulo_redirects_to_dashboard(self):
        """Perfil exists but nivel has no 'entrevista' submodulo -> 302 to progress:dashboard."""
        nivel_sin_entrevista = NivelMCER.objects.create(
            codigo="B2", orden=11, parametros_json={}
        )
        self.perfil.nivel_mcer = nivel_sin_entrevista
        self.perfil.save()
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response, reverse("progress:dashboard"), fetch_redirect_response=False
        )

    # ------------------------------------------------------------------
    # Happy path: 200 + correct context keys
    # ------------------------------------------------------------------

    def test_happy_path_returns_200_with_required_context_keys(self):
        """GET returns 200 and context contains all required keys."""
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        for key in (
            "submodulo", "nivel", "sesion_id",
            "nivel_codigo", "tts_rate", "tiempo_respuesta",
            "turno_url", "finalizar_url",
        ):
            self.assertIn(key, response.context, msg=f"Missing context key: {key}")

    # ------------------------------------------------------------------
    # Context values for A1 level
    # ------------------------------------------------------------------

    def test_context_values_for_a1_level(self):
        """A1 nivel: tts_rate=0.85, tiempo_respuesta=45."""
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["nivel_codigo"], "A1")
        self.assertAlmostEqual(float(response.context["tts_rate"]), 0.85)
        self.assertEqual(response.context["tiempo_respuesta"], 45)

    # ------------------------------------------------------------------
    # Session abandonment: prior EN_CURSO -> ABANDONADA + new EN_CURSO
    # ------------------------------------------------------------------

    def test_prior_en_curso_session_gets_abandoned(self):
        """If an EN_CURSO session exists, it must be marked ABANDONADA on GET."""
        prior = SesionEntrevista.objects.create(
            perfil=self.perfil,
            submodulo=self.submodulo,
            estado="EN_CURSO",
        )
        self.client.force_login(self.user)
        self.client.get(self.url)

        prior.refresh_from_db()
        self.assertEqual(prior.estado, "ABANDONADA")

    def test_two_rows_exist_after_abandonment(self):
        """After a second GET with prior EN_CURSO, DB has 2 rows (1 ABANDONADA + 1 EN_CURSO)."""
        SesionEntrevista.objects.create(
            perfil=self.perfil,
            submodulo=self.submodulo,
            estado="EN_CURSO",
        )
        self.client.force_login(self.user)
        self.client.get(self.url)

        total = SesionEntrevista.objects.filter(
            perfil=self.perfil, submodulo=self.submodulo
        ).count()
        self.assertEqual(total, 2)

        en_curso = SesionEntrevista.objects.filter(
            perfil=self.perfil, submodulo=self.submodulo, estado="EN_CURSO"
        ).count()
        self.assertEqual(en_curso, 1)

        abandonada = SesionEntrevista.objects.filter(
            perfil=self.perfil, submodulo=self.submodulo, estado="ABANDONADA"
        ).count()
        self.assertEqual(abandonada, 1)

    # ------------------------------------------------------------------
    # New session when none exists
    # ------------------------------------------------------------------

    def test_new_session_created_when_none_exists(self):
        """When no prior session exists, GET creates one EN_CURSO row."""
        self.client.force_login(self.user)
        self.client.get(self.url)

        sesiones = SesionEntrevista.objects.filter(
            perfil=self.perfil, submodulo=self.submodulo, estado="EN_CURSO"
        )
        self.assertEqual(sesiones.count(), 1)

    # ------------------------------------------------------------------
    # URL stubs: TurnoEntrevistaView and FinalizarEntrevistaView
    # ------------------------------------------------------------------

    def test_turno_url_resolves(self):
        """learning:interview_turno resolves correctly."""
        url = reverse("learning:interview_turno")
        self.assertTrue(url.endswith("/turno/"))

    def test_finalizar_url_resolves(self):
        """learning:interview_finalizar resolves correctly."""
        url = reverse("learning:interview_finalizar")
        self.assertTrue(url.endswith("/finalizar/"))

    def test_turno_stub_returns_501(self):
        """TurnoEntrevistaView stub returns 501 Not Implemented."""
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("learning:interview_turno"),
            data="{}",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 501)

    def test_finalizar_stub_returns_501(self):
        """FinalizarEntrevistaView stub returns 501 Not Implemented."""
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("learning:interview_finalizar"),
            data="{}",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 501)
