import streamlit as st

from database import MealLogCreate

def render():
    st.title("Log Meal")
    
    user = st.session_state.current_user
    
    with st.form("log_meal_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            meal_name = st.text_input("Meal Name", placeholder="e.g., Chicken Biryani")
            meal_type = st.selectbox("Meal Type", ["breakfast", "lunch", "dinner", "snack"])
            quantity = st.text_input("Quantity", placeholder="e.g., 1 bowl, 150g")
        
        with col2:
            calories = st.number_input("Calories", min_value=0, value=300)
            protein_g = st.number_input("Protein (g)", min_value=0.0, value=0.0, step=0.5)
            carbs_g = st.number_input("Carbs (g)", min_value=0.0, value=0.0, step=0.5)
        
        fat_g = st.number_input("Fat (g)", min_value=0.0, value=0.0, step=0.5)
        fiber_g = st.number_input("Fiber (g)", min_value=0.0, value=0.0, step=0.5)
        ingredients = st.text_area("Ingredients (comma-separated)", placeholder="e.g., rice, chicken, onion, spices")
        
        submitted = st.form_submit_button("Log Meal", type="primary", use_container_width=True)
        
        if submitted:
            if not meal_name:
                st.error("Please enter meal name.")
            else:
                try:
                    db_service = st.session_state.db_service
                    
                    meal_log = MealLogCreate(
                        user_id=user.id,
                        meal_name=meal_name,
                        meal_type=meal_type,
                        quantity=quantity,
                        calories=calories,
                        protein_g=protein_g if protein_g > 0 else None,
                        carbs_g=carbs_g if carbs_g > 0 else None,
                        fat_g=fat_g if fat_g > 0 else None,
                        fiber_g=fiber_g if fiber_g > 0 else None,
                        ingredients=ingredients if ingredients else None
                    )
                    
                    db_service.log_meal(meal_log)
                    st.success(f"Meal logged: {meal_name}")
                
                except Exception as e:
                    st.error(f"Error logging meal: {str(e)}")

