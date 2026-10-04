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
+4.17%`), para saber si viene de un subidón o es ruido.

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
Se queda mirando los precios cada 5 minutos. Para pararlo, `Ctrl+C`.

Si pasa media hora sin poder consultar los precios, te avisa por Telegram, y
otra vez cuando vuelve a funcionar. Si se para por errores, también te lo dice.
Y si una cripto de `WATCHLIST` no existe en CoinGecko (un `bitcion`), te avisa
una vez al arrancar para que no te quedes esperando un aviso que nunca llegará.

**Manejarlo desde Telegram:**

Mientras está en modo `--loop` puedes escribirle al bot desde el móvil:

| Comando | Qué hace |
|---|---|
| `/status` | Cómo van tus criptos ahora |
| `/precio solana` | Lo que vale una cripto ahora y cómo va en 24 h, aunque no la vigiles |
| `/cartera` | Tu cartera: cuánto vale, cuánto ganas o pierdes y la gráfica de 7 días |
| `/cartera 30d` | Lo mismo, con la gráfica del tramo que digas |
| `/compra bitcoin 0.01 600` | Apunta en la cartera que has comprado 0,01 por 600 € |
| `/venta bitcoin 0.005` | Apunta una venta (`/venta bitcoin todo` la saca de la cartera) |
| `/alerta bitcoin 70000` | Te avisa una vez cuando llegue a ese precio |
| `/alerta bitcoin +10%` | Te avisa una vez cuando suba un 10% desde ahora |
| `/alerta cartera 5000` | Lo mismo con lo que vale tu cartera entera (también `-10%`) |
| `/alertas` | Las alertas que tienes puestas y cuánto le falta a cada una |
| `/quitar 3` | Quita la alerta número 3 (`/quitar todas` las quita todas) |
| `/vigilar` | Lo que está vigilando y cómo |
| `/vigilar solana %5` | Añade una cripto, o cambia cómo vigila una que ya estaba |
| `/dejar solana` | Deja de vigilarla |
| `/historico bitcoin` | Imagen con la gráfica de las últimas 24 h, máximo y mínimo |
| `/historico bitcoin 7d` | Lo mismo, del tramo que digas (`12h`, `7d`, `30d`...) |
| `/convertir 0.05 bitcoin` | Cuánto es en euros al precio de ahora |
| `/convertir 500 eur solana` | Al revés: cuánta solana compras con 500 € (vale `500€`) |
| `/exportar bitcoin 30d` | Te manda un CSV con los precios guardados (sin tramo, 30 días) |
| `/buscar btc` | Encuentra el id de CoinGecko de una cripto |
| `/consultas` | Cuántas consultas a CoinGecko llevas este mes |
| `/bot` | Si sigue funcionando: desde cuándo está encendido y cuándo fue el último ciclo |
| `/mute 2h` | Calla los avisos un rato |
| `/unmute` | Vuelve a avisar |
| `/ayuda` | La lista de comandos |

Al escribir `/` en el chat te salen solos. Solo contesta a tu chat id, y si
estaba apagado, al volver ignora lo que le escribiste hace más de 10 minutos.

**Botones en los avisos:**

Cada aviso lleva debajo unos botones para reaccionar de un toque:

- **📈 Gráfica**: la de las últimas 24 h, como `/historico`.
- **🎯 Si vuelve a 64.000**: te avisa una vez si vuelve al precio que acaba de
  cruzar, como `/alerta`.
- **🔕 Callar 1 h**: como `/mute 1h`.

Si en un mensaje vienen varias criptos, salen los botones de las tres primeras.

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
vale cada una, el total y cuánto llevas ganado o perdido. Debajo de cada una
te pone a cuánto te salió de media y a cuánto está ahora (`Te salió a
€62.500,00 · ahora €76.258,00`). Si solo quieres eso, escríbele `/cartera`.

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

**Apuntar compras y ventas desde el móvil:**

No hace falta tocar el `.env` cada vez que compras. Escríbele
`/compra bitcoin 0.01 600` y suma 0,01 a lo que tienes y 600 € a lo que te
costó. Si no pones el precio (`/compra solana 3`), lo apunta a lo que vale en
ese momento.

`/venta bitcoin 0.005` lo resta, y lo que te costó baja en la misma proporción:
si vendes la mitad, se va la mitad de lo invertido. `/venta bitcoin todo` la
saca de la cartera.

Como con `/vigilar`, el `.env` es la base y lo de Telegram va encima. Si una
cripto la cambias por Telegram, deja de mirar lo que ponga de ella `PORTFOLIO`.

**Callar los avisos un rato:**
```
python main.py --mute 2h
```
No te avisa durante dos horas. Vale `30m`, `2h` o `1d`; sin letra se entienden
horas. Sigue mirando y guardando precios, solo se calla.

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

Si además tienes `PORTFOLIO`, los domingos a esa misma hora te llega **tu
semana**: cuánto ha ganado o perdido la cartera en 7 días, cada cripto de la que
mejor ha ido a la que peor y la gráfica de la semana. Sale de los precios que ya
tiene guardados, así que no gasta consultas, pero necesita que el bot lleve
unos días en `--loop`.

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
| `CHECK_INTERVAL` | Segundos entre consulta y consulta | `300` (5 min) |
| `HISTORY_DAYS` | Días de histórico que se guardan | `90` |
| `DATABASE_PATH` | Dónde se guardan los datos | `data/prices.db` |
| `RESUMEN_DIARIO` | Hora del resumen de cada día (`09:00`). Vacío, sin resumen | vacío |
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
  convertir.py   entiende lo que le pides a /convertir
  exportar.py    el CSV de /exportar
  puntuales.py   las alertas de /alerta
  vigiladas.py   lo que cambias con /vigilar
  movimientos.py las compras y ventas de /compra y /venta
  proximo.py     a qué precio salta el siguiente aviso
  cartera.py     cuánto vale lo que tienes
  grafica.py     las imágenes de /historico y /cartera
  periodo.py     lee tramos como 7d
  diario.py      el resumen diario y las horas tranquilas
  semanal.py     el resumen de la semana de la cartera
  salud.py       avisa si el bot deja de funcionar
  cuota.py       cuenta las consultas a CoinGecko
  comandos.py    entiende lo que le escribes
main.py          junta todo
tests/           los tests
windows/         para dejarlo corriendo en un servidor
```

Pasar los tests y el linter:
```
pip install pytest ruff
pytest
ruff check .
```

Hecho con Python, SQLite, matplotlib, la API de CoinGecko y la de Telegram.

Price data by [CoinGecko](https://www.coingecko.com).

MIT
