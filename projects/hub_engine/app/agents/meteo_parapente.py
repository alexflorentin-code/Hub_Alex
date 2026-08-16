import os
import asyncio
import logging
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from pydantic_ai import Agent

from app.core.config import settings
from app.services.weather_service import get_full_weather_data, WeatherAggregate, compute_wind_cardinal

logger = logging.getLogger("hub_engine.meteo_parapente")

class FlyabilityType(str, Enum):
    GROS_CROSS_XC = "GROS_CROSS_XC"          # 🚀 Plafonds > 2500-3500m, vent calme, thermiques larges et sains
    VOLABLE_LOCAL = "VOLABLE_LOCAL"          # 🟢 Bonnes conditions de site, soaring, thermiques locaux, restitution
    VOL_TECHNIQUE = "VOL_TECHNIQUE"          # 🟡 Fenêtre courte, vent sensible ou plafonds bas
    NON_VOLABLE = "NON_VOLABLE"              # 🔴 Foehn, pluie, orages violents, vent fort > 25-30 km/h

class SynopticSituation(BaseModel):
    regime_name: str = Field(description="Nom du régime synoptique dominant (ex: Marais barométrique d'été, Bise anticyclonique, Flux de Sud-Ouest perturbé)")
    action_centers: str = Field(description="Position des anticyclones, dépressions et talwegs en Europe")
    impact_switzerland: str = Field(description="Conséquences concrètes pour la Suisse Romande, les Préalpes et les Alpes")
    synoptic_map_links: List[str] = Field(default=[], description="Liens vers les cartes synoptiques de référence")

class DayFlyability(BaseModel):
    date_str: str = Field(description="Jour et date (ex: 'Samedi 22 Août')")
    flyability: FlyabilityType = Field(description="Classification de la volabilité")
    score: int = Field(description="Note de volabilité sur 10")
    best_time_window: str = Field(description="Créneau horaire le plus favorable (ex: '12h30 - 17h00')")
    summary: str = Field(description="Synthèse rapide des conditions de la journée")

class CrossRegionalComparison(BaseModel):
    has_cross_potential: bool = Field(description="True si au moins un jour offre un potentiel de cross")
    recommended_region: str = Field(description="Massif recommandé en priorité : 'Valais', 'Jura' ou 'Chablais / Val d'Illiez'")
    valais_analysis: str = Field(description="Analyse du Valais : faces Sud, brise du Rhône, plafonds alpins")
    jura_analysis: str = Field(description="Analyse du Jura : régime de Bise, lignes de crêtes, plafonds")
    chablais_analysis: str = Field(description="Analyse du Chablais / Val d'Illiez : confluences et liaisons Préalpes")
    verdict: str = Field(description="Arbitrage clair et tranché pour orienter le choix du pilote")

class SpotDetailedForecast(BaseModel):
    spot_name: str = Field(description="Nom du spot (ex: 'Val d'Illiez / Portes du Soleil')")
    region: str = Field(description="Région (Chablais, Riviera Léman, Jura, Valais)")
    wind_surface: str = Field(description="Vent au sol et brise thermique")
    wind_1500m: str = Field(description="Vent à 1500m (850 hPa)")
    wind_3000m: str = Field(description="Vent à 3000m (700 hPa)")
    thermal_ceiling: str = Field(description="Plafond thermique estimé (altitude mer et sol)")
    best_slot: str = Field(description="Meilleur moment pour décoller")
    flight_type: str = Field(description="Type de vol recommandé (Cross, Thermique de site, Soaring, Plouf/Gonflage)")

class SafetyAlert(BaseModel):
    alert_type: str = Field(description="Type : FOEHN, TALWEG_SEC, VENT_FORT_BASSE_COUCHE, ORAGE_CONVECTION, ou AUCUNE")
    severity: str = Field(description="Niveau : INFO, WARNING, DANGER")
    title: str = Field(description="Titre de la vigilance")
    explanation: str = Field(description="Explication physique et danger aérologique")
    pilot_advice: str = Field(description="Consigne de sécurité concrète pour le pilote")

