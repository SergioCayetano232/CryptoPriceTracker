"""/version: qué versión del bot está corriendo."""

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Version:
    numero: str | None
    commit: str | None = None
    fecha: str | None = None  # la del commit, AAAA-MM-DD


def numero(pyproject: Path = RAIZ / "pyproject.toml") -> str | None:
    # Con regex y no tomllib, que no está en Python 3.10.
    try:
        texto = pyproject.read_text(encoding="utf-8")
    except OSError:
        return None
    hallado = re.search(r'^version\s*=\s*"([^"]+)"', texto, re.MULTILINE)
    return hallado.group(1) if hallado else None


def ultimo_commit(raiz: Path = RAIZ) -> tuple[str, str] | None:
    """El hash corto y la fecha del último commit, si hay git."""
    try:
        salida = subprocess.run(
            ["git", "log", "-1", "--format=%h %cs"],
            cwd=raiz,
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        ).stdout.split()
    except (OSError, subprocess.SubprocessError):
        return None
    # En un zip descargado no hay .git y git no saca nada.
    return (salida[0], salida[1]) if len(salida) == 2 else None


def leer(raiz: Path = RAIZ) -> Version:
    commit = ultimo_commit(raiz)
    return Version(numero(raiz / "pyproject.toml"), *(commit or (None, None)))
