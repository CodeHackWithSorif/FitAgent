import streamlit as st

from app_utils import *

def render():
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