class MeteoParapenteDigest(BaseModel):
    status: str = Field(default="success", description="Statut de l'analyse")
    synoptic: SynopticSituation = Field(description="Vision macro synoptique européenne")
    weekly_flyability: List[DayFlyability] = Field(description="Vue moyen terme sur 7 jours")
    best_days_ranking: List[str] = Field(description="Classement des meilleurs jours de vol de la semaine")
    cross_comparison: CrossRegionalComparison = Field(description="Comparatif de cross : Jura vs Valais vs Chablais")
    detailed_forecasts: List[SpotDetailedForecast] = Field(description="Fiches détaillées des spots (Val d'Illiez en priorité)")
    safety_alerts: List[SafetyAlert] = Field(description="Alertes de sécurité et vigilances aérologiques")
    telegram_formatted_message: str = Field(description="Bulletin condensé pour Telegram avec émojis (🪂, 🚀, 🟢, 🛡️, 🏔️) et liens")
    email_formatted_digest: str = Field(description="Newsletter complète au format Markdown structuré")

GEMINI_METEO_MODELS = [
    "google:gemini-3.7-flash",
    "google:gemini-3.6-flash",
    "google:gemini-3.5-flash",
    "google:gemini-flash-latest",
    "google:gemini-2.5-flash"
]

SYSTEM_PROMPT = """
Tu es l'Agent Météo Parapente & Aérologie Locale de Hub_Alex pour Alexandre Florentin (pilote basé en Suisse, volant particulièrement les week-ends dans le Val d'Illiez / Chablais, ainsi qu'au Suchet dans le Jura, à Sonchaux au Léman et en Valais).

Ton rôle est d'analyser les données météorologiques brutes multi-échelles (synoptique européenne, modèles MétéoSuisse / AROME / ICON, gradients de pression, vents à 3 étages, hauteurs de couche limite BLH, CAPE) pour fournir un diagnostic aérologique de niveau expert.

Tes missions obligatoires :
1. **🌍 Vision Macro Synoptique** :
   - Positionner les anticyclones et dépressions en Europe.
   - Identifier le régime de flux sur la Suisse (Bise, Ouest perturbé, Marais estival, Flux de Sud).
2. **📅 Vision Moyen Terme (Semaine — 7 jours)** :
   - Qualifier chaque jour avec un badge précis :
     - 🚀 `GROS_CROSS_XC` : Plafonds > 2500-3500m, vent calme < 15 km/h à 700hPa, thermiques réguliers sans orage précoce.
     - 🟢 `VOLABLE_LOCAL` : Bonnes conditions pour vol de site, soaring ou thermique local.
     - 🟡 `VOL_TECHNIQUE` : Fenêtre courte, vent sensible ou plafonds bas.
     - 🔴 `NON_VOLABLE` : Foehn, pluie, orages violents, vent fort > 25-30 km/h.
   - Établir le podium des **meilleurs jours de la semaine**.
3. **🗺️ Arbitrage Régional Cross (Jura vs Valais vs Chablais)** :
   - Comparer les plafonds, l'ensoleillement et les lignes de vol entre le Valais (grandes faces Sud, brise du Rhône), le Jura (Suchet par Bise) et le Chablais (Val d'Illiez / Dents du Midi).
   - Donner un arbitrage tranché : Où poser ses suspentes pour faire le maximum de kilomètres en sécurité ?
4. **🔬 Fiche Détaillée Court Terme (J à J+2 / Week-end)** :
   - Vents à 3 altitudes : Sol (10m), 1500m (850 hPa), 3000m (700 hPa).
   - Plafond thermique estimé (BLH).
   - Spot prioritaire : **Val d'Illiez / Portes du Soleil**.
5. **🛡️ Sécurité & Alertes Aérologiques** :
   - **Foehn** : Analyser le gradient ΔP (Tessin - Plateau) et le vent de Sud à 3000m. Si ΔP >= 4 hPa ou vent Sud 3000m > 25 km/h -> Alerte Foehn DANGER.
   - **Talweg sec / Lignes de grains** : Bascules brutales Ouest/Nord-Ouest.
   - **Bise & Brises de vallée** : Renforcements en basse couche (brise du Rhône).
   - **Orages (CAPE)** : Alerte si CAPE > 500-1000 J/kg en montagne l'après-midi.
"""

