"""Tests de los datos del panel web."""

from datetime import datetime, timedelta, timezone

import pytest

from crypto_tracker import panel
from crypto_tracker.config import Posicion
from crypto_tracker.puntuales import Puntual

AHORA = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)


def _cartera():
    return [
        Posicion("solana", 10, 1000.0),
        Posicion("bitcoin", 0.1, 5000.0),
    ]


def test_cartera_de_la_que_mas_vale_a_la_que_menos():
    filas, faltan = panel.filas_cartera(
        _cartera(), {"bitcoin": 60000.0, "solana": 100.0}, {}, {}
    )

    assert [f.coin_id for f in filas] == ["bitcoin", "solana"]
    assert faltan == []
    assert filas[0].valor == 6000.0
    assert filas[0].peso == pytest.approx(6000 / 7000 * 100)


def test_ganancia_de_cada_una():
    filas, _ = panel.filas_cartera(
        _cartera(), {"bitcoin": 60000.0, "solana": 100.0}, {}, {}
    )
    btc, sol = filas

    assert btc.ganancia == 1000.0
    assert btc.porcentaje == pytest.approx(20.0)
    assert sol.ganancia == 0.0


def test_sin_lo_que_costo_no_hay_ganancia():
    filas, _ = panel.filas_cartera([Posicion("bitcoin", 1)], {"bitcoin": 50.0}, {}, {})

    assert filas[0].ganancia is None
    assert filas[0].porcentaje is None


def test_la_que_no_tiene_precio_se_dice_aparte():
    filas, faltan = panel.filas_cartera(_cartera(), {"bitcoin": 60000.0}, {}, {})

    assert [f.coin_id for f in filas] == ["bitcoin"]
    assert faltan == ["solana"]
    assert filas[0].peso == 100.0


def test_cambio_en_24_horas():
    filas, _ = panel.filas_cartera(
        _cartera(), {"bitcoin": 66000.0, "solana": 100.0}, {"bitcoin": 60000.0}, {}
    )

    assert filas[0].cambio_24h == pytest.approx(10.0)
    assert filas[1].cambio_24h is None


def test_totales_del_panel():
    filas, _ = panel.filas_cartera(
        _cartera(), {"bitcoin": 60000.0, "solana": 100.0}, {}, {}
    )
    p = panel.Panel("eur", filas, [], [], [], AHORA, total_antes=6000.0)

    assert p.total == 7000.0
    assert p.invertido == 6000.0
    assert p.ganancia == 1000.0
    assert p.porcentaje == pytest.approx(100 / 6)
    assert p.cambio_24h == pytest.approx(100 / 6)


def test_panel_sin_cartera():
    p = panel.Panel("eur", [], [], [], [], None)

    assert p.total is None
    assert p.ganancia is None
    assert p.cambio_24h is None


def test_total_de_ayer_necesita_todas():
    assert panel.total_antes(_cartera(), {"bitcoin": 50000.0}) is None
    assert panel.total_antes(
        _cartera(), {"bitcoin": 50000.0, "solana": 90.0}
    ) == pytest.approx(5900.0)


def _alerta(id_, coin_id, objetivo, sube=True):
    return Puntual(id_, coin_id, objetivo, sube)


def test_alertas_primero_las_mas_cercanas():
    lista = panel.alertas(
        [
            _alerta(1, "bitcoin", 80000.0),
            _alerta(2, "bitcoin", 58000.0, sube=False),
            _alerta(3, "rara", 1.0),
        ],
        {"bitcoin": 60000.0},
        None,
    )

    assert [a.id for a in lista] == [2, 1, 3]
    assert lista[0].falta == pytest.approx(-3.333, abs=0.01)
    assert lista[2].falta is None


def test_alerta_de_la_cartera_usa_lo_que_vale_todo():
    [a] = panel.alertas([_alerta(1, "cartera", 8000.0)], {}, 7000.0)

    assert a.precio == 7000.0
    assert a.falta == pytest.approx(100 / 7)


@pytest.mark.parametrize(
    "objetivo, sube, precio, alcanzada",
    [
        (70000.0, True, 60000.0, False),
        (70000.0, True, 70000.0, True),
        (50000.0, False, 49000.0, True),
        (50000.0, False, 60000.0, False),
        (50000.0, False, None, False),
    ],
)
def test_alerta_alcanzada(objetivo, sube, precio, alcanzada):
    assert panel.Alerta(1, "bitcoin", objetivo, sube, precio).alcanzada is alcanzada


