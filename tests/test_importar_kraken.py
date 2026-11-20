"""Tests de /importar con el trades.csv de Kraken."""

from datetime import datetime, timezone

import pytest

from crypto_tracker.importar import ImportarError, leer, leer_kraken

CABECERA = (
    '"txid","ordertxid","pair","time","type","ordertype","price","cost","fee",'
    '"vol","margin","misc","ledgers"\n'
)


def _fila(par, cuando, tipo, precio, coste, comision, vol, margen="0.00000"):
    return (
        f'"T1","O1","{par}","{cuando}","{tipo}","limit","{precio}","{coste}",'
        f'"{comision}","{vol}","{margen}","","L1,L2"'
    )


def _csv(*filas):
    return CABECERA + "".join(f"{f}\n" for f in filas)


def test_compra_con_comision():
    texto = _csv(
        _fila(
            "XXBTZEUR",
            "2024-03-01 10:15:22.1234",
            "buy",
            "50000.0",
            "100.00",
            "0.26",
            "0.00200000",
        )
    )

    lectura = leer_kraken(texto, "eur")
    (op,) = lectura.operaciones

    assert lectura.origen == "Kraken"
    assert op.cuando == datetime(2024, 3, 1, 10, 15, 22, tzinfo=timezone.utc)
    assert op.coin_id == "bitcoin"
    assert op.tipo == "compra"
    assert op.cantidad == pytest.approx(0.002)
    assert op.coste == pytest.approx(100.26)  # cost no lleva la comisión
    assert op.comision == pytest.approx(0.26)


def test_venta_resta_la_comision():
    texto = _csv(
        _fila(
            "XETHZEUR",
            "2024-05-02 08:00:00.0000",
            "sell",
            "3000.0",
            "300.00",
            "0.78",
            "0.1",
        )
    )

    (op,) = leer_kraken(texto, "eur").operaciones

    assert op.coin_id == "ethereum"
    assert op.tipo == "venta"
    assert op.coste == pytest.approx(299.22)


@pytest.mark.parametrize(
    "par, coin_id",
    [
        ("XXBTZEUR", "bitcoin"),
        ("XBT/EUR", "bitcoin"),
        ("SOLEUR", "solana"),
        ("XXDGZEUR", "dogecoin"),
        ("XXRPZEUR", "ripple"),
        ("XBTUSDT", None),  # USDT, no USD: con eur se salta
    ],
)
def test_nombres_de_kraken(par, coin_id):
    texto = _csv(_fila(par, "2024-01-01 00:00:00", "buy", "1", "10", "0", "10"))

    ops = leer_kraken(texto, "eur").operaciones
    assert (ops[0].coin_id if ops else None) == coin_id


def test_sin_decimales_en_la_hora():
    texto = _csv(_fila("SOLEUR", "2024-01-01 12:30:45", "buy", "1", "10", "0", "10"))

    assert leer_kraken(texto, "eur").operaciones[0].cuando.second == 45


def test_salta_lo_que_no_puede_apuntar():
    texto = _csv(
        _fila("XETHXXBT", "2024-01-01 00:00:00", "buy", "0.05", "0.05", "0", "1"),
        _fila("XXBTZUSD", "2024-01-01 00:00:00", "buy", "1", "10", "0", "1"),
        _fila("XXBTZEUR", "2024-01-01 00:00:00", "buy", "1", "10", "0", "1", "5.0"),
        _fila("RAROEUR", "2024-01-01 00:00:00", "buy", "1", "10", "0", "1"),
        _fila("SOLEUR", "mal", "buy", "1", "10", "0", "1"),
    )

    lectura = leer_kraken(texto, "eur")

    assert lectura.operaciones == []
    assert lectura.saltadas == {
        "en BTC, no en EUR": 1,
        "filas que no entiendo": 1,
        "en USD, no en EUR": 1,
        "con margen": 1,
        "no sé qué es RARO": 1,
    }


def test_con_usd_valen_las_estables():
    texto = _csv(
        _fila("XBTUSDT", "2024-01-01 00:00:00", "buy", "1", "10", "0", "1"),
        _fila("XXBTZUSD", "2024-01-02 00:00:00", "buy", "1", "10", "0", "1"),
    )

    assert len(leer_kraken(texto, "usd").operaciones) == 2


def test_las_ordena_de_vieja_a_nueva():
    texto = _csv(
        _fila("SOLEUR", "2024-02-01 00:00:00", "sell", "1", "10", "0", "1"),
        _fila("SOLEUR", "2024-01-01 00:00:00", "buy", "1", "10", "0", "1"),
    )

    tipos = [o.tipo for o in leer_kraken(texto, "eur").operaciones]

    assert tipos == ["compra", "venta"]


def test_leer_distingue_kraken_y_binance():
    kraken = _csv(_fila("SOLEUR", "2024-01-01 00:00:00", "buy", "1", "10", "0", "1"))
    binance = (
        '"Date(UTC)","Pair","Side","Price","Executed","Amount","Fee"\n'
        '"2024-03-01 10:15:22","BTCEUR","BUY","50,000.00","0.002BTC",'
        '"100EUR","0EUR"\n'
    )

    assert leer("﻿" + kraken, "eur").origen == "Kraken"
    assert leer(binance, "eur").origen == "Binance"


def test_leer_otro_csv():
    with pytest.raises(ImportarError, match="ni el de Kraken"):
        leer("fecha;importe\n2024-01-01;5\n", "eur")
