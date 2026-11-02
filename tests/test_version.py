"""Tests de /version."""

import subprocess

from crypto_tracker import version
from crypto_tracker.alerts import formatear_version
from crypto_tracker.comandos import interpretar
from crypto_tracker.version import Version


def test_numero(tmp_path):
    archivo = tmp_path / "pyproject.toml"
    archivo.write_text('[project]\nname = "x"\nversion = "1.4.2"\n', encoding="utf-8")

    assert version.numero(archivo) == "1.4.2"


def test_numero_sin_archivo(tmp_path):
    assert version.numero(tmp_path / "no.toml") is None


def test_numero_sin_version(tmp_path):
    archivo = tmp_path / "pyproject.toml"
    archivo.write_text('[tool.ruff]\ntarget-version = "py310"\n', encoding="utf-8")

    assert version.numero(archivo) is None


def test_sin_git(tmp_path, monkeypatch):
    def falla(*args, **kwargs):
        raise FileNotFoundError("git")

    monkeypatch.setattr(subprocess, "run", falla)

    assert version.ultimo_commit(tmp_path) is None


def test_carpeta_sin_repo(tmp_path):
    assert version.leer(tmp_path) == Version(None)


def test_formatear():
    texto = formatear_version(Version("0.2.0", "4e9583c", "2026-11-02"))

    assert texto == (
        "🏷️ <b>CryptoPriceTracker 0.2.0</b>\nÚltimo cambio: 4e9583c, del 02/11/2026"
    )


def test_formatear_sin_git():
    assert formatear_version(Version("0.2.0")) == "🏷️ <b>CryptoPriceTracker 0.2.0</b>"


def test_formatear_sin_nada():
    assert formatear_version(Version(None)) == (
        "🏷️ <b>CryptoPriceTracker</b>\nNo he encontrado el número de versión."
    )


def test_comando():
    assert interpretar("/version") == ("version", "")
    assert interpretar("/versión") == ("version", "")