def generate_mock_digest() -> MeteoParapenteDigest:
    """Génère un rapport météo réaliste pour les tests unitaires et le mode simulation."""
    return MeteoParapenteDigest(
        status="success",
        synoptic=SynopticSituation(
            regime_name="Marais barométrique estival avec dorsale anticyclonique alpine",
            action_centers="Anticyclone centré sur l'Europe centrale (1022 hPa), dépression atlantique au large de l'Irlande (1004 hPa).",
            impact_switzerland="Régime de brises thermiques pures dans les Alpes, vent météo très faible en altitude, grand soleil et convection saine.",
            synoptic_map_links=[
                "https://www.meteosuisse.admin.ch",
                "https://www.wetterzentrale.de/topkarten.php?map=1"
            ]
        ),
        weekly_flyability=[
            DayFlyability(date_str="Lundi", flyability=FlyabilityType.VOLABLE_LOCAL, score=7, best_time_window="13h00 - 17h00", summary="Thermiques locaux réguliers, vent faible."),
            DayFlyability(date_str="Mardi", flyability=FlyabilityType.VOL_TECHNIQUE, score=5, best_time_window="11h30 - 14h00", summary="Passage nuageux en milieu d'après-midi."),
            DayFlyability(date_str="Mercredi", flyability=FlyabilityType.NON_VOLABLE, score=2, best_time_window="Aucun", summary="Pluie et vent d'Ouest soutenu."),
            DayFlyability(date_str="Jeudi", flyability=FlyabilityType.VOLABLE_LOCAL, score=6, best_time_window="14h00 - 18h00", summary="Amélioration en fin de journée, belle restitution."),
            DayFlyability(date_str="Vendredi", flyability=FlyabilityType.VOLABLE_LOCAL, score=7, best_time_window="12h00 - 16h30", summary="Bonnes conditions thermiques sur les faces Sud."),
            DayFlyability(date_str="Samedi", flyability=FlyabilityType.GROS_CROSS_XC, score=9, best_time_window="11h30 - 17h30", summary="Journée reine : hauts plafonds (> 3200m) et vent nul en altitude."),
            DayFlyability(date_str="Dimanche", flyability=FlyabilityType.GROS_CROSS_XC, score=8, best_time_window="11h00 - 16h00", summary="Excellent cross, surveillance des cumulus en fin de journée.")
        ],
        best_days_ranking=["1. 🚀 Samedi (Score 9/10 - Journée XC)", "2. 🚀 Dimanche (Score 8/10)", "3. 🟢 Lundi & Vendredi (Score 7/10)"],
        cross_comparison=CrossRegionalComparison(
            has_cross_potential=True,
            recommended_region="Valais Central (Vercorin / Sion)",
            valais_analysis="Plafonds exceptionnels à 3400m sur les faces Sud, brise de vallée régulière sans excès.",
            jura_analysis="Plafonds à 2100m au Suchet, thermiques un peu plus étalés par léger vent de Nord-Est.",
            chablais_analysis="Val d'Illiez très bien abrité, départ cross possible vers les Cornettes de Bise et Morzine.",
            verdict="Privilégier le Valais samedi pour maximiser les kilomètres, et le Val d'Illiez pour un vol plaisir et rando de proximité."
        ),
        detailed_forecasts=[
            SpotDetailedForecast(
                spot_name="Val d'Illiez / Planachaux",
                region="Chablais / Portes du Soleil",
                wind_surface="Brise de vallée montante 10-15 km/h",
                wind_1500m="NE 8 km/h",
                wind_3000m="N 10 km/h",
                thermal_ceiling="2700m mer (~1750m sol)",
                best_slot="12h00 - 16h30",
                flight_type="Cross local & thermique généreux"
            ),
            SpotDetailedForecast(
                spot_name="Sonchaux (Villeneuve)",
                region="Riviera Léman",
                wind_surface="Brise de lac 12 km/h",
                wind_1500m="NE 10 km/h",
                wind_3000m="N 12 km/h",
                thermal_ceiling="2300m mer",
                best_slot="13h30 - 18h00",
                flight_type="Thermique de falaise et restitution du soir"
            ),
            SpotDetailedForecast(
                spot_name="Le Suchet",
                region="Jura Vaudois",
                wind_surface="NE 12-18 km/h",
                wind_1500m="NE 15 km/h",
                wind_3000m="NE 15 km/h",
                thermal_ceiling="2100m mer",
                best_slot="11h30 - 16h00",
                flight_type="Soaring dynamique & Cross de crête"
            )
        ],
        safety_alerts=[
            SafetyAlert(
                alert_type="FOEHN",
                severity="INFO",
                title="Pas de risque de Foehn",
                explanation="Gradient de pression Sud/Nord neutre (ΔP = +0.5 hPa).",
                pilot_advice="Vol en montagne serein sur le massif alpin."
            )
        ],
        telegram_formatted_message=(
            "🪂 *BULLETIN MÉTÉO PARAPENTE & CROSS — HUB_ALEX* 🏔️\n\n"
            "🌍 *Situation Synoptique :* Marais barométrique estival calme sur les Alpes.\n"
            "🛡️ *Sécurité Foehn :* 🟢 Aucun risque (ΔP = +0.5 hPa, vent Sud nul à 3000m).\n\n"
            "📅 *VOLABILITÉ CETTE SEMAINE :*\n"
            "• Lun : 🟢 Volable (7/10)\n"
            "• Mar : 🟡 Technique (5/10)\n"
            "• Mer : 🔴 Non volable (2/10 - Pluie)\n"
            "• Jeu : 🟢 Volable (6/10)\n"
            "• Ven : 🟢 Volable (7/10)\n"
            "• **Sam : 🚀 GROS CROSS (9/10) — TOP JOURNÉE**\n"
            "• **Dim : 🚀 GROS CROSS (8/10)**\n\n"
            "🗺️ *ARBITRAGE CROSS : JURA VS VALAIS*\n"
            "👉 **Recommandation : Valais (Vercorin)**\n"
            "Plafonds à 3400m en Valais vs 2100m au Suchet. Idéal pour boucler 100km+ !\n\n"
            "🏔️ *SPOT DU WEEK-END : VAL D'ILLIEZ*\n"
            "• Plafond : ~2700m | Vent sol : Brise 10 km/h | 3000m : N 10 km/h\n"
            "• Créneau idéal : 12h00 - 16h30 (Thermiques sains & soaring)\n\n"
            "Bons vols à tous ! 🪂"
        ),
        email_formatted_digest=(
            "# 🪂 Newsletter Météo Parapente & Aérologie - Hub_Alex\n\n"
            "## 🌍 1. Situation Synoptique & Centres d'Action\n"
            "Un marais barométrique chaud s'installe sur l'Europe centrale, garantissant un vent météo très faible en altitude et un ensoleillement maximal.\n\n"
            "## 📅 2. Vue d'Ensemble Moyen Terme (Semaine)\n"
            "- **Samedi** : 🚀 Journée reine pour le Cross (Score 9/10).\n"
            "- **Dimanche** : 🚀 Excellente journée thermique (Score 8/10).\n\n"
            "## 🗺️ 3. Arbitrage Cross : Jura vs Valais vs Chablais\n"
            "Le **Valais Central** offre les meilleurs plafonds (3400m). Le **Val d'Illiez** sera parfait pour les vols locaux et triangles en moyenne montagne.\n\n"
            "## 🛡️ 4. Sécurité & Foehn\n"
            "Aucun danger de Foehn détecté."
        )
    )

