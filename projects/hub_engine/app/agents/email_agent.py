import os
import asyncio
import logging
from typing import List, Optional
from pydantic import BaseModel, Field
from pydantic_ai import Agent

from app.core.config import settings
from app.services.gmail_service import fetch_unread_emails, create_gmail_draft, EmailItem, DraftResult

logger = logging.getLogger("hub_engine.email_agent")

class EmailClassification(BaseModel):
    category: str = Field(description="Catégorie : 🚨 URGENT, 📋 ACTION REQUISE, 📰 INFO / NEWSLETTER, ou 💬 ÉCHANGE")
    sender: str = Field(description="Nom ou adresse de l'expéditeur")
    subject: str = Field(description="Objet du message")
    summary: str = Field(description="Résumé en 1 phrase de la demande ou de l'information clé")
    action_needed: str = Field(description="Action attendue d'Alexandre (ex: 'Valider le devis', 'Confirmer le créneau', 'Aucune action requise')")
    suggested_reply: Optional[str] = Field(default=None, description="Proposition de texte de réponse rapide")
    is_urgent: bool = Field(default=False, description="True si le message est critique ou requiert une attention immédiate")

class InboxDigest(BaseModel):
    status: str = Field(default="success", description="Statut de l'analyse")
    unread_count: int = Field(description="Nombre d'e-mails analysés")
    urgent_count: int = Field(description="Nombre d'e-mails urgents nécessitant une action rapide")
    urgent_alerts: List[EmailClassification] = Field(default=[], description="Liste des alertes urgentes")
    classifications: List[EmailClassification] = Field(default=[], description="Liste complète des e-mails classés")
    telegram_formatted_message: str = Field(description="Synthèse formatée pour Telegram avec émojis et points clés")

class DraftProposal(BaseModel):
    to: str = Field(description="Adresse e-mail du destinataire")
    subject: str = Field(description="Objet professionnel du message")
    body: str = Field(description="Corps complet du message rédigé en français selon les préférences d'Alexandre")
    explanation: str = Field(description="Courte explication du ton et de la structure adoptée")

GEMINI_EMAIL_MODELS = [
    "google:gemini-3.6-flash",
    "google:gemini-3.7-flash",
    "google:gemini-3.5-flash",
    "google:gemini-flash-latest",
    "google:gemini-2.5-flash"
]

EMAIL_TRIAGE_PROMPT = """
Tu es l'Agent E-mail et Communication de Hub_Alex pour Alexandre Florentin.
Ton rôle est d'analyser la boîte de réception Gmail d'Alexandre, de classifier les e-mails avec une grande précision, et d'isoler les urgences.

Consignes de classification :
1. 🚨 URGENT : Demande d'un client majeur, problème technique bloquant, échéance dans les 24h, mot-clé urgent.
2. 📋 ACTION REQUISE : Question posée, demande d'avis, validation attendue.
3. 📰 INFO / NEWSLETTER : Mises à jour, reçus, notifications automatiques, lectures recommandées.
4. 💬 ÉCHANGE : Conversation courante, remerciements, suivi sans urgence.

Pour chaque e-mail :
- Identifie l'expéditeur et le sujet réel.
- Rédige un résumé clair en une seule phrase percutante.
- Propose une réponse courte si une action est requise.
- Rédige un message global `telegram_formatted_message` clair, aéré et percutant.
"""

DRAFT_GENERATION_PROMPT = """
Tu es l'Agent de Rédaction d'E-mails de Hub_Alex pour Alexandre Florentin.
Ton rôle est de rédiger des brouillons d'e-mails impeccables, professionnels, chaleureux et percutants selon les consignes d'Alexandre.

Règles de rédaction :
- Langue : Français soigné.
- Style : Professionnel, direct, courtois et synthétique.
- Structure : Salutation personnalisée, message clair, proposition d'action / date concrète si besoin, formule de politesse chaleureuse, signature 'Alexandre Florentin'.
- Sécurité : Ce message sera enregistré comme BROUILLON dans Gmail.
"""

