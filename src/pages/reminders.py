import streamlit as st
from streamlit_autorefresh import st_autorefresh

from app_utils import *
from database import ReminderSettingsCreate

def render():
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

