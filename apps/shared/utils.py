from difflib import SequenceMatcher


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
