import unittest.mock
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from apps.authentication.models import Perfil
from apps.curriculum.models import NivelMCER
from apps.exams.models import Certificado, ExamenIntento
from apps.question_bank.models import Question

User = get_user_model()


class ExamenIntentoTipoChoicesTests(TestCase):
    """`tipo` must be one of the allowed choices, enforced at clean level."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="gina", email="gina@example.com", password="x"
        )
        self.perfil = Perfil.objects.get(usuario=self.user)

    def test_invalid_tipo_raises_validation_error(self):
        examen = ExamenIntento(
            perfil=self.perfil,
            tipo="INVALIDO",
            puntaje=Decimal("0.00"),
        )
        with self.assertRaises(ValidationError):
            examen.full_clean()

    def test_valid_tipo_passes_clean_fields(self):
        examen = ExamenIntento(
            perfil=self.perfil,
            tipo="DIAGNOSTICO",
            puntaje=Decimal("50.00"),
        )
        # Should not raise for a valid choice. `detalle_json` is excluded
        # because JSONField treats its default `{}` as blank for
        # full_clean() purposes, which is unrelated to the `tipo` check
        # under test here.
        examen.full_clean(exclude=["detalle_json"])


class ExamenIntentoDiagnosticoTests(TestCase):
    """DIAGNOSTICO row persists with perfil, nivel_objetivo, and puntaje."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="hugo", email="hugo@example.com", password="x"
        )
        self.perfil = Perfil.objects.get(usuario=self.user)
        self.nivel = NivelMCER.objects.create(codigo="A1", orden=1)

    def test_diagnostico_row_persists_with_expected_fields(self):
        examen = ExamenIntento.objects.create(
            perfil=self.perfil,
            tipo="DIAGNOSTICO",
            nivel_objetivo=self.nivel,
            puntaje=Decimal("75.50"),
        )

        examen.refresh_from_db()
        self.assertEqual(examen.perfil, self.perfil)
        self.assertEqual(examen.nivel_objetivo, self.nivel)
        self.assertEqual(examen.puntaje, Decimal("75.50"))
        self.assertEqual(examen.tipo, "DIAGNOSTICO")
        self.assertFalse(examen.aprobado)
        self.assertEqual(examen.detalle_json, {})


