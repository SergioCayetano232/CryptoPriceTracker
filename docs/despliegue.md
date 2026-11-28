# Dejarlo funcionando

[← Volver al README](../README.md)

## Dejarlo funcionando con Docker

Si tienes Docker, no hace falta instalar Python ni preparar nada más. Con el
`.env` ya rellenado (ver [la configuración](configuracion.md#configuración)):

```
docker compose up -d --build
```

Ya está: arranca solo cada vez que se enciende el ordenador y, si se cae,
vuelve a arrancar. El histórico se guarda en un volumen de Docker, así que no se
pierde al actualizar ni al borrar el contenedor.

| Para | Escribe |
|---|---|
| Ver lo que va haciendo | `docker compose logs -f` |
| Mandar el mensaje de prueba | `docker compose run --rm bot python main.py --test` |
| Actualizar tras bajar cambios | `docker compose up -d --build` |
| Pararlo | `docker compose down` |
| Sacar una copia de la base de datos | `docker compose cp bot:/app/data/prices.db ./copia.db` |

**La hora** va por la zona de Madrid. Si estás en otra, añade al `.env` algo
como `TZ=America/Mexico_City`; si no, el resumen del día te llegaría a otra hora.

**Si ya tenías el bot funcionando sin Docker** y quieres conservar el histórico,
con el contenedor parado:
```
docker compose run --rm -v "$PWD/data:/viejo" bot cp /viejo/prices.db /app/data/prices.db
```

`DATABASE_PATH` del `.env` no cuenta aquí: dentro de Docker la base de datos va
siempre en el volumen.

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

## Dejarlo funcionando siempre en un servidor Linux

Vale para cualquier VPS con systemd (Ubuntu, Debian, Fedora...). Copia la
carpeta al servidor **sin** `.venv`, que está hecha para el otro ordenador, y
**con** el `.env` (es un archivo oculto, a veces no se copia solo). Luego, desde
la carpeta y con tu usuario normal, no como root:

```
bash linux/instalar.sh
```

Prepara el entorno, te manda el mensaje de prueba y, si llega, deja el bot como
servicio: arranca solo al encender el servidor y, si se cae, vuelve a los 30
segundos. Te pide la contraseña de `sudo` para lo de systemd. Si quieres ver
antes lo que va a instalar, `bash linux/instalar.sh --mostrar`.

| Para | Escribe |
|---|---|
| Ver si está funcionando | `systemctl status cryptopricetracker` |
| Ver lo que va haciendo | `journalctl -u cryptopricetracker -f` |
| Reiniciarlo tras cambiar el `.env` | `sudo systemctl restart cryptopricetracker` |
| Quitarlo | `bash linux/quitar.sh` |

Los logs van al registro del sistema (`journalctl`), no a `data/tracker.log`.

**El panel desde tu ordenador:** el panel solo escucha en el propio servidor.
Lánzalo allí con `.venv/bin/python main.py --panel` y, en tu ordenador, abre un
túnel:
```
ssh -L 8000:127.0.0.1:8000 tu-usuario@tu-servidor
```
Con el túnel abierto, entra en <http://127.0.0.1:8000>. Nadie más puede verlo.
