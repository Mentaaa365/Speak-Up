import json
import os

import anthropic

MODEL = "claude-haiku-4-5"


class AIEvaluationError(Exception):
    pass


def _strip_fences(raw):
    raw = raw.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        inner = parts[1]
        if inner.startswith("json"):
            inner = inner[4:]
        raw = inner.strip()
    return raw


class AIWritingEvaluator:
    _RUBRIC = {
        "A1": "The student is MCER level A1 (beginner). Expect: 2-3 simple present-tense sentences, basic vocabulary, simple grammar. Be lenient with minor errors.",
        "A2": "The student is MCER level A2 (elementary). Expect: 3-5 connected sentences, everyday vocabulary, past and future tenses. Moderate standards.",
        "B1": "The student is MCER level B1 (intermediate). Expect: 5-8 well-structured sentences forming a coherent paragraph, varied vocabulary, complex grammar. Higher standards.",
    }

    def __init__(self):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY is not set")
        self._client = anthropic.Anthropic(api_key=api_key)

    def _call(self, system, messages, max_tokens=800):
        response = self._client.messages.create(
            model=MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
        )
        return response.content[0].text.strip()

    def evaluate(self, text, nivel, prompt_topic):
        if not text or not text.strip():
            return {
                "score": 0,
                "grammar": 0,
                "coherence": 0,
                "vocabulary": 0,
                "suggestions": "No text provided.",
            }

        rubric = self._RUBRIC.get(nivel, self._RUBRIC["A1"])
        system = (
            "You evaluate English writing exercises for language learners. "
            f"{rubric} "
            "Return ONLY valid JSON with EXACTLY these keys: "
            '{"grammar": <int 0-100>, "coherence": <int 0-100>, "vocabulary": <int 0-100>, '
            '"suggestions": "<brief feedback in Spanish>"}. '
            "No other keys. No prose outside the JSON."
        )
        user_msg = f"Writing prompt: {prompt_topic}\n\nStudent's text:\n{text}"

        try:
            raw = self._call(system, [{"role": "user", "content": user_msg}])
            parsed = json.loads(_strip_fences(raw))
            grammar = int(parsed["grammar"])
            coherence = int(parsed["coherence"])
            vocabulary = int(parsed["vocabulary"])
            score = round((grammar + coherence + vocabulary) / 3)
            return {
                "score": score,
                "grammar": grammar,
                "coherence": coherence,
                "vocabulary": vocabulary,
                "suggestions": parsed.get("suggestions", ""),
            }
        except Exception as exc:
            raise AIEvaluationError(f"Writing evaluation failed: {exc}") from exc

    def evaluate_batch(self, items, nivel):
        if not items:
            return []

        rubric = self._RUBRIC.get(nivel, self._RUBRIC["A1"])
        system = (
            "You evaluate multiple English writing exercises for language learners. "
            f"{rubric} "
            "Return ONLY a valid JSON ARRAY. Each element must have EXACTLY these keys: "
            '{"index": <int>, "grammar": <int 0-100>, "coherence": <int 0-100>, '
            '"vocabulary": <int 0-100>, "suggestions": "<brief feedback in Spanish>"}. '
            "Evaluate each item independently. No prose outside the JSON array."
        )

        prompts_text = "\n\n".join(
            f"[Item {i}]\nPrompt: {item['prompt']}\nStudent's text:\n{item['text']}"
            for i, item in enumerate(items)
        )

        try:
            raw = self._call(
                system,
                [{"role": "user", "content": prompts_text}],
                max_tokens=300 * len(items),
            )
            parsed = json.loads(_strip_fences(raw))

            results_by_index = {}
            for entry in parsed:
                idx = int(entry["index"])
                grammar = int(entry["grammar"])
                coherence = int(entry["coherence"])
                vocabulary = int(entry["vocabulary"])
                results_by_index[idx] = {
                    "score": round((grammar + coherence + vocabulary) / 3),
                    "grammar": grammar,
                    "coherence": coherence,
                    "vocabulary": vocabulary,
                    "suggestions": entry.get("suggestions", ""),
                }

            results = []
            for i in range(len(items)):
                if i in results_by_index:
                    results.append(results_by_index[i])
                else:
                    results.append({
                        "score": 0, "grammar": 0, "coherence": 0,
                        "vocabulary": 0, "suggestions": "Evaluation unavailable.",
                    })
            return results

        except Exception as exc:
            raise AIEvaluationError(f"Batch writing evaluation failed: {exc}") from exc
