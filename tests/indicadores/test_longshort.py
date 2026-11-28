"""Tests de /longshort."""

import pytest

from crypto_tracker.indicadores import longshort
from crypto_tracker.indicadores.funding import FundingError
from crypto_tracker.indicadores.longshort import LongShort, Reparto, lectura, leer

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


def test_extremo():
    assert longshort.extremo(_ls([70] * 9 + [80])) == longshort.ALCISTA
    assert longshort.extremo(_ls([70] * 9 + [60])) == longshort.BAJISTA
    assert longshort.extremo(_ls([70] * 10)) == ""
    assert longshort.extremo(_ls([60, 80])) == ""


def test_avisa_al_entrar_en_un_lado_y_no_mientras_sigue():
    alcista = _ls([70] * 9 + [80])
    nada = _ls([70] * 10)
    v = longshort.Vigilado("BTCUSDT", "bitcoin")

    assert longshort.toca(v, alcista) == (True, longshort.ALCISTA)
    ya = longshort.Vigilado("BTCUSDT", "bitcoin", longshort.ALCISTA)
    assert longshort.toca(ya, alcista) == (False, longshort.ALCISTA)
    # Al calmarse se olvida, para avisar si vuelve.
    assert longshort.toca(ya, nada) == (False, "")
    assert longshort.toca(ya, _ls([70] * 9 + [60])) == (True, longshort.BAJISTA)


def test_toca_mirar_cada_cuatro_horas():
    from datetime import datetime, timedelta, timezone

    ahora = datetime(2026, 11, 24, 12, tzinfo=timezone.utc)
    v = longshort.Vigilado("BTCUSDT", "bitcoin")

    assert longshort.toca_mirar(v, ahora)
    hace = lambda h: longshort.Vigilado("BTCUSDT", "bitcoin", mirado=ahora - h)  # noqa: E731
    assert not longshort.toca_mirar(hace(timedelta(hours=3)), ahora)
    assert longshort.toca_mirar(hace(timedelta(hours=4)), ahora)


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
from crypto_tracker.nucleo import database, telegram  # noqa: E402
from crypto_tracker.nucleo.config import Config, Watch  # noqa: E402


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


# --- el aviso ---

from datetime import datetime, timedelta, timezone  # noqa: E402

from crypto_tracker.respuestas import revisiones  # noqa: E402


def _dentro_de(horas):
    return datetime.now(timezone.utc) + timedelta(hours=horas)


def _cambiante(monkeypatch, hoy=70):
    """Binance con un mes a 70 y el último día a lo que diga estado["hoy"]."""
    estado = {"hoy": hoy, "pedidas": 0}

    def pedir(par):
        estado["pedidas"] += 1
        if isinstance(estado["hoy"], Exception):
            raise estado["hoy"]
        todos = [_dato(d, 70) for d in range(9)] + [_dato(9, estado["hoy"])]
        return todos, []

    monkeypatch.setattr(longshort, "pedir", pedir)
    return estado


def _avisos(enviados):
    return [t for t in enviados if "No repito" in t]


def test_poner_el_aviso(config, enviados, monkeypatch):
    _cambiante(monkeypatch)

    main.atender(config, _mensaje("/longshort btc avisa"))

    assert "🔔 Hecho: te aviso cuando en <b>bitcoin</b>" in enviados[0]
    assert "Ahora: lo de siempre, ni más ni menos que otros días." in enviados[0]
    [v] = database.get_longshort(config.database_path)
    assert (v.par, v.coin_id, v.extremo) == ("BTCUSDT", "bitcoin", "")


def test_avisa_una_vez_al_entrar_y_otra_si_vuelve(config, enviados, monkeypatch):
    estado = _cambiante(monkeypatch)
    main.atender(config, _mensaje("/longshort btc avisa"))
    enviados.clear()

    for horas, hoy in ((4, 80), (8, 81), (12, 70), (16, 60)):
        estado["hoy"] = hoy
        revisiones.revisar_longshort(config, set(), None, _dentro_de(horas))

    avisos = _avisos(enviados)
    assert len(avisos) == 2
    assert "🐂 <b>BTC: más gente que de costumbre apuesta a que sube</b>" in avisos[0]
    assert "🔺 80% apuesta a que sube, cuando lo normal del mes es un 71%" in avisos[0]
    assert "🐻" in avisos[1]


def test_no_pregunta_antes_de_cuatro_horas(config, enviados, monkeypatch):
    estado = _cambiante(monkeypatch)
    main.atender(config, _mensaje("/longshort btc avisa"))
    antes = estado["pedidas"]

    revisiones.revisar_longshort(config, set(), None, _dentro_de(3))

    assert estado["pedidas"] == antes


def test_si_ya_estaba_en_un_lado_no_avisa_de_eso(config, enviados, monkeypatch):
    _cambiante(monkeypatch, hoy=80)
    main.atender(config, _mensaje("/longshort btc avisa"))
    enviados.clear()

    revisiones.revisar_longshort(config, set(), None, _dentro_de(4))

    assert enviados == []


def test_si_binance_falla_sigue_puesto(config, enviados, monkeypatch):
    estado = _cambiante(monkeypatch)
    main.atender(config, _mensaje("/longshort btc avisa"))
    enviados.clear()
    estado["hoy"] = FundingError("Binance no contesta")

    revisiones.revisar_longshort(config, set(), None, _dentro_de(4))

    assert enviados == []
    assert len(database.get_longshort(config.database_path)) == 1


def test_callada_no_avisa(config, enviados, monkeypatch):
    estado = _cambiante(monkeypatch)
    main.atender(config, _mensaje("/longshort btc avisa"))
    enviados.clear()
    estado["hoy"] = 80

    revisiones.revisar_longshort(config, {"bitcoin"}, None, _dentro_de(4))
    assert enviados == []

    revisiones.revisar_longshort(config, set(), None, _dentro_de(4))
    assert len(_avisos(enviados)) == 1


def test_quitar_el_aviso(config, enviados, monkeypatch):
    _cambiante(monkeypatch)
    main.atender(config, _mensaje("/longshort btc avisa"))

    main.atender(config, _mensaje("/longshort btc no"))
    main.atender(config, _mensaje("/longshort btc no"))

    assert "ya no te aviso de los largos de bitcoin" in enviados[1]
    assert "No tenías ese aviso" in enviados[2]
    assert database.get_longshort(config.database_path) == []


def test_sin_aviso_no_lo_menciona_y_con_aviso_si(config, enviados, monkeypatch):
    _cambiante(monkeypatch)

    main.atender(config, _mensaje("/longshort btc"))
    main.atender(config, _mensaje("/longshort btc avisa"))
    main.atender(config, _mensaje("/longshort btc"))

    assert "🔔" not in enviados[0]
    assert "🔔 Te aviso si se va más gente de lo normal" in enviados[2]
    assert "/longshort btc no" in enviados[2]


def test_el_ciclo_lo_revisa(config, enviados, monkeypatch):
    llamadas = []
    monkeypatch.setattr(
        main, "revisar_longshort", lambda c, calladas, sueltos: llamadas.append(c)
    )
    # Sin precios el ciclo se para antes de llegar a las revisiones.
    monkeypatch.setattr(
        main.coingecko, "get_prices", lambda ids, cur: {"solana": 150.0}
    )

    main.ejecutar_ciclo(config, {})

    assert llamadas == [config]
