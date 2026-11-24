"""Tests de /mapa."""

import pytest

from crypto_tracker.mapa import CUANTAS, Casilla, Mapa, leer, repartir


def _moneda(coin_id, capital, variacion=1.0, **cambios):
    datos = {
        "id": coin_id,
        "symbol": coin_id[:4],
        "name": coin_id.title(),
        "current_price": 50.0,
        "market_cap": capital,
        "price_change_percentage_24h": variacion,
        "price_change_percentage_30d_in_currency": -10.0,
    }
    return {**datos, **cambios}


def _solapan(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    en_x = ax + aw > bx + 1e-9 and bx + bw > ax + 1e-9
    return en_x and ay + ah > by + 1e-9 and by + bh > ay + 1e-9


@pytest.mark.parametrize(
    "valores",
    [[1], [6, 6, 4, 3, 2, 2, 1], [60, 10, 5, 5, 3, 1, 1, 0.5], [1] * 30],
)
def test_repartir_llena_todo_sin_solapar(valores):
    rects = repartir(valores, 1.0, 1.0)

    assert len(rects) == len(valores)
    total = sum(valores)
    for v, (x, y, w, h) in zip(valores, rects, strict=True):
        assert w * h == pytest.approx(v / total)
        assert min(x, y) >= 0
        assert x + w <= 1 + 1e-9 and y + h <= 1 + 1e-9
    for i, a in enumerate(rects):
        assert not any(_solapan(a, b) for b in rects[i + 1 :])


def test_repartir_salen_casi_cuadrados():
    # El ejemplo de siempre del algoritmo: con 6x4, ninguno pasa de 3 a 1.
    rects = repartir([6, 6, 4, 3, 2, 2, 1], 6.0, 4.0)

    assert all(max(w / h, h / w) < 3 for _, _, w, h in rects)


def test_leer_de_la_mas_grande_a_la_mas_pequeña():
    m = leer([_moneda("sol", 50), _moneda("bitcoin", 1000, -2.5), _moneda("eth", 300)])

    assert [c.coin_id for c in m.casillas] == ["bitcoin", "eth", "sol"]
    assert m.casillas[0].simbolo == "BITC"
    assert m.casillas[0].variacion == -2.5


def test_leer_como_mucho_treinta():
    m = leer([_moneda(f"c{i}", 100 - i) for i in range(45)])

    assert len(m.casillas) == CUANTAS


def test_leer_sin_estables_ni_fondos():
    datos = [
        _moneda("bitcoin", 1000),
        _moneda("tether", 200, symbol="usdt", current_price=1.0),
        _moneda("buidl", 5, name="BlackRock USD Fund", current_price=1.0),
        _moneda(
            "heloc", 5, current_price=1.05, price_change_percentage_30d_in_currency=0.2
        ),
    ]

    assert [c.coin_id for c in leer(datos).casillas] == ["bitcoin"]


def test_leer_ignora_basura():
    datos = [
        None,
        {"name": "sin id"},
        _moneda("a", None),
        _moneda("b", 0),
        _moneda("c", 10, variacion=None),
        _moneda("d", 10, current_price="x"),
        _moneda("e", 10),
    ]

    assert [c.coin_id for c in leer(datos).casillas] == ["e"]
    assert leer({"error": "algo"}) is None
    assert leer([]) is None


def test_suben_bajan_y_media_por_tamaño():
    m = Mapa(
        [
            Casilla("a", "A", 300, 2.0),
            Casilla("b", "B", 100, -6.0),
            Casilla("c", "C", 100, 0.0),
        ]
    )

    assert (m.suben, m.bajan) == (1, 1)
    assert m.media == pytest.approx((600 - 600) / 500)
