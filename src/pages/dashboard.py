import streamlit as st

from app_utils import *

def render():
    st.title("Dashboard")
    
    user = st.session_state.current_user
    db_service = st.session_state.db_service
    
    # Header with user info
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Current Weight", f"{user.weight_kg} kg")
    with col2:
        bmi = user.weight_kg / ((user.height_cm / 100) ** 2)
        st.metric("BMI", f"{bmi:.1f}")
    with col3:
        st.metric("Goal", user.goal.replace("_", " ").title())
    with col4:
        st.metric("Diet", user.diet_preference.title())
    
    st.markdown("---")
    
    # Today's stats
    st.markdown("### Today's Summary")
    
    today_calories = db_service.get_today_calories(user.id)
    today_burned = db_service.get_today_calories_burned(user.id)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Calories Consumed", f"{today_calories:.0f} cal")
    with col2:
        st.metric("Calories Burned", f"{today_burned:.0f} cal")
    with col3:
        net = today_calories - today_burned
        st.metric("Net Calories", f"{net:.0f} cal")
    
    st.markdown("---")
    display_due_reminders(user)
    
    # Recent activity
    st.markdown("### Recent Activity")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Last 7 Days - Meals")
        meals = db_service.get_user_meal_logs(user.id, days=7)
        if meals:
            for meal in meals[:5]:
                st.write(f"  {meal.meal_name} ({meal.meal_type}) - {meal.calories:.0f} cal")
        else:
            st.info("No meals logged yet")
    
    with col2:
        st.markdown("#### Last 7 Days - Workouts")
        workouts = db_service.get_user_workout_logs(user.id, days=7)
        if workouts:
            for workout in workouts[:5]:
                st.write(f"  {workout.exercise_name} ({workout.exercise_type}) - {workout.duration_minutes} min")
        else:
            st.info("No workouts logged yet")

