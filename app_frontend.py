import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta, timezone
import random
import folium
from streamlit_folium import st_folium

# --- Configuration ---
BACKEND_URL = "http://localhost:5000"
DEFAULT_LAT = 60.17 # Helsinki, Finland coordinates
DEFAULT_LON = 24.94


st.set_page_config(
    page_title="🎣 KalAI Fishing Assistant",
    layout="wide"
)

# --- Helper Functions for API Calls ---

def api_call(endpoint, method="GET", params=None, json_data=None):
    """Generic API caller with error handling."""
    url = f"{BACKEND_URL}/{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, params=params)
        elif method == "POST":
            response = requests.post(url, json=json_data)
        
        response.raise_for_status() 
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error connecting to backend: Is the Flask server running? ({e})")
        return None

def get_species_list():
    
    return ["pike", "perch", "trout"]



st.title("🎣 KalAI: AI Fishing Assistant Demo")


if 'lat' not in st.session_state:
    st.session_state.lat = DEFAULT_LAT
    st.session_state.lon = DEFAULT_LON
    st.session_state.species = "pike"
    st.session_state.waterbodies = []


st.sidebar.header("🎯 Input & Prediction")

# Location Input
st.sidebar.markdown("**1. Set Location**")
st.session_state.lat = st.sidebar.number_input("Latitude", value=st.session_state.lat, format="%.4f")
st.session_state.lon = st.sidebar.number_input("Longitude", value=st.session_state.lon, format="%.4f")


species_options = get_species_list()
st.session_state.species = st.sidebar.selectbox("2. Select Target Species", species_options, index=species_options.index(st.session_state.species))


if st.sidebar.button("✨ Run Prediction", key="run_predict"):
    pass 

st.sidebar.markdown("---")
st.sidebar.info("🌐 Backend is simulated for offline demo (no live OpenWeather/Overpass APIs needed).")

# --- Main Content Area ---
tab1, tab2 = st.tabs(["🗺️ Map & Prediction", "📝 Log Catch"])

with tab1:
    
    nearby_data = api_call("nearby", params={"lat": st.session_state.lat, "lon": st.session_state.lon})
    if nearby_data:
        st.session_state.waterbodies = nearby_data.get('waterbodies', [])
    
    # 1. Display Map
    st.header("Nearby Waterbodies")
    map_data = pd.DataFrame({
        'lat': [st.session_state.lat] + [w['lat'] for w in st.session_state.waterbodies],
        'lon': [st.session_state.lon] + [w['lon'] for w in st.session_state.waterbodies],
        'name': ['Current Location'] + [w['name'] for w in st.session_state.waterbodies],
    })

    st.header("Nearby waterbodies (Click to set location)")

    m = folium.Map(
        location=[st.session_state.lat, st.session_state.lon],
        zoom_start=10
    )

    folium.Marker(
        [st.session_state.lat, st.session_state.lon],
        tooltip="Current Location",
        icon=folium.Icon(color="red")
    ).add_to(m)
    
    for w in st.session_state.waterbodies:
        folium.Marker(
            [w['lat'], w['lon']],
            tooltip=w['name'],
            icon=folium.Icon(color="blue", icon="tint")
        ).add_to(m)

    map_data = st_folium(m, width=700, height=500)

    if map_data and map_data.get("last_clicked"):
        st.session_state.lat = map_data["last_clicked"]["lat"]
        st.session_state.lon = map_data["last_clicked"]["lng"]
        st.success(f"Location updated to: ({st.session_state.lat:.4f}, {st.session_state.lon:.4f})")
    
    # 2. Prediction Results
    st.subheader("KalAI Prediction")
    
    result = api_call("predict", params={"lat": st.session_state.lat, "lon": st.session_state.lon, "species": st.session_state.species})
    
    if result:
        col1, col2, col3 = st.columns(3)
        

        with col1:
            score = result['activity_score']
            label = result['activity_label'].upper()
            
            if label == "HIGH": color = "🟢"; st.success(f"{color} {label}")
            elif label == "MEDIUM": color = "🟡"; st.warning(f"{color} {label}")
            else: color = "🔴"; st.error(f"{color} {label}")
            
            st.metric(f"Activity Score for {result['species'].capitalize()}", f"**{score}%**")
            
        # --- Best Time Window Card ---
        with col2:
            st.markdown("##### Best Time Windows")
            for window in result['best_time_windows']:
                # Format time for display
                start_dt = datetime.fromisoformat(window['start']).strftime("%H:%M")
                end_dt = datetime.fromisoformat(window['end']).strftime("%H:%M")
                st.success(f"**{start_dt} - {end_dt}** (Score: {window['score']}%)")

        # --- Lure Suggestions Card ---
        with col3:
            st.markdown("##### Recommended Lures")
            
            if "recommended_lures" in result and result['recommended_lures']:
                for lure in result['recommended_lures']:
                    st.progress(lure["confidence"] / 100)
                    st.markdown(f"**{lure['name']}** - Confidence: {lure['confidence']}%")
            else:
                st.info("No lure recommendations available.")

        st.markdown("---")
        
        st.subheader("Prediction Explanation")
        st.info(result['explanation'])

        # Display the 24-hour heatstrip/chart
        st.subheader("Hourly Activity Forecast")
        
        hourly_scores = []
        for h in range(24):
             current_hour = datetime.now().hour
             time_diff = abs(current_hour + h - 12) # Closer to noon = lower score penalty
             mock_score = score + random.randint(-15, 15) - time_diff * 2
             hourly_scores.append(max(0, min(100, mock_score)))

        chart_data = pd.DataFrame({
            'Hour': [(datetime.now() + timedelta(hours=h)).strftime("%H:00") for h in range(24)],
            'Activity Score': hourly_scores
        }).set_index('Hour')
        
        st.bar_chart(chart_data)

with tab2:
    st.header("Log Your Catch")
    st.markdown("Log successful or unsuccessful fishing attempts to help the model learn.")
    
    with st.form("catch_log_form"):
        log_species = st.selectbox("Species Caught (or Targeted)", species_options, index=species_options.index(st.session_state.species))
        caught_status = st.radio("Did you catch the target species?", ["Caught Fish", "No Catch"], index=0)
        
        caught_bool = caught_status == "Caught Fish"
        
        if caught_bool:
            num_caught = st.number_input("Number Caught", min_value=1, value=1, step=1)
        else:
            num_caught = 0
            
        catch_notes = st.text_area("Notes (e.g., bait used, time of day, weather)")
        
        submit_log = st.form_submit_button("Submit Feedback")

        if submit_log:
            log_data = {
                "lat": st.session_state.lat,
                "lon": st.session_state.lon,
                "species": log_species,
                "caught": caught_bool,
                "notes": f"Count: {num_caught}. {catch_notes}"
            }
            
            response = api_call("feedback", method="POST", json_data=log_data)
            
            if response:
                st.success(f"Feedback logged successfully! Total logs in memory: {response['total_logs']}.")
                st.markdown("##### Minimal data stored (for privacy):")
                st.json({k: v for k, v in log_data.items() if k not in ['lat', 'lon']})