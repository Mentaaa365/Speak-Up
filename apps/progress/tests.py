from django.contrib.auth import get_user_model
from django.db import models
from django.test import TestCase

from apps.curriculum.models import Ejercicio, NivelMCER, Submodulo
from apps.progress.models import IntentoEjercicio

User = get_user_model()


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
