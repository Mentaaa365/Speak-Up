import json
import os

import anthropic

from apps.learning.writing_evaluator import AIEvaluationError

MODEL = "claude-haiku-4-5"


class ProsodyEvaluator:
    """Evaluates intonation and rhythm proxies from STT transcriptions."""

    def __init__(self):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY is not set")
        self._client = anthropic.Anthropic(api_key=api_key, timeout=30.0)

    def evaluate(self, line_transcriptions, lrc_lines, nivel):
        """Return prosody scores based on transcription quality.

        Args:
            line_transcriptions: {str(index): transcript, ...}
            lrc_lines: list of target lyric strings
            nivel: 'A2' or 'B1'

        Returns for A2: {"pronunciation": int 0-100}
        Returns for B1: {"intonation": int 0-100, "precision": int 0-100}
        """
        pairs = []
        for i, target in enumerate(lrc_lines):
            transcript = line_transcriptions.get(str(i), '')
            if transcript:
                pairs.append(f"Line {i}: target=\"{target}\" → spoken=\"{transcript}\"")

        if not pairs:
            raise AIEvaluationError("No transcription pairs to evaluate")

        if nivel == "A2":
            keys = '"pronunciation": <int 0-100>'
        else:
            keys = '"intonation": <int 0-100>, "precision": <int 0-100>'

        system = (
            "You evaluate English pronunciation quality from STT transcriptions "
            "compared to target lyrics. Assess naturalness: are function words "
            "present (not skipped)? Are multi-syllable words intact? Are contractions "
            "used naturally? These are proxies for intonation and rhythm since you "
            "only have text, not audio. "
            f"Return ONLY valid JSON with keys: {{{keys}}}. No prose."
        )
        user_msg = f"Student level: {nivel}\n\n" + "\n".join(pairs)

        try:
            response = self._client.messages.create(
                model=MODEL,
                max_tokens=200,
                system=system,
                messages=[{"role": "user", "content": user_msg}],
            )
            raw = response.content[0].text.strip()
            if raw.startswith("```"):
                parts = raw.split("```")
                inner = parts[1]
                if inner.startswith("json"):
                    inner = inner[4:]
                raw = inner.strip()
            return json.loads(raw)
        except Exception as exc:
            raise AIEvaluationError(f"Prosody evaluation failed: {exc}") from exc
