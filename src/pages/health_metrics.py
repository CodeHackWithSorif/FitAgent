import streamlit as st

from database import HealthMetricsCreate

def render():
    st.title("Health Metrics")
    
    user = st.session_state.current_user
    
    with st.form("health_metrics_form"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            weight_kg = st.number_input("Weight (kg)", min_value=30.0, value=user.weight_kg)
            water_intake = st.number_input("Water Intake (liters)", min_value=0.0, value=2.0, step=0.5)
        
        with col2:
            steps = st.number_input("Steps", min_value=0, value=0)
            sleep_hours = st.number_input("Sleep Hours", min_value=0.0, value=8.0, step=0.5)
        
        with col3:
            mood = st.selectbox("Mood", ["happy", "neutral", "stressed", "tired"])
            energy_level = st.selectbox("Energy Level", ["low", "medium", "high"])
        
        notes = st.text_area("Additional Notes", placeholder="Any observations about your health today?")
        
        submitted = st.form_submit_button("Log Metrics", type="primary", use_container_width=True)
        
        if submitted:
            try:
                db_service = st.session_state.db_service
                
                bmi = weight_kg / ((user.height_cm / 100) ** 2)
                
                metrics_log = HealthMetricsCreate(
                    user_id=user.id,
                    weight_kg=weight_kg,
                    bmi=bmi,
                    water_intake_liters=water_intake,
                    steps=steps,
                    sleep_hours=sleep_hours if sleep_hours > 0 else None,
                    mood=mood,
                    energy_level=energy_level,
                    notes=notes if notes else None
                )
                
                db_service.log_health_metrics(metrics_log)
                st.success("Health metrics logged!")
            
            except Exception as e:
                st.error(f"Error logging metrics: {str(e)}")

