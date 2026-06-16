from difflib import SequenceMatcher


def _similitud(a: str, b: str) -> float:
    """Returns a 0.0–1.0 similarity score between two text strings."""
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()
