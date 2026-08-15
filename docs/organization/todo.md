# TODO List Globale — Hub_Alex

Ce fichier liste les tâches d'implémentation et d'organisation du projet.

---

## 🚀 Phase 0 : Fondations (En cours)
- [x] Initialiser le dépôt Git et lier le dépôt GitHub (`alexflorentin-code/Hub_Alex`)
- [x] Configurer la clé SSH dédiée pour le compte personnel
- [x] Rédiger la documentation technique (architecture, spécifications techniques)
- [ ] Créer les fichiers de règles locales et d'organisation (En cours)
- [ ] Créer le code de base de `projects/hub_engine` (FastAPI + SQLite)
- [ ] Configurer Docker Compose et l'instance n8n locale

---

## 📈 Phase 1 : Agents de Veille & Newsletters (En cours)
- [x] Configurer le flux RSS de veille IA dans `projects/hub_engine`
- [x] Écrire l'agent de veille IA sous PydanticAI (rapports Telegram et Newsletter Email)
- [x] Déployer l'agent de veille Parapente (FSVL, sorties matériel, sécurité, XC)
- [ ] Mettre en place la table de veille dans SQLite et l'indexation ChromaDB
- [ ] Créer le rapport quotidien à 7h30 sur Telegram

---

## 📅 Phase 2 : Calendriers (À faire)
- [ ] Authentification Google Calendar et Microsoft Outlook Calendar dans n8n
- [ ] Créer le script de fusion d'agenda et détection de conflits
- [ ] Rédiger le briefing d'agenda quotidien
