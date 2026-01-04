import os
import json
import random
from datetime import datetime, timedelta, timezone
from flask import Flask, request, jsonify
from dotenv import load_dotenv

from kalai.utils.environmental import get_moon_phase, read_water_sensor_mock
from kalai.model.rule_based_model import rule_based_activity_score
from kalai.model.lure_recommender import recommended_lures, feeding_mode

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_secret')
SPECIES_DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'species_db.json')
USER_LOGS = [] 

# --- Core Data Loading ---

def load_species_db():
    """Loads species data from local JSON file."""
    try:
        with open(SPECIES_DB_PATH, 'r') as f:
            return {sp['key']: sp for sp in json.load(f)}
    except FileNotFoundError:
        print(f"Error: {SPECIES_DB_PATH} not found.")
        return {}

SPECIES_PROFILES = load_species_db()


def get_species_profile(species_key: str) -> dict | None:
    return SPECIES_PROFILES.get(species_key.lower())

def get_simulated_weather(lat: float, lon: float, dt: datetime = None) -> dict:
    """Simulates OpenWeather OneCall API data."""
    if dt is None:
        dt = datetime.now(timezone.utc)
    
    sunrise = dt.replace(hour=7, minute=30, second=0, microsecond=0)
    sunset = dt.replace(hour=16, minute=30, second=0, microsecond=0)
    

    water_temp = read_water_sensor_mock() 


    air_temp = water_temp + random.uniform(2.0, 5.0) 
    moon_phase, moon_fraction = get_moon_phase(dt)
    
    return {
        "temp_c": round(air_temp, 1),
        "water_temp_c": round(water_temp, 1),
        "wind_speed_ms": round(random.uniform(1.0, 7.0), 1),
        "cloud_cover_percent": random.randint(30, 90),
        "pressure_hpa": random.randint(1000, 1020),
        "humidity_percent": random.randint(70, 90),
        "sunrise_h": sunrise.hour,
        "sunset_h": sunset.hour,
        "current_time": dt.isoformat(),
        "moon_phase": moon_phase, 
        "moon_fraction": moon_fraction,
        "model_source": "SIMULATED_DATA"
    }

# --- REST API Endpoints ---

@app.route('/nearby', methods=['GET'])
def nearby():
    """GET /nearby: Simulated Overpass API call."""
    lat = request.args.get('lat', 60.17, type=float)
    lon = request.args.get('lon', 24.94, type=float)
    
    waterbodies = [
        {"name": "Seurasaarenselkä", "lat": 60.176, "lon": 24.912, "tags": {"water": "bay"}, "distance_km": 3},
        {"name": "Vantaanjoki (River Vantaa)", "lat": 60.25, "lon": 24.90, "tags": {"water": "river"}, "distance_km": 15},
    ]
    return jsonify({"waterbodies": waterbodies, "source": "SIMULATED_OVERPASS"})

@app.route('/predict', methods=['GET'])
def predict():
    """GET /predict: Main prediction endpoint using Rule-Based Scorer."""
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    species_key = request.args.get('species', 'pike').lower()
    
    if lat is None or lon is None:
        return jsonify({"error": "Missing 'lat' or 'lon' query parameters"}), 400
        
    species_profile = get_species_profile(species_key)
    if not species_profile:
        return jsonify({"error": f"Species '{species_key}' not found."}), 404

    current_time = datetime.now(timezone.utc)
    weather_data = get_simulated_weather(lat, lon, current_time)

    # 1. Compute 24-hour windows
    best_time_windows = []
    
    for i in range(24):
        dt_hour = current_time + timedelta(hours=i)
        hourly_weather = get_simulated_weather(lat, lon, dt_hour)
        score, _ = rule_based_activity_score(species_profile, hourly_weather, dt_hour)
        
        if score > 75:
            best_time_windows.append({
                "start": dt_hour.isoformat(),
                "end": (dt_hour + timedelta(hours=1)).isoformat(),
                "score": score
            })
            
    best_time_windows.sort(key=lambda x: x['score'], reverse=True)
    best_time_windows = best_time_windows[:3]

    current_score, explanation = rule_based_activity_score(species_profile, weather_data, current_time)

    mode = feeding_mode(current_score)

    context = {
        "feeding_mode": mode,
        "water_temp": weather_data["water_temp_c"],
        "cloud_cover": weather_data["cloud_cover_percent"],
        "wind_speed": weather_data["wind_speed_ms"]
    }
    
    activity_label = "high" if current_score > 75 else "medium" if current_score > 40 else "low"

    recommended = recommended_lures(species_profile, context, top_n=3)
    
    response = {
      "location": {"lat": lat, "lon": lon},
      "species": species_profile["key"],
      "activity_score": current_score,
      "activity_label": activity_label,
      "best_time_windows": best_time_windows,
      "feeding_mode": mode,
      "recommended_lures": recommended,
      "explanation": explanation,
      "model_used": "rule_based"
    }

    return jsonify(response)


@app.route('/feedback', methods=['POST'])
def submit_feedback():
    """POST /feedback: Logs user catch/no-catch data to in-memory list."""
    data = request.get_json()
    if not all(k in data for k in ["lat", "lon", "species", "caught"]):
        return jsonify({"error": "Missing required fields in body"}), 400
        
    species_profile = get_species_profile(data['species'])
    if not species_profile:
        return jsonify({"error": f"Species '{data['species']}' not found for logging."}), 404
        
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "species": data['species'],
        "caught": data['caught'],
        "notes": data.get('notes', ''),
        "approx_location": f"{round(data['lat'], 2)}, {round(data['lon'], 2)}"
    }
    
    USER_LOGS.append(log_entry)
    
    return jsonify({
        "message": "Feedback logged successfully to in-memory logs.", 
        "total_logs": len(USER_LOGS)
    }), 201

if __name__ == '__main__':
    print("Starting KalAI Flask Backend...") 
    app.run(debug=True, host='0.0.0.0', port=5000)