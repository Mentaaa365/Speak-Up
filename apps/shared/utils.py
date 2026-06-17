from difflib import SequenceMatcher


def _similitud(a: str, b: str) -> float:
    """Returns a 0.0–1.0 similarity score between two text strings."""
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def _submodulo_completado(perfil, submodulo) -> bool:
    """Return True iff every Ejercicio in submodulo has an active passing attempt.

    An attempt is considered passing when activo=True and puntaje >= 80.
    Returns False when the submodule contains no exercises (vacuous-True guard).

    The import of IntentoEjercicio is inline to avoid circular imports:
    apps.progress imports from apps.shared, so a module-level import here
    would create a cycle.
    """
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
