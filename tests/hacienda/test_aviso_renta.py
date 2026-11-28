"""Tests del aviso de la Renta."""

from datetime import date, datetime, time

import pytest

from crypto_tracker.hacienda.aviso_renta import hay_que_declarar, toca_aviso
from crypto_tracker.hacienda.impuestos import Impuestos

NUEVE = time(9, 0)


def _el(mes, dia, hora=9, minuto=30):
    return datetime(date.today().year, mes, dia, hora, minuto).astimezone()


@pytest.mark.parametrize(
    "cuando, sale",
    [
        (_el(4, 1), True),
        (_el(4, 15), True),
        (_el(4, 16), False),
        (_el(3, 31), False),
        (_el(5, 1), False),
        (_el(4, 1, 8), False),  # antes de la hora del resumen
    ],
)
def test_toca_aviso(cuando, sale):
    assert toca_aviso(cuando, NUEVE, None) is sale


def test_toca_aviso_una_vez_al_año():
    año = date.today().year

    assert not toca_aviso(_el(4, 5), NUEVE, date(año, 4, 2))
    assert toca_aviso(_el(4, 5), NUEVE, date(año - 1, 4, 2))


def _imp(ganancia, ventas):
    return Impuestos(2025, ganancia, [], 0, ventas)


@pytest.mark.parametrize(
    "i, recibido, sale",
    [
        (_imp(1000, 2), 0, True),
        (_imp(-500, 1), 0, True),  # con pérdidas también
        (_imp(0, 0), 30, True),  # solo staking
        (_imp(0, 0), 0, False),
    ],
)
def test_hay_que_declarar(i, recibido, sale):
    assert hay_que_declarar(i, recibido) is sale


# --- el aviso, de punta a punta ---

from dataclasses import replace  # noqa: E402
from datetime import timedelta, timezone  # noqa: E402

import main  # noqa: E402
from crypto_tracker import database, telegram  # noqa: E402
from crypto_tracker.config import Config, Posicion, Watch  # noqa: E402

AÑO = date.today().year
EL_AÑO_PASADO = datetime(AÑO - 1, 6, 1, 12, tzinfo=timezone.utc)


@pytest.fixture
def config(tmp_path):
    ruta = str(tmp_path / "test.db")
    database.init_db(ruta)
    return Config(
        telegram_token="token",
        telegram_chat_id="123",
        watchlist=[Watch("bitcoin", percent=5)],
        vs_currency="eur",
        check_interval=300,
        database_path=ruta,
        history_days=0,
        resumen_diario=NUEVE,
    )


@pytest.fixture
def mandados(monkeypatch):
    lista = []
    monkeypatch.setattr(
        telegram,
        "send_message",
        lambda token, chat, texto, **kw: (
            lista.append((texto, kw.get("botones"))) or True
        ),
    )
    return lista


def _vendido(config, coste_venta, cuando=EL_AÑO_PASADO):
    ruta = config.database_path
    una = Posicion("bitcoin", 1, 1000)
    database.apuntar_movimiento(
        ruta, "bitcoin", "compra", 1, 1000, None, una, cuando=cuando
    )
    database.apuntar_movimiento(
        ruta, "bitcoin", "venta", 1, coste_venta, una, None, cuando=cuando
    )


def test_aviso_en_abril_con_ganancias(config, mandados):
    _vendido(config, 3000)  # +2.000

    main.aviso_de_la_renta(config, _el(4, 2))
    main.aviso_de_la_renta(config, _el(4, 3))

    [(texto, botones)] = mandados
    assert texto.startswith(f"🧾 <b>Ya puedes hacer la Renta de {AÑO - 1}</b>")
    assert "Has ganado vendiendo <b>+€2.000,00</b>" in texto
    assert "El plazo suele acabar el 30 de junio" in texto
    assert botones == [
        [
            ("📄 Informe en PDF", f"/informe {AÑO - 1}"),
            ("📊 Ventas en CSV", f"/impuestos {AÑO - 1} csv"),
        ]
    ]


def test_aviso_en_abril_con_perdidas(config, mandados):
    _vendido(config, 400)

    main.aviso_de_la_renta(config, _el(4, 2))

    assert "la puedes restar de lo que ganes los próximos 4 años" in mandados[0][0]


def test_aviso_en_abril_solo_con_staking(config, mandados):
    database.apuntar_movimiento(
        config.database_path,
        "ethereum",
        "recompensa",
        0.01,
        30,
        None,
        Posicion("ethereum", 0.01, 30),
        cuando=EL_AÑO_PASADO,
    )

    main.aviso_de_la_renta(config, _el(4, 2))

    [(texto, botones)] = mandados
    assert "Recibiste €30,00 en recompensas" in texto
    # Sin ventas no hay informe que sacar.
    assert botones is None


def test_aviso_en_abril_sin_nada_no_manda_y_no_insiste(config, mandados):
    _vendido(config, 3000, cuando=datetime(AÑO, 1, 10, tzinfo=timezone.utc))

    main.aviso_de_la_renta(config, _el(4, 2))

    assert mandados == []
    assert database.ultimo_resumen(config.database_path, "aviso_renta") == date(
        AÑO, 4, 2
    )


def test_aviso_fuera_de_abril(config, mandados):
    _vendido(config, 3000)

    main.aviso_de_la_renta(config, _el(3, 31))
    main.aviso_de_la_renta(config, _el(4, 16))

    assert mandados == []


def test_aviso_sin_resumen_diario(config, mandados):
    _vendido(config, 3000)

    main.aviso_de_la_renta(replace(config, resumen_diario=None), _el(4, 2))

    assert mandados == []


def test_aviso_callado_espera(config, mandados):
    _vendido(config, 3000)
    database.silenciar_hasta(
        config.database_path, datetime.now(timezone.utc) + timedelta(days=1)
    )

    main.aviso_de_la_renta(config, _el(4, 2))

    assert mandados == []


def test_aviso_si_falla_telegram_lo_reintenta(config, monkeypatch):
    _vendido(config, 3000)
    intentos = []

    def send_message(token, chat_id, texto, **k):
        intentos.append(texto)
        return len(intentos) > 1

    monkeypatch.setattr(telegram, "send_message", send_message)

    main.aviso_de_la_renta(config, _el(4, 2))
    main.aviso_de_la_renta(config, _el(4, 3))
    main.aviso_de_la_renta(config, _el(4, 4))

    assert len(intentos) == 2
