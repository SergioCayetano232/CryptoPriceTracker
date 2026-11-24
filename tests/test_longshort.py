"""Tests de /longshort."""

import pytest

from crypto_tracker import longshort
from crypto_tracker.funding import FundingError
from crypto_tracker.longshort import LongShort, Reparto, lectura, leer

DIA = 86_400_000


def _dato(dia, largos):
    return {
        "symbol": "BTCUSDT",
        "longAccount": f"{largos / 100:.4f}",
        "shortAccount": f"{1 - largos / 100:.4f}",
        "longShortRatio": "2",
        "timestamp": 1_795_000_000_000 + dia * DIA,
    }


def _ls(largos, grandes=None):
    todos = [_dato(i, v) for i, v in enumerate(largos)]
    return leer("BTCUSDT", todos, [] if grandes is None else [_dato(99, grandes)])


def test_leer_ordena_y_pasa_a_porcentaje():
    ls = leer("BTCUSDT", [_dato(2, 73.46), _dato(1, 67.75)], [_dato(2, 61.05)])

    assert [round(r.largos, 2) for r in ls.todos] == [67.75, 73.46]
    assert ls.hoy.cortos == pytest.approx(26.54)
    assert ls.grandes.largos == pytest.approx(61.05)


def test_leer_sin_grandes_sigue():
    assert _ls([70, 72]).grandes is None
    assert _ls([70, 72]).separacion is None


def test_leer_ignora_basura():
    todos = [None, {"timestamp": "x"}, _dato(0, 70) | {"longAccount": "?"}]
    todos.append(_dato(1, 150))

    assert leer("BTCUSDT", todos, []) is None
    assert leer("BTCUSDT", {"code": -1}, []) is None


def test_media_y_frente_al_mes():
    ls = _ls([70] * 9 + [80])

    assert ls.media == pytest.approx(71)
    assert ls.frente_al_mes == pytest.approx(9)


@pytest.mark.parametrize(
    "largos, grandes, emoji",
    [
        ([70] * 9 + [80], None, "🐂"),
        ([70] * 9 + [60], None, "🐻"),
        ([70] * 10, 55, "🐟"),
        ([60] * 10, 75, "🐋"),
        ([70] * 10, 66, "😐"),
        # Con pocos días no hay "de costumbre" con que comparar.
        ([60, 80], None, "😐"),
    ],
)
def test_lectura(largos, grandes, emoji):
    assert lectura(_ls(largos, grandes))[0] == emoji


def test_lo_raro_del_mes_va_antes_que_la_separacion():
    assert lectura(_ls([70] * 9 + [80], 60))[0] == "🐂"


def test_pedir_sin_futuros(monkeypatch):
    monkeypatch.setattr(longshort, "_get", lambda url, params: [])

    with pytest.raises(FundingError, match="sin futuros"):
        longshort.pedir("NADAUSDT")


def test_pedir_si_fallan_los_grandes_sigue_con_todos(monkeypatch):
    def get(url, params):
        if url == longshort.GRANDES_URL:
            raise FundingError("Binance no contesta")
        assert params == {"symbol": "BTCUSDT", "period": "1d", "limit": 30}
        return [_dato(0, 70)]

    monkeypatch.setattr(longshort, "_get", get)

    assert longshort.pedir("BTCUSDT") == ([_dato(0, 70)], [])


def test_reparto_cortos():
    assert Reparto(None, 72.5).cortos == 27.5
    assert LongShort("X", [Reparto(None, 50)], None).hoy.largos == 50


# --- el comando ---

import time  # noqa: E402

import main  # noqa: E402
from crypto_tracker import database, telegram  # noqa: E402
from crypto_tracker.config import Config, Watch  # noqa: E402


@pytest.fixture
def config(tmp_path):
    ruta = str(tmp_path / "test.db")
    database.init_db(ruta)
    return Config("token", "123", [Watch("solana", percent=5)], "eur", 300, ruta, 0)


@pytest.fixture
def enviados(monkeypatch):
    lista = []
    monkeypatch.setattr(
        telegram, "send_message", lambda t, c, texto, **kw: lista.append(texto) or True
    )
    return lista


def _mensaje(texto):
    return {"chat": {"id": 123}, "text": texto, "date": int(time.time())}


def _binance(monkeypatch, todos, grandes=()):
    pedidos = []

    def get(url, params):
        pedidos.append((url, params))
        if isinstance(todos, Exception):
            raise todos
        return list(grandes) if url == longshort.GRANDES_URL else todos

    monkeypatch.setattr(longshort, "_get", get)
    return pedidos


def test_longshort(config, enviados, monkeypatch):
    todos = [_dato(d, 70) for d in range(9)] + [_dato(9, 80)]
    pedidos = _binance(monkeypatch, todos, [_dato(9, 61)])

    main.atender(config, _mensaje("/longshort btc"))

    assert pedidos[0][1]["symbol"] == "BTCUSDT"
    texto = enviados[0]
    assert texto.startswith("⚖️ <b>Largos y cortos de Bitcoin</b> · BTCUSDT")
    assert "🔺 80% apuesta a que sube · 🔻 20% a que baja" in texto
    assert "<code>▓▓▓▓▓▓▓▓░░</code> 80%" in texto
    assert "Media de 10 días: 71% a que sube" in texto
    assert "Los que más mueven: 61% a que sube" in texto
    assert "🐂 <b>Más gente que de costumbre apuesta a que sube" in texto
    assert "/oi btc</i>" in texto


def test_longshort_a_secas_usa_la_primera_que_vigilas(config, enviados, monkeypatch):
    pedidos = _binance(monkeypatch, [_dato(0, 70)])

    main.atender(config, _mensaje("/largos"))

    assert pedidos[0][1]["symbol"] == "SOLUSDT"
    texto = enviados[0]
    assert "🔺 70% apuesta a que sube" in texto
    # Con un día no hay media ni barrita, ni nada de los grandes.
    assert "Media" not in texto
    assert "Los que más mueven" not in texto


def test_longshort_la_barra_dice_lo_mismo_que_el_numero(config, enviados, monkeypatch):
    _binance(monkeypatch, [_dato(0, 70.8)])

    main.atender(config, _mensaje("/longshort btc"))

    assert "🔺 71% apuesta" in enviados[0]
    assert "</code> 71%" in enviados[0]


def test_longshort_sin_futuros(config, enviados, monkeypatch):
    _binance(monkeypatch, FundingError("sin futuros"))

    main.atender(config, _mensaje("/longshort noexiste"))

    assert "<b>noexiste</b> no tiene futuros en Binance" in enviados[0]


def test_longshort_binance_caido(config, enviados, monkeypatch):
    _binance(monkeypatch, FundingError("Binance no contesta: timeout"))

    main.atender(config, _mensaje("/longshort btc"))

    assert "No he podido mirarlo ahora mismo: Binance no contesta" in enviados[0]


def test_longshort_sin_datos_que_sirvan(config, enviados, monkeypatch):
    _binance(monkeypatch, [{"timestamp": "roto"}])

    main.atender(config, _mensaje("/longshort btc"))

    assert "no me ha dado cuántos apuestan" in enviados[0]


def test_longshort_de_dos_en_dos(config, enviados):
    main.atender(config, _mensaje("/longshort btc eth"))

    assert "De una en una" in enviados[0]
