"""Tests de /dificultad."""

from datetime import datetime, timedelta, timezone

import pytest

from crypto_tracker import dificultad
from crypto_tracker.dificultad import DificultadError, falta, leer

AHORA = datetime(2026, 11, 24, 12, 0, tzinfo=timezone.utc)


def _ajuste(**cambios):
    datos = {
        "progressPercent": 81.99,
        "difficultyChange": 9.05,
        "estimatedRetargetDate": int((AHORA + timedelta(hours=55)).timestamp() * 1000),
        "remainingBlocks": 363,
        "remainingTime": 199847472,
        "previousRetarget": -9.13,
        "nextRetargetHeight": 977760,
        "timeAvg": 550544,
    }
    return {**datos, **cambios}


def _potencia(valores):
    return {
        "hashrates": [
            {"timestamp": 1_790_000_000 + i * 86400, "avgHashrate": v * 1e18}
            for i, v in enumerate(valores)
        ]
    }


def test_leer():
    d = leer(_ajuste(), _potencia([900, 1000]))

    assert d.progreso == 81.99
    assert d.cambio == 9.05
    assert d.anterior == -9.13
    assert d.faltan == 363
    assert d.cuando == AHORA + timedelta(hours=55)
    assert d.cada == pytest.approx(9.1757, abs=0.001)
    assert d.potencia == [900, 1000]


def test_leer_sin_hashrate_sigue():
    d = leer(_ajuste(), {})

    assert d.potencia == []
    assert d.potencia_mes is None
    assert not d.capitulacion


def test_leer_sin_lo_basico_no_hay():
    assert leer(_ajuste(difficultyChange=None), {}) is None
    assert leer(_ajuste(timeAvg=0), {}) is None
    assert leer(_ajuste(remainingBlocks=True), {}) is None
    assert leer("roto", {}) is None


def test_leer_ordena_y_salta_lo_roto():
    p = _potencia([1000, 900])
    p["hashrates"].reverse()
    p["hashrates"] += [None, {"timestamp": 1}, {"timestamp": 2, "avgHashrate": 0}]

    assert leer(_ajuste(), p).potencia == [1000, 900]


def test_el_progreso_no_se_sale():
    assert leer(_ajuste(progressPercent=104), {}).progreso == 100


def test_potencia_mes_y_capitulacion():
    sube = leer(_ajuste(), _potencia([1000] * 31 + [1100]))
    cae = leer(_ajuste(), _potencia([1000] * 31 + [880]))

    assert sube.potencia_mes == pytest.approx(10)
    assert not sube.capitulacion
    assert cae.potencia_mes == pytest.approx(-12)
    assert cae.capitulacion


@pytest.mark.parametrize(
    "horas, sale",
    [
        (0.5, "menos de una hora"),
        (5, "5 h"),
        (24, "1 día"),
        (31, "1 día y 7 h"),
        (55, "2 días y 7 h"),
    ],
)
def test_falta(horas, sale):
    assert falta(AHORA + timedelta(hours=horas), AHORA) == sale


def test_pedir_sin_hashrate_sigue(monkeypatch):
    def get(url):
        if url == dificultad.POTENCIA_URL:
            raise DificultadError("mempool.space no contesta")
        return _ajuste()

    monkeypatch.setattr(dificultad, "_get", get)

    assert dificultad.pedir() == (_ajuste(), {})
