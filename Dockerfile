# Utiliser l'image Python 3.13 basée sur Alpine
FROM python:3.13-alpine

# Définir le répertoire de travail dans le conteneur
WORKDIR /app

# Installer les dépendances système nécessaires pour compiler 
# certaines bibliothèques Python (C/C++, Rust, et libyaml)
# Utiliser --no-cache pour réduire la taille de l'image en ne gardant pas le cache apk
RUN apk add --no-cache \
    build-base \
    python3-dev \
    gcc \
    libc-dev \
    linux-headers \
    rust \
    cargo \
    libyaml-dev 
    # Ajoutez d'autres dépendances apk si nécessaire pour votre projet (ex: postgresql-dev, libffi-dev)

# Mettre à jour pip
RUN pip install --upgrade pip

# Copier d'abord le fichier des dépendances pour profiter du cache Docker
COPY requirements.txt requirements.txt

# Installer les dépendances Python
# --no-cache-dir peut réduire la taille de l'image pip
# PyYAML nécessite maintenant libyaml-dev qui a été installé ci-dessus
RUN pip install --no-cache-dir -r requirements.txt

# Copier le reste du code de l'application dans le répertoire de travail
COPY . .

# Exposer le port sur lequel Uvicorn va écouter à l'intérieur du conteneur
EXPOSE 8000

# Commande pour lancer l'application lorsque le conteneur démarre
# Utilise l'hôte 0.0.0.0 pour être accessible depuis l'extérieur du conteneur
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]