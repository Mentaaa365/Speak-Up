from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.curriculum.models import Ejercicio, NivelMCER, Submodulo


class NivelMCERModelTests(TestCase):
    def test_codigo_is_unique(self):
        NivelMCER.objects.create(codigo="A1", orden=1)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                NivelMCER.objects.create(codigo="A1", orden=2)

    def test_orden_is_unique(self):
        NivelMCER.objects.create(codigo="A1", orden=1)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                NivelMCER.objects.create(codigo="A2", orden=1)

    def test_parametros_json_round_trip(self):
        payload = {"vocabulario": 500, "gramatica": ["presente", "pasado"]}

        nivel = NivelMCER.objects.create(
            codigo="A1", orden=1, parametros_json=payload
        )
        nivel.refresh_from_db()

        self.assertEqual(nivel.parametros_json, payload)


class SubmoduloModelTests(TestCase):
    def test_submodulo_cascades_on_nivel_delete(self):
        nivel = NivelMCER.objects.create(codigo="A1", orden=1)
        submodulo = Submodulo.objects.create(nivel=nivel, tipo="lectura", orden=1)

        nivel.delete()

        self.assertFalse(Submodulo.objects.filter(pk=submodulo.pk).exists())


class EjercicioModelTests(TestCase):
    def test_ejercicio_requires_existing_submodulo(self):
        nivel = NivelMCER.objects.create(codigo="A1", orden=1)
        submodulo = Submodulo.objects.create(nivel=nivel, tipo="lectura", orden=1)

        ejercicio = Ejercicio.objects.create(
            submodulo=submodulo,
            contenido_json={"pregunta": "¿Cómo estás?"},
            nivel_dificultad="A1",
        )

        self.assertEqual(ejercicio.submodulo_id, submodulo.id)

    def test_ejercicio_cascades_on_submodulo_delete(self):
        nivel = NivelMCER.objects.create(codigo="A1", orden=1)
        submodulo = Submodulo.objects.create(nivel=nivel, tipo="lectura", orden=1)
        ejercicio = Ejercicio.objects.create(
            submodulo=submodulo,
            contenido_json={"pregunta": "¿Cómo estás?"},
            nivel_dificultad="A1",
        )

        submodulo.delete()

        self.assertFalse(Ejercicio.objects.filter(pk=ejercicio.pk).exists())

    def test_contenido_json_round_trip(self):
        nivel = NivelMCER.objects.create(codigo="A1", orden=1)
        submodulo = Submodulo.objects.create(nivel=nivel, tipo="lectura", orden=1)
        payload = {"pregunta": "¿Cómo estás?", "opciones": ["Bien", "Mal"]}

        ejercicio = Ejercicio.objects.create(
            submodulo=submodulo,
            contenido_json=payload,
            nivel_dificultad="A1",
        )
        ejercicio.refresh_from_db()

        self.assertEqual(ejercicio.contenido_json, payload)

    def test_texto_objetivo_round_trip(self):
        """WU-1.T-1: texto_objetivo persists correctly on new Ejercicio."""
        nivel = NivelMCER.objects.create(codigo="A1", orden=1)
        submodulo = Submodulo.objects.create(nivel=nivel, tipo="vocabulario", orden=1)

        ejercicio = Ejercicio.objects.create(
            submodulo=submodulo,
            contenido_json={},
            nivel_dificultad="A1",
            texto_objetivo="Hello world",
        )
        ejercicio.refresh_from_db()

        self.assertEqual(ejercicio.texto_objetivo, "Hello world")

    def test_texto_objetivo_is_text_field(self):
        """WU-1.T-1: texto_objetivo must be a TextField, not CharField."""
        field = Ejercicio._meta.get_field("texto_objetivo")
        self.assertEqual(field.get_internal_type(), "TextField")
