import streamlit as st
import os
from datetime import datetime
from streamlit.components.v1 import html

from reminder_engine import (
    ReminderType,
    ReminderHistory,
    generate_water_reminders,
    generate_sleep_reminder,
    generate_mood_check_reminder,
    create_notification_from_reminder,
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

def set_page(page_name):
    """Navigate to a different page."""
    st.session_state.page = page_name

def logout_user():
    """Logout current user."""
    st.session_state.user_id = None
    st.session_state.current_user = None
    st.session_state.page = "home"

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
        script = build_cron_job_script(reminders)
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
            created.append(db_service.create_reminder(ReminderCreate(**reminder.model_dump(exclude_none=True, exclude={"id", "created_at", "completed_at"}))))

    if settings.sleep_reminder_enabled and not has_reminder(ReminderType.SLEEP.value):
        sleep_reminder = generate_sleep_reminder(user.id, settings.sleep_reminder_time)
        if sleep_reminder:
            created.append(db_service.create_reminder(ReminderCreate(**sleep_reminder.model_dump(exclude_none=True, exclude={"id", "created_at", "completed_at"}))))

    if settings.mood_check_enabled and not has_reminder(ReminderType.MOOD.value):
        mood_reminder = generate_mood_check_reminder(user.id, settings.mood_check_time)
        if mood_reminder:
            created.append(db_service.create_reminder(ReminderCreate(**mood_reminder.model_dump(exclude_none=True, exclude={"id", "created_at", "completed_at"}))))

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
