"""Tests de los invitados."""

from datetime import datetime, timezone

import pytest

from crypto_tracker.config import Config, Posicion, Watch
from crypto_tracker.usuarios import (
    LARGO,
    LETRAS,
    MAX_INVITADOS,
    UsuarioError,
    archivo,
    caducidad,
    codigo,
    comprobar_hueco,
    config_de,
    es_chat,
    leer_codigo,
    nombre,
)

CONFIG = Config(
    telegram_token="token",
    telegram_chat_id="123",
    watchlist=[Watch("bitcoin", percent=5)],
    vs_currency="eur",
    check_interval=300,
    database_path="data/prices.db",
    history_days=90,
    cartera=(Posicion("bitcoin", 1, 1000),),
)


def test_codigo():
    c = codigo()
    assert len(c) == LARGO
    assert set(c) <= set(LETRAS)
    assert codigo() != c  # al azar de verdad


@pytest.mark.parametrize(
    "texto,esperado",
    [("ABCD2345", "ABCD2345"), (" abcd2345 ", "ABCD2345"), ("", None),
     ("ABCD234", None), ("ABCD234O", None), ("../../etc", None)],
)  # fmt: skip
def test_leer_codigo(texto, esperado):
    assert leer_codigo(texto) == esperado


def test_es_chat():
    assert es_chat("123456")
    assert es_chat("-100123")
    assert not es_chat("12a")
    assert not es_chat("../123")
    assert not es_chat("")


def test_archivo_junto_al_tuyo():
    assert archivo(CONFIG, "555") == "data/usuarios/555.db"
    with pytest.raises(ValueError):
        archivo(CONFIG, "../../etc/passwd")


def test_config_de_un_invitado_empieza_vacia():
    c = config_de(CONFIG, "555")

    assert c.telegram_chat_id == "555"
    assert c.database_path == "data/usuarios/555.db"
    assert c.watchlist == [] and c.cartera == ()
    assert c.invitado
    assert c.vs_currency == "eur"  # lo demás, como el tuyo
    assert not CONFIG.invitado


def test_nombre():
    assert nombre({"first_name": "Ana", "username": "ana_btc"}) == "Ana (@ana_btc)"
    assert nombre({"first_name": "Ana"}) == "Ana"
    assert nombre({"username": "ana_btc"}) == "@ana_btc"
    assert nombre({}) is None


def test_hueco():
    comprobar_hueco(MAX_INVITADOS - 1)
    with pytest.raises(UsuarioError, match="máximo"):
        comprobar_hueco(MAX_INVITADOS)


def test_caducidad():
    ahora = datetime(2026, 11, 21, 12, tzinfo=timezone.utc)
    assert caducidad(ahora) == datetime(2026, 11, 22, 12, tzinfo=timezone.utc)
