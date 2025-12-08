import math
from datetime import datetime, timezone
import random

def get_moon_phase(dt: datetime) -> tuple[str, float]:
    """Calculates the Moon Phase and illumination fraction for a given datetime (simplified)."""

    known_new_moon = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)
    dt_utc = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
    delta = dt_utc - known_new_moon
    days_since_new_moon = delta.total_seconds() / 86400 

    cycle_fraction = days_since_new_moon % 29.530588
    
    # Approximate illumination fraction (0.0 to 1.0)
    illumination_frac = 0.5 * (1 - math.cos(2 * math.pi * (cycle_fraction / 29.530588)))

    # Determine phase name based on days passed
    if 0 <= cycle_fraction < 1.84: phase = "New Moon"
    elif 1.84 <= cycle_fraction < 5.53: phase = "Waxing Crescent"
    elif 5.53 <= cycle_fraction < 9.22: phase = "First Quarter"
    elif 9.22 <= cycle_fraction < 12.91: phase = "Waxing Gibbous"
    elif 12.91 <= cycle_fraction < 16.6: phase = "Full Moon"
    elif 16.6 <= cycle_fraction < 20.29: phase = "Waning Gibbous"
    elif 20.29 <= cycle_fraction < 23.98: phase = "Last Quarter"
    elif 23.98 <= cycle_fraction < 27.67: phase = "Waning Crescent"
    else: phase = "New Moon"
        
    return phase, round(illumination_frac, 2)

def time_of_day_label(hour: int, sunrise_h: int, sunset_h: int) -> str:
    """Classifies the time of day into dawn/dusk/day/night."""
    if (sunrise_h - 2) <= hour < sunrise_h:
        return "dawn"
    elif sunrise_h <= hour < sunset_h:
        return "day"
    elif sunset_h <= hour < (sunset_h + 2):
        return "dusk"
    else:
        return "night"

# --- DS18B20 Sensor Simulation ---
def read_water_sensor_mock() -> float:
    """
    Mocks reading the DS18B20 water temperature sensor. 
    In a Raspberry Pi environment, this would use 'w1thermsensor'.
    """
    try:

        from w1thermsensor import W1ThermSensor, NoSensorFoundError
        sensor = W1ThermSensor()
        temp_c = sensor.get_temperature()
        return round(temp_c, 1)
    except (ImportError, NoSensorFoundError):
        # Fallback to simulated data (8.0 to 18.0 C range for freshwater)
        return round(random.uniform(8.0, 18.0), 1)