class ExamenIntentoPromocionTests(TestCase):
    """PROMOCION attempts accumulate across multiple failed tries; none deleted."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="ines", email="ines@example.com", password="x"
        )
        self.perfil = Perfil.objects.get(usuario=self.user)
        self.nivel = NivelMCER.objects.create(codigo="B1", orden=3)

    def test_multiple_failed_promocion_attempts_all_persist(self):
        for i in range(3):
            ExamenIntento.objects.create(
                perfil=self.perfil,
                tipo="PROMOCION",
                nivel_objetivo=self.nivel,
                puntaje=Decimal("40.00"),
                aprobado=False,
            )

        attempts = ExamenIntento.objects.filter(
            perfil=self.perfil, tipo="PROMOCION"
        )
        self.assertEqual(attempts.count(), 3)
        self.assertTrue(all(not a.aprobado for a in attempts))


class CertificadoTests(TestCase):
    """Certificado: UUID pk, unique codigo_hash, OneToOne PROTECT to examen."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="javi", email="javi@example.com", password="x"
        )
        self.perfil = Perfil.objects.get(usuario=self.user)
        self.nivel = NivelMCER.objects.create(codigo="B2", orden=4)
        self.examen = ExamenIntento.objects.create(
            perfil=self.perfil,
            tipo="CERTIFICACION",
            nivel_objetivo=self.nivel,
            puntaje=Decimal("90.00"),
            aprobado=True,
        )

    def test_id_is_uuid(self):
        import uuid

        certificado = Certificado.objects.create(
            examen=self.examen,
            codigo_hash="a" * 64,
            nivel=self.nivel,
        )
        self.assertIsInstance(certificado.id, uuid.UUID)

    def test_codigo_hash_unique(self):
        Certificado.objects.create(
            examen=self.examen,
            codigo_hash="b" * 64,
            nivel=self.nivel,
        )

        otro_examen = ExamenIntento.objects.create(
            perfil=self.perfil,
            tipo="CERTIFICACION",
            nivel_objetivo=self.nivel,
            puntaje=Decimal("95.00"),
            aprobado=True,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Certificado.objects.create(
                    examen=otro_examen,
                    codigo_hash="b" * 64,
                    nivel=self.nivel,
                )

    def test_examen_protect_on_delete(self):
        Certificado.objects.create(
            examen=self.examen,
            codigo_hash="c" * 64,
            nivel=self.nivel,
        )

        from django.db.models import ProtectedError

        with self.assertRaises(ProtectedError):
            self.examen.delete()

    def test_examen_is_onetoone(self):
        certificado = Certificado.objects.create(
            examen=self.examen,
            codigo_hash="d" * 64,
            nivel=self.nivel,
        )
        self.assertEqual(self.examen.certificado, certificado)


class ExamStartViewGuardTests(TestCase):
    """ExamStartView enforces 5 entry guards in strict order (PR A — RF-06)."""

    def setUp(self):
        self.nivel = NivelMCER.objects.create(codigo='A1', orden=1, parametros_json={})
        self.user = User.objects.create_user(
            username='examstart@example.com',
            email='examstart@example.com',
            password='TestPass1!',
        )
        self.perfil = self.user.perfil
        self.client.force_login(self.user)
        self.url = reverse('exams:start')

    def _populate_bank(self):
        for i in range(5):
            Question.objects.create(
                level='A1', question_type='SPEAKING', bank_context='PROMOTION_EXAM',
                text=f'Speak phrase {i}', target_phrase=f'phrase {i}',
            )
            Question.objects.create(
                level='A1', question_type='LISTENING', bank_context='PROMOTION_EXAM',
                text=f'Listen question {i}', audio_text=f'audio {i}',
            )
            Question.objects.create(
                level='A1', question_type='CHOICE', bank_context='PROMOTION_EXAM',
                text=f'Choose answer {i}',
            )
            Question.objects.create(
                level='A1', question_type='WRITING', bank_context='PROMOTION_EXAM',
                text=f'Write about topic {i}',
            )

    # ── Guard 1: no nivel_mcer ────────────────────────────────────────────────

    def test_guard1_no_nivel_mcer_redirects_to_diagnosis(self):
        response = self.client.get(self.url)
        self.assertRedirects(
            response, reverse('diagnosis:welcome'), fetch_redirect_response=False
        )

    # ── Guard 2: Certificado already exists ───────────────────────────────────

    def test_guard2_certificado_exists_redirects_to_certificate(self):
        self.perfil.nivel_mcer = self.nivel
        self.perfil.save()
        examen = ExamenIntento.objects.create(
            perfil=self.perfil, tipo='CERTIFICACION', nivel_objetivo=self.nivel,
            puntaje=Decimal('90.00'), aprobado=True,
        )
        Certificado.objects.create(examen=examen, codigo_hash='a' * 64, nivel=self.nivel)
        response = self.client.get(self.url)
        self.assertRedirects(
            response, reverse('exams:certificate'), fetch_redirect_response=False
        )

    # ── Guard 3: already approved attempt (PROMOCION passed) ─────────────────

    def test_guard3_approved_attempt_redirects_to_dashboard(self):
        self.perfil.nivel_mcer = self.nivel
        self.perfil.save()
        ExamenIntento.objects.create(
            perfil=self.perfil, tipo='PROMOCION', nivel_objetivo=self.nivel,
            puntaje=Decimal('85.00'), aprobado=True,
        )
        response = self.client.get(self.url)
        self.assertRedirects(
            response, reverse('progress:dashboard'), fetch_redirect_response=False
        )

    # ── Guard 4: 2 failed attempts exhausted ─────────────────────────────────

    def test_guard4_two_failed_attempts_shows_exhausted_message(self):
        self.perfil.nivel_mcer = self.nivel
        self.perfil.save()
        for _ in range(2):
            ExamenIntento.objects.create(
                perfil=self.perfil, tipo='PROMOCION', nivel_objetivo=self.nivel,
                puntaje=Decimal('70.00'), aprobado=False,
            )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('agotado', response.content.decode())

    def test_guard4_one_attempt_does_not_block(self):
        self.perfil.nivel_mcer = self.nivel
        self.perfil.save()
        ExamenIntento.objects.create(
            perfil=self.perfil, tipo='PROMOCION', nivel_objetivo=self.nivel,
            puntaje=Decimal('70.00'), aprobado=False,
        )
        self._populate_bank()
        response = self.client.get(self.url)
        # Guard 4 must NOT fire — falls through to guard 5 (bank ok) → 200 stub
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('agotado', response.content.decode())

    # ── Guard 5: bank insufficient ────────────────────────────────────────────

    def test_guard5_empty_bank_shows_unavailable_message(self):
        self.perfil.nivel_mcer = self.nivel
        self.perfil.save()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('aún no tiene preguntas', response.content.decode())

    def test_guard5_partial_bank_shows_unavailable_message(self):
        self.perfil.nivel_mcer = self.nivel
        self.perfil.save()
        # Only 3 SPEAKING — not enough
        for i in range(3):
            Question.objects.create(
                level='A1', question_type='SPEAKING', bank_context='PROMOTION_EXAM',
                text=f'Speak {i}', target_phrase=f'phrase {i}',
            )
        response = self.client.get(self.url)
        self.assertIn('aún no tiene preguntas', response.content.decode())

    # ── All guards pass ───────────────────────────────────────────────────────

    def test_all_guards_pass_returns_200(self):
        self.perfil.nivel_mcer = self.nivel
        self.perfil.save()
        self._populate_bank()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('aún no tiene preguntas', response.content.decode())
        self.assertNotIn('agotado', response.content.decode())


class ExamStartViewQuestionSelectionTests(TestCase):
    """ExamStartView selects 20 questions, caches IDs in session, determines tipo (PR B)."""

    def setUp(self):
        self.nivel_a1 = NivelMCER.objects.create(codigo='A1', orden=1, parametros_json={})
        self.nivel_a2 = NivelMCER.objects.create(codigo='A2', orden=2, parametros_json={})
        self.user = User.objects.create_user(
            username='select@example.com',
            email='select@example.com',
            password='TestPass1!',
        )
        self.perfil = self.user.perfil
        self.perfil.nivel_mcer = self.nivel_a1
        self.perfil.save()
        self.client.force_login(self.user)
        self.url = reverse('exams:start')
        self._populate_bank('A1')

    def _populate_bank(self, codigo):
        for i in range(5):
            Question.objects.create(
                level=codigo, question_type='SPEAKING', bank_context='PROMOTION_EXAM',
                text=f'{codigo} Speak {i}', target_phrase=f'phrase {i}',
            )
            Question.objects.create(
                level=codigo, question_type='LISTENING', bank_context='PROMOTION_EXAM',
                text=f'{codigo} Listen {i}', audio_text=f'audio {i}',
            )
            Question.objects.create(
                level=codigo, question_type='CHOICE', bank_context='PROMOTION_EXAM',
                text=f'{codigo} Choose {i}',
            )
            Question.objects.create(
                level=codigo, question_type='WRITING', bank_context='PROMOTION_EXAM',
                text=f'{codigo} Write {i}',
            )

    def test_get_caches_20_question_ids_in_session(self):
        self.client.get(self.url)
        ids = self.client.session.get('examen_promocion_ids')
        self.assertIsNotNone(ids)
        self.assertEqual(len(ids), 20)

    def test_selected_questions_are_5_per_type(self):
        self.client.get(self.url)
        ids = self.client.session['examen_promocion_ids']
        qs = Question.objects.filter(id__in=ids)
        self.assertEqual(qs.filter(question_type='SPEAKING').count(), 5)
        self.assertEqual(qs.filter(question_type='LISTENING').count(), 5)
        self.assertEqual(qs.filter(question_type='CHOICE').count(), 5)
        self.assertEqual(qs.filter(question_type='WRITING').count(), 5)

    def test_selected_questions_are_all_from_nivel_activo(self):
        self.client.get(self.url)
        ids = self.client.session['examen_promocion_ids']
        qs = Question.objects.filter(id__in=ids)
        self.assertTrue(all(q.level == 'A1' for q in qs))

    def test_selected_questions_are_all_promotion_exam_context(self):
        self.client.get(self.url)
        ids = self.client.session['examen_promocion_ids']
        qs = Question.objects.filter(id__in=ids)
        self.assertTrue(all(q.bank_context == 'PROMOTION_EXAM' for q in qs))

    def test_second_get_reuses_cached_session_ids(self):
        self.client.get(self.url)
        first_ids = list(self.client.session['examen_promocion_ids'])
        self.client.get(self.url)
        second_ids = list(self.client.session['examen_promocion_ids'])
        self.assertEqual(first_ids, second_ids)

    def test_tipo_is_promocion_when_next_nivel_exists(self):
        # nivel_a1 has orden=1, nivel_a2 has orden=2 → tipo='PROMOCION'
        response = self.client.get(self.url)
        self.assertEqual(response.context['tipo'], 'PROMOCION')

    def test_tipo_is_certificacion_when_no_next_nivel(self):
        self.perfil.nivel_mcer = self.nivel_a2
        self.perfil.save()
        self._populate_bank('A2')
        # Clear session so questions get re-selected for A2
        session = self.client.session
        session.pop('examen_promocion_ids', None)
        session.save()
        response = self.client.get(self.url)
        self.assertEqual(response.context['tipo'], 'CERTIFICACION')

    def test_context_contains_nivel_activo(self):
        response = self.client.get(self.url)
        self.assertEqual(response.context['nivel_activo'], self.nivel_a1)


class ExamScoringAndPersistenceTests(TestCase):
    """POST to exams:start scores answers and persists ExamenIntento (PR C — RF-06)."""

    def setUp(self):
        self.nivel = NivelMCER.objects.create(codigo='A1', orden=1, parametros_json={})
        self.user = User.objects.create_user(
            username='score@example.com',
            email='score@example.com',
            password='TestPass1!',
        )
        self.perfil = self.user.perfil
        self.perfil.nivel_mcer = self.nivel
        self.perfil.save()
        self.client.force_login(self.user)
        self.url = reverse('exams:start')

        # Populate bank
        from apps.question_bank.models import Option
        self.speaking_questions = []
        self.listening_questions = []
        self.choice_questions = []
        self.writing_questions = []

        for i in range(5):
            sq = Question.objects.create(
                level='A1', question_type='SPEAKING', bank_context='PROMOTION_EXAM',
                text=f'Say this {i}', target_phrase=f'target phrase {i}',
            )
            self.speaking_questions.append(sq)

            lq = Question.objects.create(
                level='A1', question_type='LISTENING', bank_context='PROMOTION_EXAM',
                text=f'Listen {i}', audio_text=f'audio {i}',
            )
            Option.objects.create(question=lq, text='correct', is_correct=True)
            Option.objects.create(question=lq, text='wrong', is_correct=False)
            self.listening_questions.append(lq)

            cq = Question.objects.create(
                level='A1', question_type='CHOICE', bank_context='PROMOTION_EXAM',
                text=f'Choose {i}',
            )
            Option.objects.create(question=cq, text='correct', is_correct=True)
            Option.objects.create(question=cq, text='wrong', is_correct=False)
            self.choice_questions.append(cq)

            wq = Question.objects.create(
                level='A1', question_type='WRITING', bank_context='PROMOTION_EXAM',
                text=f'Write about {i}',
            )
            self.writing_questions.append(wq)

        # Trigger GET to cache questions in session
        self.client.get(self.url)

    def _get_cached_ids(self):
        return self.client.session.get('examen_promocion_ids', [])

    def _build_perfect_answers(self):
        """Build answers payload that gets everything correct."""
        answers = []
        session_ids = self._get_cached_ids()
        for q_id in session_ids:
            q = Question.objects.get(id=q_id)
            if q.question_type == 'SPEAKING':
                answers.append({
                    'type': 'SPEAKING',
                    'answer': q.target_phrase,
                    'targetPhrase': q.target_phrase,
                    'optionId': '',
                })
            elif q.question_type == 'LISTENING':
                correct_opt = q.options.filter(is_correct=True).first()
                answers.append({
                    'type': 'LISTENING',
                    'answer': '',
                    'targetPhrase': '',
                    'optionId': str(correct_opt.id) if correct_opt else '',
                })
            elif q.question_type == 'CHOICE':
                correct_opt = q.options.filter(is_correct=True).first()
                answers.append({
                    'type': 'CHOICE',
                    'answer': '',
                    'targetPhrase': '',
                    'optionId': str(correct_opt.id) if correct_opt else '',
                })
            elif q.question_type == 'WRITING':
                answers.append({
                    'questionId': str(q.id),
                    'type': 'WRITING',
                    'answer': 'I enjoy learning English because it helps me communicate with people around the world.',
                    'targetPhrase': '',
                    'optionId': '',
                })
        return answers

    def _post_answers(self, answers):
        import json
        return self.client.post(self.url, {'answers_data': json.dumps(answers)})

    # ── Scoring boundaries ────────────────────────────────────────────────────

    @unittest.mock.patch('apps.exams.views.AIWritingEvaluator')
    def test_perfect_score_is_100_and_aprobado_true(self, MockEval):
        mock_instance = MockEval.return_value
        mock_instance.evaluate_batch.return_value = [{'score': 100, 'grammar': 100, 'coherence': 100, 'vocabulary': 100, 'suggestions': ''}] * 5
        self._post_answers(self._build_perfect_answers())
        intento = ExamenIntento.objects.get(perfil=self.perfil, nivel_objetivo=self.nivel)
        self.assertEqual(intento.puntaje, Decimal('100'))
        self.assertTrue(intento.aprobado)

    def test_all_wrong_is_aprobado_false(self):
        session_ids = self._get_cached_ids()
        answers = [
            {'questionId': q_id, 'type': Question.objects.get(id=q_id).question_type, 'answer': 'zzz', 'targetPhrase': 'nothing', 'optionId': ''}
            for q_id in session_ids
        ]
        self._post_answers(answers)
        intento = ExamenIntento.objects.get(perfil=self.perfil, nivel_objetivo=self.nivel)
        self.assertFalse(intento.aprobado)

    # ── Persistence ───────────────────────────────────────────────────────────

    def test_post_creates_exactly_one_examen_intento(self):
        self._post_answers(self._build_perfect_answers())
        self.assertEqual(
            ExamenIntento.objects.filter(perfil=self.perfil, nivel_objetivo=self.nivel).count(), 1
        )

    def test_intento_nivel_objetivo_is_nivel_activo_not_siguiente(self):
        nivel_a2 = NivelMCER.objects.create(codigo='A2', orden=2, parametros_json={})
        self._post_answers(self._build_perfect_answers())
        intento = ExamenIntento.objects.get(perfil=self.perfil)
        self.assertEqual(intento.nivel_objetivo, self.nivel)
        self.assertNotEqual(intento.nivel_objetivo, nivel_a2)

    def test_intento_tipo_is_promocion_when_next_nivel_exists(self):
        NivelMCER.objects.create(codigo='A2', orden=2, parametros_json={})
        self._post_answers(self._build_perfect_answers())
        intento = ExamenIntento.objects.get(perfil=self.perfil, nivel_objetivo=self.nivel)
        self.assertEqual(intento.tipo, 'PROMOCION')

    def test_intento_tipo_is_certificacion_when_no_next_nivel(self):
        # nivel A1 has no next nivel (only one in DB)
        self._post_answers(self._build_perfect_answers())
        intento = ExamenIntento.objects.get(perfil=self.perfil, nivel_objetivo=self.nivel)
        self.assertEqual(intento.tipo, 'CERTIFICACION')

    def test_session_cleared_after_post(self):
        self._post_answers(self._build_perfect_answers())
        self.assertNotIn('examen_promocion_ids', self.client.session)

    def test_speaking_only_correct_scores_25(self):
        session_ids = self._get_cached_ids()
        answers = []
        for q_id in session_ids:
            q = Question.objects.get(id=q_id)
            if q.question_type == 'SPEAKING':
                answers.append({'questionId': str(q.id), 'type': 'SPEAKING', 'answer': q.target_phrase, 'targetPhrase': q.target_phrase, 'optionId': ''})
            else:
                answers.append({'questionId': str(q.id), 'type': q.question_type, 'answer': '', 'targetPhrase': '', 'optionId': ''})
        self._post_answers(answers)
        intento = ExamenIntento.objects.get(perfil=self.perfil, nivel_objetivo=self.nivel)
        self.assertEqual(intento.puntaje, Decimal('25'))


class PostPassSideEffectsTests(TestCase):
    """PR D — post-approval side effects and CertificateView (RF-06)."""

    def _make_bank(self, nivel):
        from apps.question_bank.models import Option
        for i in range(5):
            Question.objects.create(
                level=nivel.codigo, question_type='SPEAKING', bank_context='PROMOTION_EXAM',
                text=f'Say {i}', target_phrase=f'phrase {i}',
            )
            lq = Question.objects.create(
                level=nivel.codigo, question_type='LISTENING', bank_context='PROMOTION_EXAM',
                text=f'Listen {i}', audio_text=f'audio {i}',
            )
            Option.objects.create(question=lq, text='correct', is_correct=True)
            Option.objects.create(question=lq, text='wrong', is_correct=False)
            cq = Question.objects.create(
                level=nivel.codigo, question_type='CHOICE', bank_context='PROMOTION_EXAM',
                text=f'Choose {i}',
            )
            Option.objects.create(question=cq, text='correct', is_correct=True)
            Option.objects.create(question=cq, text='wrong', is_correct=False)
            Question.objects.create(
                level=nivel.codigo, question_type='WRITING', bank_context='PROMOTION_EXAM',
                text=f'Write about {i}',
            )

    def _build_perfect_answers(self):
        session_ids = self.client.session.get('examen_promocion_ids', [])
        answers = []
        for q_id in session_ids:
            q = Question.objects.get(id=q_id)
            if q.question_type == 'SPEAKING':
                answers.append({'questionId': str(q.id), 'type': 'SPEAKING', 'answer': q.target_phrase, 'targetPhrase': q.target_phrase, 'optionId': ''})
            elif q.question_type == 'WRITING':
                answers.append({'questionId': str(q.id), 'type': 'WRITING', 'answer': 'I enjoy learning English.', 'targetPhrase': '', 'optionId': ''})
            else:
                correct_opt = q.options.filter(is_correct=True).first()
                answers.append({'questionId': str(q.id), 'type': q.question_type, 'answer': '', 'targetPhrase': '', 'optionId': str(correct_opt.id) if correct_opt else ''})
        return answers

    def setUp(self):
        self.nivel_a1 = NivelMCER.objects.create(codigo='A1', orden=1, parametros_json={})
        self.nivel_a2 = NivelMCER.objects.create(codigo='A2', orden=2, parametros_json={})
        self.user = User.objects.create_user(
            username='effects@example.com', email='effects@example.com', password='TestPass1!',
        )
        self.perfil = self.user.perfil
        self.perfil.nivel_mcer = self.nivel_a1
        self.perfil.save()
        self.client.force_login(self.user)
        self.url = reverse('exams:start')
        self._make_bank(self.nivel_a1)

    # ── PROMOCION pass ────────────────────────────────────────────────────────

    @unittest.mock.patch('apps.exams.views.AIWritingEvaluator')
    def test_promocion_pass_advances_perfil_nivel_mcer(self, MockEval):
        MockEval.return_value.evaluate_batch.return_value = [{'score': 100, 'grammar': 100, 'coherence': 100, 'vocabulary': 100, 'suggestions': ''}] * 5
        self.client.get(self.url)
        self.client.post(self.url, {'answers_data': __import__('json').dumps(self._build_perfect_answers())})
        self.perfil.refresh_from_db()
        self.assertEqual(self.perfil.nivel_mcer, self.nivel_a2)

    @unittest.mock.patch('apps.exams.views.AIWritingEvaluator')
    def test_promocion_pass_does_not_create_certificado(self, MockEval):
        MockEval.return_value.evaluate_batch.return_value = [{'score': 100, 'grammar': 100, 'coherence': 100, 'vocabulary': 100, 'suggestions': ''}] * 5
        self.client.get(self.url)
        self.client.post(self.url, {'answers_data': __import__('json').dumps(self._build_perfect_answers())})
        self.assertEqual(Certificado.objects.filter(examen__perfil=self.perfil).count(), 0)

    def test_fail_does_not_advance_nivel_mcer(self):
        self.client.get(self.url)
        import json
        answers = [{'questionId': '', 'type': 'SPEAKING', 'answer': 'zzz', 'targetPhrase': 'nothing', 'optionId': ''} for _ in range(20)]
        self.client.post(self.url, {'answers_data': json.dumps(answers)})
        self.perfil.refresh_from_db()
        self.assertEqual(self.perfil.nivel_mcer, self.nivel_a1)

    # ── CERTIFICACION pass ────────────────────────────────────────────────────

    @unittest.mock.patch('apps.exams.views.AIWritingEvaluator')
    def test_certificacion_pass_creates_certificado(self, MockEval):
        MockEval.return_value.evaluate_batch.return_value = [{'score': 100, 'grammar': 100, 'coherence': 100, 'vocabulary': 100, 'suggestions': ''}] * 5
        self.nivel_a2.delete()
        self.client.get(self.url)
        self.client.post(self.url, {'answers_data': __import__('json').dumps(self._build_perfect_answers())})
        self.assertEqual(Certificado.objects.filter(examen__perfil=self.perfil).count(), 1)

    @unittest.mock.patch('apps.exams.views.AIWritingEvaluator')
    def test_certificacion_certificado_nivel_is_nivel_activo(self, MockEval):
        MockEval.return_value.evaluate_batch.return_value = [{'score': 100, 'grammar': 100, 'coherence': 100, 'vocabulary': 100, 'suggestions': ''}] * 5
        self.nivel_a2.delete()
        self.client.get(self.url)
        self.client.post(self.url, {'answers_data': __import__('json').dumps(self._build_perfect_answers())})
        cert = Certificado.objects.get(examen__perfil=self.perfil)
        self.assertEqual(cert.nivel, self.nivel_a1)

    @unittest.mock.patch('apps.exams.views.AIWritingEvaluator')
    def test_certificacion_certificado_has_codigo_hash(self, MockEval):
        MockEval.return_value.evaluate_batch.return_value = [{'score': 100, 'grammar': 100, 'coherence': 100, 'vocabulary': 100, 'suggestions': ''}] * 5
        self.nivel_a2.delete()
        self.client.get(self.url)
        self.client.post(self.url, {'answers_data': __import__('json').dumps(self._build_perfect_answers())})
        cert = Certificado.objects.get(examen__perfil=self.perfil)
        self.assertEqual(len(cert.codigo_hash), 64)

    # ── CertificateView ───────────────────────────────────────────────────────

    def test_certificate_view_redirects_to_dashboard_when_no_cert(self):
        response = self.client.get(reverse('exams:certificate'))
        self.assertRedirects(response, reverse('progress:dashboard'))

    @unittest.mock.patch('apps.exams.views.AIWritingEvaluator')
    def test_certificate_view_200_when_cert_exists(self, MockEval):
        MockEval.return_value.evaluate_batch.return_value = [{'score': 100, 'grammar': 100, 'coherence': 100, 'vocabulary': 100, 'suggestions': ''}] * 5
        self.nivel_a2.delete()
        self.client.get(self.url)
        self.client.post(self.url, {'answers_data': __import__('json').dumps(self._build_perfect_answers())})
        response = self.client.get(reverse('exams:certificate'))
        self.assertEqual(response.status_code, 200)

    @unittest.mock.patch('apps.exams.views.AIWritingEvaluator')
    def test_certificate_view_context_contains_certificado(self, MockEval):
        MockEval.return_value.evaluate_batch.return_value = [{'score': 100, 'grammar': 100, 'coherence': 100, 'vocabulary': 100, 'suggestions': ''}] * 5
        self.nivel_a2.delete()
        self.client.get(self.url)
        self.client.post(self.url, {'answers_data': __import__('json').dumps(self._build_perfect_answers())})
        response = self.client.get(reverse('exams:certificate'))
        self.assertIn('certificado', response.context)

    @unittest.mock.patch('apps.exams.views.AIWritingEvaluator')
    def test_certificate_view_context_puntaje_matches_intento(self, MockEval):
        MockEval.return_value.evaluate_batch.return_value = [{'score': 100, 'grammar': 100, 'coherence': 100, 'vocabulary': 100, 'suggestions': ''}] * 5
        self.nivel_a2.delete()
        self.client.get(self.url)
        self.client.post(self.url, {'answers_data': __import__('json').dumps(self._build_perfect_answers())})
        intento = ExamenIntento.objects.get(perfil=self.perfil)
        response = self.client.get(reverse('exams:certificate'))
        self.assertEqual(response.context['puntaje'], intento.puntaje)
