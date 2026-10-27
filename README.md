# CryptoPriceTracker

Te avisa por Telegram cuando el precio de una cripto sube o baja de cierto punto.

Consulta los precios cada pocos minutos, los va guardando y te manda un mensaje
cuando pasa algo. Puedes dejarlo funcionando en un servidor y olvidarte.

---

## Lo que necesitas

- Un ordenador o servidor con **Python 3.10 o superior** ([descargar](https://www.python.org/downloads/))
- Telegram

---

## Instalación

**1. Descarga el proyecto y ábrelo en una terminal.**

**2. Prepara el entorno:**

Windows:
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Mac o Linux:
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Crear el bot de Telegram

Necesitas dos datos: el **token** del bot y tu **chat id**.

**El token:**

1. Abre Telegram y busca **@BotFather**
2. Escríbele `/newbot`
3. Te pide un nombre y un usuario para el bot
4. Te da un texto largo tipo `123456789:AAxxxxxx...` — ese es el token

**Tu chat id:**

1. Busca **@userinfobot** en Telegram
2. Escríbele cualquier cosa
3. Te contesta con un número — ese es tu chat id

**Importante:** busca el bot que acabas de crear y escríbele `/start`. Si no lo
haces, Telegram no le deja mandarte mensajes.

---

## La clave de CoinGecko

Es gratis y evita que CoinGecko te bloquee las consultas de precios, cosa que
sin clave pasa con bastantes conexiones.

1. Entra en [coingecko.com/en/api/pricing](https://www.coingecko.com/en/api/pricing)
   y elige el plan **Demo** (gratis)
2. Regístrate y, en tu panel, crea una clave. Empieza por `CG-`
3. Luego la pegas en `COINGECKO_API_KEY` del `.env`

---

## Configuración

Copia el archivo de ejemplo:

Windows: `copy .env.example .env`
Mac/Linux: `cp .env.example .env`

Abre el `.env` con cualquier editor de texto y rellena el token y el chat id.

Luego elige qué criptos vigilar en la línea `WATCHLIST`. Hay tres formas:

**Avisarte cada vez que pase un múltiplo:**
```
WATCHLIST=bitcoin:1000
```
Te avisa cuando Bitcoin pase por 63.000, luego por 64.000, luego por 65.000...

**Avisarte cuando se mueva un porcentaje:**
```
WATCHLIST=bitcoin:%5
```
Te avisa cada vez que suba o baje un 5% desde el último aviso. Va por tramos: si
sube un 12% de golpe te avisa una vez, y vuelve a avisarte al siguiente 5%.

Suele ser la más útil: un paso de 1.000 € no significa lo mismo con Bitcoin a
30.000 que a 120.000, y un porcentaje sí.

**Avisarte al salir de un rango:**
```
WATCHLIST=bitcoin:55000:75000
```
Te avisa si baja de 55.000 o si sube de 75.000.

Cada aviso lleva debajo cuánto ha variado en las últimas 24 h (`En 24 h: 🔺
+4.17%`), para saber si viene de un subidón o es ruido, y cuánto le falta para
su máximo histórico.

**Puedes mezclar y poner varias separadas por comas:**
```
WATCHLIST=bitcoin:%5,ethereum:100,solana:5
```

Los nombres son los de CoinGecko: `bitcoin`, no `BTC`. Si no sabes cuál es,
búscalo:
```
python main.py --buscar btc
```
Te saca los candidatos con el más probable primero. Funciona aunque todavía no
hayas rellenado el `.env`.

---

## Probar que funciona

```
python main.py --test
```

Si te llega un mensaje a Telegram, ya está todo bien. Si no, revisa el token, el
chat id, y que le hayas escrito `/start` al bot.

---

## Usarlo

**Mirar los precios una vez:**
```
python main.py
```

**Dejarlo vigilando:**
```
python main.py --loop
```
Se queda mirando los precios cada cinco minutos y medio. Para pararlo, `Ctrl+C`.

Al arrancar te manda un 🟢 *Encendido* con lo que vigila, cuántas alertas tienes
puestas y, si llevaba un rato parado, desde cuándo. Así sabes si el servidor se
ha reiniciado.

Si pasa media hora sin poder consultar los precios, te avisa por Telegram, y
otra vez cuando vuelve a funcionar. Si se para por errores, también te lo dice.
Y si una cripto de `WATCHLIST` no existe en CoinGecko (un `bitcion`), te avisa
una vez al arrancar para que no te quedes esperando un aviso que nunca llegará.

**Manejarlo desde Telegram:**

Mientras está en modo `--loop` puedes escribirle al bot desde el móvil:

| Comando | Qué hace |
|---|---|
| `/status` | Cómo van tus criptos ahora |
| `/hoy` | Cómo van desde las 00:00 en vez de en las últimas 24 h, con el máximo y el mínimo de hoy (`/hoy btc eth`, solo esas). Sale de lo guardado y no gasta consultas |
| `/resumen` | El resumen del día cuando lo pidas, con el índice de miedo y codicia. No quita el de la hora de siempre |
| `/horario 8:30` | Cambia la hora del resumen del día (y del de los domingos). `/horario no` lo quita; a secas, te dice cuál tienes |
| `/precio solana` | Lo que vale una cripto ahora y cómo va en la última hora, en 24 h, en 7 y en 30 días, aunque no la vigiles, entre qué precios se ha movido en 24 h, lo que vale en sats, cuánto se ha emitido ya de su máximo (si tiene), su máximo histórico con lo que le falta para volver, su puesto por capitalización y cuánto se ha negociado en 24 h (y qué parte es de lo que vale). Debajo, unas barritas `▁▃▅▇` con la forma de las últimas 24 h, si tiene precios guardados. Si la tienes en la cartera, también lo que vale lo tuyo |
| `/precio btc eth sol` | Lo mismo de varias a la vez, una por línea (hasta 10) |
| `/precio` | Sin decir cuál, todas las que vigilas |
| `/precio btc usd` | En otra moneda solo esa vez (`eur`, `usd` o `gbp`; también `$` o `dólares`). Vale con varias y con `/precio usd` a secas. No sale lo tuyo de la cartera, que va en la moneda del `.env` |
| `btc` o `btc eth` | Sin barra, lo mismo que `/precio`. Solo con las conocidas, para que un "hola" no se lo tome como una cripto |
| `/ath bitcoin` | Su máximo histórico, cuándo fue y cuánto le falta para volver, y debajo su mínimo histórico y cuánto ha subido desde ahí (vale `/ath btc eth`, solo con el máximo, y a secas, las que vigilas) |
| `/cartera` | Tu cartera: cuánto vale, cuánto ganas o pierdes, el total en sats y la gráfica de 7 días |
| `/cartera 30d` | Lo mismo, con la gráfica del tramo que digas |
| `/cartera usd` | Lo que vale en otra moneda (`eur`, `usd` o `gbp`). Sin lo que ganas ni gráfica, que lo que te costó va en la moneda del `.env` |
| `/reparto` | Qué parte de tu cartera es cada cripto, con una imagen de barras. Si tienes más de 6, las pequeñas van juntas en "Otras" |
| `/semana` | El resumen de tu semana sin esperar al domingo. No gasta consultas |
| `/semana bitcoin` | La semana de una sola: lo mismo que `/historico bitcoin 7d` |
| `/compra bitcoin 0.01 600` | Apunta en la cartera que has comprado 0,01 por 600 € |
| `/compra bitcoin 0.01 @60000` | Lo mismo, con el precio de cada una en vez del total |
| `/venta bitcoin 0.005 350` | Apunta una venta y lo que te dieron (`/venta bitcoin todo` la saca de la cartera) |
| `/ganancias` | Lo que has ganado o perdido de verdad con lo que ya vendiste |
| `/primera` | Tu primera compra, cuánto hace, cuánto ha cambiado el precio desde entonces y lo que vale hoy lo que compraste (`/primera btc`, la primera de esa). Solo las apuntadas con `/compra` |
| `/movimientos` | Tus últimas compras y ventas, con un botón para deshacer la última (`/movimientos btc`, solo las de esa) |
| `/deshacer` | Quita la última compra o venta y deja la cripto como estaba |
| `/alerta bitcoin 70000` | Te avisa una vez cuando llegue a ese precio |
| `/alerta bitcoin +10%` | Te avisa una vez cuando suba un 10% desde ahora |
| `/alerta bitcoin 70000 7d` | Lo mismo, pero si en 7 días no ha llegado se borra sola y te lo dice |
| `/alerta bitcoin 70000 vender la mitad` | Con una nota detrás, que te sale en el aviso (también después del tramo) |
| `/alerta bitcoin` | Sin precio, te dice a cuánto está y te pone un ejemplo |
| `/alerta cartera 5000` | Lo mismo con lo que vale tu cartera entera (también `-10%`). Si espera a que suba, con una barra `▓▓▓▓░░` de lo que llevas |
| `/alertas` | Las alertas que tienes puestas y cuánto le falta a cada una, la más cerca primero, con un 🗑 para quitarlas |
| `/ultimo` | Cuándo te avisó por última vez cada una de las que vigilas, a qué precio y cuánto se ha movido desde entonces. Solo cuenta los avisos que llegaron, no los del silencio |
| `/quitar 3` | Quita la alerta número 3 (`/quitar 2 5` varias, `/quitar bitcoin` las de esa cripto, `/quitar todas` todas) |
| `/volatilidad bitcoin 30d` | Cuánto se mueve de media al día y cuántos avisos te habría dado `/vigilar` con %2, %5 y %10 (sin tramo, 30 días) |
| `/vigilar` | Lo que está vigilando y cómo, con un ✖ en cada una para dejarla |
| `/vigilar solana %5` | Añade una cripto, o cambia cómo vigila una que ya estaba |
| `/dejar solana` | Deja de vigilarla (`/dejar sol eth` varias a la vez) |
| `/historico bitcoin` | Imagen con la gráfica de las últimas 24 h, máximo y mínimo |
| `/historico bitcoin 7d` | Lo mismo, del tramo que digas (`12h`, `7d`, `30d`...) |
| `/historico` | Sin decir cuál, la primera que vigilas (también `/historico 7d`) |
| `/media bitcoin` | Su media de 7, 30 y 90 días y si el precio de ahora está por encima o por debajo de cada una, y si lo está de todas (`/media bitcoin 14d`, solo la de esos días). Sale de lo guardado y no gasta consultas |
| `/racha bitcoin` | Cuántos días seguidos lleva subiendo o bajando y cuánto lleva en esa racha. Sale de lo guardado y no gasta consultas |
| `/extremo bitcoin 30d` | El día que más subió y el que más bajó en ese tramo, con la fecha y hace cuánto fue, el % y de qué precio a cuál (sin tramo, 30 días). Sale de lo guardado y no gasta consultas |
| `/verdes bitcoin 30d` | Cuántos días subió y cuántos bajó en ese tramo, qué parte fue en verde y cómo fueron los últimos 7 en cuadraditos 🟩🟥 (sin tramo, 30 días). Sale de lo guardado y no gasta consultas |
| `/diasemana bitcoin 90d` | Lo que sube o baja de media cada día de la semana, cuál suele ser el mejor y el peor, y cómo suele ir el de hoy (sin tramo, 90 días). Sale de lo guardado y no gasta consultas |
| `/horas bitcoin 30d` | A qué hora del día suele estar más barata y a cuál más cara, comparando cada hora con la media de su día, con una barrita de las 24 horas y cómo suele estar a la hora de ahora (sin tramo, 30 días). Solo cuenta los días que tiene casi enteros. Sale de lo guardado y no gasta consultas |
| `/rango bitcoin 30d` | Su máximo y su mínimo en ese tramo con hace cuánto fueron, su media y en qué punto del rango está hoy (sin tramo, 7 días). Sale de lo guardado y no gasta consultas |
| `/dia bitcoin 01/09` | Qué día de la semana fue, a cuánto cerró, su máximo y su mínimo, y cuánto ha cambiado desde entonces. Vale `ayer` y con año (`01/09/2025`). Sale de lo guardado y no gasta consultas |
| `/cuando bitcoin 60000` | La última vez que estuvo a ese precio (o más abajo, si ahora está por encima), hace cuánto y lo que ha cambiado desde entonces. Vale `60k`. Sale de lo guardado y no gasta consultas |
| `/redondo bitcoin` | Cuánto le falta para la siguiente cifra redonda por arriba y por abajo (de 64.000 a 70.000 y a 60.000). A secas, las que vigilas. Sale de lo guardado y no gasta consultas |
| `/rsi bitcoin` | Su RSI de 14 días: por encima de 70 ha subido demasiado rápido (sobrecomprada) y por debajo de 30 ha bajado demasiado (sobrevendida). Necesita 15 días seguidos guardados y no gasta consultas |
| `/caida bitcoin 30d` | Cuánto ha bajado desde el máximo del tramo y cuál fue su peor caída, de qué precio a cuál (sin tramo, 30 días). Sale de lo guardado y no gasta consultas |
| `/sube bitcoin 30d` | Lo contrario: cuánto ha subido desde el mínimo del tramo y cuál fue su mejor subida, de qué precio a cuál (sin tramo, 30 días). También con `/minimo`. Sale de lo guardado y no gasta consultas |
| `/comparar btc eth sol 7d` | Qué tal le ha ido a cada una en ese tramo, de la mejor a la peor (sin tramo, 7 días; sin criptos, las que vigilas) |
| `/correlacion btc eth 30d` | Si dos criptos suben y bajan a la vez (de -1 a +1), para saber si tu cartera está repartida de verdad (sin tramo, 30 días; sin criptos, las dos primeras que vigilas). Sale de lo guardado y no gasta consultas |
| `/ratio eth btc 30d` | Cuánto vale una en la otra (1 ethereum = 0,03 bitcoin) y cuánto ha cambiado en ese tramo, con barritas, el máximo, el mínimo y en qué punto del rango está. Si sube, a la primera le ha ido mejor (sin tramo, 30 días; sin criptos, las dos primeras que vigilas). Sale de lo guardado y no gasta consultas |
| `/convertir 0.05 bitcoin` | Cuánto es en euros al precio de ahora |
| `/convertir 500 eur solana` | Al revés: cuánta solana compras con 500 € (vale `500€`) |
| `/convertir 1 eth btc` | De una cripto a otra: cuánto bitcoin es 1 ethereum, y al revés |
| `/convertir 100000 sats` | En satoshis (cien millones son un bitcoin). Vale al revés, `/convertir 50 eur sats`, y entre criptos, `/convertir 1 eth sats` |
| `/si 1000 bitcoin 30d` | Cuánto tendrías hoy si hubieras metido 1.000 € hace 30 días (sin tramo, 30 días) |
| `/dca 50 bitcoin semanal 90d` | Lo mismo metiendo 50 € cada semana, con lo invertido y el precio medio. También `diario` o `mensual`; sin decirlo, semanal y 90 días |
| `/objetivo bitcoin 100000` | Cuánto valdría tu cartera si bitcoin llegara a ese precio, y cuánto ganarías sobre lo invertido. Vale `100k`, y también para ver una bajada |
| `/equilibrio` | A qué precio dejas de perder con cada cripto de tu cartera y cuánto le falta, de la que más lejos está a la que menos, y cuánto tendría que subir todo junto. Solo con las que dicen lo que te costaron |
| `/doble` | A qué precio tiene que llegar cada cripto de tu cartera para que dobles lo que metiste, cuánto le falta y cuánto tendría que subir todo junto. Solo con las que dicen lo que te costaron |
| `/exportar bitcoin 30d` | Te manda un CSV con los precios guardados (sin tramo, 30 días) |
| `/mercado` | Lo que vale todo el mercado cripto, cómo va en 24 h y qué parte es de Bitcoin, Ethereum y las estables |
| `/halving` | Cuántos días faltan para el próximo halving de Bitcoin, cuánto va de ciclo y cuánto bajará lo que se paga por bloque. La fecha es aproximada y no gasta consultas |
| `/cumple` | Los años de Bitcoin, los días que lleva funcionando y cuánto falta para su cumpleaños (el 3 de enero) |
| `/whitepaper` | Los años del whitepaper de Bitcoin, los días desde que Satoshi lo publicó y cuánto falta para que cumpla (el 31 de octubre) |
| `/merge` | Los años desde The Merge, cuando Ethereum dejó la minería, los días que lleva y cuánto falta para el aniversario (el 15 de septiembre) |
| `/pizza` | Lo que valdrían hoy los 10.000 BTC que se pagaron por dos pizzas en 2010, y cuánto falta para el Bitcoin Pizza Day |
| `/millonario` | Cuánto bitcoin (u otra, `/millonario eth`) necesitas para tener un millón al precio de hoy y, si la tienes en la cartera, cuánto llevas del camino |
| `/sat` | Lo que vale un satoshi (la cien millonésima parte de un bitcoin) y cuántos te dan 1, 10 y 100. Para cantidades exactas, `/convertir 50 eur sats` |
| `/lambo` | Cuántos Lamborghinis te da tu cartera, a unos 250.000 cada uno, y cuánto te falta para el siguiente |
| `/cafe` | Cuántos cafés te da tu cartera, a 1,50 cada uno, y para cuánto tiempo tienes tomando uno al día |
| `/bigmac` | Cuántos Big Mac te da tu cartera, a unos 5,50 cada uno |
| `/gasolina` | Cuántos litros de gasolina te da tu cartera, a unos 1,80 el litro, y cuántos depósitos de 50 litros son |
| `/sueldo` | Cuántos meses (o años) de salario mínimo es tu cartera, con el SMI de 2026: 1.221 € en 14 pagas. Solo en euros |
| `/tendencias` | Las 7 criptos que más se buscan hoy en CoinGecko, con un botón en cada una para ver su precio y ponerle una alerta |
| `/top` | Las 5 que más suben y las 5 que más bajan hoy de las 100 más grandes, con su precio |
| `/aleatoria` | Una de las 100 más grandes al azar, con su puesto, su precio y cómo va hoy. No saca las que ya vigilas ni las estables. Con un botón para pedir otra |
| `/caraocruz` | ¿Compro o vendo? Lo decide una moneda al aire (`/caraocruz btc`, con la cripto). Es de broma y no gasta consultas |
| `/frase` | Una frase famosa del mundo cripto al azar, de Satoshi, Hal Finney, Buffett y otros, con quién la dijo y cuándo. No gasta consultas |
| `/glosario fomo` | Lo que significa una palabra cripto: hodl, fomo, fud, dca, ath, ballena... A secas, la lista de las que sabe |
| `/miedo` | El índice de miedo y codicia del mercado (0 pánico, 100 euforia), con el de ayer y el de hace una semana. Viene de alternative.me y no gasta consultas de CoinGecko |
| `/buscar btc` | Encuentra el id de CoinGecko de una cripto |
| `/copia` | Las líneas `WATCHLIST`, `PORTFOLIO` y `RESUMEN_DIARIO` como están ahora, con lo cambiado por Telegram, listas para pegar en el `.env`. Para guardarlo por si cambias de servidor |
| `/ajustes` | Lo que tienes puesto en el `.env`: la moneda, cada cuánto consulta, los días que guarda, el resumen, el aviso de movimientos bruscos, el de máximos y mínimos y las horas tranquilas |
| `/consultas` | Cuántas consultas a CoinGecko llevas este mes |
| `/bot` | Si sigue funcionando: desde cuándo está encendido, cuándo fue el último ciclo y las consultas del mes. También con `/ping` |
| `/mute` | Te pregunta cuánto tiempo callarse, con botones: 1 h, 4 h o hasta las 8:00 (si ya está callado, o tienes alguna cripto callada, te dice hasta cuándo) |
| `/mute 2h` | Calla los avisos ese rato, con un botón para deshacerlo |
| `/mute hasta 8:00` | Calla los avisos hasta esa hora (si ya ha pasado, la de mañana) |
| `/mute bitcoin 2h` | Calla solo esa cripto; las demás siguen avisando. Sus `/alerta` esperan a que vuelva |
| `/unmute` | Vuelve a avisar, también de las que callaste una a una |
| `/unmute bitcoin` | Vuelve a avisar solo de esa |
| `/ayuda` | La lista de comandos |
| `/ayuda alerta` | Ese comando con ejemplos de todo lo que admite |

En los comandos vale el símbolo de las más conocidas en vez del id: `/precio btc`,
`/alerta eth 3000`, `/compra sol 2`. Para las demás, el id de `/buscar`.

Al escribir `/` en el chat te salen solos. Solo contesta a tu chat id, y si
estaba apagado, al volver ignora lo que le escribiste hace más de 10 minutos.

**Botones en los avisos:**

Cada aviso lleva debajo unos botones para reaccionar de un toque:

- **📈 Gráfica**: la de las últimas 24 h, como `/historico`.
- **🎯 Si vuelve a 64.000**: te avisa una vez si vuelve al precio que acaba de
  cruzar, como `/alerta`.
- **🔁 Otra a +5%**: solo cuando salta una `/alerta`. Te pone otra un 5 % más
  allá del precio de ahora, hacia donde iba (si bajaba, `-5%`).
- **🔕 Callar 1 h**: como `/mute 1h`.

Si en un mensaje vienen varias criptos, salen los botones de las tres primeras.

`/mute` a secas te deja elegir cuánto con un toque, y al callarlo sale un
**🔔 Volver a avisar** por si te arrepientes.

`/precio` de una sola lleva **🔔 Si sube un 5%** y **🔔 Si baja un 5%**, que
te ponen esa `/alerta` desde lo que vale ahora, y un **📈 Gráfica** con la de
las últimas 24 h si tiene precios guardados.

`/status`, `/resumen`, `/cartera`, `/alertas` y `/precio` de varias llevan un
**🔄 Actualizar** para volver a pedirlos de un toque.

**Alertas de una sola vez:**

Escríbele `/alerta bitcoin 70000` y te avisa cuando llegue a 70.000, suba o
baje, según dónde esté ahora. Avisa una vez y se borra sola, sin tocar el `.env`
ni reiniciar. Vale cualquier cripto, aunque no esté en `WATCHLIST`, y puedes
escribir el precio como `70.000` o `0,35`. Si estás en `/mute`, no se pierde: te
avisa al volver si sigue en ese precio.

Si no quieres hacer cuentas, ponlo en porcentaje: `/alerta bitcoin +10%` o
`/alerta solana -5%`. Calcula el precio con lo que vale en ese momento y te
contesta a cuánto ha quedado. El signo es obligatorio, que un `10%` a secas no
dice si esperar a que suba o a que baje.

Para que no se te acumulen alertas viejas, ponles caducidad al final:
`/alerta bitcoin 70000 7d` o `/alerta solana +10% 12h`. Si en ese tiempo no
llega, se borra sola y te manda un ⌛ sin sonido para que lo sepas. `/alertas`
te enseña cuándo caduca cada una. Las que pongas sin tramo no caducan nunca.

Lo que escribas después del precio (o del tramo) se guarda como nota y te sale
con el aviso: `/alerta bitcoin 70000 vender la mitad`. Así te acuerdas de por
qué la pusiste.

El resumen del día (y `/resumen`) te enseña las que están a menos de un 3 % de
saltar. Si no hay ninguna tan cerca, te dice cuántas tienes y cuál está más
cerca, para que no se te olviden.

Con `cartera` en vez de una cripto, mira lo que vale todo lo que tienes junto:
`/alerta cartera 5000` o `/alerta cartera -10%`. Si en un ciclo falta el precio
de alguna, ese ciclo no la mira, que el total saldría más bajo de lo que es y
daría un aviso falso.

**Cambiar lo que vigila sin tocar el `.env`:**

`/vigilar` admite lo mismo que `WATCHLIST`, con espacios en vez de dos puntos:
`/vigilar solana 10`, `/vigilar solana %5` o `/vigilar bitcoin 55000 75000`
(con un `-` dejas un lado sin vigilar: `/vigilar ethereum - 4000`). Se aplica al
momento, sin reiniciar, y se guarda aunque se apague.

El `.env` sigue siendo la base y lo que hagas por Telegram va encima. Si una
cripto la has tocado por Telegram, manda eso aunque luego cambies el `.env`.
`/vigilar` te lo marca con *(desde Telegram)*.

**Ver cómo van ahora mismo:**
```
python main.py --status
```
Te manda a Telegram un resumen con el precio de todo lo que vigilas y cuánto ha
cambiado en las últimas 24 horas. Ese dato lo da CoinGecko en la misma consulta,
así que sale desde el primer momento aunque acabes de instalarlo.

Debajo de cada una te dice a qué precio saltaría el siguiente aviso y cuánto le
falta, por ejemplo `↑ €64.000,00 (+1.59%) · ↓ €63.000,00 (-0.90%)`. Así sabes si
está a punto de avisarte o le queda mucho.

**Ver cuánto vale lo que tienes:**
```
PORTFOLIO=bitcoin:0.016:1000,ethereum:0.4:1000
```
Cada una es `cripto:cantidad:lo que te costó`. La cantidad es la que te sale en
el exchange; lo que te costó es opcional, pero sin eso no sabe si ganas o
pierdes. El resumen (`--status`, `/status` y el diario) añade al final lo que
vale cada una, cuánto llevas ganado o perdido con ella y el total. Debajo de
cada una te pone qué parte del total es, a cuánto te salió de media y a cuánto
está ahora (`38% del total · te salió a €62.500,00 · ahora €76.258,00`). Si solo
quieres eso, escríbele `/cartera`.

`/cartera` además te manda una gráfica de lo que ha valido, con una línea
discontinua en lo que invertiste. Ojo: usa las cantidades de ahora, así que es
lo que habría valido lo que tienes hoy, no tu historial de compras. Empieza a
tener datos en cuanto el bot lleva un rato en `--loop`.

**Sacar los precios a una hoja de cálculo:**

`/exportar bitcoin 30d` te manda por Telegram un archivo `.csv` con todos los
precios guardados de ese tramo, con la fecha en tu hora. Va con punto y coma y
coma decimal, que es como lo abre bien Excel en español con doble clic. Solo
tiene lo que el bot ha ido guardando, así que no llega más atrás de
`HISTORY_DAYS` ni de cuando lo instalaste.

**Saber cuánto tendrías si hubieras comprado:**

`/si 1000 bitcoin 30d` te dice cuánto valdrían hoy 1.000 € metidos en Bitcoin
hace 30 días, y cuánto habrías ganado o perdido. Sale de los precios que ya
tiene guardados, así que no gasta consultas, pero solo vale con las criptos que
vigila y no llega más atrás de cuando lo instalaste.

**Saber cuánto valdría tu cartera a un precio:**

`/objetivo bitcoin 100000` te dice cuánto valdría todo lo que tienes si Bitcoin
llegara a 100.000 €, cuánto es respecto a hoy y, si apuntaste lo que pagaste,
cuánto ganarías. Las demás criptos las deja a su precio de ahora. Solo vale con
las que tienes en la cartera.

**Apuntar compras y ventas desde el móvil:**

No hace falta tocar el `.env` cada vez que compras. Escríbele
`/compra bitcoin 0.01 600` y suma 0,01 a lo que tienes y 600 € a lo que te
costó. Si no pones el precio (`/compra solana 3`), lo apunta a lo que vale en
ese momento. Si prefieres poner a cuánto te salió cada una, como lo enseña el
exchange, va con `@`: `/compra bitcoin 0.01 @60000`.

`/venta bitcoin 0.005 350` lo resta, y lo que te costó baja en la misma
proporción: si vendes la mitad, se va la mitad de lo invertido. El último número
es lo que te dieron, o con `@` a cuánto cada una; sin él, se apunta al precio de
ahora. `/venta bitcoin todo` la saca de la cartera.

`/ganancias` suma lo que has sacado con cada venta, contando lo que te costó
esa parte al precio medio. Las ventas apuntadas antes de esto no guardaban el
precio, así que no entran.

Si te equivocas, cada respuesta lleva un **↩️ Deshacer** que la deja como
estaba. `/movimientos` te enseña las últimas que has apuntado, y `/deshacer`
quita la última (repítelo para ir más atrás).

Como con `/vigilar`, el `.env` es la base y lo de Telegram va encima. Si una
cripto la cambias por Telegram, deja de mirar lo que ponga de ella `PORTFOLIO`.

**Callar los avisos un rato:**
```
python main.py --mute 2h
```
No te avisa durante dos horas. Vale `30m`, `2h` o `1d`; sin letra se entienden
horas. También hasta una hora: `--mute "hasta 8:00"` (si ya ha pasado, la de
mañana). Sigue mirando y guardando precios, solo se calla.

Para volver antes de tiempo:
```
python main.py --unmute
```

El silencio se guarda, así que aguanta aunque reinicies o se apague el servidor.
Y `--status` te sigue funcionando: lo que se calla son los avisos automáticos, no
lo que pidas tú.

**Enterarte de los desplomes:**

```
MOVIMIENTO_BRUSCO=8%/1h
```
Te avisa si cualquiera de tus criptos sube o baja un 8% en menos de una hora,
aunque no cruce ninguno de sus niveles. Cuenta desde el punto más alto o más
bajo de esa hora, así que también pilla un "sube un 10% y lo devuelve todo".
Tras un aviso, solo vuelve a avisar si se mueve otro 8% desde ahí.

**Saber cuándo marca un máximo o un mínimo:**

```
MAXIMOS_MINIMOS=30d
```
Te avisa cuando una de tus criptos supera el precio más alto de los últimos 30
días, o baja del más bajo. Lo mira con los precios que ya tiene guardados, así
que no gasta consultas, pero necesita llevar esos 30 días funcionando: hasta
entonces no dice nada, para no llamar "máximo de 30 días" a algo de anteayer.
Avisa como mucho una vez al día de cada cosa, que en plena subida cada ciclo es
un máximo nuevo. Tiene que ser de 2 días o más, y no más de los que guarda
`HISTORY_DAYS`.

**Recibir un resumen cada mañana:**

Pon la hora en el `.env`:
```
RESUMEN_DIARIO=09:00
```
Mientras esté en modo `--loop`, te manda cada día a esa hora lo mismo que
`--status`. Si a esa hora estaba apagado, te lo manda al volver, pero solo hasta
dos horas tarde. Con `--mute` tampoco llega.

Desde Telegram puedes cambiar la hora con `/horario 8:30` o quitarlo con
`/horario no`, sin tocar el `.env`. Lo que pongas ahí manda sobre el `.env`.

Si además tienes `PORTFOLIO`, los domingos a esa misma hora te llega **tu
semana**: cuánto ha ganado o perdido la cartera en 7 días, cada cripto de la que
mejor ha ido a la que peor y la gráfica de la semana. Sale de los precios que ya
tiene guardados, así que no gasta consultas, pero necesita que el bot lleve
unos días en `--loop`. Con `/semana` lo pides cuando quieras.

**Que no te despierte:**
```
HORAS_TRANQUILAS=23-8
```
De 11 de la noche a 8 de la mañana los avisos llegan sin sonar ni vibrar. No
se pierde ninguno: por la mañana los tienes todos. Lo que le preguntes por
Telegram sí suena, que si escribes es que estás despierto.

**Ver el histórico de una cripto:**
```
python main.py --history bitcoin
```
Lista los últimos precios guardados y, debajo, un gráfico de una línea con la
forma que ha tenido, más el máximo, el mínimo, la media y cuánto ha variado.

La primera vez que lo lanzas no te avisa de nada, solo apunta los precios.
Necesita saber dónde estaban antes para saber si han cruzado algo.

---

## Dejarlo funcionando siempre en un servidor Windows

En la carpeta `windows/` está todo lo necesario. Si es la primera vez,
`INSTALAR-EN-EL-SERVIDOR.txt` lo explica paso a paso, desde copiar la carpeta.
Si ya lo tienes preparado:

**1. Haz clic derecho en `instalar-tarea.bat` → Ejecutar como administrador.**

Te pide tu contraseña de Windows dos veces, para poder arrancar aunque nadie
inicie sesión. Ya está: el bot arranca solo cada vez que se enciende el
servidor, y si por lo que sea se cierra, vuelve a arrancar en menos de 15
minutos. Si cambias la contraseña, vuelve a ejecutarlo.

**Para arrancarlo ahora mismo sin reiniciar**, abre una terminal como
administrador y escribe:
```
schtasks /run /tn "CryptoPriceTracker"
```

**Los otros archivos:**

- `estado.bat` — te dice si está funcionando y enseña lo último que hizo
- `quitar-tarea.bat` — lo desinstala (ejecutar como administrador)
- `iniciar.bat` — lo arranca a mano, no hace falta tocarlo
- `revisar.bat` — el vigía: la tarea lo lanza cada 15 minutos y vuelve a
  arrancar el bot si se ha caído. Tampoco hace falta tocarlo

Todo lo que va haciendo queda apuntado en `data/tracker.log`.

---

## Otras opciones del `.env`

| Opción | Qué hace | Por defecto |
|---|---|---|
| `COINGECKO_API_KEY` | Clave gratuita de CoinGecko (ver arriba) | vacío |
| `VS_CURRENCY` | Moneda de los precios (`usd`, `eur`, `gbp`) | `eur` |
| `CHECK_INTERVAL` | Segundos entre consulta y consulta | `330` (5 min y medio) |
| `HISTORY_DAYS` | Días de histórico que se guardan | `90` |
| `DATABASE_PATH` | Dónde se guardan los datos | `data/prices.db` |
| `RESUMEN_DIARIO` | Hora del resumen de cada día (`09:00`), que acaba con el índice de miedo y codicia. Vacío, sin resumen | vacío |
| `MOVIMIENTO_BRUSCO` | Aviso si se mueve mucho en poco tiempo (`8%/1h`). Vacío, sin aviso | vacío |
| `MAXIMOS_MINIMOS` | Aviso al marcar el máximo o mínimo de esos días (`30d`). Vacío, sin aviso | vacío |
| `HORAS_TRANQUILAS` | Tramo en que los avisos llegan sin sonar (`23-8`) | vacío |
| `PORTFOLIO` | Lo que tienes, para ver cuánto vale (`bitcoin:0.016:1000`) | vacío |

No bajes mucho `CHECK_INTERVAL`. La clave gratuita de CoinGecko da 10.000
consultas al mes y cada ciclo gasta una: con `330` (cinco minutos y medio) te
quedan unas 2.000 de margen para `/status`, el resumen y las búsquedas. Con
`300` vas muy justo.

Por si acaso, lleva la cuenta: al pasar del 80 % del mes te avisa, con cómo
acabarías a ese ritmo, y otra vez si llegas al 100 %. Cuenta por mes natural en
UTC, y `/consultas` te dice cómo vas.

---

## Si algo no va

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

**Me avisa demasiado**
El paso es muy pequeño. Con `bitcoin:100` te avisa continuamente; prueba con
`bitcoin:1000` o más. Con porcentajes, sube del `%2` al `%5`.

---

## Para desarrolladores

```
crypto_tracker/
  config.py      lee el .env
  coingecko.py   consulta los precios
  database.py    guarda el histórico
  telegram.py    manda los mensajes
  botones.py     los botones de debajo de los avisos
  alerts.py      decide cuándo avisar y escribe los avisos
  brusco.py      los movimientos bruscos
  extremos.py    los máximos y mínimos de los últimos días
  comparar.py    el ranking de /comparar
  correlacion.py si dos criptos se mueven juntas, para /correlacion
  ratio.py       lo que vale una cripto en otra, para /ratio
  convertir.py   entiende lo que le pides a /convertir
  exportar.py    el CSV de /exportar
  hubiera.py     entiende lo que le pides a /si
  objetivo.py    lo que valdría tu cartera, para /objetivo
  equilibrio.py  a qué precio dejas de perder, para /equilibrio
  doble.py       a qué precio doblas lo que metiste, para /doble
  callar.py      entiende /mute con una sola cripto
  dca.py         las compras periódicas de /dca
  maximo.py      el máximo histórico de /ath
  tendencias.py  lo que más se busca, para /tendencias
  aleatoria.py   una de las más grandes al azar, para /aleatoria
  caraocruz.py   la moneda al aire de /caraocruz
  frase.py       las frases famosas de /frase
  glosario.py    las palabras que explica /glosario
  mercado.py     el mercado entero, para /mercado
  halving.py     cuánto falta para el próximo halving, para /halving
  cumple.py      los años de Bitcoin, para /cumple
  whitepaper.py  los años del whitepaper, para /whitepaper
  merge.py       los años de The Merge de Ethereum, para /merge
  pizza.py       los 10.000 BTC de las pizzas, para /pizza
  millonario.py  lo que hace falta para un millón, para /millonario
  lambo.py       tu cartera en Lamborghinis, para /lambo
  cafe.py        tu cartera en cafés, para /cafe
  sueldo.py      tu cartera en salarios mínimos, para /sueldo
  gasolina.py    tu cartera en litros de gasolina, para /gasolina
  bigmac.py      tu cartera en Big Macs, para /bigmac
  sat.py         lo que vale un satoshi, para /sat
  puntuales.py   las alertas de /alerta
  vigiladas.py   lo que cambias con /vigilar
  volatilidad.py lo que se mueve cada día, para /volatilidad
  movimientos.py las compras y ventas de /compra y /venta
  ganancias.py   lo ganado con lo vendido, para /ganancias
  primera.py     tu primera compra, para /primera
  proximo.py     a qué precio salta el siguiente aviso
  cartera.py     cuánto vale lo que tienes
  grafica.py     las imágenes de /historico y /cartera
  media.py       las medias de 7, 30 y 90 días, para /media
  racha.py       los días seguidos subiendo o bajando, para /racha
  verdes.py      los días que sube y los que baja, para /verdes
  mejor.py       el mejor y el peor día, para /extremo
  diasemana.py   lo que cambia cada día de la semana, para /diasemana
  horas.py       la hora más barata y la más cara, para /horas
  reparto.py     qué parte de la cartera es cada una, para /reparto
  rango.py       el máximo, el mínimo y la media de /rango
  dia.py         a cuánto estaba un día concreto, para /dia
  cuando.py      la última vez que estuvo a un precio, para /cuando
  avisados.py    el último aviso de cada una, para /ultimo
  redondo.py     la siguiente cifra redonda, para /redondo
  rsi.py         el RSI de 14 días, para /rsi
  caida.py       lo que ha bajado desde el máximo, para /caida
  sube.py        lo que ha subido desde el mínimo, para /sube
  periodo.py     lee tramos como 7d
  moneda.py      la moneda que pides al final de /precio
  simbolos.py    btc, eth... a su id de CoinGecko
  diario.py      el resumen diario y las horas tranquilas
  hoy.py         cómo van desde las 00:00, para /hoy
  semanal.py     el resumen de la semana de la cartera
  salud.py       avisa si el bot deja de funcionar
  copia.py       lo de ahora escrito como va en el .env, para /copia
  ajustes.py     lo que tienes puesto en el .env, para /ajustes
  cuota.py       cuenta las consultas a CoinGecko
  comandos.py    entiende lo que le escribes
main.py          junta todo
tests/           los tests
windows/         para dejarlo corriendo en un servidor
```

Pasar los tests y el linter (instala las versiones fijadas en `pyproject.toml`):
```
pip install -e ".[dev]"
pytest
ruff check .
```

Hecho con Python, SQLite, matplotlib, la API de CoinGecko y la de Telegram.

Price data by [CoinGecko](https://www.coingecko.com).

MIT
