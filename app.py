import streamlit as st
from streamlit_autorefresh import st_autorefresh
from streamlit.components.v1 import html
from dotenv import load_dotenv
import os
import sys
import json
from datetime import datetime

# --- GOOGLE CLOUD AUTHENTICATION FIX FOR STREAMLIT ---
# Streamlit Secrets 
if "GCP_SERVICE_ACCOUNT" in st.secrets:
    with open("gcp_credentials.json", "w") as f:
        json.dump(dict(st.secrets["GCP_SERVICE_ACCOUNT"]), f)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "gcp_credentials.json"


# Add src to path for imports
sys.path.insert(0, 'src')

# Load environment variables
load_dotenv()

# Import modules
from planning_engine import generate_health_plan
from alarm_logic import simulate_alarm_sync
from nutritional_engine import analyze_food_item
from database import DatabaseService, UserCreate, MealLogCreate, WorkoutLogCreate, HealthMetricsCreate
from dashboard_engine import (
    build_weight_trend_data,
    calculate_progress_metrics,
    calculate_goal_progress_items,
    get_health_insights,
)
from reminder_engine import (
    ReminderType,
    ReminderHistory,
    generate_meal_reminders,
    generate_water_reminders,
    generate_workout_reminders,
    generate_sleep_reminder,
    generate_mood_check_reminder,
    create_notification_from_reminder,
    get_reminder_insights,
    is_in_quiet_hours,
)
from reminder_scheduler import (
    build_ics_calendar,
    build_windows_task_script,
    build_cron_job_script,
)
from database import (
    ReminderSettingsCreate,
    ReminderCreate,
)

import plotly.graph_objects as go

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="FitAgent - AI Health Co-Pilot",
    page_icon="🏋️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- INITIALIZE SESSION STATE ---
if "db_service" not in st.session_state:
    st.session_state.db_service = DatabaseService()
    st.session_state.db_service.init_db()

if "user_id" not in st.session_state:
    st.session_state.user_id = None

if "current_user" not in st.session_state:
    st.session_state.current_user = None

if "page" not in st.session_state:
    st.session_state.page = "home"

if "plan" not in st.session_state:
    st.session_state.plan = None

if "alarms_synced" not in st.session_state:
    st.session_state.alarms_synced = False

if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = {}

if "notification_permission_requested" not in st.session_state:
    st.session_state.notification_permission_requested = False

# --- HELPER FUNCTIONS ---
def set_page(page_name):
    """Navigate to a different page."""
    st.session_state.page = page_name

def logout_user():
    """Logout current user."""
    st.session_state.user_id = None
    st.session_state.current_user = None
    st.session_state.page = "home"

def load_user_profile(user_id):
    """Load user profile from database."""
    db_service = st.session_state.db_service
    user = db_service.get_user(user_id)
    return user

def get_or_create_reminder_settings(user_id):
    """Retrieve or initialize reminder settings for the user."""
    db_service = st.session_state.db_service
    settings = db_service.get_reminder_settings(user_id)
    if settings is None:
        settings = db_service.create_reminder_settings(ReminderSettingsCreate(user_id=user_id))
    return settings

def build_reminder_history(reminders):
    """Convert completed reminders into ReminderHistory items."""
    history_items = []
    for reminder in reminders:
        if reminder.status == "completed" and reminder.completed_at:
            completion_minutes = int((reminder.completed_at - reminder.scheduled_time).total_seconds() / 60)
            history_items.append(ReminderHistory(
                reminder_id=reminder.id,
                user_id=reminder.user_id,
                reminder_type=reminder.reminder_type,
                title=reminder.title,
                scheduled_time=reminder.scheduled_time,
                completed_at=reminder.completed_at,
                completion_time_minutes=completion_minutes,
            ))
    return history_items


def get_pending_due_reminders(user_id):
    """Return pending reminders due now or overdue."""
    db_service = st.session_state.db_service
    reminders = db_service.get_user_reminders(user_id, days=1)
    return [
        reminder for reminder in reminders
        if reminder.status == "pending" and reminder.scheduled_time <= datetime.utcnow()
    ]


