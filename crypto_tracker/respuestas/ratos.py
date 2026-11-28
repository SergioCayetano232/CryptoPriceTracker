"""Juegos y bromas para pasar el rato: horóscopo, bola mágica, quiz..."""

from datetime import date

from .. import adivina, bola, horoscopo, ppt, quiz
from ..avisos import alerts
from ..nucleo import comandos, telegram
from ..nucleo.config import Config
from .base import (
    Respuesta,
    _precio_o_pedirlo,
)


def _comando_horoscopo(config: Config, argumento: str) -> Respuesta:
    try:
        signo = horoscopo.interpretar(argumento)
    except horoscopo.HoroscopoError as e:
        return telegram.escape(str(e))
    return alerts.formatear_horoscopo(horoscopo.leer(signo, date.today()))


def _comando_bola(config: Config, argumento: str) -> Respuesta:
    try:
        pregunta = bola.interpretar(argumento)
    except bola.BolaError as e:
        return telegram.escape(str(e))
    return alerts.formatear_bola(pregunta, bola.agitar())


def _comando_quiz(config: Config, argumento: str) -> Respuesta:
    elegida = quiz.interpretar(argumento)
    if elegida is None:
        return comandos.ConBotones(*alerts.formatear_quiz(quiz.sacar()))
    return comandos.ConBotones(*alerts.formatear_respuesta_quiz(*elegida))


def _comando_ppt(config: Config, argumento: str) -> Respuesta:
    try:
        tuya = ppt.interpretar(argumento)
    except ppt.PptError as e:
        return telegram.escape(str(e))
    del_bot = ppt.sacar()
    return alerts.formatear_ppt(tuya, del_bot, ppt.resultado(tuya, del_bot))


def _adivina(config: Config, argumento: str) -> str:
    try:
        coin_id, dicho = adivina.interpretar(argumento)
    except adivina.AdivinaError as e:
        return telegram.escape(str(e))
    precio = _precio_o_pedirlo(config, coin_id)
    if isinstance(precio, str):
        return precio
    intento = adivina.Intento(coin_id, dicho, precio)
    return alerts.formatear_adivina(intento, config.vs_currency)
