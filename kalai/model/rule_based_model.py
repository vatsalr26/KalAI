from datetime import datetime
from kalai.utils.environmental import get_moon_phase, time_of_day_label

# Score Weights (Total 100 max)
WEIGHTS = {
    "temperature": 40,
    "time_of_day": 30,
    "moon_phase": 20,
    "wind_speed": 10
}

# Mapping of Moon Phase to a simple multiplier (Solunar Theory)
MOON_MULTIPLIERS = {
    "New Moon": 1.15,
    "Full Moon": 1.2,
    "Waxing Gibbous": 1.1,
    # Others are baseline or slightly lower
}

def rule_based_activity_score(species_profile: dict, weather_data: dict, current_time: datetime) -> tuple[int, str]:
    """Computes a deterministic activity score (0-100) and an explanation."""
    
    score = 0
    explanations = []
    
    # --- 1. Temperature Score (Weight: 40) ---
    water_temp = weather_data.get("water_temp_c", 15.0)
    low = species_profile["best_temp_low"]
    high = species_profile["best_temp_high"]
    
    if low <= water_temp <= high:
        temp_score = WEIGHTS["temperature"]
        explanations.append(f"Water temp ({water_temp:.1f}°C) is **optimal**.")
    elif (low - 3) <= water_temp <= (high + 3):
        temp_score = WEIGHTS["temperature"] * 0.75
        explanations.append(f"Water temp ({water_temp:.1f}°C) is acceptable, near preferred range.")
    else:
        temp_score = WEIGHTS["temperature"] * 0.2
        explanations.append(f"Water temp ({water_temp:.1f}°C) is too far from optimal ({low}°C-{high}°C).")

    score += temp_score
    
    # --- 2. Time of Day Score (Weight: 30) ---
    current_h = current_time.hour
    time_label = time_of_day_label(current_h, weather_data["sunrise_h"], weather_data["sunset_h"])
    time_base_score = species_profile["preferred_times_json"].get(time_label, 0)
    
    time_score = (time_base_score / 100) * WEIGHTS["time_of_day"]
    
    score += time_score
    explanations.append(f"Time is **{time_label}**, which is a **{time_base_score}%** preferred window.")
    
    # --- 3. Moon Phase Score (Weight: 20) ---
    moon_phase = weather_data.get("moon_phase", "Waxing Gibbous")
    moon_multiplier = MOON_MULTIPLIERS.get(moon_phase, 1.0)
    
    moon_score = WEIGHTS["moon_phase"] * moon_multiplier * 0.5 
    
    score += moon_score
    explanations.append(f"Moon phase is **{moon_phase}**, which suggests **higher** activity.")
    
    # --- 4. Wind/Weather Score (Weight: 10) ---
    wind_speed = weather_data.get("wind_speed_ms", 3.0)
    cloud_cover = weather_data.get("cloud_cover_percent", 50)
    
    wind_score = 0
    if 1.5 <= wind_speed <= 5.0: # Light to moderate chop can stimulate feeding
        wind_score += 5
    if cloud_cover >= 75: # Overcast is good for most fish
        wind_score += 5
    
    wind_score = min(WEIGHTS['wind_speed'], max(0, wind_score)) # Clamp
    score += wind_score
    
    # Final clamping and explanation
    final_score = int(min(100, max(0, score)))
    
    final_explanation = (
        f"Prediction for **{species_profile['display_name']}**: "
        f"{explanations[0]}, {explanations[1]}, and the "
        f"{explanations[2].lower().replace('full moon', 'strong moon phase')}."
    )
    
    return final_score, final_explanation