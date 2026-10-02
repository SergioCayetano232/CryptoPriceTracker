"""Tests de los botones de debajo de los avisos."""

from crypto_tracker import comandos, puntuales
from crypto_tracker.alerts import ALTO, BAJO, Alert
from crypto_tracker.botones import CALLAR, para_avisos


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
