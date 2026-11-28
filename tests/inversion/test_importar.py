"""Tests de /importar con el CSV de Binance."""

from datetime import datetime, timezone

import pytest

from crypto_tracker.inversion.importar import ImportarError, leer_binance

CABECERA = '"Date(UTC)","Pair","Side","Price","Executed","Amount","Fee"\n'


def _csv(*filas):
    return CABECERA + "".join(f"{f}\n" for f in filas)


def test_compra_con_comision_en_la_cripto():
    texto = _csv(
        '"2024-03-01 10:15:22","BTCEUR","BUY","50,000.00","0.00200000BTC",'
        '"100.00000000EUR","0.00000200BTC"'
    )

    (op,) = leer_binance(texto, "eur").operaciones

    assert op.cuando == datetime(2024, 3, 1, 10, 15, 22, tzinfo=timezone.utc)
    assert op.coin_id == "bitcoin"
    assert op.tipo == "compra"
    assert op.cantidad == pytest.approx(0.001998)  # te llega menos
    assert op.coste == 100
    assert op.comision == pytest.approx(0.1)


def test_venta_con_comision_en_euros():
    texto = _csv(
        '"2024-05-02 08:00:00","ETHEUR","SELL","3000","0.5ETH","1500EUR","1.5EUR"'
    )

    (op,) = leer_binance(texto, "eur").operaciones

    assert op.tipo == "venta"
    assert op.cantidad == 0.5
    assert op.coste == 1498.5  # lo que te queda de verdad
    assert op.comision == 1.5


def test_comision_en_bnb_se_apunta_sin_ella():
    texto = _csv(
        '"2024-05-02 08:00:00","ETHEUR","BUY","3000","0.5ETH","1500EUR","0.01BNB"'
    )

    lectura = leer_binance(texto, "eur")

    assert lectura.operaciones[0].comision is None
    assert lectura.operaciones[0].coste == 1500
    assert lectura.sin_comision == 1


def test_formato_viejo_sin_moneda_pegada():
    texto = _csv('"2023-01-01 00:00:00","SOLEUR","BUY","10","3","30","0"')

    (op,) = leer_binance(texto, "eur").operaciones

    assert (op.coin_id, op.cantidad, op.coste, op.comision) == ("solana", 3, 30, None)


def test_con_usd_valen_las_estables():
    texto = _csv(
        '"2023-01-01 00:00:00","BTCUSDT","BUY","20000","0.1BTC","2000USDT","0"'
    )

    assert len(leer_binance(texto, "usd").operaciones) == 1
    assert leer_binance(texto, "eur").saltadas == {"en USDT, no en EUR": 1}


def test_salta_lo_que_no_puede_apuntar():
    texto = _csv(
        '"2023-01-01 00:00:00","ETHBTC","BUY","0.05","1ETH","0.05BTC","0"',
        '"2023-01-01 00:00:00","ZZZEUR","BUY","1","5ZZZ","5EUR","0"',
        '"esto no es una fecha","BTCEUR","BUY","1","1BTC","1EUR","0"',
        '"2023-01-01 00:00:00","BTCEUR","BUY","1","1BTC","1EUR","0"',
    )

    lectura = leer_binance(texto, "eur")

    assert len(lectura.operaciones) == 1
    assert lectura.saltadas == {
        "en BTC, no en EUR": 1,
        "no sé qué es ZZZ": 1,
        "filas que no entiendo": 1,
    }


def test_las_ordena_de_vieja_a_nueva():
    # Binance las exporta de la más nueva a la más vieja
    texto = _csv(
        '"2024-02-01 00:00:00","BTCEUR","SELL","1","1BTC","1EUR","0"',
        '"2024-01-01 00:00:00","BTCEUR","BUY","1","1BTC","1EUR","0"',
    )

    tipos = [o.tipo for o in leer_binance(texto, "eur").operaciones]

    assert tipos == ["compra", "venta"]


def test_con_bom_de_excel():
    texto = "﻿" + _csv('"2023-01-01 00:00:00","BTCEUR","BUY","1","1BTC","1EUR","0"')

    assert len(leer_binance(texto, "eur").operaciones) == 1


@pytest.mark.parametrize("texto", ["", "hola,adios\n1,2\n", "Date,Coin\n"])
def test_si_no_es_de_binance(texto):
    with pytest.raises(ImportarError):
        leer_binance(texto, "eur")
