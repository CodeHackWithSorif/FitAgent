import streamlit as st

from app_utils import *

def render():
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

