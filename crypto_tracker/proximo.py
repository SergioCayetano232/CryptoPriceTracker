"""A que precio saltaria el siguiente aviso de cada cripto."""

from .alerts import _a_float, _es_ref_pct
from .config import Watch


def objetivos(
    watch: Watch, referencia: str | None, precio: float
) -> tuple[float | None, float | None]:
    """(arriba, abajo): los precios que dispararian el siguiente aviso.

    Sale de lo mismo que mira alerts.revisar, asi que no puede prometer un
    aviso que luego no llegue. None en un lado es que por ahi no avisa.
    """
    if watch.percent is not None:
        if not _es_ref_pct(referencia):
            return None, None  # recien puesta: aun no hay desde donde contar
        base = _a_float(referencia[1:])
        if not base or base <= 0:
            return None, None
        return base * (1 + watch.percent / 100), base * (1 - watch.percent / 100)

    if watch.step is not None:
        nivel = _a_float(referencia)
        if nivel is None:
            return None, None
        # Sube al llegar al siguiente multiplo; baja al perder el suyo.
        return nivel + watch.step, nivel

    # Por encima del maximo ya aviso; lo siguiente es caer por abajo.
    maximo, minimo = watch.max_price, watch.min_price
    arriba = maximo if maximo is not None and precio <= maximo else None
    abajo = minimo if minimo is not None and precio >= minimo else None
    return arriba, abajo
