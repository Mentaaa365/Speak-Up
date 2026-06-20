from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import models
from django.test import TestCase
from django.urls import reverse

from apps.curriculum.models import Ejercicio, NivelMCER, Submodulo
from apps.exams.models import ExamenIntento
from apps.progress.models import IntentoEjercicio

User = get_user_model()


class DashboardURLsTests(TestCase):
    """Dashboard context URLs must use reverse(), not hardcoded strings. (Bug 5)"""

    def setUp(self):
        self.nivel = NivelMCER.objects.create(
            codigo="A1", orden=1, parametros_json={}
        )
        submodulo = Submodulo.objects.create(nivel=self.nivel, tipo="vocabulario", orden=1)
        self.user = User.objects.create_user(
            username="urls@example.com", email="urls@example.com", password="x"
        )
        self.perfil = self.user.perfil
        self.perfil.nivel_mcer = self.nivel
        self.perfil.save()
        self.client.force_login(self.user)

    def test_vocabulario_url_resolves_correctly(self):
        response = self.client.get(reverse("progress:dashboard"))
        submodulos = response.context["submodulos"]
        vocab = next((s for s in submodulos if "Vocabulario" in s["nombre"]), None)
        self.assertIsNotNone(vocab)
        self.assertEqual(str(vocab["url"]), reverse("learning:vocabulary"))

    def test_examen_context_has_url_key(self):
        response = self.client.get(reverse("progress:dashboard"))
        self.assertIn("url", response.context["examen"])

    def test_examen_url_resolves_to_exams_start(self):
        response = self.client.get(reverse("progress:dashboard"))
        self.assertEqual(str(response.context["examen"]["url"]), reverse("exams:start"))


