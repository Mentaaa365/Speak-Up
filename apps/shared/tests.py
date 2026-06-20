from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

from apps.curriculum.models import Ejercicio, NivelMCER, Submodulo
from apps.learning.models import SesionEntrevista
from apps.progress.models import IntentoEjercicio
from apps.shared.utils import (
    _parse_lrc_lines,
    _score_musica,
    _score_musica_ponderado,
    _score_palabra_por_palabra,
    _seleccionar_blanks,
    _submodulo_completado,
)

User = get_user_model()


class ScorePalabraPorPalabraTests(SimpleTestCase):
    """Positional word-by-word scoring — must mirror vocabulary.js score()."""

    def test_exact_match_returns_100(self):
        self.assertEqual(_score_palabra_por_palabra("appointment", "appointment"), 100)

    def test_no_match_returns_0(self):
        self.assertEqual(_score_palabra_por_palabra("hello world", "appointment schedule"), 0)

    def test_partial_match_rounds_correctly(self):
        # "I have an meeting" vs "I have an appointment" → 3/4 = 75
        self.assertEqual(_score_palabra_por_palabra("I have an meeting", "I have an appointment"), 75)

    def test_case_insensitive(self):
        self.assertEqual(_score_palabra_por_palabra("Hello World", "hello world"), 100)

    def test_punctuation_stripped(self):
        self.assertEqual(_score_palabra_por_palabra("hello, world!", "hello world"), 100)

    def test_parentheses_stripped(self):
        self.assertEqual(_score_palabra_por_palabra("(hello) world", "hello world"), 100)

    def test_empty_transcripcion_returns_0(self):
        self.assertEqual(_score_palabra_por_palabra("", "hello"), 0)

    def test_empty_objetivo_returns_0(self):
        self.assertEqual(_score_palabra_por_palabra("hello", ""), 0)

    def test_both_empty_returns_0(self):
        self.assertEqual(_score_palabra_por_palabra("", ""), 0)

    def test_whitespace_only_returns_0(self):
        self.assertEqual(_score_palabra_por_palabra("   ", "hello"), 0)

    def test_word_order_matters(self):
        # "am I happy" vs "I am happy" → only "happy" at pos 2 matches → 1/3 = 33
        self.assertEqual(_score_palabra_por_palabra("am I happy", "I am happy"), 33)

    def test_extra_words_in_transcript_ignored(self):
        # "I am very happy today" vs "I am happy" → pos 0: ok, pos 1: ok, pos 2: "very" != "happy" → 2/3 = 67
        self.assertEqual(_score_palabra_por_palabra("I am very happy today", "I am happy"), 67)

    def test_fewer_words_in_transcript(self):
        # "I" vs "I am happy" → pos 0: ok, pos 1: missing, pos 2: missing → 1/3 = 33
        self.assertEqual(_score_palabra_por_palabra("I", "I am happy"), 33)

    def test_multi_word_full_match(self):
        self.assertEqual(_score_palabra_por_palabra(
            "the quick brown fox jumps over the lazy dog",
            "the quick brown fox jumps over the lazy dog",
        ), 100)


class ParseLrcLinesTests(SimpleTestCase):
    """LRC parser — must mirror music.js parseLRC() (text extraction only)."""

    SAMPLE_LRC = (
        "[00:10.00]Hello world\n"
        "[00:15.50]How are you\n"
        "[00:20.00]I am fine thank you\n"
    )

    def test_parses_standard_lrc(self):
        lines = _parse_lrc_lines(self.SAMPLE_LRC)
        self.assertEqual(lines, ["Hello world", "How are you", "I am fine thank you"])

    def test_empty_string_returns_empty_list(self):
        self.assertEqual(_parse_lrc_lines(""), [])

    def test_skips_lines_with_empty_text(self):
        lrc = "[00:10.00]Hello\n[00:15.00]\n[00:20.00]World\n"
        self.assertEqual(_parse_lrc_lines(lrc), ["Hello", "World"])

    def test_handles_two_digit_milliseconds(self):
        lrc = "[00:10.50]Two digits\n"
        self.assertEqual(_parse_lrc_lines(lrc), ["Two digits"])

    def test_handles_three_digit_milliseconds(self):
        lrc = "[00:10.500]Three digits\n"
        self.assertEqual(_parse_lrc_lines(lrc), ["Three digits"])

    def test_handles_integer_seconds(self):
        lrc = "[01:05]No decimal\n"
        self.assertEqual(_parse_lrc_lines(lrc), ["No decimal"])

    def test_ignores_non_lrc_lines(self):
        lrc = "[ti:Song Title]\n[ar:Artist]\n[00:05.00]Actual lyric\n"
        self.assertEqual(_parse_lrc_lines(lrc), ["Actual lyric"])

    def test_strips_whitespace_from_text(self):
        lrc = "[00:10.00]  spaced out  \n"
        self.assertEqual(_parse_lrc_lines(lrc), ["spaced out"])


