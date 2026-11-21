# slim vale: matplotlib trae sus ruedas y no hay nada que compilar.
FROM python:3.13-slim

WORKDIR /app

# Las dependencias antes que el código: si solo cambias el código, esta capa
# sale de la caché y no se reinstala todo.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY crypto_tracker/ crypto_tracker/
# pyproject.toml, para que /version sepa cuál es.
COPY main.py pyproject.toml ./

# Sin root. data/ ya es suya para que el volumen nazca con el dueño bueno.
RUN useradd --create-home --uid 1000 bot && mkdir data && chown bot data
USER bot

ENV PYTHONUNBUFFERED=1

# docker stop manda SIGTERM y lo cortaría a medias; con esto es como un Ctrl+C.
STOPSIGNAL SIGINT
CMD ["python", "main.py", "--loop"]
