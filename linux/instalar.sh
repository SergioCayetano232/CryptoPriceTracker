#!/usr/bin/env bash
# Deja el bot como servicio de systemd: arranca con el servidor y se levanta solo.
# Uso: bash linux/instalar.sh            (pide sudo para lo de systemd)
#      bash linux/instalar.sh --mostrar  (solo enseña el servicio, no toca nada)
set -euo pipefail

SERVICIO=cryptopricetracker
CARPETA="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
USUARIO="$(id -un)"

# El | de sed se rompería con una carpeta que lo lleve, mejor avisar que instalar mal.
if [[ "$CARPETA" == *"|"* || "$CARPETA" == *" "* ]]; then
    echo "La carpeta no puede tener espacios ni '|': $CARPETA" >&2
    echo "Muévela a algo como /home/$USUARIO/CryptoPriceTracker" >&2
    exit 1
fi

servicio() {
    sed -e "s|__USUARIO__|$USUARIO|g" -e "s|__CARPETA__|$CARPETA|g" \
        "$CARPETA/linux/$SERVICIO.service"
}

if [[ "${1:-}" == "--mostrar" ]]; then
    servicio
    exit 0
fi

if [[ "$USUARIO" == "root" ]]; then
    echo "Lánzalo con tu usuario normal, no como root: pediré sudo cuando haga falta." >&2
    exit 1
fi

cd "$CARPETA"

if ! python3 -c 'import sys; sys.exit(sys.version_info < (3, 10))' 2>/dev/null; then
    echo "Hace falta Python 3.10 o superior. En Debian/Ubuntu:" >&2
    echo "    sudo apt install python3 python3-venv" >&2
    exit 1
fi

if [[ ! -f .env ]]; then
    echo "Falta el archivo .env con el token de Telegram." >&2
    echo "    cp .env.example .env   y rellénalo" >&2
    exit 1
fi

if [[ ! -x .venv/bin/python ]]; then
    echo "Preparando el entorno (tarda un minuto)..."
    # Si .venv viene copiado de otro ordenador no vale: se rehace.
    rm -rf .venv
    python3 -m venv .venv
fi
.venv/bin/pip install --quiet -r requirements.txt
mkdir -p data

echo "Probando que Telegram contesta..."
if ! .venv/bin/python main.py --test; then
    echo "No ha llegado el mensaje de prueba. Revisa el token y el chat id del .env." >&2
    exit 1
fi

servicio | sudo tee "/etc/systemd/system/$SERVICIO.service" >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable --now "$SERVICIO"

echo
echo "Listo. El bot ya está vigilando y arrancará solo con el servidor."
echo "  Cómo va:        systemctl status $SERVICIO"
echo "  Ver los logs:   journalctl -u $SERVICIO -f"
echo "  Reiniciarlo:    sudo systemctl restart $SERVICIO   (tras cambiar el .env)"
echo "  Quitarlo:       bash linux/quitar.sh"