async def analyze_inbox(max_emails: int = 8) -> InboxDigest:
    """Récupère les e-mails non lus et les classe via PydanticAI."""
    logger.info("Démarrage de l'analyse de la boîte de réception...")
    emails = fetch_unread_emails(max_results=max_emails)

    # Si aucun e-mail ou mode test simulé
    if not emails or (not settings.GEMINI_API_KEY and not settings.OPENAI_API_KEY):
        mock_classifications = [
            EmailClassification(
                category="📋 ACTION REQUISE",
                sender="Pierre Martin",
                subject="Devis projet Hub",
                summary="Demande de validation du planning de livraison avant vendredi.",
                action_needed="Confirmer la date de démarrage",
                suggested_reply="Bonjour Pierre, je te confirme que nous validons le devis. On démarre lundi.",
                is_urgent=False
            )
        ] if not emails else []

        return InboxDigest(
            status="success",
            unread_count=len(emails) or 1,
            urgent_count=0,
            urgent_alerts=[],
            classifications=mock_classifications,
            telegram_formatted_message=(
                "📬 **Synthèse Boîte de Réception Gmail**\n\n"
                "• **Pierre Martin** — *Devis projet Hub*\n"
                "  ↳ Action : Confirmer la date de démarrage\n\n"
                "💡 *Tous les autres e-mails sont traités ou en ordre.*"
            )
        )

    # Préparation du contexte d'e-mails pour le LLM
    context_list = []
    for idx, e in enumerate(emails, 1):
        context_list.append(
            f"[{idx}] ID: {e.id}\nDe: {e.sender}\nDate: {e.date}\nObjet: {e.subject}\nContenu:\n{e.body_text[:500]}\n"
        )
    context_str = "\n---\n".join(context_list)
    prompt = f"Voici les e-mails non lus d'Alexandre :\n\n{context_str}\n\nConsigne : Classifie chaque e-mail, identifie les urgences et génère la synthèse Telegram."

    # Exécution avec cascade multi-modèles
    if settings.OPENAI_API_KEY:
        os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY
        agent = Agent("openai:gpt-4o-mini", output_type=InboxDigest, system_prompt=EMAIL_TRIAGE_PROMPT)
        res = await agent.run(prompt)
        return res.output

    if settings.GEMINI_API_KEY:
        os.environ["GEMINI_API_KEY"] = settings.GEMINI_API_KEY
        last_error = None
        for m in GEMINI_EMAIL_MODELS:
            for attempt in range(2):
                try:
                    agent = Agent(m, output_type=InboxDigest, system_prompt=EMAIL_TRIAGE_PROMPT)
                    res = await agent.run(prompt)
                    return res.output
                except Exception as e:
                    last_error = e
                    logger.warning(f"Email triage : Modèle {m} indisponible ({str(e)[:100]}). Essai suivant...")
                    await asyncio.sleep(1.0)
        raise last_error

async def draft_email(instruction: str, recipient: Optional[str] = None) -> DraftProposal:
    """Génère et crée un brouillon dans Gmail à partir d'une consigne utilisateur."""
    logger.info(f"Génération d'un brouillon pour la consigne : {instruction}...")

    # Si mode test sans LLM
    if not settings.GEMINI_API_KEY and not settings.OPENAI_API_KEY:
        target_to = recipient or "destinataire@example.com"
        subject = "Suite à notre échange"
        body = f"Bonjour,\n\nFaisant suite à votre demande, je vous confirme la bonne prise en compte.\n\nBien cordialement,\nAlexandre Florentin"
        create_gmail_draft(to_email=target_to, subject=subject, body_text=body)
        return DraftProposal(
            to=target_to,
            subject=subject,
            body=body,
            explanation="Brouillon généré en mode simulé."
        )

    user_prompt = f"Consigne d'Alexandre : {instruction}\nDestinataire suggéré : {recipient or 'À déduire de la consigne ou placeholder'}"

    agent_draft = None
    if settings.OPENAI_API_KEY:
        os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY
        agent_draft = Agent("openai:gpt-4o-mini", output_type=DraftProposal, system_prompt=DRAFT_GENERATION_PROMPT)
        res = await agent_draft.run(user_prompt)
        proposal = res.output
    elif settings.GEMINI_API_KEY:
        os.environ["GEMINI_API_KEY"] = settings.GEMINI_API_KEY
        for m in GEMINI_EMAIL_MODELS:
            try:
                agent_draft = Agent(m, output_type=DraftProposal, system_prompt=DRAFT_GENERATION_PROMPT)
                res = await agent_draft.run(user_prompt)
                proposal = res.output
                break
            except Exception as e:
                logger.warning(f"Draft generation : {m} failed ({str(e)[:80]}). Trying next...")
                await asyncio.sleep(1.0)

    # Création effective du brouillon dans Gmail
    try:
        create_gmail_draft(
            to_email=proposal.to,
            subject=proposal.subject,
            body_text=proposal.body
        )
    except Exception as e:
        logger.error(f"Erreur lors de l'enregistrement du brouillon dans Gmail : {str(e)}")

    return proposal
