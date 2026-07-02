import streamlit as st

from app_utils import *
from database import UserCreate

def render():
    st.title("Create Your Profile")
    st.markdown("Tell us about yourself so we can create a personalized health plan.")
    
    with st.form("create_profile_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Full Name", placeholder="e.g., Raj Kumar")
            age = st.number_input("Age", min_value=15, max_value=100, value=30)
            gender = st.selectbox("Gender", ["Male", "Female", "Other"])
            height_cm = st.number_input("Height (cm)", min_value=140, max_value=220, value=175)
        
        with col2:
            weight_kg = st.number_input("Weight (kg)", min_value=30, max_value=200, value=75)
            goal = st.selectbox(
                "Primary Goal",
                ["weight_loss", "muscle_gain", "maintenance", "endurance"],
                format_func=lambda x: x.replace("_", " ").title()
            )
            diet_preference = st.selectbox(
                "Diet Preference",
                ["vegetarian", "non_veg", "vegan"],
                format_func=lambda x: x.replace("_", " ").title()
            )
        
        st.markdown("---")
        st.markdown("### Additional Information")
        
        col1, col2 = st.columns(2)
        with col1:
            daily_water_goal = st.number_input("Daily Water Goal (liters)", min_value=1.0, max_value=5.0, value=2.5, step=0.5)
            daily_steps_goal = st.number_input("Daily Steps Goal", min_value=1000, max_value=50000, value=10000, step=1000)
        
        with col2:
            dietary_restrictions = st.text_area(
                "Dietary Restrictions (if any)",
                placeholder="e.g., No gluten, No dairy, Nut allergy",
                height=90
            )
            health_conditions = st.text_area(
                "Health Conditions (if any)",
                placeholder="e.g., Diabetes, Hypertension, PCOS",
                height=90
            )
        
        lifestyle = st.text_area(
            "Describe Your Lifestyle",
            placeholder="e.g., I work 9-5 at a desk, I want to lose weight and gain energy. I prefer home-cooked meals.",
            height=100
        )
        
        submitted = st.form_submit_button("Create Profile", type="primary", use_container_width=True)
        
        if submitted:
            if not name:
                st.error("Please enter your name.")
            elif not lifestyle:
                st.error("Please describe your lifestyle.")
            else:
                try:
                    db_service = st.session_state.db_service
                    
                    user_create = UserCreate(
                        name=name,
                        age=age,
                        gender=gender,
                        height_cm=height_cm,
                        weight_kg=weight_kg,
                        goal=goal,
                        diet_preference=diet_preference,
                        daily_water_goal=daily_water_goal,
                        daily_steps_goal=daily_steps_goal,
                        dietary_restrictions=dietary_restrictions if dietary_restrictions else None,
                        health_conditions=health_conditions if health_conditions else None
                    )
                    
                    user = db_service.create_user(user_create)
                    
                    st.session_state.user_id = user.id
                    st.session_state.current_user = user
                    
                    st.success(f"Profile created successfully! Welcome, {name}!")
                    st.balloons()
                    
                    # Redirect to dashboard
                    import time
                    time.sleep(1)
                    set_page("dashboard")
                    st.rerun()
                
                except Exception as e:
                    st.error(f"Error creating profile: {str(e)}")

