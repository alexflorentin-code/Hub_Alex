# Guide d'Utilisation & Bonnes Pratiques — Gmail & Hub_Alex

Ce document est votre guide de référence pour maintenir votre boîte de réception saine, exploiter les automatisations du Hub et corriger facilement les éventuelles erreurs de classement.

---

## 1. Vue d'Ensemble du Système Installé

### A. Structure des 7 Libellés Cibles

| Libellé | Rôle & Contenu | Comportement automatique |
| :--- | :--- | :--- |
| **`0. @Action`** | E-mails prioritaires exigeant une réponse ou une tâche de votre part (> 2 min). | Manuel (attribué par vous ou l'Agent IA). |
| **`1. @Attente`** | Suivis en cours, devis envoyés, réponses attendues d'un tiers. | Manuel. |
| **`6. @Finance & Investissement`** | SwissBorg, October, VIAC, Binance, Kraken, Coinbase, Revolut, banques. | Automatique + Archivé de l'INBOX. |
| **`4. @Emploi & Réseau`** | Jobup.ch, alertes LinkedIn, recruteurs, candidatures, cabinets RH. | Automatique + Archivé de l'INBOX. |
| **`Personnel/Parapente`** | FFVL, FSVL, Ozone, Advance, Niviuk, carnets de vol, sécurité et météo aérologique. | Automatique + Archivé de l'INBOX. |
| **`5. @Hub_Alex`** | Newsletters IA, bulletins météo et synthèses générées par votre Hub. | Automatique (reste visible dans l'INBOX). |
| **`2. @Lecture`** | Promotions, IKEA, e-commerce, actualités générales et lectures de fond. | Automatique + Archivé de l'INBOX. |
| **`3. @Administratif`** | Factures, reçus fiscaux, confirmations de commande, abonnements. | Automatique + Archivé de l'INBOX. |
| **`Personnel/IncaMail`** | Courriers sécurisés IncaMail et archives officielles LVA. | Automatique + Archivé de l'INBOX. |
| **`9. @À Supprimer`** | E-mails polluants obsolètes (promos < 2025, vieux réseaux sociaux, logs noreply) prêts pour suppression manuelle. | Regroupement sécurisé sans suppression définitive. |

---

## 2. Bonnes Pratiques au Quotidien (Workflow en 3 Minutes)

### Règle d'or : "L'INBOX est une boîte de passage, pas de stockage"
Votre boîte de réception ne doit contenir que ce qui est récent et non traité.

1. **Chaque matin (07h00 - 08h00)** :
   * Consultez la synthèse matinale sur **Telegram** ou envoyez **`/emails`** à votre bot.
   * Ouvrez Gmail en vue **"Non lus d'abord"** (*Paramètres ⚙️ > Configuration rapide > Type de boîte : Non lus d'abord*).
2. **Appliquez la règle des 4D à chaque ouverture** :
   * **Delete / Archiver (`e`)** : Si le message est informatif et ne demande rien ➔ archivez immédiatement.
   * **Do (< 2 min)** : Si la réponse prend moins de 2 minutes ➔ répondez tout de suite.
   * **Delegate / Attente (`v` ➔ `1. @Attente`)** : Si vous attendez un retour suite à votre envoi.
   * **Defer / Action (`v` ➔ `0. @Action`)** : Si la tâche demande du temps, déplacez-la dans `@Action` pour la traiter dans un bloc dédié.

### Raccourcis Clavier Gmail indispensables
*(À activer dans Paramètres ⚙️ > Général > Raccourcis clavier)* :
* **`e`** : **Archiver** (retire l'e-mail de l'INBOX sans le supprimer).
* **`v`** : **Déplacer / Appliquer un libellé** (tapez ensuite le début du nom du libellé).
* **`#`** : **Supprimer** (mise à la corbeille).
* **`gi`** : **Retourner à la boîte de réception**.

---

## 3. Que faire si un e-mail est à un endroit qui ne convient pas ?

### Cas 1 : Correction ponctuelle d'un e-mail (1 clic)
* **Si un e-mail important a été archivé par erreur** :
  1. Retrouvez-le dans son libellé ou via la recherche.
  2. Cliquez sur l'icône **"Déplacer vers la boîte de réception"** (ou tapez le raccourci **`v`** et sélectionnez `0. @Action`).
  3. Décochez le libellé indésirable en cliquant sur la petite croix `x` à côté de son nom.
* **Si une pub/newsletter atterrit dans l'INBOX** :
  1. Glissez-déposez le message dans le libellé approprié dans la colonne de gauche (`2. @Lecture` ou `6. @Finance`).
  2. Ou appuyez sur **`v`** puis tapez le libellé.

### Cas 2 : Correction durable d'une règle (Pour les futurs e-mails)
Si vous constatez qu'un expéditeur régulier est systématiquement mal classé :
* **Option A (Via Gmail en 2 clics)** :
  1. Ouvrez l'e-mail en question.
  2. Cliquez sur les **3 petits points verticaux** (à droite du message) > **"Filtrer les messages similaires"**.
  3. Cliquez sur **Créer un filtre** et choisissez l'action désirée (ex: *Appliquer le libellé X* + *Ne pas afficher dans la boîte de réception*).
* **Option B (Demander au Coordinateur Hub_Alex)** :
  * Dites simplement dans le chat : *"Ajoute [expéditeur ou mot-clé] dans le filtre Finance (ou Parapente / Emploi)"*.
  * Le Hub mettra à jour [`gmail_filters.xml`](file:///Users/alexandreflorentin/Documents/Git/Hub_Alex/docs/organization/gmail_filters.xml) et [`gmail_filter_runner.py`](file:///Users/alexandreflorentin/Documents/Git/Hub_Alex/projects/hub_engine/app/services/gmail_filter_runner.py) et appliquera la correction rétroactivement.

---

## 4. Fichiers et Scripts associés dans le Hub

* **Définition XML des filtres Gmail** : [`docs/organization/gmail_filters.xml`](file:///Users/alexandreflorentin/Documents/Git/Hub_Alex/docs/organization/gmail_filters.xml)
* **Script de tri et archivage par lots** : [`projects/hub_engine/app/services/gmail_filter_runner.py`](file:///Users/alexandreflorentin/Documents/Git/Hub_Alex/projects/hub_engine/app/services/gmail_filter_runner.py)
* **Agent IA Triage & Brouillons** : [`projects/hub_engine/app/agents/email_agent.py`](file:///Users/alexandreflorentin/Documents/Git/Hub_Alex/projects/hub_engine/app/agents/email_agent.py)
