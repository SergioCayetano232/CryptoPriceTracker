"""Tests de /sectores."""

from crypto_tracker.indicadores.sectores import MINIMO, SECTORES, leer


def _categoria(id_, cambio=1.0, capital=1e9):
    return {
        "id": id_,
        "name": id_,
        "market_cap": capital,
        "market_cap_change_24h": cambio,
    }


def _todas(**cambios):
    return [_categoria(i, cambios.get(i.replace("-", "_"), 0.0)) for i in SECTORES]


def test_leer_ordena_de_la_que_mas_sube_a_la_que_mas_baja():
    lista = leer(_todas(meme_token=5.2, privacy_coins=-7.9))

    assert len(lista) == len(SECTORES)
    assert (lista[0].nombre, lista[0].cambio) == ("Memes", 5.2)
    assert (lista[-1].nombre, lista[-1].cambio) == ("Privacidad", -7.9)
    assert lista[0].ejemplos == "DOGE, SHIB, PEPE"


def test_leer_se_salta_las_que_no_dicen_nada():
    datos = _todas() + [_categoria("made-in-usa", 50.0), _categoria("stablecoins")]

    assert {s.nombre for s in leer(datos)} == {n for n, _ in SECTORES.values()}


def test_leer_ignora_basura():
    datos = _todas()
    datos[0] = _categoria("layer-1", cambio=None)
    datos[1] = _categoria("layer-2", capital=0)
    datos += [None, {"name": "sin id"}, _categoria("oracle", cambio=float("nan"))]

    nombres = [s.nombre for s in leer(datos)]

    assert "Blockchains base" not in nombres
    assert "Capas sobre Ethereum" not in nombres
    assert nombres.count("Oráculos") == 1


def test_con_pocas_no_saca_nada():
    datos = [_categoria(i) for i in list(SECTORES)[: MINIMO - 1]]

    assert leer(datos) == []
    assert leer({"error": "algo"}) == []
