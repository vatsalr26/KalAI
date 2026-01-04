# This algorithm will reccomend the lure 

def feeding_mode(activity_score: int) -> str:
    if activity_score > 75:
        return "aggressive"
    elif activity_score >= 40:
        return "moderate"
    else:
        return "passive"
    
def score_lure(lure: dict, context: dict) -> int:
    score = 20

    if context["feeding_mode"] in lure["best_modes"]:
        score += 30

    if context["water_temp"] < 10 and lure["speed"] == "slow":
        score += 15
    elif context["water_temp"] >= 10 and lure["speed"] == "fast":
        score += 10

    if context["cloud_cover"] > 70 and lure["visibility"] == "high":
        score += 15

    if context["wind_speed"] > 4 and lure["type"] == "reaction":
        score += 10

    return min(score, 100)

def recommended_lures(species_profile: dict, context: dict, top_n: int = 3) -> list:
    scored = []

    for lure in species_profile.get("lures", []):
        scored.append({
            "name": lure["name"],
            "confidence": score_lure(lure, context)
        })

    return sorted(scored, key=lambda x: x["confidence"], reverse=True)[:top_n]