def render_reminder_notification_card(reminder):
    """Render a notification-style card for a pending reminder."""
    notification = create_notification_from_reminder(reminder)
    card_html = f"""
    <div style="border: 2px solid #4ECDC4; border-radius: 14px; padding: 16px; margin-bottom: 12px; background: linear-gradient(135deg, #f0fffb, #dcffef); box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);">
      <div style="font-size: 18px; font-weight: 700; margin-bottom: 8px;">🔔 {notification.title}</div>
      <div style="font-size: 14px; margin-bottom: 10px;">{notification.body}</div>
      <div style="font-size: 12px; color: #555;">Actions: {', '.join([button['label'] for button in notification.action_buttons])}</div>
    </div>
    """
    html(card_html, height=150)


def request_browser_notification_permission():
    """Request browser notification permission for mobile alerts."""
    if st.session_state.notification_permission_requested:
        return
    html(
        """
        <script>
          if (!('Notification' in window)) {
            console.log('Browser notifications not supported');
          } else if (Notification.permission !== 'granted') {
            Notification.requestPermission().then(function(permission) {
              console.log('Notification permission:', permission);
            });
          }
        </script>
        """,
        height=0,
    )
    st.session_state.notification_permission_requested = True


def show_browser_notification(title: str, body: str):
    """Show a browser notification if permission is granted."""
    safe_title = title.replace('"', '\\"')
    safe_body = body.replace('"', '\\"')
    notification_js = f"""
    <script>
      if ('Notification' in window && Notification.permission === 'granted') {{
        new Notification("{safe_title}", {{ body: "{safe_body}", icon: "https://cdn-icons-png.flaticon.com/512/1827/1827392.png" }});
      }}
    </script>
    """
    html(notification_js, height=0)


def play_alarm_sound(vibrate=True):
    """Trigger a short alarm sound and vibration if supported."""
    vibrate_js = "true" if vibrate else "false"
    sound_js = f"""
    <script>
      try {{
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        const ctx = new AudioContext();
        const oscillator = ctx.createOscillator();
        const gain = ctx.createGain();
        oscillator.type = 'sine';
        oscillator.frequency.value = 880;
        gain.gain.value = 0.12;
        oscillator.connect(gain);
        gain.connect(ctx.destination);
        oscillator.start();
        oscillator.stop(ctx.currentTime + 0.20);
        if ({vibrate_js} && navigator.vibrate) {{
          navigator.vibrate([180, 90, 180]);
        }}
      }} catch (e) {{
        console.log('Alarm sound disabled or blocked:', e);
      }}
    </script>
    """
    html(sound_js, height=0)


def export_reminders_as_ics(reminders):
    """Build and download a calendar file for mobile and desktop calendar imports."""
    if not reminders:
        return
    ics_data = build_ics_calendar(reminders)
    st.download_button(
        "Download reminders as .ics",
        ics_data,
        file_name="fitagent_reminders.ics",
        mime="text/calendar",
    )
    st.markdown(
        "Import this file into your mobile or desktop calendar app to create native OS-level scheduled reminders."
    )


def export_scheduler_scripts(reminders):
    """Offer a Windows task scheduler script or Linux cron file for laptop reminders."""
    if not reminders:
        return
    if os.name == "nt":
        script = build_windows_task_script(reminders)
        st.download_button(
            "Download Windows Task Scheduler script",
            script,
            file_name="fitagent_schedule_tasks.bat",
            mime="application/x-msdownload",
        )
        st.markdown(
            "Run this downloaded script on Windows to schedule desktop reminder popups."
        )
    else:
        script = build_cron_job_script(reminders, sys.executable, os.getcwd())
        st.download_button(
            "Download cron job script",
            script,
            file_name="fitagent_reminders.cron",
            mime="text/x-sh",
        )
        st.markdown(
            "Use this shell script on Linux/macOS to install cron jobs for reminders."
        )


