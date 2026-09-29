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

**Puedes mezclar y poner varias separadas por comas:**
```
WATCHLIST=bitcoin:%5,ethereum:100,solana:5
```

Los nombres son los de CoinGecko: `bitcoin`, no `BTC`. Si no sabes cuál es,
búscalo en [coingecko.com](https://www.coingecko.com) y mira la dirección de la
página: `coingecko.com/en/coins/`**`bitcoin`**.

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

**Manejarlo desde Telegram:**

Mientras está en modo `--loop` puedes escribirle al bot desde el móvil:

| Comando | Qué hace |
|---|---|
| `/status` | Cómo van tus criptos ahora |
| `/historico bitcoin` | Gráfica y máximo/mínimo de las últimas 24 h |
| `/mute 2h` | Calla los avisos un rato |
| `/unmute` | Vuelve a avisar |
| `/ayuda` | La lista de comandos |

Al escribir `/` en el chat te salen solos. Solo contesta a tu chat id, y si
estaba apagado, al volver ignora lo que le escribiste hace más de 10 minutos.

**Ver cómo van ahora mismo:**
```
python main.py --status
```
Te manda a Telegram un resumen con el precio de todo lo que vigilas y cuánto ha
cambiado en las últimas 24 horas. Si acabas de instalarlo no hay con qué
comparar, así que pone "sin histórico" hasta que lleve un día funcionando.

**Ver cuánto vale lo que tienes:**
```
PORTFOLIO=bitcoin:0.016:1000,ethereum:0.4:1000
```
Cada una es `cripto:cantidad:lo que te costó`. La cantidad es la que te sale en
el exchange; lo que te costó es opcional, pero sin eso no sabe si ganas o
pierdes. El resumen (`--status`, `/status` y el diario) añade al final lo que
vale cada una, el total y cuánto llevas ganado o perdido.

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

**Recibir un resumen cada mañana:**

Pon la hora en el `.env`:
```
RESUMEN_DIARIO=09:00
```
Mientras esté en modo `--loop`, te manda cada día a esa hora lo mismo que
`--status`. Si a esa hora estaba apagado, te lo manda al volver, pero solo hasta
dos horas tarde. Con `--mute` tampoco llega.

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

En la carpeta `windows/` hay cuatro archivos:

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

Todo lo que va haciendo queda apuntado en `data/tracker.log`.

---

## Otras opciones del `.env`

| Opción | Qué hace | Por defecto |
|---|---|---|
| `VS_CURRENCY` | Moneda de los precios (`usd`, `eur`, `gbp`) | `eur` |
| `CHECK_INTERVAL` | Segundos entre consulta y consulta | `300` (5 min) |
| `HISTORY_DAYS` | Días de histórico que se guardan | `90` |
| `DATABASE_PATH` | Dónde se guardan los datos | `data/prices.db` |
| `RESUMEN_DIARIO` | Hora del resumen de cada día (`09:00`). Vacío, sin resumen | vacío |
| `MOVIMIENTO_BRUSCO` | Aviso si se mueve mucho en poco tiempo (`8%/1h`). Vacío, sin aviso | vacío |
| `HORAS_TRANQUILAS` | Tramo en que los avisos llegan sin sonar (`23-8`) | vacío |
| `PORTFOLIO` | Lo que tienes, para ver cuánto vale (`bitcoin:0.016:1000`) | vacío |

No bajes mucho `CHECK_INTERVAL`: CoinGecko es gratis pero corta si le pides
demasiado seguido. Cinco minutos va bien.

---

## Si algo no va

**No me llega ningún mensaje**
Lanza `python main.py --test`. Si tampoco llega, es el token o el chat id. Y
asegúrate de haberle escrito `/start` al bot.

**Dice que no encuentra una cripto**
El nombre no es el correcto. Búscalo en coingecko.com y usa el que aparece en la
dirección de la página.

**Sale un error 429**
Le estás pidiendo precios demasiado rápido. Lo reintenta solo un par de veces,
así que si aparece de vez en cuando puedes ignorarlo. Si sale continuamente,
sube `CHECK_INTERVAL`.

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
  alerts.py      decide cuándo avisar
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

Hecho con Python, SQLite, la API de CoinGecko y la de Telegram.

MIT
