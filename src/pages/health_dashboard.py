import streamlit as st
from datetime import datetime
import plotly.graph_objects as go

from dashboard_engine import build_weight_trend_data, calculate_progress_metrics, calculate_goal_progress_items, get_health_insights

def render():
    """Health Metrics Dashboard - Track progress with visualizations."""
    st.title("📊 Health Metrics Dashboard")
    
    if st.session_state.user_id is None:
        st.error("Please load a profile first.")
        return
    
    db_service = st.session_state.db_service
    user = st.session_state.current_user
    
    # Get health metrics data
    health_metrics_7d = db_service.get_user_health_metrics(user.id, days=7)
    health_metrics_30d = db_service.get_user_health_metrics(user.id, days=30)
    
    # Get meal logs for calorie tracking
    meal_logs_7d = db_service.get_user_meal_logs(user.id, days=7)
    
    if not health_metrics_7d and not meal_logs_7d:
        st.info("📈 Start logging health metrics and meals to see your dashboard!")
        return
    
    # Convert data to dictionaries for processing
    metrics_data_7d = [
        {
            "date": m.recorded_at,
            "weight_kg": m.weight_kg,
            "bmi": m.bmi,
            "water_liters": m.water_intake_liters or 0,
            "steps": m.steps or 0,
            "sleep_hours": m.sleep_hours,
            "mood": m.mood,
            "energy_level": m.energy_level,
        }
        for m in health_metrics_7d
    ]
    
    metrics_data_30d = [
        {
            "date": m.recorded_at,
            "weight_kg": m.weight_kg,
            "bmi": m.bmi,
            "water_liters": m.water_intake_liters or 0,
            "steps": m.steps or 0,
            "sleep_hours": m.sleep_hours,
            "mood": m.mood,
            "energy_level": m.energy_level,
        }
        for m in health_metrics_30d
    ]
    
    meal_data_7d = [
        {
            "date": m.logged_at,
            "calories": m.calories or 0,
            "protein_g": m.protein_g or 0,
            "carbs_g": m.carbs_g or 0,
            "fat_g": m.fat_g or 0,
        }
        for m in meal_logs_7d
    ]
    
    # Dashboard tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "Weight & BMI",
        "Calories & Macros",
        "Daily Metrics",
        "Goal Progress",
    ])
    
    # --- TAB 1: Weight & BMI ---
    with tab1:
        st.subheader("Weight & BMI Tracking")
        
        time_range = st.radio(
            "Select time range:",
            ["Last 7 Days", "Last 30 Days"],
            horizontal=True,
        )
        
        data_to_use = metrics_data_7d if time_range == "Last 7 Days" else metrics_data_30d
        weight_trend = build_weight_trend_data(data_to_use, user.goal)
        
        if weight_trend["dates"]:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if weight_trend["weights"]:
                    latest_weight = weight_trend["weights"][-1]
                    st.metric(
                        "Current Weight",
                        f"{latest_weight} kg",
                        f"{weight_trend['total_change_kg']} kg",
                    )
            
            with col2:
                if weight_trend["bmi"]:
                    latest_bmi = weight_trend["bmi"][-1]
                    st.metric("Current BMI", f"{latest_bmi}", weight_trend["trend"])
            
            with col3:
                st.metric("Goal", user.goal.replace("_", " ").title(), weight_trend["trend"])
            
            # Weight trend chart
            fig_weight = go.Figure()
            fig_weight.add_trace(go.Scatter(
                x=weight_trend["dates"],
                y=weight_trend["weights"],
                mode="lines+markers",
                name="Weight (kg)",
                line=dict(color="#FF6B6B", width=3),
                marker=dict(size=8),
            ))
            fig_weight.update_layout(
                title="Weight Trend",
                xaxis_title="Date",
                yaxis_title="Weight (kg)",
                hovermode="x unified",
                template="plotly_white",
                height=400,
            )
            st.plotly_chart(fig_weight, use_container_width=True)
            
            # BMI trend chart
            if weight_trend["bmi"]:
                fig_bmi = go.Figure()
                fig_bmi.add_trace(go.Scatter(
                    x=weight_trend["dates"],
                    y=weight_trend["bmi"],
                    mode="lines+markers",
                    name="BMI",
                    line=dict(color="#4ECDC4", width=3),
                    marker=dict(size=8),
                    fill="tozeroy",
                ))
                fig_bmi.add_hline(y=25, line_dash="dash", line_color="orange", annotation_text="Overweight")
                fig_bmi.add_hline(y=18.5, line_dash="dash", line_color="green", annotation_text="Underweight")
                fig_bmi.update_layout(
                    title="BMI Trend with Health Zones",
                    xaxis_title="Date",
                    yaxis_title="BMI",
                    hovermode="x unified",
                    template="plotly_white",
                    height=400,
                )
                st.plotly_chart(fig_bmi, use_container_width=True)
        else:
            st.info("No weight data available yet.")
    
    # --- TAB 2: Calories & Macros ---
    with tab2:
        st.subheader("Calorie & Macro Tracking")
        
        # Determine daily calorie goal based on user goal
        calorie_goals = {
            "weight_loss": 1800,
            "muscle_gain": 2500,
            "maintenance": 2000,
            "endurance": 2200,
        }
        target_calories = calorie_goals.get(user.goal, 2000)
        
        if meal_data_7d:
            # Group calories by date for cleaner visualization
            daily_totals = {}
            for meal in meal_data_7d:
                date_str = meal["date"].strftime("%m-%d") if isinstance(meal["date"], datetime) else str(meal["date"])
                if date_str not in daily_totals:
                    daily_totals[date_str] = {"calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0}
                daily_totals[date_str]["calories"] += meal["calories"]
                daily_totals[date_str]["protein_g"] += meal["protein_g"]
                daily_totals[date_str]["carbs_g"] += meal["carbs_g"]
                daily_totals[date_str]["fat_g"] += meal["fat_g"]
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                avg_cal = sum(d["calories"] for d in daily_totals.values()) / len(daily_totals)
                st.metric("Avg Daily Calories", f"{int(avg_cal)}", f"vs {target_calories}")
            
            with col2:
                avg_protein = sum(d["protein_g"] for d in daily_totals.values()) / len(daily_totals)
                st.metric("Avg Protein", f"{int(avg_protein)}g", "daily")
            
            with col3:
                st.metric("Goal Calories", f"{target_calories}", "per day")
            
            # Calorie trend chart
            dates_list = list(daily_totals.keys())
            calories_list = [daily_totals[d]["calories"] for d in dates_list]
            
            fig_cal = go.Figure()
            fig_cal.add_trace(go.Bar(
                x=dates_list,
                y=calories_list,
                name="Calories",
                marker=dict(color="#95E1D3"),
            ))
            fig_cal.add_hline(
                y=target_calories,
                line_dash="dash",
                line_color="red",
                annotation_text=f"Target: {target_calories}",
            )
            fig_cal.update_layout(
                title="Daily Calorie Intake",
                xaxis_title="Date",
                yaxis_title="Calories",
                hovermode="x",
                template="plotly_white",
                height=400,
            )
            st.plotly_chart(fig_cal, use_container_width=True)
            
            # Macro breakdown (latest day)
            latest_date = dates_list[-1]
            latest_macros = daily_totals[latest_date]
            
            fig_macros = go.Figure(data=[
                go.Pie(
                    labels=["Protein", "Carbs", "Fat"],
                    values=[latest_macros["protein_g"], latest_macros["carbs_g"], latest_macros["fat_g"]],
                    marker=dict(colors=["#FF6B6B", "#4ECDC4", "#FFE66D"]),
                )
            ])
            fig_macros.update_layout(
                title=f"Macro Distribution - {latest_date}",
                height=400,
            )
            st.plotly_chart(fig_macros, use_container_width=True)
        else:
            st.info("Start logging meals to see calorie trends.")
    
    # --- TAB 3: Daily Metrics ---
    with tab3:
        st.subheader("Daily Health Metrics")
        
        if metrics_data_7d:
            col1, col2, col3, col4 = st.columns(4)
            
            latest_metric = metrics_data_7d[-1]
            
            with col1:
                water_val = latest_metric.get("water_liters", 0)
                st.metric("Water Intake", f"{water_val}L", "today")
            
            with col2:
                steps_val = latest_metric.get("steps", 0)
                st.metric("Steps", f"{steps_val}", "today")
            
            with col3:
                sleep_val = latest_metric.get("sleep_hours")
                st.metric("Sleep", f"{sleep_val}h" if sleep_val else "N/A", "last night")
            
            with col4:
                mood_val = latest_metric.get("mood", "N/A")
                st.metric("Mood", mood_val.title() if mood_val else "N/A", "today")
            
            # Water intake trend
            water_dates = [m["date"].strftime("%m-%d") if isinstance(m["date"], datetime) else str(m["date"]) for m in metrics_data_7d]
            water_values = [m["water_liters"] for m in metrics_data_7d]
            
            fig_water = go.Figure()
            fig_water.add_trace(go.Scatter(
                x=water_dates,
                y=water_values,
                mode="lines+markers",
                name="Water (L)",
                line=dict(color="#4ECDC4", width=3),
                fill="tozeroy",
            ))
            fig_water.add_hline(y=2.5, line_dash="dash", line_color="green", annotation_text="Goal: 2.5L")
            fig_water.update_layout(
                title="Water Intake Trend",
                xaxis_title="Date",
                yaxis_title="Liters",
                template="plotly_white",
                height=350,
            )
            st.plotly_chart(fig_water, use_container_width=True)
            
            # Steps trend
            steps_dates = [m["date"].strftime("%m-%d") if isinstance(m["date"], datetime) else str(m["date"]) for m in metrics_data_7d]
            steps_values = [m["steps"] for m in metrics_data_7d]
            
            fig_steps = go.Figure()
            fig_steps.add_trace(go.Bar(
                x=steps_dates,
                y=steps_values,
                name="Steps",
                marker=dict(color="#FFE66D"),
            ))
            fig_steps.add_hline(y=10000, line_dash="dash", line_color="green", annotation_text="Goal: 10k")
            fig_steps.update_layout(
                title="Daily Steps",
                xaxis_title="Date",
                yaxis_title="Steps",
                template="plotly_white",
                height=350,
            )
            st.plotly_chart(fig_steps, use_container_width=True)
        else:
            st.info("No health metrics logged yet.")
    
    # --- TAB 4: Goal Progress ---
    with tab4:
        st.subheader("Goal Progress Tracking")
        
        progress = calculate_progress_metrics(
            metrics_data_30d,
            user.goal,
            target_weight=None,
            target_calories=2000,
            target_steps=10000,
            target_water=2.5,
        )
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Days Tracked", progress.days_tracked, "this month")
        
        with col2:
            if progress.weight_change_kg is not None:
                st.metric("Weight Change", f"{progress.weight_change_kg}kg")
        
        with col3:
            st.metric("Avg Water/Day", f"{progress.average_water}L")
        
        st.markdown("---")
        
        # Goal progress items
        latest_metric = metrics_data_7d[-1] if metrics_data_7d else {}
        goals = calculate_goal_progress_items(
            user.goal,
            latest_metric.get("weight_kg"),
            user.weight_kg,
            user.height_cm,
        )
        
        for goal in goals:
            with st.container(border=True):
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.write(f"**{goal.goal_name}**")
                    st.write(f"{goal.current_value} / {goal.target_value} {goal.unit}")
                    st.write(goal.recommendation)
                with col2:
                    st.metric("Progress", f"{int(goal.progress_percent)}%")
                    progress_bar_html = f"""
                    <div style="background-color: #f0f0f0; border-radius: 5px; height: 10px; width: 100%;">
                        <div style="background-color: #4ECDC4; height: 100%; width: {goal.progress_percent}%; border-radius: 5px;"></div>
                    </div>
                    """
                    st.markdown(progress_bar_html, unsafe_allow_html=True)
        
        # Health insights
        st.markdown("---")
        st.subheader("📈 Health Insights")
        insights = get_health_insights(progress, user.goal)
        for insight in insights:
            st.write(insight)