def ensure_daily_reminder_schedule(user):
    """Create today's default reminders if they are missing."""
    db_service = st.session_state.db_service
    settings = get_or_create_reminder_settings(user.id)
    today = datetime.utcnow().date()
    existing_reminders = db_service.get_user_reminders(user.id, days=1)

    def has_reminder(reminder_type):
        return any(
            r.reminder_type == reminder_type and r.scheduled_time.date() == today
            for r in existing_reminders
        )

    created = []
    if settings.water_reminders_enabled and not has_reminder(ReminderType.WATER.value):
        reminders = generate_water_reminders(user.id, settings.water_reminder_interval_hours)
        for reminder in reminders:
            created.append(db_service.create_reminder(ReminderCreate(**reminder.dict(exclude_none=True, exclude={"id", "created_at", "completed_at"}))))

    if settings.sleep_reminder_enabled and not has_reminder(ReminderType.SLEEP.value):
        sleep_reminder = generate_sleep_reminder(user.id, settings.sleep_reminder_time)
        if sleep_reminder:
            created.append(db_service.create_reminder(ReminderCreate(**sleep_reminder.dict(exclude_none=True, exclude={"id", "created_at", "completed_at"}))))

    if settings.mood_check_enabled and not has_reminder(ReminderType.MOOD.value):
        mood_reminder = generate_mood_check_reminder(user.id, settings.mood_check_time)
        if mood_reminder:
            created.append(db_service.create_reminder(ReminderCreate(**mood_reminder.dict(exclude_none=True, exclude={"id", "created_at", "completed_at"}))))

    return created


def display_due_reminders(user):
    """Show an alert banner and cards for reminders due now."""
    due_reminders = get_pending_due_reminders(user.id)
    if not due_reminders:
        return

    settings = st.session_state.db_service.get_reminder_settings(user.id)
    quiet_active = False
    if settings:
        quiet_active = is_in_quiet_hours(datetime.utcnow(), settings.quiet_hours_start, settings.quiet_hours_end)

    if quiet_active:
        st.info("Quiet hours are active. Notifications are shown silently in the app.")

    st.warning(f"You have {len(due_reminders)} reminder(s) due now.")
    for reminder in due_reminders:
        render_reminder_notification_card(reminder)

    if settings and settings.notification_sound_enabled:
        play_alarm_sound(vibrate=settings.vibration_enabled)
        if st.session_state.notification_permission_requested:
            show_browser_notification(due_reminders[0].title, due_reminders[0].description)

    if st.button("Open Reminders", type="secondary"):
        set_page("reminders")
        st.rerun()

# --- SIDEBAR ---
with st.sidebar:
    st.title("FitAgent")
    st.markdown("---")
    
    if st.session_state.user_id is None:
        # Not logged in - show login/signup options
        st.markdown("### Get Started")
        if st.button("Create New Profile", key="btn_create_profile", use_container_width=True):
            set_page("create_profile")
        if st.button("Load Existing Profile", key="btn_load_profile", use_container_width=True):
            set_page("load_profile")
    else:
        # Logged in - show user menu
        st.markdown(f"### Welcome, {st.session_state.current_user.name}!")
        st.markdown(f"**Goal:** {st.session_state.current_user.goal}")
        st.markdown(f"**Current Weight:** {st.session_state.current_user.weight_kg} kg")
        st.markdown("---")
        
        # Navigation
        st.markdown("### Navigation")
        if st.button("Dashboard", key="btn_dashboard", use_container_width=True):
            set_page("dashboard")
        if st.button("Generate Health Plan", key="btn_gen_plan", use_container_width=True):
            set_page("health_plan")
        if st.button("Log Meal", key="btn_log_meal", use_container_width=True):
            set_page("log_meal")
        if st.button("Log Workout", key="btn_log_workout", use_container_width=True):
            set_page("log_workout")
        if st.button("Health Metrics", key="btn_metrics", use_container_width=True):
            set_page("health_metrics")
        if st.button("Food Analysis", key="btn_food_analysis", use_container_width=True):
            set_page("food_analysis")
        if st.button("Health Dashboard", key="btn_dashboard_health", use_container_width=True):
            set_page("health_dashboard")
        if st.button("Reminders", key="btn_reminders", use_container_width=True):
            set_page("reminders")
        if st.button("Notification Inbox", key="btn_notification_inbox", use_container_width=True):
            set_page("notification_inbox")
        if st.button("Export Reminders", key="btn_export_reminders", use_container_width=True):
            set_page("reminder_export")
        if st.button("Mobile / Laptop Setup", key="btn_mobile_setup", use_container_width=True):
            set_page("mobile_setup")
        
        st.markdown("---")
        if st.button("Edit Profile", key="btn_edit_profile", use_container_width=True):
            set_page("edit_profile")
        if st.button("Logout", key="btn_logout", use_container_width=True):
            logout_user()
            st.rerun()