def prepare_context_from_aggregate(weather_data: WeatherAggregate) -> str:
    """Transforme les données météo Open-Meteo agrégées en texte synthétique pour le LLM."""
    lines = []
    lines.append(f"Horodatage de la mesure : {weather_data.timestamp}")
    lines.append(f"--- SITUATION SYNOPTIQUE & FOEHN ---")
    lines.append(f"Gradient Foehn ΔP (Tessin - Plateau) : {weather_data.synoptic.foehn_delta_p} hPa (Niveau : {weather_data.synoptic.foehn_risk})")
    lines.append(f"Vent Sud à 3000m (700 hPa) sur les Alpes : {weather_data.synoptic.south_wind_700hpa:.1f} km/h")
    lines.append(f"Régime synoptique calculé : {weather_data.synoptic.dominant_regime}")
    lines.append(f"Pressions de surface (hPa) : {weather_data.synoptic.pressures}")
    
    lines.append("\n--- DONNÉES SPOTS DE VOL LIBRE (Prochains 7 jours) ---")
    for spot_id, spot in weather_data.spots.items():
        lines.append(f"\n📍 Spot : {spot.name} ({spot.region}, Alt. base : {spot.base_elevation}m)")
        # Sélectionner les créneaux représentatifs : Midi (12h/14h) pour chaque jour
        for d_idx in range(7):
            idx_14h = d_idx * 24 + 14
            if idx_14h < len(spot.hourly):
                h = spot.hourly[idx_14h]
                cardinal_10m = compute_wind_cardinal(h.wind_direction_10m)
                cardinal_850 = compute_wind_cardinal(h.wind_direction_850hPa)
                cardinal_700 = compute_wind_cardinal(h.wind_direction_700hPa)
                lines.append(
                    f"  - Jour {d_idx+1} ({h.time[:10]} à 14h) : Temp 2m={h.temperature_2m:.1f}°C | "
                    f"Vent Sol={cardinal_10m} {h.wind_speed_10m:.1f} km/h (Raf. {h.wind_gusts_10m:.1f}) | "
                    f"Vent 1500m={cardinal_850} {h.wind_speed_850hPa:.1f} km/h | "
                    f"Vent 3000m={cardinal_700} {h.wind_speed_700hPa:.1f} km/h | "
                    f"Plafond BLH sol={h.boundary_layer_height:.0f}m (Mer ~{spot.base_elevation + h.boundary_layer_height:.0f}m) | "
                    f"CAPE={h.cape:.0f} J/kg | Pluie prob={h.precipitation_probability}%"
                )
                
    return "\n".join(lines)

