import random
import re
from difflib import SequenceMatcher

_PUNCTUATION_RE = re.compile(r'[.,!?¿¡()]')
_LRC_LINE_RE = re.compile(r'\[(\d{2}):(\d{2}\.\d{2,3}|\d{2})\](.*)')

_STOP_WORDS = frozenset({
    'i', 'a', 'an', 'the', 'is', 'am', 'are', 'was', 'were',
    'to', 'in', 'on', 'at', 'by', 'for', 'of', 'and', 'or',
    'but', 'my', 'your', 'he', 'she', 'it', 'we', 'they',
    'do', 'does', 'did', 'not', 'no', 'so', 'up', 'with',
    'have', 'has', 'had', 'be', 'been', 'will', 'can',
})

_BLANKS_PER_LEVEL = {'A1': 1, 'A2': 2, 'B1': 3}


def _score_palabra_por_palabra(transcripcion: str, objetivo: str) -> int:
    """Positional word-by-word scoring — mirrors vocabulary.js score().

    Both music.js and vocabulary.js use this same algorithm. If you change
    the logic here, update both JS files to stay in sync.

    Returns an integer 0–100.
    """
    if not objetivo or not objetivo.strip():
        return 0
    if not transcripcion or not transcripcion.strip():
        return 0

    clean_t = _PUNCTUATION_RE.sub('', transcripcion.lower()).split()
    clean_o = _PUNCTUATION_RE.sub('', objetivo.lower()).split()

    if not clean_o:
        return 0

    correct = sum(
        1 for i, word in enumerate(clean_o)
        if i < len(clean_t) and clean_t[i] == word
    )
    return round((correct / len(clean_o)) * 100)


def _parse_lrc_lines(lrc_text: str) -> list[str]:
    """Extract lyric text lines from LRC format — mirrors music.js parseLRC().

    Both this function and music.js parseLRC() parse the same LRC data from
    Ejercicio.contenido_json['lrc']. If you change the regex or filtering
    rules here, update music.js parseLRC() to stay in sync.
    """
    lines = []
    for raw_line in lrc_text.split('\n'):
        match = _LRC_LINE_RE.match(raw_line)
        if match:
            text = match.group(3).strip()
            if text:
                lines.append(text)
    return lines


def _score_musica(line_transcriptions: dict, lrc_text: str) -> int:
    """Compute global music score from per-line best transcriptions.

    Returns 0–100: percentage of LRC lines where the student's best
    transcription scored >= 80 via _score_palabra_por_palabra().
    """
    lines = _parse_lrc_lines(lrc_text)
    if not lines:
        return 0

    passed = sum(
        1 for i, target in enumerate(lines)
        if _score_palabra_por_palabra(
            line_transcriptions.get(str(i), ''), target
        ) >= 80
    )
    return round((passed / len(lines)) * 100)


def _seleccionar_blanks(texto: str, nivel: str) -> list[int]:
    """Return sorted word indices to hide as blanks for a fill-in-blank exercise.

    Selects N content words (non-stop-words) per MCER level. Both this
    function and the JS equivalent in music.js use the same STOP_WORDS
    set and level config. If you change the list here, update music.js.
    """
    words = texto.split()
    content_indices = [i for i, w in enumerate(words) if w.lower() not in _STOP_WORDS]
    n = min(_BLANKS_PER_LEVEL.get(nivel, 1), len(content_indices))
    return sorted(random.sample(content_indices, n)) if n > 0 else []


def _score_musica_ponderado(precision: int, nivel: str, ai_scores: dict | None = None) -> int:
    """Apply RF-04 weighted scoring for music exercises.

    A1: 100% precision (no AI evaluation).
    A2: 50% precision + 50% pronunciation (AI).
    B1: 40% precision + 30% intonation (AI) + 30% precision_ai (AI).

    Falls back to 100% precision if ai_scores is None (Claude unavailable,
    as specified in RF-04 exceptions).
    """
    if nivel == 'A1' or ai_scores is None:
        return precision

    if nivel == 'A2':
        pronunciation = ai_scores.get('pronunciation', precision)
        return round(0.50 * precision + 0.50 * pronunciation)

    # B1
    intonation = ai_scores.get('intonation', precision)
    precision_ai = ai_scores.get('precision', precision)
    return round(0.40 * precision + 0.30 * intonation + 0.30 * precision_ai)


def _similitud(a: str, b: str) -> float:
    """Returns a 0.0–1.0 similarity score between two text strings."""
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def _submodulo_completado(perfil, submodulo) -> bool:
    """Return True iff the submodule is considered completed for the given perfil.

    Dispatches on submodulo.tipo:
    - 'entrevista': requires a SesionEntrevista with estado='COMPLETADA' and puntaje >= 80.
    - All other tipos: requires every Ejercicio to have an active passing IntentoEjercicio
      (activo=True, puntaje >= 80). Returns False when the submodule has no exercises.

    All model imports are inline to avoid circular imports: apps.progress and apps.learning
    both import from apps.shared, so module-level imports here would create cycles.
    """
    if submodulo.tipo == "entrevista":
        from apps.learning.models import SesionEntrevista  # noqa: PLC0415

        return SesionEntrevista.objects.filter(
            perfil=perfil,
            submodulo=submodulo,
            estado="COMPLETADA",
            puntaje__gte=80,
        ).exists()

    from apps.progress.models import IntentoEjercicio  # noqa: PLC0415

    total = submodulo.ejercicios.count()
    if total == 0:
        return False
    aprobados = (
        IntentoEjercicio.objects.filter(
            perfil=perfil,
            ejercicio__submodulo=submodulo,
            activo=True,
            puntaje__gte=80,
        )
        .values("ejercicio")
        .distinct()
        .count()
    )
    return aprobados >= total
