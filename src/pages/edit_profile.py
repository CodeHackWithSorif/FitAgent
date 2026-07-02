import streamlit as st


def render():
    st.title("Edit Profile")
    
    user = st.session_state.current_user
    
    with st.form("edit_profile_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Full Name", value=user.name)
            age = st.number_input("Age", min_value=15, max_value=100, value=user.age)
            weight_kg = st.number_input("Weight (kg)", min_value=30, max_value=200, value=user.weight_kg)
        
        with col2:
            goal = st.selectbox("Primary Goal", ["weight_loss", "muscle_gain", "maintenance", "endurance"], 
                               index=["weight_loss", "muscle_gain", "maintenance", "endurance"].index(user.goal),
                               format_func=lambda x: x.replace("_", " ").title())
            daily_water_goal = st.number_input("Daily Water Goal (liters)", min_value=1.0, max_value=5.0, value=user.daily_water_goal, step=0.5)
            daily_steps_goal = st.number_input("Daily Steps Goal", min_value=1000, max_value=50000, value=user.daily_steps_goal, step=1000)
        
        dietary_restrictions = st.text_area("Dietary Restrictions", value=user.dietary_restrictions or "")
        health_conditions = st.text_area("Health Conditions", value=user.health_conditions or "")
        
        submitted = st.form_submit_button("Update Profile", type="primary", use_container_width=True)
        
        if submitted:
            try:
                from database import UserBase
                db_service = st.session_state.db_service
                
                user_update = UserBase(
                    name=name,
                    age=age,
                    gender=user.gender,
                    height_cm=user.height_cm,
                    weight_kg=weight_kg,
                    goal=goal,
                    diet_preference=user.diet_preference,
                    daily_water_goal=daily_water_goal,
                    daily_steps_goal=daily_steps_goal,
                    dietary_restrictions=dietary_restrictions if dietary_restrictions else None,
                    health_conditions=health_conditions if health_conditions else None
                )
                
                updated_user = db_service.update_user(user.id, user_update)
                st.session_state.current_user = updated_user
                
                st.success("Profile updated successfully!")
            
            except Exception as e:
                st.error(f"Error updating profile: {str(e)}")