class ScoreMusicaTests(SimpleTestCase):
    """Global music score: % of LRC lines with word-by-word score >= 80."""

    SAMPLE_LRC = (
        "[00:10.00]Hello world\n"
        "[00:15.50]How are you\n"
        "[00:20.00]I am fine thank you\n"
    )

    def test_all_lines_perfect_returns_100(self):
        transcriptions = {
            "0": "Hello world",
            "1": "How are you",
            "2": "I am fine thank you",
        }
        self.assertEqual(_score_musica(transcriptions, self.SAMPLE_LRC), 100)

    def test_no_transcriptions_returns_0(self):
        self.assertEqual(_score_musica({}, self.SAMPLE_LRC), 0)

    def test_partial_lines_returns_percentage(self):
        # 2 of 3 lines passed → 67%
        transcriptions = {
            "0": "Hello world",
            "1": "How are you",
            "2": "wrong wrong wrong wrong",
        }
        self.assertEqual(_score_musica(transcriptions, self.SAMPLE_LRC), 67)

    def test_empty_lrc_returns_0(self):
        self.assertEqual(_score_musica({"0": "hello"}, ""), 0)

    def test_line_below_80_does_not_count(self):
        # "Hello wrong" vs "Hello world" → 1/2 = 50% < 80 → not passed
        transcriptions = {"0": "Hello wrong"}
        self.assertEqual(_score_musica(transcriptions, self.SAMPLE_LRC), 0)

    def test_missing_line_indices_count_as_zero(self):
        # Only line 1 attempted → 1/3 = 33%
        transcriptions = {"1": "How are you"}
        self.assertEqual(_score_musica(transcriptions, self.SAMPLE_LRC), 33)

    def test_ignores_extra_indices_beyond_lrc_lines(self):
        transcriptions = {
            "0": "Hello world",
            "1": "How are you",
            "2": "I am fine thank you",
            "99": "ghost line",
        }
        self.assertEqual(_score_musica(transcriptions, self.SAMPLE_LRC), 100)


class SeleccionarBlanksTests(SimpleTestCase):
    """_seleccionar_blanks — picks content-word indices to hide per MCER level."""

    def test_a1_hides_one_word(self):
        indices = _seleccionar_blanks("Hello how are you", "A1")
        self.assertEqual(len(indices), 1)

    def test_a2_hides_two_words(self):
        indices = _seleccionar_blanks("I have breakfast with my family", "A2")
        self.assertEqual(len(indices), 2)

    def test_b1_hides_three_words(self):
        indices = _seleccionar_blanks("I have always wanted to travel the world", "B1")
        self.assertEqual(len(indices), 3)

    def test_never_hides_stop_words(self):
        for _ in range(20):
            indices = _seleccionar_blanks("I am the cat", "A1")
            words = "I am the cat".split()
            for idx in indices:
                self.assertNotIn(words[idx].lower(), {
                    'i', 'a', 'am', 'the', 'is', 'to', 'in', 'on', 'at',
                })

    def test_returns_sorted_indices(self):
        indices = _seleccionar_blanks("The quick brown fox jumps over", "A2")
        self.assertEqual(indices, sorted(indices))

    def test_caps_at_available_content_words(self):
        # "I am" has 0 content words (both are stop words)
        indices = _seleccionar_blanks("I am", "B1")
        self.assertEqual(len(indices), 0)

    def test_short_line_caps_naturally(self):
        # "cat" has 1 content word — A2 asks for 2 but only 1 is available
        indices = _seleccionar_blanks("cat", "A2")
        self.assertEqual(len(indices), 1)

    def test_returns_integer_indices(self):
        indices = _seleccionar_blanks("Hello world", "A1")
        for idx in indices:
            self.assertIsInstance(idx, int)


