"""Tests de los botones de debajo de los avisos."""

from crypto_tracker import comandos, puntuales
from crypto_tracker.alerts import ALTO, BAJO, Alert
from crypto_tracker.botones import (
    CALLAR,
    MAX_ALERTAS,
    deshacer_mute,
    para_alertas,
    para_avisos,
    para_mute,
    para_tendencias,
)
from crypto_tracker.tendencias import Tendencia


def test_un_aviso():
    filas = para_avisos([Alert("bitcoin", 64100.0, 64000.0, ALTO)], "eur")

    assert filas == [
        [
            ("📈 Gráfica", "/historico bitcoin"),
            ("🎯 Si vuelve a €64.000,00", "/alerta bitcoin 64000,0"),
        ],
        [CALLAR],
    ]


def test_el_precio_del_boton_se_lee_bien():
    # 1.234 con punto lo leeria como mil y pico
    filas = para_avisos([Alert("cardano", 1.3, 1.234, ALTO)], "usd")
    nombre, argumento = comandos.interpretar(filas[0][1][1])

    assert nombre == "alerta"
    assert puntuales.interpretar(argumento) == ("cardano", 1.234)


def test_precio_diminuto():
    filas = para_avisos([Alert("pepe", 0.000012, 0.00001, BAJO)], "usd")
    _, argumento = comandos.interpretar(filas[0][1][1])

    assert puntuales.interpretar(argumento) == ("pepe", 0.00001)


def test_varios_avisos_dicen_de_cual():
    filas = para_avisos(
        [
            Alert("bitcoin", 64100.0, 64000.0, ALTO),
            Alert("ethereum", 2900.0, 3000.0, BAJO),
        ],
        "eur",
    )

    assert filas[0][0] == ("📈 Bitcoin", "/historico bitcoin")
    assert filas[1][0] == ("📈 Ethereum", "/historico ethereum")
    assert filas[-1] == [CALLAR]


def test_la_misma_cripto_dos_veces_una_fila():
    filas = para_avisos(
        [
            Alert("bitcoin", 55000.0, 56000.0, BAJO),
            Alert("bitcoin", 55000.0, 60000.0, BAJO, percent=-8.3, minutos=60),
        ],
        "eur",
    )

    assert len(filas) == 2
    # manda el primero
    assert filas[0][1][1] == "/alerta bitcoin 56000,0"


def test_como_mucho_tres_criptos():
    avisos = [Alert(f"cripto-{i}", 2.0, 1.0, ALTO) for i in range(5)]

    filas = para_avisos(avisos, "eur")

    assert len(filas) == 4
    assert filas[-1] == [CALLAR]


def test_un_id_larguisimo_se_queda_sin_los_botones_que_no_caben():
    coin_id = "x" * 60
    filas = para_avisos([Alert(coin_id, 2.0, 1.0, ALTO)], "eur")

    # Telegram rechazaria el mensaje entero, mejor sin esos botones
    assert filas == [[CALLAR]]


def test_aviso_de_la_cartera_lleva_a_cartera():
    filas = para_avisos([Alert("cartera", 5100.0, 5000.0, ALTO, puntual=True)], "eur")

    assert filas[0] == [
        ("📈 Gráfica", "/cartera"),
        ("🎯 Si vuelve a €5.000,00", "/alerta cartera 5000,0"),
    ]


# --- /alertas ---


def test_una_alerta():
    filas = para_alertas([puntuales.Puntual(3, "bitcoin", 70000.0, True)])

    assert filas == [
        [("🗑 3 Bitcoin", "/quitar 3")],
        [("🔄 Actualizar", "/alertas")],  # sin "todas" para una sola
    ]


