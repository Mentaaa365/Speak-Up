from django.db import models
from django.test import TestCase

from apps.question_bank.models import Option, Question


class QuestionBankContextTests(TestCase):
    """Question.bank_context discriminator behavior."""

    def test_filter_by_bank_context_excludes_other_contexts(self):
        Question.objects.create(
            level="A1",
            question_type="CHOICE",
            text="Exercise question 1",
            bank_context="EXERCISE",
        )
        Question.objects.create(
            level="A1",
            question_type="CHOICE",
            text="Exercise question 2",
            bank_context="EXERCISE",
        )
        Question.objects.create(
            level="A1",
            question_type="CHOICE",
            text="Promotion exam question",
            bank_context="PROMOTION_EXAM",
        )

        promotion_questions = Question.objects.filter(bank_context="PROMOTION_EXAM")
        self.assertEqual(promotion_questions.count(), 1)

    def test_bank_context_defaults_to_diagnostic(self):
        question = Question.objects.create(
            level="DIAG",
            question_type="CHOICE",
            text="Diagnostic question",
        )

        question.refresh_from_db()
        self.assertEqual(question.bank_context, "DIAGNOSTIC")


class OptionQuestionForeignKeyTests(TestCase):
    """Option.question FK is indexed and cascades on delete."""

    def test_question_fk_has_db_index_and_cascade(self):
        field = Option._meta.get_field("question")
        self.assertTrue(field.db_index)
        self.assertIs(field.remote_field.on_delete, models.CASCADE)

    def test_deleting_question_cascades_to_options(self):
        question = Question.objects.create(
            level="A1",
            question_type="CHOICE",
            text="Question with options",
            bank_context="EXERCISE",
        )
        Option.objects.create(question=question, text="Option A", is_correct=True)
        Option.objects.create(question=question, text="Option B", is_correct=False)

        question.delete()

        self.assertEqual(Option.objects.count(), 0)
