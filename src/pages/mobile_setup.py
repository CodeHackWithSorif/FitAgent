import streamlit as st

from app_utils import *

def render():
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

