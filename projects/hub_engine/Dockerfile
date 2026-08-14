FROM python:3.11-slim

# Empêche Python de mettre en mémoire tampon les sorties (logs immédiats dans Cloud Logging)
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Dépendances système minimales
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cloud Run injecte automatiquement la variable d'environnement PORT (par défaut 8080)
ENV PORT=8000
EXPOSE 8000

# Démarrage optimisé avec support dynamique de $PORT
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