# --- PAGE: HOME ---
def page_home():
    st.title("FitAgent: Autonomous Health Co-Pilot")
    st.markdown("""
    Welcome to **FitAgent** - your personal AI health companion built for the **INDIA RUNS Hackathon**.
    
    FitAgent bridges the gap between knowing *what* to do and actually *doing* it by:
    - [TARGET] Generating personalized diet & exercise plans (India-focused)
    - [FOOD] Analyzing nutritional content of foods ("Food as Medicine")
    - [SCHEDULE] Creating actionable daily schedules with alarms
    - [TRACK] Tracking health metrics and progress
    - [REMIND] Sending reminders to keep you on track
    
    ---
    
    ### Getting Started
    1. **Create a Profile** - Tell us your health goals, dietary preferences, and lifestyle
    2. **Generate a Plan** - AI creates a personalized diet & exercise routine
    3. **Log Your Progress** - Track meals, workouts, and health metrics
    4. **Stay Accountable** - Daily reminders keep you on track
    """)
    
    st.info("Use the sidebar to create or load a profile!")
    if st.session_state.user_id:
        display_due_reminders(st.session_state.current_user)

# --- PAGE: CREATE PROFILE ---
def page_create_profile():
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

# --- PAGE: LOAD PROFILE ---
def page_load_profile():
    st.title("Load Existing Profile")
    
    db_service = st.session_state.db_service
    all_users = db_service.get_all_users()
    
    if not all_users:
        st.warning("No profiles found. Create a new profile to get started!")
        return
    
    user_options = {f"{u.name} (ID: {u.id})": u.id for u in all_users}
    
    selected = st.selectbox("Select a profile:", list(user_options.keys()))
    
    if st.button("Load Profile", type="primary", use_container_width=True):
        user_id = user_options[selected]
        user = db_service.get_user(user_id)
        
        st.session_state.user_id = user_id
        st.session_state.current_user = user
        
        st.success(f"Loaded profile: {user.name}")
        import time
        time.sleep(0.5)
        set_page("dashboard")
        st.rerun()

# --- PAGE: DASHBOARD ---
def page_dashboard():
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

# --- PAGE: HEALTH PLAN ---
def page_health_plan():
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
                st.session_state.alarms_synced = False
                
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
                        alarms = simulate_alarm_sync(plan)
                        st.session_state.alarms_synced = True
                        st.success("Alarms synced!")
                        st.json({"status": "success", "alarms_synced": len(plan.daily_schedule)})
            
            except Exception as e:
                st.error(f"Error generating plan: {str(e)}")
                st.info("Ensure your Google Cloud credentials (ADC) are configured and you have an internet connection.")

# --- PAGE: LOG MEAL ---
def page_log_meal():
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

# --- PAGE: LOG WORKOUT ---
def page_log_workout():
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

# --- PAGE: HEALTH METRICS ---
def page_health_metrics():
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