def test_varias_alertas_de_dos_en_dos():
    alertas = [
        puntuales.Puntual(1, "bitcoin", 70000.0, True),
        puntuales.Puntual(2, "shiba-inu", 0.00002, False),
        puntuales.Puntual(5, "cartera", 6000.0, True),
    ]

    filas = para_alertas(alertas)

    assert filas == [
        [("🗑 1 Bitcoin", "/quitar 1"), ("🗑 2 Shiba Inu", "/quitar 2")],
        [("🗑 5 Cartera", "/quitar 5")],
        [("🔄 Actualizar", "/alertas"), ("🗑 Quitar todas", "/quitar todas")],
    ]


def test_muchas_alertas_no_llenan_el_mensaje():
    alertas = [puntuales.Puntual(i, "bitcoin", 1000.0 * i, True) for i in range(1, 30)]

    filas = para_alertas(alertas)
    sueltos = [b for fila in filas[:-1] for b in fila]

    assert len(sueltos) == MAX_ALERTAS
    assert filas[-1] == [
        ("🔄 Actualizar", "/alertas"),
        ("🗑 Quitar todas", "/quitar todas"),
    ]


def test_cada_boton_de_alerta_es_un_comando_que_se_entiende():
    alertas = [puntuales.Puntual(i, "bitcoin", 1000.0, True) for i in (1, 2)]

    for fila in para_alertas(alertas):
        for _, datos in fila:
            assert comandos.interpretar(datos)[0] in ("quitar", "alertas")


def test_tendencias_de_dos_en_dos():
    lista = [
        Tendencia(f"moneda-{i}", f"Moneda {i}", f"M{i}", None, None) for i in range(3)
    ]

    assert para_tendencias(lista) == [
        [("🎯 M0", "/alerta moneda-0"), ("🎯 M1", "/alerta moneda-1")],
        [("🎯 M2", "/alerta moneda-2")],
    ]


def test_tendencias_con_id_larguisimo():
    larga = Tendencia("x" * 60, "Larga", "L", None, None)
    corta = Tendencia("pepe", "Pepe", "", None, None)

    # Telegram no admite mas de 64 bytes; sin simbolo va el nombre.
    assert para_tendencias([larga, corta]) == [[("🎯 Pepe", "/alerta pepe")]]


def test_mute_a_elegir():
    assert para_mute() == [
        [("1 h", "/mute 1h"), ("4 h", "/mute 4h")],
        [("🌙 Hasta las 8:00", "/mute hasta 8:00")],
    ]


def test_mute_ya_callado_primero_volver():
    filas = para_mute(ya_callado=True)

    assert filas[0] == [("🔔 Volver a avisar", "/unmute")]
    assert filas[1:] == para_mute()


def test_deshacer_mute():
    assert deshacer_mute() == [[("🔔 Volver a avisar", "/unmute")]]


def test_los_comandos_del_mute_caben():
    for fila in para_mute(ya_callado=True):
        for _, comando in fila:
            assert len(comando.encode()) <= 64


def test_una_alerta_que_salta_ofrece_otra_mas_alla():
    filas = para_avisos([Alert("bitcoin", 71000.0, 70000.0, ALTO, puntual=True)], "eur")

    assert filas[1] == [("🔁 Otra a +5%", "/alerta bitcoin +5%")]
    assert filas[-1] == [CALLAR]


def test_si_salta_bajando_la_otra_es_mas_abajo():
    filas = para_avisos(
        [
            Alert("bitcoin", 59000.0, 60000.0, BAJO, puntual=True),
            Alert("ethereum", 3100.0, 3000.0, ALTO),
        ],
        "eur",
    )

    assert filas[1] == [("🔁 Bitcoin -5%", "/alerta bitcoin -5%")]
    # La de ethereum no era de /alerta: sin boton de otra
    assert all("🔁" not in b[0] for fila in filas[2:] for b in fila)


def test_el_boton_de_otra_se_entiende_como_alerta_relativa():
    filas = para_avisos([Alert("cartera", 5100.0, 5000.0, ALTO, puntual=True)], "eur")
    nombre, argumento = comandos.interpretar(filas[1][0][1])

    assert nombre == "alerta"
    assert puntuales.interpretar_relativa(argumento) == ("cartera", 5.0)
