"""Tests de la copia de seguridad: que se mande cuando toca y que sirva."""

import io
import zipfile
from datetime import date, timedelta

import pytest

import main
from crypto_tracker import ajustes, backup, comandos, database, telegram
from crypto_tracker.config import Config, ConfigError, Watch, parse_copia_semanal

HOY = date(2026, 11, 9)


@pytest.fixture
def config(tmp_path):
    ruta = str(tmp_path / "prices.db")
    database.init_db(ruta)
    return Config(
        telegram_token="token",
        telegram_chat_id="123",
        watchlist=[Watch("bitcoin", percent=5)],
        vs_currency="eur",
        check_interval=300,
        database_path=ruta,
        history_days=0,
        copia_semanal=True,
    )


@pytest.fixture
def mandados(monkeypatch):
    lista = []

    def send_document(token, chat, contenido, nombre, pie="", **kw):
        lista.append((contenido, nombre, pie, kw))
        return True

    monkeypatch.setattr(telegram, "send_document", send_document)
    return lista


@pytest.fixture
def mensajes(monkeypatch):
    lista = []
    monkeypatch.setattr(
        telegram,
        "send_message",
        lambda token, chat, texto, **kw: lista.append(texto) or True,
    )
    return lista


def _ultima(config):
    return database.ultimo_resumen(config.database_path, database.ULTIMA_COPIA)


def _restaurar(contenido, carpeta):
    with zipfile.ZipFile(io.BytesIO(contenido)) as archivo:
        assert archivo.namelist() == ["prices.db"]
        archivo.extractall(carpeta)
    return str(carpeta / "prices.db")


def test_la_primera_vez_toca():
    assert backup.toca(None, HOY)


@pytest.mark.parametrize("dias,sale", [(0, False), (6, False), (7, True), (30, True)])
def test_toca_cada_siete_dias(dias, sale):
    assert backup.toca(HOY - timedelta(days=dias), HOY) is sale


def test_nombre_con_la_fecha():
    assert backup.nombre(HOY) == "copia-cryptotracker-2026-11-09.zip"


def test_la_copia_se_puede_restaurar(config, tmp_path):
    database.save_prices(config.database_path, {"bitcoin": 123.0}, "eur")
    database.apuntar_movimiento(
        config.database_path, "bitcoin", "compra", 1, 100, None, None
    )
    destino = tmp_path / "restaurada"

    ruta = _restaurar(backup.crear(config.database_path), destino)

    assert database.get_last_price(ruta, "bitcoin") == 123.0
    assert len(database.get_movimientos(ruta, None)) == 1


def test_lo_escrito_despues_no_toca_la_copia(config, tmp_path):
    database.save_prices(config.database_path, {"bitcoin": 123.0}, "eur")
    contenido = backup.crear(config.database_path)
    database.save_prices(config.database_path, {"bitcoin": 999.0}, "eur")

    ruta = _restaurar(contenido, tmp_path / "restaurada")

    assert database.get_last_price(ruta, "bitcoin") == 123.0
    assert database.get_last_price(config.database_path, "bitcoin") == 999.0


def test_backup_manda_un_archivo(config):
    respuesta = main.responder(config, "backup", "")

    assert isinstance(respuesta, comandos.Archivo)
    assert respuesta.nombre.endswith(".zip")
    assert "/copia" in respuesta.pie
    assert zipfile.is_zipfile(io.BytesIO(respuesta.contenido))


def test_backup_si_es_demasiado_grande(config, monkeypatch):
    monkeypatch.setattr(backup, "MAX_BYTES", 1)

    assert main.responder(config, "backup", "") == backup.GRANDE


def test_backup_si_falla_lo_dice(config, monkeypatch):
    def falla(ruta):
        raise OSError("disco lleno")

    monkeypatch.setattr(backup, "crear", falla)

    assert main.responder(config, "backup", "") == backup.FALLO


def test_backup_ya_no_es_copia():
    assert comandos.interpretar("/backup") == ("backup", "")
    assert comandos.interpretar("/respaldo") == ("backup", "")


def test_sin_activar_no_manda_nada(config, mandados):
    main.copia_semanal(Config(**{**config.__dict__, "copia_semanal": False}), HOY)

    assert mandados == []


def test_la_primera_se_manda_sin_sonido_y_se_apunta(config, mandados):
    main.copia_semanal(config, HOY)

    assert len(mandados) == 1
    assert mandados[0][1].endswith(".zip")
    assert mandados[0][3] == {"sin_sonido": True}
    assert _ultima(config) == HOY


def test_no_se_repite_hasta_la_semana_siguiente(config, mandados):
    main.copia_semanal(config, HOY)
    main.copia_semanal(config, HOY + timedelta(days=6))
    assert len(mandados) == 1

    main.copia_semanal(config, HOY + timedelta(days=7))
    assert len(mandados) == 2
    assert _ultima(config) == HOY + timedelta(days=7)


def test_si_no_llega_se_reintenta(config, monkeypatch):
    intentos = []
    monkeypatch.setattr(
        telegram,
        "send_document",
        lambda *a, **k: intentos.append(1) and False,
    )

    main.copia_semanal(config, HOY)
    main.copia_semanal(config, HOY)

    assert len(intentos) == 2
    assert _ultima(config) is None


def test_demasiado_grande_avisa_una_vez_por_semana(
    config, mandados, mensajes, monkeypatch
):
    monkeypatch.setattr(backup, "MAX_BYTES", 1)

    main.copia_semanal(config, HOY)
    main.copia_semanal(config, HOY)

    assert mandados == []
    assert mensajes == [backup.GRANDE]


@pytest.mark.parametrize(
    "error", [OSError("disco lleno"), database.DatabaseError("rota")]
)
def test_un_fallo_no_tumba_el_bucle(config, mandados, monkeypatch, error):
    def falla(ruta):
        raise error

    monkeypatch.setattr(backup, "crear", falla)

    main.copia_semanal(config, HOY)

    assert mandados == []
    assert _ultima(config) is None


@pytest.mark.parametrize(
    "entrada,sale", [("si", True), ("SÍ", True), ("", False), ("no", False)]
)
def test_parse_copia_semanal(entrada, sale):
    assert parse_copia_semanal(entrada) is sale


def test_parse_copia_semanal_mal():
    with pytest.raises(ConfigError, match="COPIA_SEMANAL"):
        parse_copia_semanal("7")


def test_sale_en_ajustes(config):
    assert "📦 Copia de seguridad cada semana" in ajustes.lineas(config)
    apagada = Config(**{**config.__dict__, "copia_semanal": False})
    assert "📦 Sin copia semanal" in ajustes.lineas(apagada)


@pytest.mark.parametrize(
    "nombre,tipo",
    [("copia.zip", "application/zip"), ("precios.csv", "text/csv")],
)
def test_el_tipo_y_la_espera_del_archivo(monkeypatch, nombre, tipo):
    llamadas = []

    class Respuesta:
        status_code = 200

        def json(self):
            return {"ok": True}

    def post(url, data, files, timeout):
        llamadas.append((data, files, timeout))
        return Respuesta()

    monkeypatch.setattr(telegram.requests, "post", post)

    assert telegram.send_document("t", "1", b"x", nombre, sin_sonido=True)

    datos, archivos, espera = llamadas[0]
    assert archivos["document"] == (nombre, b"x", tipo)
    assert datos["disable_notification"] == "true"
    assert espera == telegram.TIMEOUT_ARCHIVO