def test_muestrear_se_queda_con_el_ultimo():
    valores = list(range(1000))

    muestra = panel.muestrear(valores, 10)

    assert len(muestra) == 10
    assert muestra[0] == 0
    assert muestra[-1] == 999


def test_muestrear_corto_lo_deja_igual():
    assert panel.muestrear([1, 2, 3], 10) == [1, 2, 3]


def test_trazo_de_abajo_arriba():
    # En SVG la y crece hacia abajo: el mínimo va abajo del todo.
    assert panel.trazo([1.0, 3.0, 2.0], 100, 50) == "M0.0,50.0 L50.0,0.0 L100.0,25.0"


def test_trazo_plano_a_media_altura():
    assert panel.trazo([5.0, 5.0], 10, 20) == "M0.0,10.0 L10.0,10.0"


def test_trazo_con_un_punto_no_dibuja():
    assert panel.trazo([5.0], 10, 20) == ""


@pytest.mark.parametrize(
    "atras, texto",
    [
        (timedelta(seconds=20), "hace un momento"),
        (timedelta(minutes=7), "hace 7 min"),
        (timedelta(hours=5), "hace 5 h"),
        (timedelta(days=3), "hace 3 días"),
    ],
)
def test_hace(atras, texto):
    assert panel.hace(AHORA - atras, AHORA) == texto


def test_hace_sin_precios():
    assert panel.hace(None, AHORA) == "todavía sin precios"


def test_parado_tras_tres_ciclos():
    assert not panel.parado(AHORA - timedelta(minutes=14), AHORA, 300)
    assert panel.parado(AHORA - timedelta(minutes=16), AHORA, 300)
    assert panel.parado(None, AHORA, 300)


def test_en_bitcoin_sigue_al_precio_de_bitcoin_desde_el_principio():
    t0 = datetime(2026, 11, 20, 12, tzinfo=timezone.utc)
    serie = [
        (t0, 1000.0),
        (t0 + timedelta(hours=1), 1100.0),
        (t0 + timedelta(hours=2), 900.0),
    ]
    # Bitcoin guardado a otras horas: vale el último de antes de cada punto, así
    # que a las 13:00 aún cuenta el de 50.000 y el de 60.000 entra a las 14:00.
    btc = [(t0 - timedelta(minutes=5), 50000.0), (t0 + timedelta(minutes=70), 60000.0)]

    assert panel.en_bitcoin(serie, btc) == [1000.0, 1000.0, 1200.0]


def test_en_bitcoin_sin_precio_al_principio_no_dibuja_nada():
    t0 = datetime(2026, 11, 20, 12, tzinfo=timezone.utc)
    serie = [(t0, 1000.0), (t0 + timedelta(hours=1), 1100.0)]

    assert panel.en_bitcoin(serie, [(t0 + timedelta(minutes=30), 50000.0)]) == []


def test_dias_cartera_semanas_enteras_con_lo_que_tienes_hoy():
    from datetime import date

    hoy = date(2026, 11, 26)  # miércoles
    cierres = [
        (date(2026, 11, 23), "bitcoin", 100.0),
        (date(2026, 11, 23), "ethereum", 10.0),
        (date(2026, 11, 24), "bitcoin", 110.0),
        (date(2026, 11, 24), "ethereum", 10.0),
        # El 25 falta ethereum: ese día no cuenta, saldría hundido.
        (date(2026, 11, 25), "bitcoin", 120.0),
    ]
    posiciones = [Posicion("bitcoin", 1.0), Posicion("ethereum", 2.0)]

    dias = panel.dias_cartera(posiciones, cierres, hoy)

    assert [d.dia for d in dias][0] == date(2026, 11, 23)  # el lunes
    assert len(dias) == 7  # hasta el domingo
    assert dias[0].valor == 120.0 and dias[0].cambio is None
    assert dias[1].valor == 130.0
    assert round(dias[1].cambio, 2) == 8.33
    assert dias[2].valor is None


def test_dias_cartera_como_mucho_un_año():
    from datetime import date

    hoy = date(2026, 11, 26)
    cierres = [(hoy - timedelta(days=d), "bitcoin", 100.0) for d in range(800)]

    dias = panel.dias_cartera([Posicion("bitcoin", 1.0)], cierres, hoy)

    assert len(dias) == 53 * 7


