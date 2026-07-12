# Utilise une image de base Python légère
FROM python:3.10-slim

# Empêche Python d'écrire des fichiers .pyc et de mettre en mémoire tampon stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Définit le répertoire de travail dans le conteneur
WORKDIR /app

# Installe les dépendances système requises
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copie les fichiers de dépendances et les installe
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Télécharge le modèle d'embeddings au moment du build (évite les erreurs réseau au runtime)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')"

# Copie le reste de l'application
COPY . /app/

# Expose le port par défaut
EXPOSE 5000

# Commande pour démarrer l'application
CMD ["python", "main.py"]
