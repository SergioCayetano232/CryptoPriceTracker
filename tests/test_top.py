"""Tests de /top."""

from crypto_tracker.top import CUANTAS, Movida, leer, separar


def _moneda(coin_id="solana", variacion=12.5, **cambios):
    datos = {
        "id": coin_id,
        "name": coin_id.title(),
        "symbol": coin_id[:3],
        "current_price": 150.0,
        "price_change_percentage_24h": variacion,
    }
    return {**datos, **cambios}


def _movida(coin_id, variacion):
    return Movida(coin_id, coin_id.title(), coin_id[:3].upper(), 150.0, variacion)


def test_leer():
    assert leer([_moneda()]) == [Movida("solana", "Solana", "SOL", 150.0, 12.5)]


def test_leer_sin_precio_o_sin_variacion_no_sirve():
    datos = [
        _moneda("a", current_price=None),
        _moneda("b", variacion=None),
        _moneda("c", variacion="x"),
        _moneda("d"),
    ]

    assert [m.coin_id for m in leer(datos)] == ["d"]


def test_leer_ignora_basura():
    assert leer([None, {"name": "Sin id"}, _moneda()])[0].coin_id == "solana"
    assert leer({"error": "algo"}) == []


def test_separar_ordena_de_mas_a_menos():
    lista = [_movida("a", 3), _movida("b", -8), _movida("c", 15), _movida("d", -2)]

    suben, bajan = separar(lista)

    assert [m.coin_id for m in suben] == ["c", "a"]
    assert [m.coin_id for m in bajan] == ["b", "d"]


def test_separar_como_mucho_cinco_de_cada():
    lista = [_movida(f"s{i}", i + 1) for i in range(8)]
    lista += [_movida(f"b{i}", -(i + 1)) for i in range(8)]

    suben, bajan = separar(lista)

    assert len(suben) == len(bajan) == CUANTAS
    assert suben[0].coin_id == "s7"
    assert bajan[0].coin_id == "b7"


def test_un_dia_todo_en_verde():
    suben, bajan = separar([_movida("a", 1), _movida("b", 0)])

    # La que no se mueve no va en ninguna
    assert [m.coin_id for m in suben] == ["a"]
    assert bajan == []
