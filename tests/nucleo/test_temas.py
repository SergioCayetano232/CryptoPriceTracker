"""Tests de los temas de /ayuda."""

from collections import Counter

from crypto_tracker.equivale import COSAS
from crypto_tracker.nucleo.comandos import ALIAS, COMANDOS
from crypto_tracker.nucleo.temas import TEMAS, TODO, botones, buscar, visibles
from crypto_tracker.nucleo.usuarios import SOLO_DUEÑO


def test_cada_comando_esta_en_un_tema_y_solo_en_uno():
    # Si añades un comando y no lo metes en un tema, no sale en /ayuda.
    contados = Counter(c for t in TEMAS for c in t.comandos)

    assert set(contados) == set(COMANDOS) - set(COSAS)
    assert [c for c, veces in contados.items() if veces > 1] == []


def test_ninguna_clave_pisa_un_comando():
    for clave in [*(t.clave for t in TEMAS), TODO]:
        assert clave not in COMANDOS
        assert clave not in ALIAS


def test_buscar():
    assert buscar("avisos").titulo == "🔔 Avisos"
    assert buscar(" AVISOS ").clave == "avisos"
    assert buscar("alerta") is None


def test_visibles_quita_los_del_dueño():
    sistema = buscar("sistema")

    assert "invitar" in visibles(sistema)
    assert "invitar" not in visibles(sistema, SOLO_DUEÑO)
    assert "ajustes" in visibles(sistema, SOLO_DUEÑO)


def test_botones_de_dos_en_dos():
    filas = botones()

    assert all(len(f) <= 2 for f in filas)
    todos = [b for f in filas for b in f]
    assert len(todos) == len(TEMAS) + 1
    assert todos[0] == ("📌 Lo básico", "/ayuda basico")
    assert todos[-1] == ("📜 Todo de golpe", "/ayuda todo")


def test_los_botones_caben_en_telegram():
    for fila in botones():
        for _, comando in fila:
            assert len(comando.encode()) <= 64