class ScoreMusicaPonderadoTests(SimpleTestCase):
    """RF-04 weighted scoring: A1=100% precision, A2=50/50, B1=40/30/30."""

    def test_a1_returns_precision_unchanged(self):
        self.assertEqual(_score_musica_ponderado(80, "A1", {"pronunciation": 50}), 80)

    def test_a1_ignores_ai_scores(self):
        self.assertEqual(_score_musica_ponderado(70, "A1"), 70)

    def test_a2_formula_50_50(self):
        # 50% * 80 + 50% * 60 = 70
        self.assertEqual(_score_musica_ponderado(80, "A2", {"pronunciation": 60}), 70)

    def test_b1_formula_40_30_30(self):
        # 40% * 80 + 30% * 70 + 30% * 60 = 32 + 21 + 18 = 71
        self.assertEqual(
            _score_musica_ponderado(80, "B1", {"intonation": 70, "precision": 60}), 71
        )

    def test_fallback_when_ai_scores_none_a2(self):
        self.assertEqual(_score_musica_ponderado(85, "A2", None), 85)

    def test_fallback_when_ai_scores_none_b1(self):
        self.assertEqual(_score_musica_ponderado(75, "B1", None), 75)

    def test_a2_missing_key_falls_back_to_precision(self):
        # ai_scores exists but pronunciation key missing → uses precision as default
        self.assertEqual(_score_musica_ponderado(80, "A2", {}), 80)

    def test_b1_partial_keys_falls_back(self):
        # Only intonation provided, precision key missing → precision fills in
        # 40% * 90 + 30% * 70 + 30% * 90 = 36 + 21 + 27 = 84
        self.assertEqual(_score_musica_ponderado(90, "B1", {"intonation": 70}), 84)


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


class SubmoduloCompletadoEntrevistaTests(TestCase):
    """WU-1 RF-05: _submodulo_completado bifurcation for tipo='entrevista'."""

    def setUp(self):
        self.nivel = NivelMCER.objects.create(codigo="A1", orden=1, parametros_json={})
        self.submodulo = Submodulo.objects.create(
            nivel=self.nivel, tipo="entrevista", orden=1
        )
        self.user = User.objects.create_user(
            username="wu1_entrevista@example.com",
            email="wu1_entrevista@example.com",
            password="x",
        )
        self.perfil = self.user.perfil

    # Scenario 1: COMPLETADA, puntaje=85 → True
    def test_entrevista_completada_passing_score_returns_true(self):
        """GIVEN estado=COMPLETADA and puntaje=85 THEN True."""
        SesionEntrevista.objects.create(
            perfil=self.perfil,
            submodulo=self.submodulo,
            estado="COMPLETADA",
            puntaje=85,
        )
        result = _submodulo_completado(self.perfil, self.submodulo)
        self.assertTrue(result)

    # Scenario 2: EN_CURSO, puntaje=None → False
    def test_entrevista_en_curso_returns_false(self):
        """GIVEN estado=EN_CURSO and puntaje=None THEN False."""
        SesionEntrevista.objects.create(
            perfil=self.perfil,
            submodulo=self.submodulo,
            estado="EN_CURSO",
            puntaje=None,
        )
        result = _submodulo_completado(self.perfil, self.submodulo)
        self.assertFalse(result)

    # Scenario 3: COMPLETADA, puntaje=70 (< 80) → False
    def test_entrevista_completada_failing_score_returns_false(self):
        """GIVEN estado=COMPLETADA and puntaje=70 (below threshold) THEN False."""
        SesionEntrevista.objects.create(
            perfil=self.perfil,
            submodulo=self.submodulo,
            estado="COMPLETADA",
            puntaje=70,
        )
        result = _submodulo_completado(self.perfil, self.submodulo)
        self.assertFalse(result)

    # Scenario 4: no sessions → False
    def test_entrevista_no_sessions_returns_false(self):
        """GIVEN no SesionEntrevista rows for this perfil+submodulo THEN False."""
        result = _submodulo_completado(self.perfil, self.submodulo)
        self.assertFalse(result)

    # Scenario 5: regression — tipo='vocabulario' still uses IntentoEjercicio path
    def test_vocabulario_tipo_unchanged_regression(self):
        """GIVEN tipo='vocabulario' THEN existing IntentoEjercicio logic applies unchanged."""
        submodulo_vocab = Submodulo.objects.create(
            nivel=self.nivel, tipo="vocabulario", orden=2
        )
        ejercicio = Ejercicio.objects.create(
            submodulo=submodulo_vocab,
            contenido_json={},
            nivel_dificultad="A1",
            texto_objetivo="hello",
        )
        IntentoEjercicio.objects.create(
            perfil=self.perfil,
            ejercicio=ejercicio,
            puntaje=90,
            activo=True,
        )
        result = _submodulo_completado(self.perfil, submodulo_vocab)
        self.assertTrue(result)
