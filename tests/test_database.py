"""Tests de la base de datos, sobre un fichero temporal."""

import pytest

from crypto_tracker import database


@pytest.fixture
def db(tmp_path):
    ruta = str(tmp_path / "test.db")
    database.init_db(ruta)
    return ruta


def test_init_crea_la_carpeta(tmp_path):
    ruta = str(tmp_path / "sub" / "otra" / "test.db")
    database.init_db(ruta)

    assert (tmp_path / "sub" / "otra" / "test.db").exists()


def test_init_se_puede_llamar_dos_veces(db):
    database.init_db(db)


def test_guardar_y_leer_ultimo_precio(db):
    database.save_prices(db, {"bitcoin": 63000.0}, "eur")

    assert database.get_last_price(db, "bitcoin") == 63000.0


def test_ultimo_precio_sin_datos(db):
    assert database.get_last_price(db, "bitcoin") is None


def test_guardar_varios(db):
    filas = database.save_prices(db, {"bitcoin": 63000.0, "ethereum": 3200.0}, "eur")

    assert filas == 2


def test_guardar_vacio_no_hace_nada(db):
    assert database.save_prices(db, {}, "eur") == 0


def test_historico_ordenado_del_mas_nuevo_al_mas_viejo(db):
    database.save_prices(db, {"bitcoin": 61000.0}, "eur")
    database.save_prices(db, {"bitcoin": 62000.0}, "eur")
    database.save_prices(db, {"bitcoin": 63000.0}, "eur")

    filas = database.get_history(db, "bitcoin")

    assert [f["price"] for f in filas] == [63000.0, 62000.0, 61000.0]


def test_historico_respeta_el_limite(db):
    for precio in range(60000, 60010):
        database.save_prices(db, {"bitcoin": float(precio)}, "eur")

    assert len(database.get_history(db, "bitcoin", limit=3)) == 3


def test_estado_va_y_vuelve(db):
    database.save_state(db, {"bitcoin": "alto", "ethereum": "63000.0"})

    assert database.load_state(db) == {"bitcoin": "alto", "ethereum": "63000.0"}


def test_estado_se_pisa(db):
    database.save_state(db, {"bitcoin": "alto"})
    database.save_state(db, {"bitcoin": "bajo"})

    assert database.load_state(db) == {"bitcoin": "bajo"}


def test_estado_vacio(db):
    assert database.load_state(db) == {}


def test_purga_respeta_lo_reciente(db):
    database.save_prices(db, {"bitcoin": 63000.0}, "eur")

    assert database.purge_old_prices(db, 90) == 0
    assert database.get_last_price(db, "bitcoin") == 63000.0


def test_purga_borra_lo_viejo(db):
    import sqlite3

    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO prices (coin_id, price, currency, created_at) VALUES (?,?,?,?)",
        ("bitcoin", 30000.0, "eur", "2020-01-01T00:00:00+00:00"),
    )
    conn.commit()
    conn.close()

    database.save_prices(db, {"bitcoin": 63000.0}, "eur")

    assert database.purge_old_prices(db, 90) == 1
    assert database.get_last_price(db, "bitcoin") == 63000.0


def test_purga_con_cero_no_borra(db):
    database.save_prices(db, {"bitcoin": 63000.0}, "eur")

    assert database.purge_old_prices(db, 0) == 0


def test_error_si_la_ruta_es_imposible():
    with pytest.raises(database.DatabaseError):
        database.init_db("/ruta/que/no/existe/y/no/se/puede/crear/x.db")


def _insertar_con_fecha(db, coin_id, precio, horas_atras):
    """Mete un precio fechado en el pasado, que save_prices siempre usa ahora."""
    import sqlite3
    from datetime import datetime, timedelta, timezone

    cuando = (datetime.now(timezone.utc) - timedelta(hours=horas_atras)).isoformat(
        timespec="seconds"
    )
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO prices (coin_id, price, currency, created_at) VALUES (?,?,?,?)",
        (coin_id, precio, "eur", cuando),
    )
    conn.commit()
    conn.close()


def test_precio_de_hace_24h(db):
    _insertar_con_fecha(db, "bitcoin", 60000.0, 30)
    database.save_prices(db, {"bitcoin": 63000.0}, "eur")

    assert database.get_price_at(db, "bitcoin", 24) == 60000.0


def test_precio_de_hace_24h_coge_el_mas_cercano(db):
    _insertar_con_fecha(db, "bitcoin", 50000.0, 80)
    _insertar_con_fecha(db, "bitcoin", 60000.0, 26)
    database.save_prices(db, {"bitcoin": 63000.0}, "eur")

    assert database.get_price_at(db, "bitcoin", 24) == 60000.0


def test_precio_de_hace_24h_sin_historico(db):
    database.save_prices(db, {"bitcoin": 63000.0}, "eur")

    # solo hay un precio de ahora mismo, nada de hace 24h
    assert database.get_price_at(db, "bitcoin", 24) is None


def test_precio_de_hace_24h_de_otra_cripto(db):
    _insertar_con_fecha(db, "ethereum", 3000.0, 30)

    assert database.get_price_at(db, "bitcoin", 24) is None


def test_precio_de_hace_24h_ignora_lo_demasiado_viejo(db):
    # el bot estuvo parado una semana: eso no es "variacion en 24h"
    _insertar_con_fecha(db, "bitcoin", 40000.0, 24 * 7)

    assert database.get_price_at(db, "bitcoin", 24) is None


def test_precio_de_hace_24h_acepta_dentro_del_margen(db):
    _insertar_con_fecha(db, "bitcoin", 60000.0, 34)

    assert database.get_price_at(db, "bitcoin", 24) == 60000.0