# --- PAGE: FOOD ANALYSIS ---
def page_food_analysis():
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

# --- PAGE: HEALTH DASHBOARD ---
def page_health_dashboard():
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

# --- PAGE: REMINDERS & NOTIFICATIONS ---
def page_reminders():
    """Reminders & Notification Manager."""
    st.title("🔔 Reminders & Notifications")
    
    if st.session_state.user_id is None:
        st.error("Please load a profile first.")
        return
    
    db_service = st.session_state.db_service
    user = st.session_state.current_user
    settings = get_or_create_reminder_settings(user.id)
    due_reminders = get_pending_due_reminders(user.id)

    st.markdown("### Live Alarm Monitoring")
    alarm_monitoring = st.checkbox(
        "Enable live reminder alarm monitoring",
        value=True,
        help="This will refresh the reminders page every 60 seconds and highlight reminders due now.",
        key="alarm_monitoring"
    )
    if alarm_monitoring:
        st_autorefresh(interval=60000, key="reminder_autorefresh")
        request_browser_notification_permission()
        st.info("Alarm monitoring is active. The page refreshes every minute to check for due reminders.")

    # Schedule today's core reminders automatically
    created_reminders = ensure_daily_reminder_schedule(user)
    if created_reminders:
        st.success(f"Auto-scheduled {len(created_reminders)} reminder(s) for today.")
        due_reminders = get_pending_due_reminders(user.id)

    if due_reminders:
        st.markdown("### Due Now")
        st.warning(f"{len(due_reminders)} reminder(s) are due now.")
        for reminder in due_reminders:
            render_reminder_notification_card(reminder)

        settings = get_or_create_reminder_settings(user.id)
        if settings.notification_sound_enabled:
            play_alarm_sound(vibrate=settings.vibration_enabled)
            if st.session_state.notification_permission_requested:
                show_browser_notification(due_reminders[0].title, due_reminders[0].description)

        col1, col2 = st.columns([1, 1])
        if col1.button("Mark all as completed", type="secondary", key="complete_all_due"):
            for reminder in due_reminders:
                st.session_state.db_service.update_reminder_status(reminder.id, "completed")
            st.success("All due reminders marked as completed.")
            st.rerun()
        if col2.button("Snooze all 10 min", type="secondary", key="snooze_all_due"):
            for reminder in due_reminders:
                st.session_state.db_service.snooze_reminder(reminder.id, minutes=10)
            st.success("All due reminders snoozed by 10 minutes.")
            st.rerun()

        st.markdown("---")

    with st.form("reminder_settings_form"):
        st.markdown("### Reminder Settings")
        meal_reminders_enabled = st.checkbox("Enable meal reminders", value=settings.meal_reminders_enabled)
        meal_reminder_time_before = st.number_input(
            "Meal reminder minutes before meal",
            min_value=0,
            max_value=120,
            value=settings.meal_reminder_time_before_minutes,
            step=5,
        )
        water_reminders_enabled = st.checkbox("Enable water reminders", value=settings.water_reminders_enabled)
        water_reminder_interval = st.number_input(
            "Water reminder interval (hours)",
            min_value=1,
            max_value=6,
            value=settings.water_reminder_interval_hours,
            step=1,
        )
        workout_reminders_enabled = st.checkbox("Enable workout reminders", value=settings.workout_reminders_enabled)
        workout_reminder_time_before = st.number_input(
            "Workout reminder minutes before session",
            min_value=0,
            max_value=60,
            value=settings.workout_reminder_time_before_minutes,
            step=5,
        )
        sleep_reminder_enabled = st.checkbox("Enable sleep reminders", value=settings.sleep_reminder_enabled)
        sleep_reminder_time = st.text_input("Sleep reminder time", value=settings.sleep_reminder_time)
        mood_check_enabled = st.checkbox("Enable mood check reminders", value=settings.mood_check_enabled)
        mood_check_time = st.text_input("Mood check reminder time", value=settings.mood_check_time)
        quiet_hours_start = st.text_input("Quiet hours start", value=settings.quiet_hours_start)
        quiet_hours_end = st.text_input("Quiet hours end", value=settings.quiet_hours_end)
        notification_sound_enabled = st.checkbox("Enable alarm sound on due reminders", value=settings.notification_sound_enabled)
        vibration_enabled = st.checkbox("Enable vibration on mobile reminders", value=settings.vibration_enabled)

        submitted_settings = st.form_submit_button("Save reminder settings", type="primary", use_container_width=True)
        if submitted_settings:
            updated_settings = ReminderSettingsCreate(
                user_id=user.id,
                meal_reminders_enabled=meal_reminders_enabled,
                meal_reminder_time_before_minutes=meal_reminder_time_before,
                water_reminders_enabled=water_reminders_enabled,
                water_reminder_interval_hours=water_reminder_interval,
                workout_reminders_enabled=workout_reminders_enabled,
                workout_reminder_time_before_minutes=workout_reminder_time_before,
                sleep_reminder_enabled=sleep_reminder_enabled,
                sleep_reminder_time=sleep_reminder_time,
                mood_check_enabled=mood_check_enabled,
                mood_check_time=mood_check_time,
                notification_sound_enabled=notification_sound_enabled,
                vibration_enabled=vibration_enabled,
                quiet_hours_start=quiet_hours_start,
                quiet_hours_end=quiet_hours_end,
            )
            db_service.update_reminder_settings(user.id, updated_settings)
            st.success("Reminder settings updated.")
            settings = updated_settings

    test_alarm = st.button("Test alarm now", key="test_alarm_now")
    if test_alarm:
        request_browser_notification_permission()
        if notification_sound_enabled:
            play_alarm_sound(vibrate=vibration_enabled)
        show_browser_notification("Test Reminder", "This is a mobile reminder test.")
        st.success("Test reminder played. Check your mobile notification and sound settings.")

    st.markdown("---")
    st.markdown("### Upcoming Reminders")
    reminders = db_service.get_user_reminders(user.id, days=7)

    if not reminders:
        st.info("No reminders scheduled yet. Generate a personalized plan or add reminders from the plan page.")
    else:
        for reminder in reminders:
            with st.container():
                cols = st.columns([3, 1, 1, 1])
                cols[0].write(f"**{reminder.scheduled_time.strftime('%Y-%m-%d %H:%M')}** — {reminder.title} ({reminder.reminder_type})")
                cols[0].write(reminder.description)
                cols[0].write(f"Status: {reminder.status.title()}")
                if reminder.data:
                    cols[0].write(f"Details: {reminder.data}")
                if reminder.status == "pending":
                    if cols[1].button("Complete", key=f"complete_{reminder.id}"):
                        db_service.update_reminder_status(reminder.id, "completed")
                        st.rerun()
                    if cols[2].button("Snooze 10 min", key=f"snooze_{reminder.id}"):
                        db_service.snooze_reminder(reminder.id, minutes=10)
                        st.rerun()
                    if cols[3].button("Delete", key=f"delete_{reminder.id}"):
                        db_service.delete_reminder(reminder.id)
                        st.rerun()
                else:
                    if cols[3].button("Delete", key=f"delete_{reminder.id}"):
                        db_service.delete_reminder(reminder.id)
                        st.rerun()

    st.markdown("---")
    if reminders:
        st.markdown("### Reminder Export Shortcut")
        st.info("Use the dedicated Export Reminders page for native calendar files and scheduler scripts.")
        if st.button("Go to Export Page", type="secondary"):
            set_page("reminder_export")
            st.rerun()

    st.markdown("---")
    st.markdown("### Reminder Insights")
    completed_reminders = [r for r in reminders if r.status == "completed"]
    reminder_history = build_reminder_history(completed_reminders)
    insights = get_reminder_insights(reminders, reminder_history)
    for insight in insights:
        st.write(insight)

