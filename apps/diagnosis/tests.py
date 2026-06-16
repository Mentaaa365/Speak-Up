import inspect
import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.authentication.models import Perfil
from apps.curriculum.models import NivelMCER
from apps.diagnosis import views
from apps.question_bank.models import Question

User = get_user_model()


class DiagnosisBankContextFilterTests(TestCase):
    """API must only serve bank_context='DIAGNOSTIC' questions (RF-03)."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="bank@example.com", email="bank@example.com", password="x"
        )
        self.client.force_login(self.user)

    def test_exercise_questions_are_excluded_from_diagnostic_api(self):
        Question.objects.create(
            level="A1", question_type="CHOICE",
            bank_context="DIAGNOSTIC", text="Diagnostic question"
        )
        Question.objects.create(
            level="A1", question_type="CHOICE",
            bank_context="EXERCISE", text="Exercise question"
        )

        response = self.client.get(reverse("diagnosis:api_get_questions"))
        texts = [q["text"] for q in response.json()["questions"]]

        self.assertIn("Diagnostic question", texts)
        self.assertNotIn("Exercise question", texts)

    def test_promotion_exam_questions_are_excluded_from_diagnostic_api(self):
        Question.objects.create(
            level="B1", question_type="CHOICE",
            bank_context="DIAGNOSTIC", text="Diagnostic B1 question"
        )
        Question.objects.create(
            level="B1", question_type="CHOICE",
            bank_context="PROMOTION_EXAM", text="Promotion exam question"
        )

        response = self.client.get(reverse("diagnosis:api_get_questions"))
        texts = [q["text"] for q in response.json()["questions"]]

        self.assertIn("Diagnostic B1 question", texts)
        self.assertNotIn("Promotion exam question", texts)


class DiagnosisModuleIndependenceTests(TestCase):
    """diagnosis must not import from apps.progress (RF-08 module independence)."""

    def test_views_source_has_no_progress_imports(self):
        source = inspect.getsource(views)
        self.assertNotIn("from apps.progress", source)
        self.assertNotIn("import apps.progress", source)


class DiagnosisResultsPersistsNivelMcerTests(TestCase):
    """Completing the diagnosis flow assigns Perfil.nivel_mcer via curriculum.NivelMCER."""

    def setUp(self):
        self.nivel_a1 = NivelMCER.objects.create(codigo="A1", orden=1)
        self.user = User.objects.create_user(
            username="gabi", email="gabi@example.com", password="x"
        )
        self.client.force_login(self.user)

    def test_post_results_assigns_nivel_mcer_to_perfil(self):
        response = self.client.post(
            reverse("diagnosis:results"),
            {"answers_data": json.dumps([])},
        )

        self.assertEqual(response.status_code, 200)

        perfil = Perfil.objects.get(usuario=self.user)
        self.assertEqual(perfil.nivel_mcer, self.nivel_a1)
