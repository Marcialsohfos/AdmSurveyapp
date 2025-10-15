FROM python:3.11-slim

# Installation des dépendances système
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-fra \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/* \
    && tesseract --version

WORKDIR /app

# Copie et installation des dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie de l'application
COPY . .

# Création des dossiers
RUN mkdir -p uploads converted static

# Exposition du port
EXPOSE 10000

# Commande de démarrage avec variable d'environnement
CMD gunicorn app:app --bind 0.0.0.0:${PORT:-10000} --timeout 120 --access-logfile -
