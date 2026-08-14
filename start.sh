#!/bin/bash

# Script de démarrage local pour Hub_Alex (FastAPI + PydanticAI)

# 1. Vérification du fichier .env
if [ ! -f .env ]; then
    echo "⚠️ Le fichier .env n'existe pas."
    echo "📁 Copie de .env.example vers .env..."
    cp .env.example .env
    echo "📝 Veuillez configurer vos clés API dans le fichier .env avant de relancer."
    exit 1
fi

# 2. Lancement du conteneur en local
echo "🚀 Lancement de Hub_Alex Engine..."
docker compose up -d --build

echo "✅ Hub_Alex est opérationnel :"
echo "👉 Interface Web : http://localhost:8000 (Login: alex / Mot de passe: voir .env)"
echo "👉 Lancer les tests : docker exec -e PYTHONPATH=/app hub_engine pytest"