def test_sin_clave_puesta_el_panel_local_no_la_pide():
    assert panel.acceso("/", "")


def test_con_clave_hay_que_traerla_bien():
    clave = "una-clave-larga-de-verdad"

    assert panel.acceso(f"/?clave={clave}", clave)
    assert panel.acceso(f"/api.json?clave={clave}", clave)
    assert not panel.acceso("/", clave)
    assert not panel.acceso("/?clave=otra", clave)


def test_a_json_lleva_lo_del_widget():
    filas, _ = panel.filas_cartera(
        [Posicion("bitcoin", 0.1, 5000.0)], {"bitcoin": 60000.0}, {}, {}
    )
    ahora = datetime(2026, 11, 20, 12, tzinfo=timezone.utc)
    p = panel.Panel("eur", filas, [], [], [], ahora, total_antes=5000.0)

    datos = panel.a_json(p, False)

    assert datos["total"] == 6000.0
    assert round(datos["cambio_24h"], 6) == 20.0
    assert datos["ganancia"] == 1000.0
    assert datos["actualizado"] == "2026-11-20T12:00:00+00:00"
    assert datos["parado"] is False
    assert datos["criptos"][0]["id"] == "bitcoin"
    assert datos["criptos"][0]["peso"] == 100.0


def firmado(token, auth_date, usuario=123, **extra):
    """Un initData como el que manda Telegram, firmado con ese token."""
    import hashlib
    import hmac
    import json
    from urllib.parse import urlencode

    campos = {"auth_date": str(auth_date), "user": json.dumps({"id": usuario})}
    campos.update(extra)
    texto = "\n".join(f"{k}={v}" for k, v in sorted(campos.items()))
    clave = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    campos["hash"] = hmac.new(clave, texto.encode(), hashlib.sha256).hexdigest()
    return urlencode(campos)


def test_usuario_telegram_con_la_firma_buena():
    datos = firmado("token", 1000, usuario=42, query_id="AAH")

    assert panel.usuario_telegram(datos, "token", 1000 + 60) == 42


def test_usuario_telegram_con_otro_token_o_tocado():
    datos = firmado("otro", 1000)
    tocado = firmado("token", 1000, usuario=42).replace("42", "43")

    assert panel.usuario_telegram(datos, "token", 1000) is None
    assert panel.usuario_telegram(tocado, "token", 1000) is None
    assert panel.usuario_telegram("", "token", 1000) is None
    assert panel.usuario_telegram("hash=%C3%B1", "token", 1000) is None


def test_usuario_telegram_caducado():
    datos = firmado("token", 1000)

    assert panel.usuario_telegram(datos, "token", 1000 + panel.VIDA_FIRMA + 1) is None


def test_sesion_vale_hasta_que_caduca():
    secreto = b"s" * 32
    pase = panel.sesion(secreto, 1000)
    ruta = f"/app/panel?sesion={pase}"

    assert panel.sesion_valida(ruta, secreto, 1000 + 60)
    assert not panel.sesion_valida(ruta, secreto, 1000 + panel.VIDA_SESION)
    assert not panel.sesion_valida(ruta, b"o" * 32, 1000)
    assert not panel.sesion_valida("/app/panel", secreto, 1000)
    # Alargar la caducidad a mano rompe la firma.
    caduca, _, firma = pase.partition(".")
    otra = f"/app/panel?sesion={int(caduca) + 9999}.{firma}"
    assert not panel.sesion_valida(otra, secreto, 1000)


def test_url_app_sin_barra_final(monkeypatch):
    monkeypatch.setenv("PANEL_URL", " https://mi-panel.example/ ")

    assert panel.url_app() == "https://mi-panel.example"


def test_enlace_firmado_con_el_token_y_de_24_h():
    url = panel.enlace("https://mi-panel.example", "token", 1000)
    ruta = url.removeprefix("https://mi-panel.example")
    secreto = panel.secreto_enlaces("token")

    assert ruta.startswith("/ver?pase=")
    assert panel.sesion_valida(ruta, secreto, 1000 + 60, "pase")
    assert panel.caducidad(ruta, "pase") == 1000 + panel.VIDA_ENLACE
    assert not panel.sesion_valida(ruta, secreto, 1000 + panel.VIDA_ENLACE, "pase")
    # Con otro bot, o sea otro token, no vale.
    assert not panel.sesion_valida(ruta, panel.secreto_enlaces("otro"), 1000, "pase")
