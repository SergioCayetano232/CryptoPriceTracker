"""/suelo: bitcoin frente a su media de 200 semanas, el suelo de cada ciclo."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

SEMANAS = 200

# % por encima de la media. En el techo de 2021 llegó a estar un +300 y pico.
ZONAS = (
    (0, "🧊", "Por debajo de su media: solo pasa en los peores fondos"),
    (50, "🟢", "Cerca del suelo"),
    (150, "😐", "En lo normal"),
    (300, "🔥", "Lejos del suelo"),
    (float("inf"), "🌋", "Muy lejos: así estaba en los techos de otros ciclos"),
)


@dataclass(frozen=True)
class Semana:
    cuando: date  # el último día que tiene la semana
    precio: float
    media: float

    @property
    def distancia(self) -> float:
        """% por encima (o por debajo) de la media."""
        return (self.precio / self.media - 1) * 100


@dataclass(frozen=True)
class Suelo:
    semanas: list[Semana]  # las que ya tienen 200 detrás, de la más vieja a hoy

    @property
    def hoy(self) -> Semana:
        return self.semanas[-1]

    @property
    def por_debajo(self) -> int:
        """Semanas cerradas por debajo de la media. La de hoy no cuenta."""
        return sum(s.distancia < 0 for s in self.semanas[:-1])

    @property
    def mas_lejos(self) -> Semana:
        return max(self.semanas, key=lambda s: s.distancia)

    @property
    def mas_abajo(self) -> Semana:
        return min(self.semanas, key=lambda s: s.distancia)

    @property
    def sube_al_año(self) -> float | None:
        """% que ha subido la media en el último año."""
        if len(self.semanas) <= 52:
            return None
        return (self.hoy.media / self.semanas[-53].media - 1) * 100

    @property
    def zona(self) -> tuple[str, str]:
        return next((e, t) for tope, e, t in ZONAS if self.hoy.distancia < tope)


def calcular(velas) -> Suelo | None:
    """Con las velas diarias de /mayer. None si no hay 200 semanas."""
    cierres: dict[date, float] = {}
    for v in velas if isinstance(velas, list) else []:
        try:
            dia = datetime.fromtimestamp(int(v[0]) / 1000, timezone.utc).date()
            precio = float(v[4])
        except (TypeError, ValueError, IndexError, OverflowError, OSError):
            continue
        if precio > 0:
            cierres[dia] = precio

    # Semanas de lunes a domingo, como las de Binance. Me quedo con el último
    # cierre de cada una; la de esta semana va con el precio de hoy.
    por_semana: dict[date, tuple[date, float]] = {}
    for dia in sorted(cierres):
        lunes = dia - timedelta(days=dia.weekday())
        por_semana[lunes] = (dia, cierres[dia])
    semanas = [por_semana[lunes] for lunes in sorted(por_semana)]
    if len(semanas) < SEMANAS:
        return None

    resultado = []
    suma = sum(p for _, p in semanas[:SEMANAS])
    for i in range(SEMANAS - 1, len(semanas)):
        if i >= SEMANAS:
            suma += semanas[i][1] - semanas[i - SEMANAS][1]
        dia, precio = semanas[i]
        resultado.append(Semana(dia, precio, suma / SEMANAS))
    return Suelo(resultado)
