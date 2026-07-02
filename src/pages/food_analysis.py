import streamlit as st
import os

from nutritional_engine import analyze_food_item

def render():
    st.title("Food Nutritional Analysis")
    st.markdown("Deep dive into nutritional profiles and Ayurvedic benefits of any food item.")
    
    # No API key check required as we use Vertex AI with Default Credentials
    
    # Two analysis modes
    analysis_mode = st.radio("Choose Analysis Type:", ["Quick Analysis", "Detailed Analysis"], horizontal=True)
    
    food_item = st.text_input(
        "Enter food item to analyze",
        placeholder="e.g., Paneer butter masala, Dal with roti, Spinach salad"
    )
    
    if st.button("Analyze", type="primary", use_container_width=True):
        if not food_item:
            st.error("Please enter a food item.")
        else:
            with st.spinner("Analyzing food..."):
                try:
                    if analysis_mode == "Quick Analysis":
                        # Simple text analysis
                        analysis = analyze_food_item(food_item)
                        st.markdown("### Nutritional & Ayurvedic Analysis")
                        st.write(analysis)
                    
                    else:
                        # Detailed structured analysis
                        from nutritional_engine import analyze_food_item_structured
                        analysis = analyze_food_item_structured(food_item)
                        
                        st.markdown("### Detailed Food Analysis")
                        
                        # Create tabs for different sections
                        tab1, tab2, tab3, tab4 = st.tabs(["Nutrition", "Ayurvedic", "Recommendations", "Benefits"])
                        
                        with tab1:
                            st.markdown(f"#### {analysis.food_name}")
                            st.write(f"**Serving Size:** {analysis.serving_size}")
                            
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("Calories", f"{analysis.nutrition.calories:.0f}")
                            with col2:
                                st.metric("Protein", f"{analysis.nutrition.protein_g:.1f}g")
                            with col3:
                                st.metric("Carbs", f"{analysis.nutrition.carbs_g:.1f}g")
                            with col4:
                                st.metric("Fat", f"{analysis.nutrition.fat_g:.1f}g")
                            
                            st.write(f"**Macro Ratios:** {analysis.macronutrient_ratio}")
                            
                            if analysis.nutrition.fiber_g:
                                st.write(f"**Fiber:** {analysis.nutrition.fiber_g:.1f}g")
                            if analysis.nutrition.sugar_g:
                                st.write(f"**Sugar:** {analysis.nutrition.sugar_g:.1f}g")
                            if analysis.nutrition.sodium_mg:
                                st.write(f"**Sodium:** {analysis.nutrition.sodium_mg:.0f}mg")
                        
                        with tab2:
                            st.markdown("#### Ayurvedic Benefits")
                            for benefit in analysis.ayurvedic_benefits:
                                with st.expander(f"{benefit.benefit}"):
                                    st.write(f"**Dosha Impact:** {benefit.dosha_impact}")
                                    st.write(f"**Principle:** {benefit.supporting_principle}")
                        
                        with tab3:
                            st.markdown("#### Recommendations")
                            st.write(f"**Best Time to Eat:** {analysis.best_time_to_eat}")
                            st.write(f"**Digestibility:** {analysis.digestibility}")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write("**Pairs Well With:**")
                                for food in analysis.pairs_well_with:
                                    st.write(f"✓ {food}")
                            
                            with col2:
                                st.write("**Avoid With:**")
                                for food in analysis.avoid_with:
                                    st.write(f"✗ {food}")
                            
                            if analysis.precautions:
                                st.warning(f"**Precautions:** {analysis.precautions}")
                        
                        with tab4:
                            st.markdown("#### Best For Health Goals")
                            for goal in analysis.ideal_for_goal:
                                st.write(f"• {goal}")
                            
                            st.markdown("#### Interesting Fact")
                            st.info(analysis.interesting_fact)
                
                except Exception as e:
                    st.error(f"Error analyzing food: {str(e)}")
                    st.info("Ensure your Google Cloud credentials (ADC) are configured and you have an internet connection.")
    
    # Display food database for quick reference
    st.markdown("---")
    st.markdown("### Indian Food Database (Quick Reference)")
    
    from nutritional_engine import INDIAN_FOOD_DATABASE
    
    db_foods = []
    for key, food in INDIAN_FOOD_DATABASE.items():
        db_foods.append({
            "Food": food["name"],
            "Serving": food["serving_size"],
            "Calories": food["calories"],
            "Protein (g)": food["protein_g"],
            "Carbs (g)": food["carbs_g"],
            "Fat (g)": food["fat_g"],
        })
    
    import pandas as pd
    df = pd.DataFrame(db_foods)
    st.dataframe(df, use_container_width=True)

