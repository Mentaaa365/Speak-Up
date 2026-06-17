from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.curriculum.models import Ejercicio, NivelMCER, Submodulo
from apps.progress.models import IntentoEjercicio
from apps.shared.utils import _submodulo_completado

User = get_user_model()


class SubmoduloCompletadoTests(TestCase):
    """WU-2.T-1: _submodulo_completado — 4 edge-case scenarios from spec Domain 2."""

    def setUp(self):
        self.nivel = NivelMCER.objects.create(codigo="B1", orden=3, parametros_json={})
        self.submodulo = Submodulo.objects.create(
            nivel=self.nivel, tipo="vocabulario", orden=1
        )
        self.user = User.objects.create_user(
            username="wu2test@example.com",
            email="wu2test@example.com",
            password="x",
        )
        self.perfil = self.user.perfil

    def _make_ejercicio(self, texto="word"):
        return Ejercicio.objects.create(
            submodulo=self.submodulo,
            contenido_json={},
            nivel_dificultad="B1",
            texto_objetivo=texto,
        )

    def _make_intento(self, ejercicio, puntaje, activo=True):
        return IntentoEjercicio.objects.create(
            perfil=self.perfil,
            ejercicio=ejercicio,
            puntaje=puntaje,
            activo=activo,
        )

    # Scenario: all exercises passed → True
    def test_all_exercises_passed_returns_true(self):
        """GIVEN 3 exercises all with active attempts puntaje >= 80 THEN True."""
        ej1 = self._make_ejercicio("appointment")
        ej2 = self._make_ejercicio("schedule")
        ej3 = self._make_ejercicio("conference")
        self._make_intento(ej1, puntaje=85)
        self._make_intento(ej2, puntaje=90)
        self._make_intento(ej3, puntaje=80)

        result = _submodulo_completado(self.perfil, self.submodulo)

        self.assertTrue(result)

    # Scenario: one exercise not yet attempted → False
    def test_one_exercise_not_attempted_returns_false(self):
        """GIVEN 3 exercises, 2 passed and 1 with no attempt THEN False."""
        ej1 = self._make_ejercicio("appointment")
        ej2 = self._make_ejercicio("schedule")
        _ej3 = self._make_ejercicio("conference")  # no intento
        self._make_intento(ej1, puntaje=85)
        self._make_intento(ej2, puntaje=90)

        result = _submodulo_completado(self.perfil, self.submodulo)

        self.assertFalse(result)

    # Scenario: one exercise failed (puntaje < 80, activo=True) → False
    def test_one_exercise_failed_returns_false(self):
        """GIVEN 2 exercises; 1 passed (puntaje=90), 1 failed (puntaje=50, activo=True) THEN False."""
        ej1 = self._make_ejercicio("appointment")
        ej2 = self._make_ejercicio("schedule")
        self._make_intento(ej1, puntaje=90)
        self._make_intento(ej2, puntaje=50)  # activo=True by default

        result = _submodulo_completado(self.perfil, self.submodulo)

        self.assertFalse(result)

    # Scenario: submodule has no exercises → False
    def test_submodulo_with_zero_exercises_returns_false(self):
        """GIVEN a submodule with no Ejercicio rows THEN False (not vacuously True)."""
        # submodulo created in setUp has no exercises yet
        result = _submodulo_completado(self.perfil, self.submodulo)

        self.assertFalse(result)
