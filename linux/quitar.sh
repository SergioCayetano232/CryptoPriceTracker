#!/usr/bin/env bash
# Para el bot y quita el servicio. La carpeta, el .env y los precios se quedan.
set -euo pipefail

SERVICIO=cryptopricetracker

sudo systemctl disable --now "$SERVICIO" 2>/dev/null || true
sudo rm -f "/etc/systemd/system/$SERVICIO.service"
sudo systemctl daemon-reload

echo "Servicio quitado. Para volver a ponerlo: bash linux/instalar.sh"
