# CryptoPriceTracker

Te avisa por Telegram cuando una cripto cruza un precio. Los datos los saca de CoinGecko y guarda el histórico en SQLite.

## Instalar

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## El bot de Telegram

Habla con **@BotFather**, mándale `/newbot` y te da un token. Luego **@userinfobot** te dice tu chat_id.

Importante: escríbele `/start` a tu bot o no podrá mandarte nada.

## Configurar

```bash
cp .env.example .env
```

Rellena el token y el chat_id. La watchlist va así:

```
WATCHLIST=bitcoin:1000,ethereum:100,solana:5
```

Eso avisa cuando Bitcoin cruza un múltiplo de 1000 (63000, 64000...), Ethereum de 100 y Solana de 5. También se puede poner un rango fijo con `bitcoin:55000:75000`.

Los ids son los de CoinGecko: `bitcoin`, no `BTC`.

## Usar

```bash
python main.py --test    
python main.py           
python main.py --loop    
```

La primera vez solo anota los precios, no avisa. Necesita una consulta previa para saber si algo ha cruzado.

## Cómo está montado

```
crypto_tracker/
  config.py      el .env
  coingecko.py   la API
  database.py    SQLite
  telegram.py    los mensajes
  alerts.py      cuándo avisar
main.py
```

Cada cosa en su archivo. `alerts.py` guarda el último nivel del que avisó, así no manda el mismo mensaje una y otra vez.

Si se cae la API o no hay internet lo apunta en el log y sigue.

## Hecho con

Python 3, sqlite3, requests, python-dotenv, CoinGecko y la API de Telegram.

MIT
