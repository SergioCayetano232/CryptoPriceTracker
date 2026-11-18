"""Tests de /alerta eth/btc."""

import pytest

from crypto_tracker import database
from crypto_tracker.alertaratio import (
    AlertaRatio,
    AlertaRatioError,
    crear,
    criptos,
    cumplida,
    es_quitar,
    es_ratio,
    interpretar,
    objetivo,
)
from crypto_tracker.alerts import (
    formatear_alerta_ratio,
    formatear_alertas_ratio,
    formatear_aviso_ratio,
    formatear_ratio_ahora,
)


@pytest.mark.parametrize(
    "argumento, sale",
    [
        ("eth/btc 0.05", True),
        ("eth/btc", True),
        ("bitcoin 70000", False),
        ("", False),
        ("btc 60000 o 80000", False),
    ],
)
def test_es_ratio(argumento, sale):
    assert es_ratio(argumento) is sale


def test_interpretar():
    assert interpretar("eth/btc 0.05") == ("ethereum", "bitcoin", "0.05")
    assert interpretar("eth/btc") == ("ethereum", "bitcoin", None)
    assert interpretar("ETH/BTC no") == ("ethereum", "bitcoin", "no")


@pytest.mark.parametrize(
    "argumento, error",
    [
        ("eth/ 0.05", "Escríbelo así"),
        ("eth/btc/sol 1", "Escríbelo así"),
        ("eth/btc 0.05 7d", "Escríbelo así"),
        ("btc/bitcoin 1", "la misma"),
    ],
)
def test_interpretar_mal(argumento, error):
    with pytest.raises(AlertaRatioError, match=error):
        interpretar(argumento)


def test_objetivo():
    assert objetivo("0.05") == 0.05
    assert objetivo("0,05") == 0.05
    for malo in ("mucho", "0", "-1"):
        with pytest.raises(AlertaRatioError, match="no es un número"):
            objetivo(malo)


def test_es_quitar():
    assert es_quitar("no") and es_quitar("Quitar")
    assert not es_quitar("0.05") and not es_quitar(None)


def test_crear_sabe_hacia_donde():
    assert crear("ethereum", "bitcoin", 0.05, 0.03).sube
    assert not crear("ethereum", "bitcoin", 0.02, 0.03).sube
    with pytest.raises(AlertaRatioError, match="justo eso"):
        crear("ethereum", "bitcoin", 0.03, 0.03)


@pytest.mark.parametrize(
    "sube, ahora, sale",
    [
        (True, 0.049, False),
        (True, 0.05, True),
        (True, 0.06, True),  # se pasó entre ciclo y ciclo
        (False, 0.051, False),
        (False, 0.04, True),
    ],
)
def test_cumplida(sube, ahora, sale):
    assert cumplida(AlertaRatio("ethereum", "bitcoin", 0.05, sube), ahora) is sale


def test_criptos_sin_repetir():
    lista = [
        AlertaRatio("ethereum", "bitcoin", 0.05, True),
        AlertaRatio("solana", "bitcoin", 0.002, False),
    ]
    assert criptos(lista) == ["ethereum", "bitcoin", "solana"]


def test_guardar_leer_y_quitar(tmp_path):
    db = str(tmp_path / "p.db")
    database.init_db(db)
    database.guardar_alerta_ratio(db, AlertaRatio("ethereum", "bitcoin", 0.05, True))
    # Una por pareja: la segunda pisa a la primera.
    database.guardar_alerta_ratio(db, AlertaRatio("ethereum", "bitcoin", 0.02, False))
    assert database.get_alertas_ratio(db) == [
        AlertaRatio("ethereum", "bitcoin", 0.02, False)
    ]
    assert database.quitar_alerta_ratio(db, "ethereum", "bitcoin")
    assert not database.quitar_alerta_ratio(db, "ethereum", "bitcoin")
    assert database.get_alertas_ratio(db) == []


def test_formatear():
    a = AlertaRatio("ethereum", "bitcoin", 0.05, True)

    creada = formatear_alerta_ratio(a, 0.0312)
    assert "cuando 1 <b>Ethereum</b> suba a 0,0500 Bitcoin" in creada
    assert "/alerta ethereum/bitcoin no" in creada
    assert "vale ahora 0,0312 Bitcoin" in formatear_ratio_ahora(
        "ethereum", "bitcoin", 0.0312
    )
    assert "1 <b>Ethereum</b> 🔺 0,0500 Bitcoin" in formatear_alertas_ratio([a])
    aviso = formatear_aviso_ratio(a, 0.0507)
    assert "<b>Ethereum</b> ha subido a <b>0,0507</b> Bitcoin" in aviso
