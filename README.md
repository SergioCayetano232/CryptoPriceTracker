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

**Ver cómo van ahora mismo:**
```
python main.py --status
```
Te manda a Telegram un resumen con el precio de todo lo que vigilas y cuánto ha
cambiado en las últimas 24 horas. Si acabas de instalarlo no hay con qué
comparar, así que pone "sin histórico" hasta que lleve un día funcionando.

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

Ya está. El bot arranca solo cada vez que se enciende el servidor, y si por lo
que sea se cierra, vuelve a arrancar en menos de 15 minutos.

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
| `VS_CURRENCY` | Moneda de los precios (`usd`, `eur`, `gbp`) | `usd` |
| `CHECK_INTERVAL` | Segundos entre consulta y consulta | `300` (5 min) |
| `HISTORY_DAYS` | Días de histórico que se guardan | `90` |
| `DATABASE_PATH` | Dónde se guardan los datos | `data/prices.db` |

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
