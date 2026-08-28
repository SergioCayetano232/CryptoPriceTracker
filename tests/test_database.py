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
