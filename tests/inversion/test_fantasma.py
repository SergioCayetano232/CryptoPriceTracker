"""Tests de /fantasma."""

from datetime import datetime, timezone

import pytest

from crypto_tracker.inversion.fantasma import (
    FantasmaError,
    Hueco,
    a_texto,
    comprar,
    de_texto,
    interpretar,
    nueva,
    vender,
)

AHORA = datetime(2026, 11, 17, 10, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    "argumento,esperado",
    [
        ("", ("ver",)),
        ("reinicia", ("reinicia", 1000)),
        ("reinicia 5000", ("reinicia", 5000)),
        ("compra btc 200", ("compra", "bitcoin", 200)),
        ("vende eth todo", ("vende", "ethereum", ("parte", 1.0))),
        ("vende eth 50%", ("vende", "ethereum", ("parte", 0.5))),
        ("vende eth 100", ("vende", "ethereum", ("importe", 100))),
    ],
)
def test_interpretar(argumento, esperado):
    assert interpretar(argumento) == esperado


@pytest.mark.parametrize(
    "argumento",
    ["compra btc", "compra btc mucho", "vende btc 150%", "vende btc -5", "hola"],
)
def test_interpretar_malo(argumento):
    with pytest.raises(FantasmaError):
        interpretar(argumento)


def test_comprar_y_valor():
    f = comprar(nueva(1000, AHORA, 50000), "bitcoin", 200, 50000)

    assert f.caja == 800
    assert f.posiciones == {"bitcoin": Hueco(0.004, 200)}
    assert f.valor({"bitcoin": 60000}) == pytest.approx(1040)
    assert f.operaciones == 1


def test_comprar_mas_de_lo_que_tienes():
    with pytest.raises(FantasmaError, match="Solo te quedan"):
        comprar(nueva(100, AHORA, None), "bitcoin", 150, 50000)


def test_comprar_dos_veces_suma():
    f = nueva(1000, AHORA, None)
    f = comprar(f, "bitcoin", 100, 50000)
    f = comprar(f, "bitcoin", 100, 25000)

    assert f.posiciones["bitcoin"] == Hueco(pytest.approx(0.006), 200)


def test_vender_mitad_todo_e_importe():
    f = comprar(nueva(1000, AHORA, None), "bitcoin", 400, 50000)  # 0,008

    f, cobrado = vender(f, "bitcoin", ("parte", 0.5), 60000)
    assert cobrado == pytest.approx(240)
    assert f.posiciones["bitcoin"] == Hueco(pytest.approx(0.004), pytest.approx(200))

    f, cobrado = vender(f, "bitcoin", ("importe", 60), 60000)
    assert cobrado == pytest.approx(60)

    f, cobrado = vender(f, "bitcoin", ("parte", 1.0), 60000)
    assert cobrado == pytest.approx(180)
    assert f.posiciones == {}
    assert f.caja == pytest.approx(1080)


def test_vender_lo_que_no_tienes():
    f = comprar(nueva(1000, AHORA, None), "bitcoin", 100, 50000)

    with pytest.raises(FantasmaError, match="No tienes"):
        vender(f, "ethereum", ("parte", 1.0), 3000)
    with pytest.raises(FantasmaError, match="Solo tienes"):
        vender(f, "bitcoin", ("importe", 500), 50000)


def test_vender_casi_todo_no_deja_migas():
    f = comprar(nueva(1000, AHORA, None), "bitcoin", 100, 50000)

    f, _ = vender(f, "bitcoin", ("importe", 99.995), 50000)

    assert f.posiciones == {}


def test_sin_precio_no_da_total():
    f = comprar(nueva(1000, AHORA, None), "bitcoin", 100, 50000)

    assert f.valor({}) is None


def test_en_bitcoin():
    assert nueva(1000, AHORA, 50000).en_bitcoin(60000) == pytest.approx(1200)
    assert nueva(1000, AHORA, None).en_bitcoin(60000) is None


def test_a_texto_y_vuelta():
    f = comprar(nueva(1000, AHORA, 50000), "bitcoin", 200, 50000)

    assert de_texto(a_texto(f)) == f


@pytest.mark.parametrize("texto", ["", "{}", "basura", '{"inicio": "ayer"}'])
def test_de_texto_malo(texto):
    assert de_texto(texto) is None
