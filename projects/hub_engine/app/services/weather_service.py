import time
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import httpx

logger = logging.getLogger("hub_engine.weather")

# Coordonnées des spots majeurs pour Alexandre
SPOTS = {
    "val_d_illiez": {
        "name": "Val d'Illiez / Portes du Soleil",
        "region": "Chablais / Valais",
        "latitude": 46.20,
        "longitude": 6.89,
        "base_elevation": 967,
        "takeoff_elevations": [1400, 1850],  # Planachaux / Croix de Culet
        "is_primary": True
    },
    "sonchaux": {
        "name": "Sonchaux (Villeneuve)",
        "region": "Riviera / Léman",
        "latitude": 46.43,
        "longitude": 6.94,
        "base_elevation": 380,
        "takeoff_elevations": [1400],
        "is_primary": False
    },
    "le_suchet": {
        "name": "Le Suchet",
        "region": "Jura Vaudois",
        "latitude": 46.77,
        "longitude": 6.46,
        "base_elevation": 1000,
        "takeoff_elevations": [1588],
        "is_primary": False
    },
    "vercorin": {
        "name": "Vercorin / Val d'Anniviers",
        "region": "Valais Central",
        "latitude": 46.25,
        "longitude": 7.53,
        "base_elevation": 1330,
        "takeoff_elevations": [2330],  # Crêt du Midi
        "is_primary": False
    }
}

# Points de calcul synoptique & Foehn
SYNOPTIC_POINTS = {
    "lugano": {"latitude": 46.00, "longitude": 8.96, "name": "Tessin (Sud des Alpes)"},
    "zurich": {"latitude": 47.38, "longitude": 8.54, "name": "Plateau Suisse (Nord)"},
    "brest": {"latitude": 48.39, "longitude": -4.48, "name": "Atlantique Ouest"},
    "london": {"latitude": 51.50, "longitude": -0.12, "name": "Îles Britanniques"},
    "genoa": {"latitude": 44.41, "longitude": 8.93, "name": "Golfe de Gênes / Méditerranée"},
    "munich": {"latitude": 48.13, "longitude": 11.58, "name": "Europe Centrale"}
}

# Cache en mémoire avec TTL (30 minutes)
_WEATHER_CACHE: Dict[str, Any] = {}
_CACHE_TIMESTAMP: float = 0
CACHE_TTL = 1800  # 30 minutes

class SpotHourlyData(BaseModel):
    time: str
    temperature_2m: float
    surface_pressure: float
    wind_speed_10m: float
    wind_direction_10m: int
    wind_gusts_10m: float
    wind_speed_850hPa: float
    wind_direction_850hPa: int
    wind_speed_700hPa: float
    wind_direction_700hPa: int
    cape: float
    boundary_layer_height: float
    cloud_cover: int
    precipitation_probability: int

class SpotForecast(BaseModel):
    spot_id: str
    name: str
    region: str
    base_elevation: int
    hourly: List[SpotHourlyData]

class SynopticSnapshot(BaseModel):
    foehn_delta_p: float  # P(Lugano) - P(Zurich) en hPa
    foehn_risk: str       # NONE, MODERATE, HIGH, SEVERE
    south_wind_700hpa: float  # Vent de Sud à 3000m au-dessus des Alpes
    dominant_regime: str  # OUEST_PERTURBE, BISE_NORD_EST, MARAIS_BAROMETRIQUE, SUD_FOEHN
    pressures: Dict[str, float]

class WeatherAggregate(BaseModel):
    timestamp: str
    synoptic: SynopticSnapshot
    spots: Dict[str, SpotForecast]

def compute_wind_cardinal(deg: int) -> str:
    """Convertit un angle en degrés vers la direction cardinale."""
    dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    ix = round(deg / (360.0 / len(dirs))) % len(dirs)
    return dirs[ix]

