"""
AIInterviewClient — wraps the Anthropic SDK to drive conversational oral interviews.

Three public methods:
    start_session(nivel_codigo)          -> str   (agent's opening question)
    next_turn_for(nivel, historial, txt) -> str   (agent's next intervention)
    evaluate_session(nivel, historial)   -> dict  (scores + puntaje_global)

Never calls the real API in tests; mock target:
    unittest.mock.patch("apps.learning.ai_client.anthropic.Anthropic")
"""

import json
import os

import anthropic

MODEL = "claude-haiku-4-5"
SPANISH_REDIRECT = "Please try in English."

# Per-level numeric scoring categories (spec v2 Correction A).
# B1 additionally returns a free-text 'sugerencias_mejora' key.
NIVEL_CATEGORIAS = {
    "A1": ["pronunciacion", "vocabulario", "fluidez"],
    "A2": ["pronunciacion", "vocabulario", "fluidez", "coherencia"],
    "B1": ["pronunciacion", "vocabulario", "fluidez", "coherencia", "riqueza_lexica"],
}


class AIInterviewClient:
    def __init__(self):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY is not set")
        self._client = anthropic.Anthropic(api_key=api_key)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _call(self, system: str, messages: list[dict], max_tokens: int = 600) -> str:
        response = self._client.messages.create(
            model=MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
        )
        return response.content[0].text.strip()

    def _system_prompt(self, nivel_codigo: str) -> str:
        base = (
            "You are a friendly English oral examiner conducting a short spoken interview. "
            "Ask ONE question at a time. Keep replies under 40 words. "
            f"If the student answers in Spanish, reply exactly starting with '{SPANISH_REDIRECT}' "
            "and then re-state your previous question in English. "
        )
        if nivel_codigo == "A1":
            return base + (
                "Level A1: use very simple present-tense questions from a FIXED set: "
                "name, age, country, family, daily routine, favorite food. "
                "Speak slowly and simply."
            )
        if nivel_codigo == "A2":
            return base + (
                "Level A2: dynamically generate everyday-topic questions (work, hobbies, "
                "past weekend, plans) adapting to the student's previous answers."
            )
        # B1
        return base + (
            "Level B1: free conversation. Ask open-ended opinion and hypothetical questions, "
            "follow up naturally, and push for elaboration. Do NOT enforce English-only "
            "redirection strictly; encourage richer responses."
        )

    def _eval_prompt(self, nivel_codigo: str, cats: list[str]) -> str:
        fields = ", ".join(f'"{c}": <int 0-100>' for c in cats)
        extra = (
            ', "sugerencias_mejora": "<free-text feedback in Spanish>"'
            if nivel_codigo == "B1"
            else ""
        )
        return (
            "You evaluate an English oral interview transcript. "
            f"Return ONLY valid JSON, no prose, with EXACTLY these keys for level {nivel_codigo}: "
            f"{{{fields}{extra}}}. "
            "Each numeric value is an integer 0-100. Do not add any other key."
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start_session(self, nivel_codigo: str) -> str:
        """Return the agent's opening question for the given level."""
        system = self._system_prompt(nivel_codigo)
        return self._call(system, [{"role": "user", "content": "[START_INTERVIEW]"}])

    def next_turn_for(self, nivel: str, historial: list[dict], respuesta_estudiante: str) -> str:
        """Given conversation history and the student's latest response, return the agent's reply."""
        system = self._system_prompt(nivel)
        messages = list(historial) + [{"role": "user", "content": respuesta_estudiante}]
        return self._call(system, messages)

    def evaluate_session(self, nivel_codigo: str, historial_completo: list[dict]) -> dict:
        """Evaluate the full conversation and return structured scores.

        Returns:
            {
                "scores": {<category>: <int 0-100>, ..., "sugerencias_mejora": <str> (B1 only)},
                "puntaje_global": <int>  — mean of numeric scores only
            }
        """
        cats = NIVEL_CATEGORIAS.get(nivel_codigo, NIVEL_CATEGORIAS["A1"])
        system = self._eval_prompt(nivel_codigo, cats)
        transcript = "\n".join(
            f"{m['role']}: {m['content']}" for m in historial_completo
        )
        raw = self._call(system, [{"role": "user", "content": transcript}], max_tokens=400)

        # Strip markdown code fences if the LLM wrapped the JSON
        raw = raw.strip()
        if raw.startswith("```"):
            parts = raw.split("```")
            # parts[1] is the code block content, possibly prefixed with 'json\n'
            inner = parts[1]
            if inner.startswith("json"):
                inner = inner[4:]
            raw = inner.strip()

        scores = json.loads(raw)
        numeric = [int(scores[c]) for c in cats]
        puntaje_global = round(sum(numeric) / len(numeric))

        return {"scores": scores, "puntaje_global": puntaje_global}
