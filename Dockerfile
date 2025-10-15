# Utilise une image Python officielle légère
FROM python:3.11-slim

# Met à jour et installe les dépendances système + Tesseract + Français
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-fra \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Définit le répertoire de travail dans le conteneur
WORKDIR /app

# Copie les requirements d'abord (optimisation du cache Docker)
COPY requirements.txt .

# Installe les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copie tout le code de l'application
COPY . .

# Crée les dossiers nécessaires
RUN mkdir -p uploads converted static

# Expose le port (Render utilise le port 10000)
EXPOSE 10000

# Commande pour démarrer l'application
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:10000", "--timeout", "120"]
