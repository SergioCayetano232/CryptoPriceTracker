"""/chiste: un chiste de cripto, al azar."""

import random

CHISTES = (
    "—¿Qué tal te va con Bitcoin?\n—Como una montaña rusa, pero sin la parte de subir.",
    "Mi cartera es como mi gimnasio: pago todos los meses y no veo resultados.",
    "—Papá, ¿me dejas 0,001 BTC?\n—¿0,0001 BTC? ¿Para qué quieres 0,00001 BTC?",
    "Compré en máximos para ir sobre seguro. Ahora estoy seguro de que no "
    "vuelvo a comprar.",
    "Le dije a mi novia que la quiero más que a Bitcoin. Desde entonces no se fía.",
    "¿Cuántos traders hacen falta para cambiar una bombilla? Ninguno, la venden "
    "a oscuras y la recompran cuando está encendida.",
    "Hodl no es una estrategia. Es lo que pasa cuando se te olvida la contraseña.",
    "Mi asesor financiero es un hámster que elige monedas. Lleva mejor año que yo.",
    "—¿Por qué Ethereum fue al psicólogo?\n—Porque tenía demasiadas dependencias.",
    "Perdí la seed phrase, pero lo llevo bien. Ahora soy holder a largo plazo, "
    "a la fuerza.",
    "Hace un año compré la caída. Sigo comprándola, la condenada no acaba nunca.",
    "Me hice minero de Bitcoin. Ahora la factura de la luz también es volátil.",
    "Diversifiqué la cartera: ahora pierdo en doce monedas distintas.",
)


def elegir(azar: random.Random | None = None) -> str:
    return (azar or random).choice(CHISTES)
