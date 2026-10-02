"""Los botones que van debajo de cada aviso."""

from .alerts import SIMBOLOS, Alert, _num
from .puntuales import CARTERA

# Telegram no deja meter mas de 64 bytes en cada boton.
MAX_DATOS = 64

# Con mas filas el aviso se queda en segundo plano detras de tanto boton.
MAX_CRIPTOS = 3

CALLAR = ("🔕 Callar 1 h", "/mute 1h")


def para_avisos(avisos: list[Alert], currency: str) -> list[list[tuple[str, str]]]:
    """Filas de (texto, comando). Pulsar un boton es como escribir el comando."""
    simbolo = SIMBOLOS.get(currency.lower(), currency.upper() + " ")
    # Si una cripto sale dos veces (nivel y brusco), la primera manda.
    primeros, vistas = [], set()
    for a in avisos:
        if a.coin_id not in vistas:
            vistas.add(a.coin_id)
            primeros.append(a)
    solo_una = len(primeros) == 1

    filas = []
    for a in primeros[:MAX_CRIPTOS]:
        nombre = a.coin_id.replace("-", " ").title()
        # Con coma: puntuales.numero leeria "1.234" como 1234.
        precio = repr(a.threshold).replace(".", ",")
        grafica = "/cartera" if a.coin_id == CARTERA else f"/historico {a.coin_id}"
        fila = [
            ("📈 Gráfica" if solo_una else f"📈 {nombre}", grafica),
            (
                f"🎯 Si vuelve a {simbolo}{_num(a.threshold)}",
                f"/alerta {a.coin_id} {precio}",
            ),
        ]
        filas.append([b for b in fila if len(b[1].encode()) <= MAX_DATOS])

    filas.append([CALLAR])
    return [f for f in filas if f]
