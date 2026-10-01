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


# --- silencio ---


def test_sin_silencio_de_entrada(db):
    assert database.silenciado_hasta(db) is None


def test_silenciar_y_leerlo(db):
    from datetime import datetime, timedelta, timezone

    hasta = datetime.now(timezone.utc) + timedelta(hours=2)
    database.silenciar_hasta(db, hasta)

    guardado = database.silenciado_hasta(db)

    assert guardado is not None
    assert abs((guardado - hasta).total_seconds()) < 2


def test_el_silencio_caduca_solo(db):
    from datetime import datetime, timedelta, timezone

    database.silenciar_hasta(db, datetime.now(timezone.utc) - timedelta(minutes=1))

    assert database.silenciado_hasta(db) is None


def test_quitar_el_silencio(db):
    from datetime import datetime, timedelta, timezone

    database.silenciar_hasta(db, datetime.now(timezone.utc) + timedelta(hours=2))
    database.silenciar_hasta(db, None)

    assert database.silenciado_hasta(db) is None


def test_silenciar_pisa_lo_anterior(db):
    from datetime import datetime, timedelta, timezone

    ahora = datetime.now(timezone.utc)
    database.silenciar_hasta(db, ahora + timedelta(hours=5))
    database.silenciar_hasta(db, ahora + timedelta(hours=1))

    guardado = database.silenciado_hasta(db)

    assert (guardado - ahora).total_seconds() < 3700


def test_un_silencio_ilegible_no_revienta(db):
    import sqlite3

    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO ajustes (clave, valor) VALUES (?, ?)",
        (database.SILENCIO, "esto no es una fecha"),
    )
    conn.commit()
    conn.close()

    assert database.silenciado_hasta(db) is None


# --- ultimas horas ---


def test_precios_de_las_ultimas_horas(db):
    _insertar_con_fecha(db, "bitcoin", 50000.0, 30)  # fuera
    _insertar_con_fecha(db, "bitcoin", 60000.0, 20)
    _insertar_con_fecha(db, "bitcoin", 61000.0, 10)
    _insertar_con_fecha(db, "ethereum", 3000.0, 5)  # otra cripto

    # del mas viejo al mas nuevo, que es como se dibuja
    assert database.get_prices_since(db, "bitcoin", 24, "eur") == [60000.0, 61000.0]


def test_precios_de_las_ultimas_horas_solo_de_esa_moneda(db):
    _insertar_con_fecha(db, "bitcoin", 60000.0, 5)
    database.save_prices(db, {"bitcoin": 68000.0}, "usd")

    assert database.get_prices_since(db, "bitcoin", 24, "eur") == [60000.0]


# --- ultimo resumen ---


def test_sin_resumen_de_entrada(db):
    assert database.ultimo_resumen(db) is None


def test_guardar_el_ultimo_resumen(db):
    from datetime import date

    database.guardar_resumen(db, date(2026, 9, 28))
    database.guardar_resumen(db, date(2026, 9, 29))

    assert database.ultimo_resumen(db) == date(2026, 9, 29)


def test_el_resumen_no_pisa_el_silencio(db):
    from datetime import date, datetime, timedelta, timezone

    database.silenciar_hasta(db, datetime.now(timezone.utc) + timedelta(hours=1))
    database.guardar_resumen(db, date(2026, 9, 29))

    assert database.silenciado_hasta(db) is not None


# --- movimiento brusco ---


def test_precios_desde_una_fecha(db):
    from datetime import datetime, timedelta, timezone

    _insertar_con_fecha(db, "bitcoin", 60000.0, 2)
    _insertar_con_fecha(db, "bitcoin", 61000.0, 0.5)

    desde = datetime.now(timezone.utc) - timedelta(hours=1)

    assert database.get_prices_desde(db, "bitcoin", desde, "eur") == [61000.0]


def test_ultimo_brusco_por_cripto(db):
    from datetime import datetime, timezone

    cuando = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)
    database.guardar_brusco(db, "bitcoin", cuando)

    assert database.ultimo_brusco(db, "bitcoin") == cuando
    assert database.ultimo_brusco(db, "ethereum") is None


# --- alertas de /alerta ---


def test_puntual_va_y_vuelve(db):
    creada = database.crear_puntual(db, "bitcoin", 70000.0, True, "eur")

    assert database.get_puntuales(db, "eur") == [creada]
    assert creada.sube is True


def test_puntuales_en_orden_de_creacion(db):
    a = database.crear_puntual(db, "bitcoin", 70000.0, True, "eur")
    b = database.crear_puntual(db, "ethereum", 2000.0, False, "eur")

    assert database.get_puntuales(db, "eur") == [a, b]


def test_puntuales_de_otra_moneda_no_cuentan(db):
    database.crear_puntual(db, "bitcoin", 70000.0, True, "usd")

    assert database.get_puntuales(db, "eur") == []


def test_borrar_puntual(db):
    a = database.crear_puntual(db, "bitcoin", 70000.0, True, "eur")
    b = database.crear_puntual(db, "bitcoin", 55000.0, False, "eur")

    assert database.borrar_puntual(db, a.id) is True
    assert database.get_puntuales(db, "eur") == [b]


def test_borrar_puntual_que_no_existe(db):
    assert database.borrar_puntual(db, 99) is False


def test_una_base_vieja_gana_la_tabla_al_arrancar(tmp_path):
    # como el prices.db de antes de las alertas: sin la tabla nueva
    import sqlite3

    ruta = str(tmp_path / "vieja.db")
    conn = sqlite3.connect(ruta)
    conn.execute("CREATE TABLE ajustes (clave TEXT PRIMARY KEY, valor TEXT NOT NULL)")
    conn.execute("INSERT INTO ajustes VALUES ('ultimo_resumen', '2026-09-30')")
    conn.commit()
    conn.close()

    database.init_db(ruta)

    assert database.get_puntuales(ruta, "eur") == []
    assert str(database.ultimo_resumen(ruta)) == "2026-09-30"
