import streamlit as st

from app_utils import *

def render():
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

