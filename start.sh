#!/bin/bash

# Script de démarrage pour Hub_Alex

# 1. Vérification du fichier .env
if [ ! -f .env ]; then
    echo "⚠️ Le fichier .env n'existe pas."
    echo "📁 Copie de .env.example vers .env..."
    cp .env.example .env
    echo "📝 Veuillez configurer vos clés API et secrets dans le fichier .env avant de relancer."
    exit 1
fi

# 2. Lancement des conteneurs
echo "🚀 Lancement de Hub_Alex (FastAPI + n8n)..."
docker compose up --build