# --- PAGE: EDIT PROFILE ---
def page_edit_profile():
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

# --- PAGE: NOTIFICATION INBOX ---
def page_notification_inbox():
    """Show all reminder notifications and history in one place."""
    st.title("📥 Notification Inbox")
    
    if st.session_state.user_id is None:
        st.error("Please load a profile first.")
        return
    
    db_service = st.session_state.db_service
    user = st.session_state.current_user
    
    st.markdown("### Due & Active Reminders")
    due_reminders = get_pending_due_reminders(user.id)
    if due_reminders:
        for reminder in due_reminders:
            render_reminder_notification_card(reminder)
    else:
        st.info("No reminders are currently due.")

    st.markdown("---")
    st.markdown("### Upcoming Reminders")
    upcoming = db_service.get_user_reminders(user.id, days=7)
    if upcoming:
        for reminder in upcoming:
            st.write(f"{reminder.scheduled_time.strftime('%Y-%m-%d %H:%M')} — {reminder.title} ({reminder.reminder_type}) — {reminder.status}")
    else:
        st.info("No upcoming reminders found.")

    st.markdown("---")
    st.markdown("### Recent Reminder History")
    completed_reminders = [r for r in upcoming if r.status == 'completed']
    if completed_reminders:
        for reminder in completed_reminders:
            st.write(f"{reminder.scheduled_time.strftime('%Y-%m-%d %H:%M')} — {reminder.title} — completed")
    else:
        st.info("No completed reminders yet.")

