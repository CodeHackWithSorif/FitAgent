import streamlit as st

from database import WorkoutLogCreate

def render():
    st.title("Log Workout")
    
    user = st.session_state.current_user
    
    with st.form("log_workout_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            exercise_name = st.text_input("Exercise Name", placeholder="e.g., Running, Yoga, Weight Training")
            exercise_type = st.selectbox("Exercise Type", ["cardio", "strength", "flexibility", "sports"])
            duration_minutes = st.number_input("Duration (minutes)", min_value=1, value=30)
        
        with col2:
            intensity = st.selectbox("Intensity", ["low", "moderate", "high"])
            calories_burned = st.number_input("Calories Burned", min_value=0, value=200)
            distance_km = st.number_input("Distance (km) - if applicable", min_value=0.0, value=0.0, step=0.1)
        
        sets_reps = st.text_input("Sets & Reps - if applicable", placeholder="e.g., 3x10, 4x12")
        notes = st.text_area("Notes", placeholder="How did you feel? Any observations?")
        
        submitted = st.form_submit_button("Log Workout", type="primary", use_container_width=True)
        
        if submitted:
            if not exercise_name:
                st.error("Please enter exercise name.")
            else:
                try:
                    db_service = st.session_state.db_service
                    
                    workout_log = WorkoutLogCreate(
                        user_id=user.id,
                        exercise_name=exercise_name,
                        exercise_type=exercise_type,
                        duration_minutes=duration_minutes,
                        intensity=intensity,
                        calories_burned=calories_burned if calories_burned > 0 else None,
                        distance_km=distance_km if distance_km > 0 else None,
                        sets_reps=sets_reps if sets_reps else None,
                        notes=notes if notes else None
                    )
                    
                    db_service.log_workout(workout_log)
                    st.success(f"Workout logged: {exercise_name}")
                
                except Exception as e:
                    st.error(f"Error logging workout: {str(e)}")

