"""/refran: un refrán de toda la vida, cambiado al mundo cripto."""

import random

REFRANES = (
    "A quien madruga, el halving le ayuda.",
    "No por mucho mirar el precio sube más temprano.",
    "Más vale satoshi en mano que bitcoin volando.",
    "Dime qué holdeas y te diré quién eres.",
    "En casa del minero, factura de la luz de acero.",
    "Cuando el río suena, ballenas lleva.",
    "Ojos que no ven gráfica, corazón que no siente.",
    "A caballo regalado no le mires el contrato.",
    "Quien compra en el pico, no se hace rico.",
    "Más vale tarde que nunca, salvo si compras en máximos.",
    "No hay mal que cien años dure, ni mercado bajista que no acabe.",
    "Dios aprieta pero no liquida.",
    "Cría memecoins y te sacarán los ojos.",
    "El que no arriesga no gana. Y el que arriesga, a veces tampoco.",
    "Al mal tiempo, buena cara y DCA.",
)


def elegir(azar: random.Random | None = None) -> str:
    return (azar or random).choice(REFRANES)
