# Utiliser l'image Python 3.13 basée sur Debian Slim
FROM python:3.13-slim

# Définir le répertoire de travail dans le conteneur
WORKDIR /app

# Installer les dépendances système nécessaires pour compiler 
# certaines bibliothèques Python (C/C++, et libyaml) sur Debian/Slim
# build-essential inclut gcc, make, etc.
# python3-dev contient les en-têtes Python
# libyaml-dev est nécessaire pour compiler PyYAML
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libyaml-dev \
    && rm -rf /var/lib/apt/lists/*
    # Note: Rust/Cargo ne sont plus installés par défaut, 
    # car les images Slim ont souvent plus de wheels pré-compilées.
    # Ajoutez 'rustc cargo' si une dépendance les requiert toujours.

# Mettre à jour pip
RUN pip install --upgrade pip

# Copier d'abord le fichier des dépendances pour profiter du cache Docker
COPY requirements.txt requirements.txt

# Installer les dépendances Python
# --no-cache-dir peut réduire la taille de l'image pip
RUN pip install --no-cache-dir -r requirements.txt

# Copier le reste du code de l'application dans le répertoire de travail
COPY . .

# Exposer le port sur lequel Uvicorn va écouter à l'intérieur du conteneur
EXPOSE 8000

# Commande pour lancer l'application lorsque le conteneur démarre
# Utilise l'hôte 0.0.0.0 pour être accessible depuis l'extérieur du conteneur
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"] 