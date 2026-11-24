"""Tests de /altseason."""

from crypto_tracker.altseason import CUANTAS, Moneda, Temporada, cuenta, leer


def _moneda(coin_id, cambio, simbolo=None, nombre=None, precio=10.0):
    return {
        "id": coin_id,
        "symbol": simbolo or coin_id[:4],
        "name": nombre or coin_id.title(),
        "current_price": precio,
        "price_change_percentage_30d_in_currency": cambio,
    }


def _mercado(bitcoin, cambios):
    datos = [_moneda("bitcoin", bitcoin, "btc")]
    return datos + [_moneda(f"alt{i}", c, f"a{i}") for i, c in enumerate(cambios)]


def _temporada(ganan, pierden):
    monedas = [Moneda(f"g{i}", f"G{i}", 5.0) for i in range(ganan)]
    monedas += [Moneda(f"p{i}", f"P{i}", -5.0) for i in range(pierden)]
    return Temporada(0.0, monedas)


def test_leer_cuenta_las_que_le_ganan_a_bitcoin():
    t = leer(_mercado(-10, [5] * 15 + [-20] * 15))

    assert t.bitcoin == -10
    assert len(t.monedas) == 30
    assert len(t.ganan) == 15
    assert t.indice == 50


def test_empatar_con_bitcoin_no_es_ganarle():
    t = leer(_mercado(-10, [-10] * 30))

    assert t.indice == 0


def test_como_mucho_cincuenta_y_por_orden_de_tamaño():
    t = leer(_mercado(0, [1] * 60 + [-1] * 10))

    assert len(t.monedas) == CUANTAS
    assert t.monedas[0].coin_id == "alt0"
    assert t.indice == 100


def test_sin_bitcoin_o_con_pocas_no_hay_indice():
    assert leer(_mercado(0, [1] * 30)[1:]) is None
    assert leer(_mercado(0, [1] * 10)) is None


def test_leer_ignora_basura():
    datos = _mercado(0, [1] * 30)
    datos += [None, {"name": "sin id"}, _moneda("x", None), _moneda("y", "mucho")]

    assert len(leer(datos).monedas) == 30
    assert leer({"error": "algo"}) is None


def test_no_cuentan_estables_oro_ni_copias():
    assert not cuenta("usdt", "Tether", 1.0, 0.0)
    assert not cuenta("pyusd", "PayPal USD", 1.0, 0.0)
    assert not cuenta("dai", "Dai", 1.0, 0.0)
    assert not cuenta("paxg", "PAX Gold", 3500.0, -11.0)
    assert not cuenta("wbtc", "Wrapped Bitcoin", 60000.0, -26.0)
    assert not cuenta("steth", "Lido Staked Ether", 1700.0, -28.0)
    assert not cuenta("reth", "Rocket Pool ETH", 1900.0, -28.0)
    assert not cuenta("jitosol", "Jito Staked SOL", 80.0, -30.0)


def test_no_cuentan_los_fondos_que_valen_un_dolar():
    assert not cuenta("buidl", "BlackRock USD Institutional", 1.0, 0.0)
    assert not cuenta("ustb", "Invesco Short Duration US Gov", 11.3, 0.3)
    # Sin nada en el nombre: vale un dólar y pico y no se mueve.
    assert not cuenta("figr_heloc", "Figure Heloc", 1.057, -0.6)


def test_cuentan_las_de_verdad():
    assert cuenta("eth", "Ethereum", 1700.0, -28.0)
    assert cuenta("xrp", "XRP", 0.91, -29.9)  # cerca de un dólar pero se mueve
    assert cuenta("sol", "Solana", 69.0, -32.0)
    assert cuenta("doge", "Dogecoin", 0.05, -29.0)


def test_toca_altcoins_bitcoin_o_ninguna():
    assert _temporada(75, 25).toca == "altcoins"
    assert _temporada(25, 75).toca == "bitcoin"
    assert _temporada(50, 50).toca == ""


def test_mejores_y_peores():
    t = Temporada(
        0.0,
        [
            Moneda(c, c.upper(), v)
            for c, v in [("a", 3), ("b", -8), ("c", 15), ("d", 1)]
        ],
    )

    assert [m.coin_id for m in t.mejores()] == ["c", "a", "d"]
    assert [m.coin_id for m in t.peores()] == ["b", "d", "a"]