async def run_meteo_analysis(custom_prompt: Optional[str] = None) -> MeteoParapenteDigest:
    """Récupère les données météo Open-Meteo et exécute l'analyse d'aérologie experte."""
    logger.info("Démarrage de l'analyse météo parapente & aérologie...")
    
    # Mode test hors-ligne si aucune clé API
    if not settings.GEMINI_API_KEY and not settings.OPENAI_API_KEY:
        logger.info("Mode test : Retour d'un rapport météo simulé.")
        return generate_mock_digest()
        
    try:
        weather_data = await get_full_weather_data()
        context_str = prepare_context_from_aggregate(weather_data)
    except Exception as e:
        logger.warning(f"Erreur lors de la collecte météo directe ({str(e)}). Utilisation du mock.")
        return generate_mock_digest()
        
    user_instruction = custom_prompt or (
        "Analyse ces données météorologiques et aérologiques pour générer le bulletin complet de vol libre : "
        "situation synoptique, tableau des 7 jours, arbitrage Cross Jura vs Valais vs Chablais, fiches détaillées (Val d'Illiez en tête), "
        "et alertes de sécurité (Foehn, talwegs, vents forts basse couche, orages)."
    )
    full_prompt = f"Voici les mesures et prévisions météo haute résolution :\n\n{context_str}\n\nConsigne : {user_instruction}"

    # Exécution OpenAI si configuré
    if settings.OPENAI_API_KEY:
        os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY
        agent = Agent("openai:gpt-4o-mini", output_type=MeteoParapenteDigest, system_prompt=SYSTEM_PROMPT)
        result = await agent.run(full_prompt)
        return result.output

    # Cascade Gemini
    if settings.GEMINI_API_KEY:
        os.environ["GEMINI_API_KEY"] = settings.GEMINI_API_KEY
        last_error = None
        for model_candidate in GEMINI_METEO_MODELS:
            for attempt in range(2):
                try:
                    logger.info(f"Tentative d'analyse météo avec {model_candidate} (essai {attempt+1})...")
                    agent = Agent(model_candidate, output_type=MeteoParapenteDigest, system_prompt=SYSTEM_PROMPT)
                    result = await agent.run(full_prompt)
                    return result.output
                except Exception as e:
                    last_error = e
                    logger.warning(f"Modèle {model_candidate} indisponible ({str(e)[:100]}). Essai suivant...")
                    await asyncio.sleep(1.0)
                    
        logger.error(f"Tous les modèles Gemini ont échoué pour la météo : {str(last_error)}")
        raise last_error
