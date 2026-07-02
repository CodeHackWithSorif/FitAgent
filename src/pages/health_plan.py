import streamlit as st
import os

from app_utils import *
from planning_engine import generate_health_plan
from alarm_logic import simulate_alarm_sync
from database import ReminderCreate
from reminder_engine import generate_meal_reminders, generate_water_reminders, generate_workout_reminders, generate_sleep_reminder, generate_mood_check_reminder

def render():
    st.title("Generate Health Plan")
    
    user = st.session_state.current_user
    db_service = st.session_state.db_service
    
    st.markdown(f"### Generating plan for {user.name}")
    st.markdown(f"- **Goal:** {user.goal.replace('_', ' ').title()}")
    st.markdown(f"- **Diet:** {user.diet_preference.title()}")
    if user.health_conditions:
        st.markdown(f"- **Health Conditions:** {user.health_conditions}")
    if user.dietary_restrictions:
        st.markdown(f"- **Dietary Restrictions:** {user.dietary_restrictions}")
    
    # No API key check required as we use Vertex AI with Default Credentials
    
    if st.button("Generate Personalized Plan", type="primary", use_container_width=True):
        with st.spinner("Analyzing your profile and generating personalized plan..."):
            try:
                # Get recent meal and workout history
                meals = db_service.get_user_meal_logs(user.id, days=7)
                workouts = db_service.get_user_workout_logs(user.id, days=7)
                
                recent_meals = [f"{m.meal_name} ({m.calories:.0f} cal)" for m in meals] if meals else None
                recent_workouts = [f"{w.exercise_name} ({w.duration_minutes} min)" for w in workouts] if workouts else None
                
                # Generate personalized plan
                plan = generate_health_plan(
                    user_goal=user.goal,
                    diet_preference=user.diet_preference,
                    age=user.age,
                    weight_kg=user.weight_kg,
                    height_cm=user.height_cm,
                    health_conditions=user.health_conditions,
                    dietary_restrictions=user.dietary_restrictions,
                    recent_meals=recent_meals,
                    recent_workouts=recent_workouts,
                )
                
                st.session_state.plan = plan
                
                # Display plan
                st.markdown("---")
                st.markdown("## Your Personalized Health Plan")
                st.markdown(f"**Goal:** {plan.user_goal}")
                st.markdown(f"**Summary:** {plan.summary}")
                
                # Display daily schedule
                st.markdown("### Daily Schedule")
                for item in plan.daily_schedule:
                    with st.expander(f"{item.time} - {item.title} ({item.activity_type})"):
                        st.write(f"**Action:** {item.description}")
                        if item.medicinal_value:
                            st.info(f"**Health Benefit:** {item.medicinal_value}")
                        if item.calories_target:
                            st.write(f"Calorie Target: {item.calories_target}")
                        if item.duration_minutes:
                            st.write(f"Duration: {item.duration_minutes} minutes")
                
                # Weekly focus
                st.markdown("### Weekly Focus")
                st.markdown(plan.weekly_focus)
                
                # Tips
                st.markdown("### Tips & Warnings")
                for tip in plan.tips_and_warnings:
                    st.write(f"• {tip}")
                
                # Create reminders from plan
                st.markdown("---")
                if st.button("Create Reminders from Plan", type="secondary"):
                    with st.spinner("Creating reminders from your health plan..."):
                        settings = get_or_create_reminder_settings(user.id)

                        reminders_to_save = []
                        if settings.meal_reminders_enabled:
                            reminders_to_save.extend(
                                generate_meal_reminders(
                                    plan.dict(),
                                    user.id,
                                    settings.meal_reminder_time_before_minutes,
                                )
                            )

                        if settings.workout_reminders_enabled:
                            plan_workouts = [
                                {
                                    "time": item.time,
                                    "exercise_name": item.title,
                                    "duration_minutes": item.duration_minutes or 30,
                                    "intensity": "moderate",
                                    "type": item.activity_type,
                                }
                                for item in plan.daily_schedule
                                if item.activity_type == "workout"
                            ]
                            reminders_to_save.extend(
                                generate_workout_reminders(
                                    user.id,
                                    plan_workouts,
                                    settings.workout_reminder_time_before_minutes,
                                )
                            )

                        if settings.water_reminders_enabled:
                            reminders_to_save.extend(
                                generate_water_reminders(
                                    user.id,
                                    settings.water_reminder_interval_hours,
                                )
                            )

                        if settings.sleep_reminder_enabled:
                            sleep_reminder = generate_sleep_reminder(
                                user.id,
                                settings.sleep_reminder_time,
                            )
                            if sleep_reminder:
                                reminders_to_save.append(sleep_reminder)

                        if settings.mood_check_enabled:
                            mood_reminder = generate_mood_check_reminder(
                                user.id,
                                settings.mood_check_time,
                            )
                            if mood_reminder:
                                reminders_to_save.append(mood_reminder)

                        created_reminders = []
                        for reminder_item in reminders_to_save:
                            reminder_payload = reminder_item.dict(exclude_none=True, exclude={"id", "created_at", "completed_at"})
                            created_reminders.append(
                                st.session_state.db_service.create_reminder(
                                    ReminderCreate(**reminder_payload)
                                )
                            )

                        st.success(f"Created {len(created_reminders)} reminders from plan.")
                        if created_reminders:
                            st.markdown("#### Upcoming reminders created")
                            for reminder_item in created_reminders:
                                st.write(
                                    f"{reminder_item.scheduled_time.strftime('%H:%M')} - {reminder_item.title} ({reminder_item.reminder_type})"
                                )

                # Sync alarms
                st.markdown("---")
                if st.button("Sync Alarms from Plan", type="secondary"):
                    with st.spinner("Syncing alarms..."):
                        simulate_alarm_sync(plan)
                        st.success("Alarms synced!")
                        st.json({"status": "success", "alarms_synced": len(plan.daily_schedule)})
            
            except Exception as e:
                st.error(f"Error generating plan: {str(e)}")
                st.info("Ensure your Google Cloud credentials (ADC) are configured and you have an internet connection.")