class ProgressDetailTemplateDynamicTests(TestCase):
    """progress_detail.html must render context values, not hardcoded mockup data."""

    def setUp(self):
        self.nivel = NivelMCER.objects.create(
            codigo="A1", orden=1, parametros_json={"nombre_descriptivo": "Principiante"}
        )
        self.user = User.objects.create_user(
            username="detail@example.com", email="detail@example.com", password="x"
        )
        self.perfil = self.user.perfil
        self.perfil.nivel_mcer = self.nivel
        self.perfil.save()
        self.client.force_login(self.user)

    def test_detail_shows_actual_nivel_not_hardcoded_a2(self):
        response = self.client.get(reverse("progress:detail"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # The hardcoded template always says "Nivel actual: A2" — fix must show A1
        self.assertNotIn("Nivel actual: A2", content)
        self.assertIn("A1", content)

    def test_detail_global_progress_is_zero_for_new_user(self):
        response = self.client.get(reverse("progress:detail"))
        self.assertEqual(response.context["global_progress"], 0)

    def test_detail_template_does_not_contain_hardcoded_33_percent(self):
        response = self.client.get(reverse("progress:detail"))
        # The mockup had ">33%<" hardcoded; after the fix it must not appear
        self.assertNotIn(">33%<", response.content.decode())


class DashboardIntentosRestantesTests(TestCase):
    """intentos_restantes must reflect real ExamenIntento records, not a hardcoded 2."""

    def setUp(self):
        self.nivel = NivelMCER.objects.create(codigo="A1", orden=1, parametros_json={})
        self.user = User.objects.create_user(
            username="dash@example.com", email="dash@example.com", password="x"
        )
        self.perfil = self.user.perfil
        self.perfil.nivel_mcer = self.nivel
        self.perfil.save()
        self.client.force_login(self.user)

    def test_intentos_restantes_is_2_when_no_attempts_exist(self):
        response = self.client.get(reverse("progress:dashboard"))
        self.assertEqual(response.context["examen"]["intentos_restantes"], 2)

    def test_intentos_restantes_decrements_after_one_attempt(self):
        ExamenIntento.objects.create(
            perfil=self.perfil,
            tipo="PROMOCION",
            nivel_objetivo=self.nivel,
            puntaje=45,
        )
        response = self.client.get(reverse("progress:dashboard"))
        self.assertEqual(response.context["examen"]["intentos_restantes"], 1)

    def test_intentos_restantes_is_zero_after_two_attempts(self):
        ExamenIntento.objects.create(
            perfil=self.perfil, tipo="PROMOCION",
            nivel_objetivo=self.nivel, puntaje=40,
        )
        ExamenIntento.objects.create(
            perfil=self.perfil, tipo="PROMOCION",
            nivel_objetivo=self.nivel, puntaje=38,
        )
        response = self.client.get(reverse("progress:dashboard"))
        self.assertEqual(response.context["examen"]["intentos_restantes"], 0)

    def test_intentos_of_other_nivel_do_not_count(self):
        otro_nivel = NivelMCER.objects.create(codigo="A2", orden=2, parametros_json={})
        ExamenIntento.objects.create(
            perfil=self.perfil, tipo="PROMOCION",
            nivel_objetivo=otro_nivel, puntaje=40,
        )
        response = self.client.get(reverse("progress:dashboard"))
        self.assertEqual(response.context["examen"]["intentos_restantes"], 2)


class IntentoEjercicioModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="greta", email="greta@example.com", password="x"
        )
        self.perfil = self.user.perfil

        nivel = NivelMCER.objects.create(codigo="A1", orden=1)
        submodulo = Submodulo.objects.create(nivel=nivel, tipo="lectura", orden=1)
        self.ejercicio = Ejercicio.objects.create(
            submodulo=submodulo,
            contenido_json={"pregunta": "¿Cómo estás?"},
            nivel_dificultad="A1",
        )

    def test_multiple_attempts_allowed_for_same_perfil_ejercicio(self):
        IntentoEjercicio.objects.create(
            perfil=self.perfil, ejercicio=self.ejercicio, puntaje=50
        )
        # No unique_together — a second attempt for the same (perfil, ejercicio)
        # must NOT raise IntegrityError.
        IntentoEjercicio.objects.create(
            perfil=self.perfil, ejercicio=self.ejercicio, puntaje=90
        )

        self.assertEqual(
            IntentoEjercicio.objects.filter(
                perfil=self.perfil, ejercicio=self.ejercicio
            ).count(),
            2,
        )

    def test_reset_flips_prior_rows_inactive_and_inserts_new_active_row(self):
        first = IntentoEjercicio.objects.create(
            perfil=self.perfil, ejercicio=self.ejercicio, puntaje=50
        )

        # "Reset": deactivate prior attempts, then append a new active attempt.
        IntentoEjercicio.objects.filter(
            perfil=self.perfil, ejercicio=self.ejercicio, activo=True
        ).update(activo=False)
        second = IntentoEjercicio.objects.create(
            perfil=self.perfil, ejercicio=self.ejercicio, puntaje=75
        )

        first.refresh_from_db()

        # Count unchanged — nothing deleted, only appended.
        self.assertEqual(
            IntentoEjercicio.objects.filter(
                perfil=self.perfil, ejercicio=self.ejercicio
            ).count(),
            2,
        )
        self.assertFalse(first.activo)
        self.assertTrue(second.activo)

    def test_filter_activo_true_returns_only_current_rows(self):
        first = IntentoEjercicio.objects.create(
            perfil=self.perfil, ejercicio=self.ejercicio, puntaje=50
        )
        IntentoEjercicio.objects.filter(pk=first.pk).update(activo=False)
        second = IntentoEjercicio.objects.create(
            perfil=self.perfil, ejercicio=self.ejercicio, puntaje=75
        )

        current = IntentoEjercicio.objects.filter(
            perfil=self.perfil, ejercicio=self.ejercicio, activo=True
        )

        self.assertEqual(current.count(), 1)
        self.assertEqual(current.first().pk, second.pk)

    def test_history_query_without_activo_filter_returns_all_attempts(self):
        first = IntentoEjercicio.objects.create(
            perfil=self.perfil, ejercicio=self.ejercicio, puntaje=50
        )
        IntentoEjercicio.objects.filter(pk=first.pk).update(activo=False)
        IntentoEjercicio.objects.create(
            perfil=self.perfil, ejercicio=self.ejercicio, puntaje=75
        )

        history = IntentoEjercicio.objects.filter(
            perfil=self.perfil, ejercicio=self.ejercicio
        )

        self.assertEqual(history.count(), 2)

    def test_composite_index_on_perfil_ejercicio_activo_exists(self):
        index_names = {
            index.name
            for index in IntentoEjercicio._meta.indexes
        }
        self.assertIn("ix_intento_perfil_ej_activo", index_names)

        target = next(
            index
            for index in IntentoEjercicio._meta.indexes
            if index.name == "ix_intento_perfil_ej_activo"
        )
        self.assertEqual(list(target.fields), ["perfil", "ejercicio", "activo"])


class IntentoEjercicioTranscripcionTests(TestCase):
    """WU-1.T-2: transcripcion field on IntentoEjercicio."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="trans@example.com", email="trans@example.com", password="x"
        )
        self.perfil = self.user.perfil

        nivel = NivelMCER.objects.create(codigo="A1", orden=1)
        submodulo = Submodulo.objects.create(nivel=nivel, tipo="vocabulario", orden=1)
        self.ejercicio = Ejercicio.objects.create(
            submodulo=submodulo,
            contenido_json={},
            nivel_dificultad="A1",
        )

    def test_transcripcion_round_trip(self):
        """An intento saved with transcripcion='appointment' round-trips correctly."""
        intento = IntentoEjercicio.objects.create(
            perfil=self.perfil,
            ejercicio=self.ejercicio,
            puntaje=85,
            transcripcion="appointment",
        )
        intento.refresh_from_db()

        self.assertEqual(intento.transcripcion, "appointment")

    def test_transcripcion_nullable(self):
        """An intento saved without transcripcion stores NULL — no error raised."""
        intento = IntentoEjercicio.objects.create(
            perfil=self.perfil,
            ejercicio=self.ejercicio,
            puntaje=70,
        )
        intento.refresh_from_db()

        self.assertIsNone(intento.transcripcion)


class GuardarEjercicioViewTests(TestCase):
    """WU-3.T-1: GuardarEjercicioView — success + error paths (7 scenarios)."""

    def setUp(self):
        self.nivel = NivelMCER.objects.create(codigo="A2", orden=2, parametros_json={})
        self.submodulo = Submodulo.objects.create(
            nivel=self.nivel, tipo="vocabulario", orden=1
        )
        self.ejercicio = Ejercicio.objects.create(
            submodulo=self.submodulo,
            contenido_json={},
            nivel_dificultad="A2",
            texto_objetivo="appointment",
        )
        self.user = User.objects.create_user(
            username="vocab@example.com", email="vocab@example.com", password="x"
        )
        self.perfil = self.user.perfil
        self.perfil.nivel_mcer = self.nivel
        self.perfil.save()
        self.url = reverse("progress:guardar_ejercicio")

    def _post_json(self, data):
        import json
        return self.client.post(
            self.url,
            data=json.dumps(data),
            content_type="application/json",
        )

    def test_sc01_approved_attempt_returns_200_aprobado_true(self):
        """POST puntaje=85, transcripcion='appointment' -> 200, aprobado=True, intento creado."""
        self.client.force_login(self.user)
        response = self._post_json(
            {"ejercicio_id": self.ejercicio.pk, "puntaje": 85, "transcripcion": "appointment"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["aprobado"])
        self.assertEqual(
            IntentoEjercicio.objects.filter(
                perfil=self.perfil, ejercicio=self.ejercicio, activo=True
            ).count(),
            1,
        )

    def test_sc01_previous_active_attempts_deactivated(self):
        """Previous active attempt is set activo=False before the new one is created."""
        self.client.force_login(self.user)
        old = IntentoEjercicio.objects.create(
            perfil=self.perfil, ejercicio=self.ejercicio, puntaje=60, activo=True
        )
        self._post_json(
            {"ejercicio_id": self.ejercicio.pk, "puntaje": 85, "transcripcion": "appointment"}
        )
        old.refresh_from_db()
        self.assertFalse(old.activo)
        self.assertEqual(
            IntentoEjercicio.objects.filter(
                perfil=self.perfil, ejercicio=self.ejercicio, activo=True
            ).count(),
            1,
        )

    def test_sc02_failed_attempt_returns_200_aprobado_false(self):
        """POST with wrong transcripcion -> server scores < 80 -> aprobado=False."""
        self.client.force_login(self.user)
        response = self._post_json(
            {"ejercicio_id": self.ejercicio.pk, "transcripcion": "meeting"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["aprobado"])
        self.assertEqual(
            IntentoEjercicio.objects.filter(
                perfil=self.perfil, ejercicio=self.ejercicio
            ).count(),
            1,
        )

    def test_sc03_missing_transcripcion_returns_400_for_vocabulary(self):
        """POST without transcripcion for a vocabulary ejercicio -> 400."""
        self.client.force_login(self.user)
        response = self._post_json({"ejercicio_id": self.ejercicio.pk, "puntaje": 90})
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_sc04_nonexistent_ejercicio_returns_404(self):
        """POST with unknown ejercicio_id -> 404 JSON."""
        self.client.force_login(self.user)
        response = self._post_json({"ejercicio_id": 999999, "puntaje": 80})
        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.json())

    def test_sc05_level_mismatch_returns_403_no_intento_created(self):
        """POST where ejercicio.submodulo.nivel != perfil.nivel_mcer -> 403, no IntentoEjercicio."""
        other_nivel = NivelMCER.objects.create(codigo="B1", orden=3, parametros_json={})
        other_sub = Submodulo.objects.create(nivel=other_nivel, tipo="vocabulario", orden=1)
        other_ej = Ejercicio.objects.create(
            submodulo=other_sub,
            contenido_json={},
            nivel_dificultad="B1",
            texto_objetivo="schedule",
        )
        self.client.force_login(self.user)
        response = self._post_json({"ejercicio_id": other_ej.pk, "puntaje": 90})
        self.assertEqual(response.status_code, 403)
        self.assertIn("error", response.json())
        self.assertEqual(
            IntentoEjercicio.objects.filter(perfil=self.perfil, ejercicio=other_ej).count(),
            0,
        )

    def test_sc06_get_request_returns_405(self):
        """GET to guardar-ejercicio/ -> 405."""
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)

    def test_sc07_unauthenticated_post_redirects_to_login(self):
        """POST without auth -> 302 redirect to login (project LOGIN_URL)."""
        import json
        response = self.client.post(
            self.url,
            data=json.dumps({"ejercicio_id": self.ejercicio.pk, "puntaje": 80}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response["Location"])


class GuardarEjercicioServerScoringTests(TestCase):
    """Server-side scoring: view must recalculate puntaje from transcripcion."""

    def setUp(self):
        self.nivel = NivelMCER.objects.create(codigo="A2", orden=2, parametros_json={})
        self.submodulo = Submodulo.objects.create(
            nivel=self.nivel, tipo="vocabulario", orden=1
        )
        self.ejercicio = Ejercicio.objects.create(
            submodulo=self.submodulo,
            contenido_json={},
            nivel_dificultad="A2",
            texto_objetivo="I have an appointment",
        )
        self.user = User.objects.create_user(
            username="scoring@example.com", email="scoring@example.com", password="x"
        )
        self.perfil = self.user.perfil
        self.perfil.nivel_mcer = self.nivel
        self.perfil.save()
        self.url = reverse("progress:guardar_ejercicio")
        self.client.force_login(self.user)

    def _post_json(self, data):
        import json
        return self.client.post(
            self.url, data=json.dumps(data), content_type="application/json",
        )

    def test_server_ignores_client_puntaje(self):
        """Client sends puntaje=100 but only 3/4 words match → server returns 75."""
        response = self._post_json({
            "ejercicio_id": self.ejercicio.pk,
            "puntaje": 100,
            "transcripcion": "I have an meeting",
        })
        data = response.json()
        self.assertEqual(data["puntaje"], "75.00")
        self.assertFalse(data["aprobado"])

    def test_perfect_transcripcion_returns_100(self):
        """Exact match → 100 regardless of client puntaje."""
        response = self._post_json({
            "ejercicio_id": self.ejercicio.pk,
            "puntaje": 50,
            "transcripcion": "I have an appointment",
        })
        data = response.json()
        self.assertEqual(data["puntaje"], "100.00")
        self.assertTrue(data["aprobado"])

    def test_stored_puntaje_matches_server_calculation(self):
        """IntentoEjercicio.puntaje must be server-computed, not client's."""
        self._post_json({
            "ejercicio_id": self.ejercicio.pk,
            "puntaje": 100,
            "transcripcion": "I have an meeting",
        })
        intento = IntentoEjercicio.objects.get(
            perfil=self.perfil, ejercicio=self.ejercicio, activo=True
        )
        self.assertEqual(intento.puntaje, 75)

    def test_transcripcion_stored_alongside_server_score(self):
        """The raw transcripcion is persisted for auditing."""
        self._post_json({
            "ejercicio_id": self.ejercicio.pk,
            "transcripcion": "I have an meeting",
        })
        intento = IntentoEjercicio.objects.get(
            perfil=self.perfil, ejercicio=self.ejercicio, activo=True
        )
        self.assertEqual(intento.transcripcion, "I have an meeting")

    def test_no_puntaje_field_still_works(self):
        """Client can omit puntaje entirely — server computes it."""
        response = self._post_json({
            "ejercicio_id": self.ejercicio.pk,
            "transcripcion": "I have an appointment",
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["aprobado"])


class GuardarEjercicioMusicaScoringTests(TestCase):
    """Server-side scoring for music: LRC lines × per-line transcriptions."""

    SAMPLE_LRC = (
        "[00:10.00]Hello world\n"
        "[00:15.50]How are you\n"
        "[00:20.00]I am fine thank you\n"
    )

    def setUp(self):
        self.nivel = NivelMCER.objects.create(codigo="A1", orden=1, parametros_json={})
        self.submodulo = Submodulo.objects.create(
            nivel=self.nivel, tipo="musica", orden=2
        )
        self.ejercicio = Ejercicio.objects.create(
            submodulo=self.submodulo,
            contenido_json={"audio_url": "https://example.com/song.mp3", "lrc": self.SAMPLE_LRC},
            nivel_dificultad="A1",
            texto_objetivo="Test Song",
        )
        self.user = User.objects.create_user(
            username="music@example.com", email="music@example.com", password="x"
        )
        self.perfil = self.user.perfil
        self.perfil.nivel_mcer = self.nivel
        self.perfil.save()
        self.url = reverse("progress:guardar_ejercicio")
        self.client.force_login(self.user)

    def _post_json(self, data):
        import json
        return self.client.post(
            self.url, data=json.dumps(data), content_type="application/json",
        )

    def test_all_lines_perfect_returns_100(self):
        response = self._post_json({
            "ejercicio_id": self.ejercicio.pk,
            "line_transcriptions": {
                "0": "Hello world",
                "1": "How are you",
                "2": "I am fine thank you",
            },
        })
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["puntaje"], "100.00")
        self.assertTrue(data["aprobado"])

    def test_server_ignores_client_puntaje_for_music(self):
        """Client sends puntaje=100 but only 1/3 lines pass → server returns 33."""
        response = self._post_json({
            "ejercicio_id": self.ejercicio.pk,
            "puntaje": 100,
            "line_transcriptions": {"0": "Hello world"},
        })
        data = response.json()
        self.assertEqual(data["puntaje"], "33.00")
        self.assertFalse(data["aprobado"])

    def test_missing_line_transcriptions_returns_400(self):
        response = self._post_json({
            "ejercicio_id": self.ejercicio.pk,
            "puntaje": 90,
        })
        self.assertEqual(response.status_code, 400)

    def test_empty_line_transcriptions_returns_400(self):
        response = self._post_json({
            "ejercicio_id": self.ejercicio.pk,
            "line_transcriptions": {},
        })
        self.assertEqual(response.status_code, 400)

    def test_stored_puntaje_is_server_computed(self):
        self._post_json({
            "ejercicio_id": self.ejercicio.pk,
            "line_transcriptions": {"0": "Hello world", "1": "How are you"},
        })
        intento = IntentoEjercicio.objects.get(
            perfil=self.perfil, ejercicio=self.ejercicio, activo=True
        )
        self.assertEqual(intento.puntaje, 67)

    def test_line_transcriptions_stored_as_json_in_transcripcion(self):
        """Per-line data persisted for auditing."""
        import json
        lt = {"0": "Hello world", "1": "How are you"}
        self._post_json({
            "ejercicio_id": self.ejercicio.pk,
            "line_transcriptions": lt,
        })
        intento = IntentoEjercicio.objects.get(
            perfil=self.perfil, ejercicio=self.ejercicio, activo=True
        )
        self.assertEqual(json.loads(intento.transcripcion), lt)


class GuardarEjercicioMusicaProsodyTests(TestCase):
    """G4: Music scoring applies AI prosody weighting for A2/B1."""

    SAMPLE_LRC = (
        "[00:10.00]Hello world\n"
        "[00:15.50]How are you\n"
        "[00:20.00]I am fine thank you\n"
    )

    def setUp(self):
        self.nivel = NivelMCER.objects.create(codigo="A2", orden=2, parametros_json={})
        self.submodulo = Submodulo.objects.create(
            nivel=self.nivel, tipo="musica", orden=2
        )
        self.ejercicio = Ejercicio.objects.create(
            submodulo=self.submodulo,
            contenido_json={"audio_url": "https://example.com/song.mp3", "lrc": self.SAMPLE_LRC},
            nivel_dificultad="A2",
            texto_objetivo="Test Song A2",
        )
        self.user = User.objects.create_user(
            username="prosody@example.com", email="prosody@example.com", password="x"
        )
        self.perfil = self.user.perfil
        self.perfil.nivel_mcer = self.nivel
        self.perfil.save()
        self.url = reverse("progress:guardar_ejercicio")
        self.client.force_login(self.user)

    def _post_json(self, data):
        import json
        return self.client.post(
            self.url, data=json.dumps(data), content_type="application/json",
        )

    @patch("apps.progress.views.ProsodyEvaluator")
    def test_a2_applies_weighted_score(self, MockProsody):
        """A2 music: 50% precision + 50% pronunciation from Claude."""
        MockProsody.return_value.evaluate.return_value = {"pronunciation": 60}
        response = self._post_json({
            "ejercicio_id": self.ejercicio.pk,
            "line_transcriptions": {
                "0": "Hello world",
                "1": "How are you",
                "2": "I am fine thank you",
            },
        })
        # precision = 100 (all lines pass), pronunciation = 60
        # weighted = 50%*100 + 50%*60 = 80
        data = response.json()
        self.assertEqual(data["puntaje"], "80.00")
        self.assertTrue(data["aprobado"])

    @patch("apps.progress.views.ProsodyEvaluator")
    def test_a2_fallback_when_claude_fails(self, MockProsody):
        """If Claude fails, A2 falls back to 100% precision."""
        from apps.learning.writing_evaluator import AIEvaluationError
        MockProsody.return_value.evaluate.side_effect = AIEvaluationError("fail")
        response = self._post_json({
            "ejercicio_id": self.ejercicio.pk,
            "line_transcriptions": {
                "0": "Hello world",
                "1": "How are you",
                "2": "I am fine thank you",
            },
        })
        # Fallback = pure precision = 100
        data = response.json()
        self.assertEqual(data["puntaje"], "100.00")

    def test_a1_never_calls_prosody(self):
        """A1 music uses 100% precision — no Claude call at all."""
        nivel_a1 = NivelMCER.objects.create(codigo="A1", orden=1, parametros_json={})
        sub_a1 = Submodulo.objects.create(nivel=nivel_a1, tipo="musica", orden=2)
        ej_a1 = Ejercicio.objects.create(
            submodulo=sub_a1,
            contenido_json={"audio_url": "x", "lrc": self.SAMPLE_LRC},
            nivel_dificultad="A1", texto_objetivo="A1 Song",
        )
        self.perfil.nivel_mcer = nivel_a1
        self.perfil.save()
        response = self._post_json({
            "ejercicio_id": ej_a1.pk,
            "line_transcriptions": {
                "0": "Hello world",
                "1": "How are you",
                "2": "I am fine thank you",
            },
        })
        self.assertEqual(response.json()["puntaje"], "100.00")
