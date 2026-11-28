"""Tests de /dormir: las horas tranquilas cambiadas desde Telegram."""

import time as reloj
from dataclasses import replace
from datetime import datetime, time, timedelta

import pytest

import main
from crypto_tracker.avisos.diario import leer_dormir
from crypto_tracker.nucleo import coingecko, database, telegram
from crypto_tracker.nucleo.config import Config, ConfigError, Watch


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("23-8", (time(23), time(8))),
        ("23:30 7:00", (time(23, 30), time(7))),
        ("de 0 a 7", (time(0), time(7))),
        ("  1-6:45 ", (time(1), time(6, 45))),
        ("no", None),
        ("OFF", None),
    ],
)
def test_leer(texto, esperado):
    assert leer_dormir(texto) == esperado


@pytest.mark.parametrize("texto", ["23", "mañana", "25-8", "23-8-9", "a-b"])
def test_leer_mal_escrito(texto):
    with pytest.raises(ConfigError, match="No entiendo"):
        leer_dormir(texto)


def test_leer_misma_hora():
    with pytest.raises(ConfigError, match="misma hora"):
        leer_dormir("8-8")


def test_se_guarda_y_se_lee(tmp_path):
    ruta = str(tmp_path / "test.db")
    database.init_db(ruta)

    assert database.horas_dormir(ruta) == (False, None)
    database.guardar_dormir(ruta, (time(23, 30), time(7)))
    assert database.horas_dormir(ruta) == (True, (time(23, 30), time(7)))
    database.guardar_dormir(ruta, None)
    assert database.horas_dormir(ruta) == (True, None)


def test_lo_guardado_roto_manda_el_env(tmp_path):
    ruta = str(tmp_path / "test.db")
    database.init_db(ruta)
    with database._connect(ruta) as conn:
        conn.execute(
            "INSERT INTO ajustes (clave, valor) VALUES (?, ?)",
            (database.HORAS_DORMIR, "las once"),
        )

    assert database.horas_dormir(ruta) == (False, None)


# --- el comando ---


@pytest.fixture
def config(tmp_path):
    ruta = str(tmp_path / "test.db")
    database.init_db(ruta)
    return Config("token", "123", [Watch("bitcoin", percent=5)], "eur", 300, ruta, 0)


@pytest.fixture
def enviados(monkeypatch):
    lista = []
    monkeypatch.setattr(
        telegram, "send_message", lambda t, c, texto, **kw: lista.append(texto) or True
    )
    return lista


def _mensaje(texto):
    return {"chat": {"id": 123}, "text": texto, "date": int(reloj.time())}


def test_a_secas_sin_nada(config, enviados):
    main.atender(config, _mensaje("/dormir"))

    assert "suenan siempre" in enviados[0]


def test_a_secas_dice_las_del_env(config, enviados):
    del_env = replace(config, horas_tranquilas=(time(23), time(8)))

    main.atender(del_env, _mensaje("/dormir"))

    assert "De 23:00 a 08:00 los avisos llegan sin sonar" in enviados[0]


def test_ponerlas_cambia_el_sonido(config, enviados):
    tres = datetime(2026, 9, 29, 3, 0)
    assert main._sin_sonido(config, tres) is False

    main.atender(config, _mensaje("/dormir 23-8"))

    assert "de 23:00 a 08:00 te llegan sin sonar" in enviados[0]
    assert main._sin_sonido(config, tres) is True
    assert main._sin_sonido(config, datetime(2026, 9, 29, 15, 0)) is False


def test_no_gana_al_env(config, enviados):
    del_env = replace(config, horas_tranquilas=(time(23), time(8)))

    main.atender(del_env, _mensaje("/dormir no"))
    main.atender(del_env, _mensaje("/dormir"))

    assert "suenan siempre" in enviados[0]
    assert "Ahora los avisos suenan siempre" in enviados[1]
    assert main._sin_sonido(del_env, datetime(2026, 9, 29, 3, 0)) is False


def test_mal_escrito_no_toca_nada(config, enviados):
    main.atender(config, _mensaje("/dormir <b>pronto</b>"))

    assert "No entiendo '&lt;b&gt;pronto&lt;/b&gt;'" in enviados[0]
    assert database.horas_dormir(config.database_path) == (False, None)


def test_tranquilas_es_lo_mismo(config, enviados):
    main.atender(config, _mensaje("/tranquilas 0-7"))

    assert "de 00:00 a 07:00" in enviados[0]


def test_noche_sigue_siendo_el_hotel(config, enviados):
    main.atender(config, _mensaje("/dormir 23-8"))

    assert main.comandos.interpretar("/noche")[0] == "hotel"


def test_sale_en_ajustes(config, enviados):
    main.atender(config, _mensaje("/dormir 1-6"))
    main.atender(config, _mensaje("/ajustes"))

    assert "🌙 Sin sonar de 01:00 a 06:00" in enviados[1]


def test_los_avisos_llegan_sin_sonar(config, monkeypatch):
    sonidos = []
    monkeypatch.setattr(
        telegram,
        "send_message",
        lambda t, c, texto, sin_sonido=False, **kw: sonidos.append(sin_sonido) or True,
    )
    monkeypatch.setattr(coingecko, "get_prices", lambda ids, cur: {"bitcoin": 90000.0})
    ahora = datetime.now()
    database.guardar_dormir(
        config.database_path,
        (
            (ahora - timedelta(hours=1)).time().replace(second=0, microsecond=0),
            (ahora + timedelta(hours=1)).time().replace(second=0, microsecond=0),
        ),
    )

    main.ejecutar_ciclo(config, {"bitcoin": "%60000.0"})

    assert sonidos == [True]
