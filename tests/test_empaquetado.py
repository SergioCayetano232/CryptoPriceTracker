"""Que al instalarlo con pip no se quede ninguna carpeta fuera."""

from fnmatch import fnmatchcase
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent


def _paquetes() -> list[str]:
    return sorted(
        ".".join(init.parent.relative_to(RAIZ).parts)
        for init in (RAIZ / "crypto_tracker").rglob("__init__.py")
    )


def test_entran_todas_las_carpetas():
    # tomllib llega con Python 3.11; en la 3.10 lo prueba la otra del CI.
    tomllib = pytest.importorskip("tomllib")
    with open(RAIZ / "pyproject.toml", "rb") as f:
        config = tomllib.load(f)
    include = config["tool"]["setuptools"]["packages"]["find"]["include"]

    paquetes = _paquetes()
    fuera = [p for p in paquetes if not any(fnmatchcase(p, i) for i in include)]

    assert "crypto_tracker.respuestas" in paquetes
    assert fuera == []
