import json
import os

import anthropic

from apps.learning.writing_evaluator import AIEvaluationError

MODEL = "claude-haiku-4-5"


class ExercisePrioritizer:
    def __init__(self):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY is not set")
        self._client = anthropic.Anthropic(api_key=api_key, timeout=30.0)

    def prioritize(self, nivel, word_errors, pending_exercises):
        """Return exercise IDs ordered by pedagogical priority based on error patterns."""
        errors_text = ", ".join(f'"{w}" ({c}x)' for w, c in word_errors.items()) or "none yet"
        exercises_text = "\n".join(
            f"- ID {e['id']}: \"{e['texto_objetivo']}\""
            for e in pending_exercises
        )

        system = (
            "You are a language learning assistant that reorders vocabulary exercises "
            "to prioritize the student's weakest areas. Consider phonetic similarity, "
            "word families, and linguistic patterns — not just exact string matches. "
            "Return ONLY a JSON array of exercise IDs ordered by priority (most "
            "beneficial first). No prose, no explanation."
        )
        user_msg = (
            f"Student level: {nivel}\n"
            f"Words the student struggles with (word → error count): {errors_text}\n\n"
            f"Pending exercises:\n{exercises_text}\n\n"
            "Return the IDs as a JSON array, most beneficial first."
        )

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
            raise AIEvaluationError(f"Exercise prioritization failed: {exc}") from exc
