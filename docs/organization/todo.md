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

## 📈 Phase 1 : Agents de Veille, Météo & Newsletters
- [x] Configurer le flux RSS de veille IA dans `projects/hub_engine`
- [x] Écrire l'agent de veille IA sous PydanticAI (rapports Telegram et Newsletter Email)
- [x] Déployer l'agent de veille Parapente (FSVL, sorties matériel, sécurité, XC)
- [x] Déployer l'agent Météo Parapente & Aérologie (7 jours, Foehn, arbitrage Jura vs Valais, Val d'Illiez)
- [x] Configurer l'envoi automatique des Newsletters par E-mail (Gmail API / App Password)
- [x] Configurer les déclencheurs Google Cloud Scheduler (Lundi 8h/14h, Jeudi 8h, Vendredi 8h)
- [x] Résoudre les timeouts du Webhook Telegram via BackgroundTasks asynchrones et déduplication d'update_id
- [x] Ajouter les outils d'administration et de purge de la file Telegram (`/api/v1/telegram/webhook-info` et `/api/v1/telegram/flush`)
- [ ] Mettre en place l'indexation vectorielle ChromaDB
- [ ] Créer le rapport quotidien à 7h00 sur Telegram
- [x] Rédiger le guide d'organisation Gmail & Inbox Zero ([guide](file:///Users/alexandreflorentin/Documents/Git/Hub_Alex/docs/process_guides/gmail_inbox_zero.md))
- [x] Créer les libellés Gmail clés (`0. @Action`, `1. @Attente`, `2. @Lecture`, `3. @Administratif`, `4. @Emploi & Réseau`, `5. @Hub_Alex`, `6. @Finance & Investissement`)
- [x] Appliquer rétroactivement les filtres thématiques (Finance, Emploi, Parapente, Promos, IncaMail)
- [x] Archiver les e-mails de l'INBOX antérieurs à 2025 (Inbox Zero opérationnel)

---

## 📅 Phase 2 : Calendriers (À faire)
- [ ] Authentification Google Calendar et Microsoft Outlook Calendar dans n8n
- [ ] Créer le script de fusion d'agenda et détection de conflits
- [ ] Rédiger le briefing d'agenda quotidien
