import os
from app.core.config import settings

def load_markdown_file(filename: str) -> str:
    """Charge le contenu d'un fichier Markdown de la mémoire froide."""
    # Le chemin est résolu par rapport à settings.DOCS_DIR
    path = os.path.abspath(os.path.join(settings.DOCS_DIR, filename))
    if not os.path.exists(path):
        return f"[Fichier non trouvé : {filename}]"
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"[Erreur lors de la lecture de {filename} : {str(e)}]"

def get_global_agent_context() -> str:
    """Compile le contexte global (préférences utilisateur et breakthroughs)."""
    preferences = load_markdown_file("memory/preferences.md")
    breakthroughs = load_markdown_file("memory/breakthroughs.md")
    
    context = (
        "=== CONTEXTE GLOBAL UTILISATEUR ===\n"
        f"{preferences}\n\n"
        "=== DERNIÈRES RÉSOLUTIONS DE BUGS (A LIRE POUR ÉVITER DE REPRODUIRE) ===\n"
        f"{breakthroughs}\n"
    )
    return context
