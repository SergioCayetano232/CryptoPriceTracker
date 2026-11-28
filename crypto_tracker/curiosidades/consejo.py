"""/consejo: un consejo de inversión malísimo, al azar."""

import random

CONSEJOS = (
    "Compra cuando esté en máximos. Si ha subido tanto, por algo será.",
    "Si baja un 10%, vende. Si baja un 50%, compra el doble. Si baja un 90%, "
    "ya no mires.",
    "Mete todo en la que te recomendó tu cuñado en la cena de Navidad.",
    "La seed phrase, en una nota del móvil que se llame «contraseñas».",
    "No vendas nunca. Ni siquiera cuando necesites el dinero.",
    "Si una moneda tiene un perro en el logo, es una inversión segura.",
    "Las pérdidas no cuentan hasta que vendes. Así que no vendas y no pierdes.",
    "Haz caso a cualquiera que tenga un láser en los ojos en la foto de perfil.",
    "Pide un préstamo para comprar más. Total, solo puede subir.",
    "Apalancamiento x100. La vida es corta.",
    "Si alguien te escribe por Telegram para doblarte el dinero, contéstale "
    "rápido, que se acaba.",
    "Diversifica: compra diez monedas que no conoces en vez de una.",
    "Mira el precio cada cinco minutos. Así lo controlas.",
    "El análisis técnico es mirar la gráfica hasta que veas una cara.",
    "Si no lo entiendes, mejor. Así no te da miedo.",
)


def elegir(azar: random.Random | None = None) -> str:
    return (azar or random).choice(CONSEJOS)