# --- PAGE: REMINDER EXPORT ---
def page_reminder_export():
    """Export reminders as native calendar or scheduler scripts."""
    st.title("📤 Export Reminders")

    if st.session_state.user_id is None:
        st.error("Please load a profile first.")
        return

    db_service = st.session_state.db_service
    user = st.session_state.current_user
    reminders = db_service.get_user_reminders(user.id, days=14)

    st.markdown("### Why export reminders?")
    st.write(
        "Exported reminders can be imported into your phone or desktop calendar so notifications can be handled by the OS, "
        "not just by the browser tab."
    )
    st.write(
        "If you want native alerts while the browser is closed, download the .ics file and add it to your mobile calendar app. "
        "For Windows or Linux, download the scheduler script to install desktop reminders."
    )

    if not reminders:
        st.warning("No reminders found to export. Create reminders from your health plan first.")
        return

    st.markdown("### Upcoming reminders")
    for reminder in reminders:
        st.write(f"{reminder.scheduled_time.strftime('%Y-%m-%d %H:%M')} — {reminder.title} ({reminder.reminder_type})")

    st.markdown("---")
    export_reminders_as_ics(reminders)
    export_scheduler_scripts(reminders)

# --- PAGE: MOBILE / LAPTOP SETUP ---
def page_mobile_setup():
    """Mobile and laptop setup guide for common users."""
    st.title("📱 Mobile & Laptop Setup")

    if st.session_state.user_id is None:
        st.error("Please load a profile first.")
        return

    db_service = st.session_state.db_service
    user = st.session_state.current_user
    reminders = db_service.get_user_reminders(user.id, days=14)

    st.markdown("### Use FitAgent on your phone")
    st.write(
        "FitAgent works best as a mobile-friendly web app, but for reliable reminders you can import reminders into your phone's calendar. "
        "The Export Reminders page produces a `.ics` file that you can add to Google Calendar or Apple Calendar."
    )
    st.markdown("#### Steps for mobile users")
    st.markdown("1. Open `Export Reminders` from the sidebar.")
    st.markdown("2. Download the `.ics` file.")
    st.markdown("3. Open the file on your phone and import it into your calendar app.")
    st.markdown("4. Allow notifications in the calendar app for native reminders.")

    st.markdown("### Use FitAgent on your laptop")
    st.write(
        "For laptop notifications outside the browser, download the scheduler script from Export Reminders. "
        "On Windows you can run the `.bat` file; on macOS/Linux you can use the shell script or add cron entries."
    )
    st.markdown("#### Steps for laptop users")
    st.markdown("1. Open `Export Reminders` from the sidebar.")
    st.markdown("2. Download the Windows Task Scheduler script or Linux/macOS shell script.")
    st.markdown("3. Follow the on-screen instructions in the downloaded file.")
    st.markdown("4. Keep your laptop powered on for the OS scheduler to trigger alerts.")

    if reminders:
        st.markdown("### Your upcoming reminders")
        for reminder in reminders:
            st.write(f"{reminder.scheduled_time.strftime('%Y-%m-%d %H:%M')} — {reminder.title} ({reminder.reminder_type})")
    else:
        st.info("No scheduled reminders yet. Generate your plan or add reminders from the health plan page.")

    if st.button("Go to Export Reminders", type="primary", use_container_width=True):
        set_page("reminder_export")
        st.rerun()