async def fetch_spot_weather(client: httpx.AsyncClient, spot_id: str, spot_info: dict) -> SpotForecast:
    """Récupère les prévisions horaires haute résolution sur 7 jours pour un spot de vol."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": spot_info["latitude"],
        "longitude": spot_info["longitude"],
        "hourly": "temperature_2m,surface_pressure,wind_speed_10m,wind_direction_10m,wind_gusts_10m,wind_speed_850hPa,wind_direction_850hPa,wind_speed_700hPa,wind_direction_700hPa,cape,boundary_layer_height,cloud_cover,precipitation_probability",
        "timezone": "Europe/Zurich",
        "forecast_days": 7
    }
    
    resp = await client.get(url, params=params, timeout=12.0)
    resp.raise_for_status()
    data = resp.json()
    
    hourly_dict = data.get("hourly", {})
    times = hourly_dict.get("time", [])
    hourly_list: List[SpotHourlyData] = []
    
    for i, t in enumerate(times):
        hourly_list.append(SpotHourlyData(
            time=t,
            temperature_2m=hourly_dict["temperature_2m"][i],
            surface_pressure=hourly_dict["surface_pressure"][i],
            wind_speed_10m=hourly_dict["wind_speed_10m"][i],
            wind_direction_10m=int(hourly_dict["wind_direction_10m"][i]),
            wind_gusts_10m=hourly_dict["wind_gusts_10m"][i],
            wind_speed_850hPa=hourly_dict["wind_speed_850hPa"][i],
            wind_direction_850hPa=int(hourly_dict["wind_direction_850hPa"][i]),
            wind_speed_700hPa=hourly_dict["wind_speed_700hPa"][i],
            wind_direction_700hPa=int(hourly_dict["wind_direction_700hPa"][i]),
            cape=hourly_dict["cape"][i] or 0.0,
            boundary_layer_height=hourly_dict["boundary_layer_height"][i] or 0.0,
            cloud_cover=int(hourly_dict["cloud_cover"][i]),
            precipitation_probability=int(hourly_dict["precipitation_probability"][i])
        ))
        
    return SpotForecast(
        spot_id=spot_id,
        name=spot_info["name"],
        region=spot_info["region"],
        base_elevation=spot_info["base_elevation"],
        hourly=hourly_list
    )

async def fetch_synoptic_snapshot(client: httpx.AsyncClient) -> SynopticSnapshot:
    """Récupère les pressions aux stations clés pour le calcul du Foehn et du régime synoptique."""
    url = "https://api.open-meteo.com/v1/forecast"
    pressures: Dict[str, float] = {}
    
    # Requête groupée des pressions actuelles
    lats = [info["latitude"] for info in SYNOPTIC_POINTS.values()]
    lons = [info["longitude"] for info in SYNOPTIC_POINTS.values()]
    
    params = {
        "latitude": ",".join(map(str, lats)),
        "longitude": ",".join(map(str, lons)),
        "current": "surface_pressure,wind_speed_10m,wind_direction_10m",
        "hourly": "wind_speed_700hPa,wind_direction_700hPa",
        "timezone": "Europe/Zurich",
        "forecast_days": 1
    }
    
    resp = await client.get(url, params=params, timeout=12.0)
    resp.raise_for_status()
    raw_results = resp.json()
    if isinstance(raw_results, dict):
        raw_results = [raw_results]
        
    point_keys = list(SYNOPTIC_POINTS.keys())
    for idx, res in enumerate(raw_results):
        k = point_keys[idx]
        pressures[k] = res.get("current", {}).get("surface_pressure", 1013.25)
        
    p_lugano = pressures.get("lugano", 1013.0)
    p_zurich = pressures.get("zurich", 1013.0)
    delta_p = round(p_lugano - p_zurich, 2)
    
    # Estimation du vent moyen à 3000m (700hPa) sur les Alpes
    south_wind_700 = 0.0
    if raw_results:
        h700_speeds = raw_results[0].get("hourly", {}).get("wind_speed_700hPa", [0])
        h700_dirs = raw_results[0].get("hourly", {}).get("wind_direction_700hPa", [0])
        if h700_speeds:
            current_spd = h700_speeds[0]
            current_dir = h700_dirs[0]
            if 140 <= current_dir <= 220:
                south_wind_700 = current_spd
                
    # Évaluation du risque de Foehn
    if delta_p >= 8.0 or (delta_p >= 5.0 and south_wind_700 >= 35.0):
        foehn_risk = "SEVERE"
    elif delta_p >= 4.0 or (delta_p >= 3.0 and south_wind_700 >= 25.0):
        foehn_risk = "HIGH"
    elif delta_p >= 2.0 or south_wind_700 >= 20.0:
        foehn_risk = "MODERATE"
    else:
        foehn_risk = "NONE"
        
    # Régime dominant
    p_brest = pressures.get("brest", 1015.0)
    p_munich = pressures.get("munich", 1015.0)
    p_genoa = pressures.get("genoa", 1015.0)
    
    if delta_p >= 4.0 or south_wind_700 >= 25.0:
        dominant_regime = "SUD_FOEHN"
    elif p_brest - p_munich > 6.0:
        dominant_regime = "OUEST_PERTURBE"
    elif p_munich - p_brest > 4.0:
        dominant_regime = "BISE_NORD_EST"
    elif abs(p_brest - p_munich) < 3.0 and abs(p_zurich - p_genoa) < 3.0:
        dominant_regime = "MARAIS_BAROMETRIQUE"
    else:
        dominant_regime = "REGIME_TRANSITION"
        
    return SynopticSnapshot(
        foehn_delta_p=delta_p,
        foehn_risk=foehn_risk,
        south_wind_700hpa=south_wind_700,
        dominant_regime=dominant_regime,
        pressures=pressures
    )

async def get_full_weather_data(force_refresh: bool = False) -> WeatherAggregate:
    """Récupère l'ensemble des données météo multi-échelles avec mise en cache."""
    global _WEATHER_CACHE, _CACHE_TIMESTAMP
    now = time.time()
    
    if not force_refresh and _WEATHER_CACHE and (now - _CACHE_TIMESTAMP < CACHE_TTL):
        logger.info("Utilisation des données météo en cache (TTL 30 min)")
        return WeatherAggregate(**_WEATHER_CACHE)
        
    logger.info("Interrogation en direct des APIs Open-Meteo pour l'aérologie suisse...")
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        # 1. Snapshot synoptique
        synoptic_task = fetch_synoptic_snapshot(client)
        
        # 2. Spots vol libre
        spot_tasks = [fetch_spot_weather(client, s_id, s_info) for s_id, s_info in SPOTS.items()]
        
        import asyncio
        results = await asyncio.gather(synoptic_task, *spot_tasks)
        
    synoptic_res = results[0]
    spots_res = {r.spot_id: r for r in results[1:]}
    
    aggregate = WeatherAggregate(
        timestamp=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)),
        synoptic=synoptic_res,
        spots=spots_res
    )
    
    _WEATHER_CACHE = aggregate.model_dump()
    _CACHE_TIMESTAMP = now
    
    return aggregate
