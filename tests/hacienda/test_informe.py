"""Tests de /informe: las cuentas y que el PDF sale."""

from datetime import date, datetime, timezone

import pytest

from crypto_tracker.hacienda import informe, informe_pdf
from crypto_tracker.inversion.movimientos import Movimiento
from crypto_tracker.nucleo.config import Posicion


def _cuando(año, mes=6, dia=1):
    return datetime(año, mes, dia, 12, tzinfo=timezone.utc)


def _pos(cantidad, invertido, coin="bitcoin"):
    return Posicion(coin, cantidad, invertido)


def _mov(id_, tipo, cantidad, coste, antes, cuando, coin="bitcoin", comision=None):
    return Movimiento(id_, coin, tipo, cantidad, coste, antes, cuando, None, comision)


# En 2024 se compra bitcoin a 100 y a 300, y solana a 50. En 2025 se venden
# 1,5 BTC por 600 en mayo (ganando 350) y la solana por 30 en marzo (perdiendo 20).
HISTORIA = [
    _mov(1, "compra", 1, 100, None, _cuando(2024, 1)),
    _mov(2, "compra", 1, 300, _pos(1, 100), _cuando(2024, 3), comision=2),
    _mov(3, "compra", 10, 50, None, _cuando(2024, 4), "solana"),
    _mov(4, "venta", 1.5, 600, _pos(2, 400), _cuando(2025, 5), comision=3),
    _mov(5, "venta", 10, 30, _pos(10, 50, "solana"), _cuando(2025, 3), "solana"),
    _mov(6, "recompensa", 0.1, 12, None, _cuando(2025, 7), "ethereum"),
]


def test_junta_las_cuentas_del_año():
    i = informe.montar(HISTORIA, 2025)

    assert len(i.ventas) == 2
    assert i.transmision == 630
    assert i.adquisicion == 300  # 100 + la mitad de 300, y los 50 de solana
    assert i.impuestos.ganancia == 330
    assert i.recompensas == 12
    assert i.comisiones.total == 3  # la de la compra es de 2024


def test_las_ventas_van_por_fecha_y_no_por_numero():
    i = informe.montar(HISTORIA, 2025)

    assert [v.coin_id for v in i.ventas] == ["solana", "bitcoin"]


def test_la_ganancia_de_cada_mes():
    i = informe.montar(HISTORIA, 2025)

    assert i.por_mes[2] == -20  # marzo
    assert i.por_mes[4] == 350  # mayo
    assert sum(i.por_mes) == i.impuestos.ganancia


def test_por_cripto_de_la_que_mas_gano_a_la_que_mas_perdio():
    i = informe.montar(HISTORIA, 2025)

    assert i.por_cripto == [("bitcoin", 350), ("solana", -20)]


def test_una_venta_sin_precio_no_entra_en_los_totales():
    historia = [
        *HISTORIA,
        _mov(7, "venta", 0.5, None, _pos(0.5, 150), _cuando(2025, 9)),
    ]

    i = informe.montar(historia, 2025)

    assert len(i.ventas) == 3
    assert len(i.contadas) == 2
    assert i.transmision == 630
    assert sum(i.por_mes) == 330


def test_un_año_sin_nada_esta_vacio():
    assert informe.montar(HISTORIA, 2023).vacio
    assert not informe.montar(HISTORIA, 2025).vacio


def test_solo_con_recompensas_no_esta_vacio():
    solo = [_mov(1, "recompensa", 0.1, 12, None, _cuando(2025), "ethereum")]

    assert not informe.montar(solo, 2025).vacio


def test_interpretar_el_año():
    assert informe.interpretar("", 2026) == 2026
    assert informe.interpretar("2025", 2026) == 2025
    with pytest.raises(informe.InformeError, match="/informe 2025"):
        informe.interpretar("mañana", 2026)


def test_las_hojas_de_la_tabla():
    ventas = list(range(informe.POR_HOJA * 2 + 1))

    assert [len(h) for h in informe.hojas(ventas)] == [
        informe.POR_HOJA,
        informe.POR_HOJA,
        1,
    ]
    assert informe.hojas([]) == []


def test_el_nombre_del_archivo():
    assert informe.nombre(2025) == "informe-2025.pdf"


def _paginas(pdf: bytes) -> int:
    # El espacio de detrás deja fuera el /Type /Pages del índice.
    return pdf.count(b"/Type /Page ")


def test_el_pdf_lleva_el_resumen_y_la_tabla():
    pdf = informe_pdf.dibujar(informe.montar(HISTORIA, 2025), "eur", date(2026, 1, 9))

    assert pdf.startswith(b"%PDF")
    assert _paginas(pdf) == 2


def test_con_muchas_ventas_la_tabla_sigue_en_otra_hoja():
    historia = [_mov(1, "compra", 1000, 1000, None, _cuando(2024))]
    tiene = 1000.0
    for n in range(informe.POR_HOJA + 5):
        historia.append(
            _mov(n + 2, "venta", 1, 3, _pos(tiene, tiene), _cuando(2025, 1 + n % 12))
        )
        tiene -= 1

    pdf = informe_pdf.dibujar(informe.montar(historia, 2025), "eur", date(2026, 1, 9))

    assert _paginas(pdf) == 3


def test_solo_con_recompensas_sale_una_hoja():
    solo = [_mov(1, "recompensa", 0.1, 12, None, _cuando(2025), "ethereum")]

    pdf = informe_pdf.dibujar(informe.montar(solo, 2025), "eur", date(2026, 1, 9))

    assert _paginas(pdf) == 1


def test_el_pdf_no_revienta_con_perdidas_ni_en_dolares():
    perdiendo = [
        _mov(1, "compra", 1, 500, None, _cuando(2024)),
        _mov(2, "venta", 1, 100, _pos(1, 500), _cuando(2025)),
    ]

    pdf = informe_pdf.dibujar(informe.montar(perdiendo, 2025), "usd", date(2026, 1, 9))

    assert pdf.startswith(b"%PDF")


@pytest.mark.parametrize(
    "valor, texto",
    [(1234.5, "€1.234,50"), (-0.5646, "-€0,56"), (-0.001, "€0,00"), (0, "€0,00")],
)
def test_el_dinero_va_con_dos_decimales(valor, texto):
    assert informe_pdf._dinero(valor, "€") == texto


def test_la_ganancia_lleva_su_signo():
    assert informe_pdf._con_signo(350, "€") == "+€350,00"
    assert informe_pdf._con_signo(-20, "€") == "-€20,00"
    assert informe_pdf._con_signo(0.001, "€") == "€0,00"