# --- ROUTER ---
pages = {
    "home": page_home,
    "create_profile": page_create_profile,
    "load_profile": page_load_profile,
    "dashboard": page_dashboard,
    "health_plan": page_health_plan,
    "log_meal": page_log_meal,
    "log_workout": page_log_workout,
    "health_metrics": page_health_metrics,
    "food_analysis": page_food_analysis,
    "health_dashboard": page_health_dashboard,
    "reminders": page_reminders,
    "notification_inbox": page_notification_inbox,
    "reminder_export": page_reminder_export,
    "mobile_setup": page_mobile_setup,
    "edit_profile": page_edit_profile,
}

# Redirect to home if no user and on protected page
if st.session_state.user_id is None and st.session_state.page not in ["home", "create_profile", "load_profile"]:
    set_page("home")

# Render current page
current_page = pages.get(st.session_state.page, page_home)
current_page()

# --- FOOTER ---
st.markdown("""
<div style="text-align: center; margin-top: 50px; padding: 20px; border-top: 1px solid #eaeaea; background-color: transparent;">
    <p style="font-size: 18px; font-weight: 600; margin-bottom: 5px;">🚀 Built by <span style="color: #4ECDC4;">Logic Loopers</span></p>
    <p style="font-size: 14px; opacity: 0.8; margin-bottom: 20px;">Created by <b>Code Hack with Sorif</b></p>
    <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 25px;">
        <a href="https://www.linkedin.com/in/sorif-hossain-code-hack/" target="_blank" style="text-decoration: none; font-size: 16px; font-weight: 500; display: flex; align-items: center; gap: 6px; color: inherit; transition: opacity 0.2s;" onmouseover="this.style.opacity='0.7'" onmouseout="this.style.opacity='1'">💼 LinkedIn</a>
        <a href="https://www.youtube.com/@CodeHackWithSorif" target="_blank" style="text-decoration: none; font-size: 16px; font-weight: 500; display: flex; align-items: center; gap: 6px; color: inherit; transition: opacity 0.2s;" onmouseover="this.style.opacity='0.7'" onmouseout="this.style.opacity='1'">🔴 YouTube</a>
        <a href="https://github.com/CodeHackWithSorif" target="_blank" style="text-decoration: none; font-size: 16px; font-weight: 500; display: flex; align-items: center; gap: 6px; color: inherit; transition: opacity 0.2s;" onmouseover="this.style.opacity='0.7'" onmouseout="this.style.opacity='1'">🐙 GitHub</a>
        <a href="https://whatsapp.com/channel/0029VbBJa7iIt5rtVuNzfP2g" target="_blank" style="text-decoration: none; font-size: 16px; font-weight: 500; display: flex; align-items: center; gap: 6px; color: inherit; transition: opacity 0.2s;" onmouseover="this.style.opacity='0.7'" onmouseout="this.style.opacity='1'">💬 WhatsApp Channel</a>
    </div>
    <p style="font-size: 12px; opacity: 0.6; margin-top: 25px;">Built for Gen AI Academy Cohort 2 &amp; India Runs Hackathon</p>
</div>
""", unsafe_allow_html=True)
