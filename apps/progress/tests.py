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

    def test_dashboard_html_does_not_contain_hardcoded_exams_start(self):
        # Make exam available by marking all submódulos complete
        ejercicio = Ejercicio.objects.create(
            submodulo=Submodulo.objects.first(),
            contenido_json={},
            nivel_dificultad="A1",
        )
        IntentoEjercicio.objects.create(
            perfil=self.perfil, ejercicio=ejercicio, puntaje=90
        )
        response = self.client.get(reverse("progress:dashboard"))
        self.assertNotIn('href="/exams/start/"', response.content.decode())


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
