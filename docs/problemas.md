# Si algo no va

[← Volver al README](../README.md)

**No me llega ningún mensaje**
Lanza `python main.py --test`. Si tampoco llega, es el token o el chat id. Y
asegúrate de haberle escrito `/start` al bot.

**Dice que no encuentra una cripto**
El nombre no es el correcto. Búscalo con `python main.py --buscar <nombre>` y
usa el id que te da.

**`/historico` manda texto en vez de imagen**
Falta matplotlib. Si has actualizado el bot, vuelve a ejecutar
`pip install -r requirements.txt` con el entorno activado.

**Sale un error 403**
CoinGecko está bloqueando las consultas sin clave desde tu conexión. Pon una
`COINGECKO_API_KEY` gratuita (ver "La clave de CoinGecko").

**Sale un error 429**
Le estás pidiendo precios demasiado rápido. Lo reintenta solo un par de veces,
así que si aparece de vez en cuando puedes ignorarlo. Si sale continuamente,
pon una `COINGECKO_API_KEY` o sube `CHECK_INTERVAL`.

**El aviso dice "Precios de Binance"**
CoinGecko no contestaba y el bot ha tirado de Binance para no dejarte sin
aviso. Solo vale con `VS_CURRENCY` en `eur` o `usd` y con las criptos
conocidas (`btc`, `eth`, `sol`...). Las estables y las raras esperan a que
vuelva CoinGecko.

**Quiero enterarme si se cae el servidor**
Si falla CoinGecko, el bot te avisa él. Pero si se va la luz o se cuelga la
máquina, no puede. Crea un check gratis en [healthchecks.io](https://healthchecks.io)
con un periodo de 10 minutos, copia su dirección en `LATIDO_URL` y reinicia: el
bot le da un toque en cada consulta buena y, si deja de llegar, te escriben
ellos. Vale cualquier servicio que funcione así (Uptime Kuma, Better Stack...).

**Me avisa demasiado**
El paso es muy pequeño. Con `bitcoin:100` te avisa continuamente; prueba con
`bitcoin:1000` o más. Con porcentajes, sube del `%2` al `%5`.
