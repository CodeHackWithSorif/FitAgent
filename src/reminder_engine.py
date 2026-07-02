"""
Reminder Engine for FitAgent - Handles alarms, reminders, and notifications.
Manages meal reminders, water intake alerts, workout notifications, and health check-ins.
"""

import re
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from enum import Enum


# --- ENUMS ---

class ReminderType(str, Enum):
    """Types of reminders supported."""
    MEAL = "meal"
    WATER = "water"
    WORKOUT = "workout"
    SLEEP = "sleep"
    MOOD = "mood"
    METRICS = "metrics"
    CUSTOM = "custom"


class ReminderStatus(str, Enum):
    """Status of a reminder."""
    PENDING = "pending"
    TRIGGERED = "triggered"
    COMPLETED = "completed"
    DISMISSED = "dismissed"


# --- PYDANTIC MODELS ---

class ReminderSettings(BaseModel):
    """User's reminder preferences."""
    user_id: int
    meal_reminders_enabled: bool = True
    meal_reminder_time_before_minutes: int = 30  # 30 mins before meal
    water_reminders_enabled: bool = True
    water_reminder_interval_hours: int = 2  # Every 2 hours
    workout_reminders_enabled: bool = True
    workout_reminder_time_before_minutes: int = 15  # 15 mins before workout
    sleep_reminder_enabled: bool = True
    sleep_reminder_time: str = "22:00"  # 10 PM
    mood_check_enabled: bool = True
    mood_check_time: str = "20:00"  # 8 PM
    notification_sound_enabled: bool = True
    vibration_enabled: bool = True
    quiet_hours_start: str = "22:00"  # No notifications 10 PM - 7 AM
    quiet_hours_end: str = "07:00"


class Reminder(BaseModel):
    """Individual reminder."""
    id: Optional[int] = None
    user_id: int
    reminder_type: ReminderType
    title: str
    description: str
    scheduled_time: datetime
    status: ReminderStatus = ReminderStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    data: Optional[Dict] = None  # Additional context (meal_name, workout_type, etc.)


class ReminderNotification(BaseModel):
    """Push notification to send to user."""
    reminder_id: Optional[int] = None
    title: str
    body: str
    notification_type: ReminderType
    action_buttons: List[Dict] = []  # {"label": "Done", "action": "complete"}
    sound: bool = True
    vibrate: bool = True
    priority: str = "high"  # low, normal, high


class ReminderHistory(BaseModel):
    """Record of completed reminders."""
    reminder_id: int
    user_id: int
    reminder_type: ReminderType
    title: str
    scheduled_time: datetime
    completed_at: datetime
    completion_time_minutes: int  # How many minutes late/early


# --- REMINDER GENERATION ---

def parse_schedule_time(time_str: str) -> Optional[datetime.time]:
    """Parse a schedule time string like '08:00 AM' or '20:30'."""
    if not time_str or not isinstance(time_str, str):
        return None

    match = re.match(r"^\s*(\d{1,2}):(\d{2})(?:\s*([APap][Mm]))?\s*$", time_str)
    if not match:
        return None

    hour = int(match.group(1))
    minute = int(match.group(2))
    ampm = match.group(3)

    if ampm:
        ampm = ampm.upper()
        if ampm == "PM" and hour != 12:
            hour += 12
        elif ampm == "AM" and hour == 12:
            hour = 0

    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return None

    return datetime.min.time().replace(hour=hour, minute=minute)


def generate_meal_reminders(
    health_plan: Dict,
    user_id: int,
    reminder_minutes_before: int = 30,
) -> List[Reminder]:
    """Generate meal reminders from health plan."""
    reminders = []
    
    if not health_plan or "daily_schedule" not in health_plan:
        return reminders
    
    today = datetime.utcnow().date()
    
    for schedule_item in health_plan.get("daily_schedule", []):
        if schedule_item.get("activity_type") == "meal":
            try:
                time_str = schedule_item.get("time", "")
                time_obj = parse_schedule_time(time_str)
                if time_obj is None:
                    continue

                scheduled_time = datetime.combine(today, time_obj)
                reminder_time = scheduled_time - timedelta(minutes=reminder_minutes_before)
                    
                reminder = Reminder(
                    user_id=user_id,
                    reminder_type=ReminderType.MEAL,
                    title=f"Time for {schedule_item.get('title', 'meal')}",
                    description=schedule_item.get("description", "Enjoy your healthy meal!"),
                    scheduled_time=reminder_time,
                    data={
                        "meal_type": schedule_item.get("title"),
                        "original_time": time_str,
                        "medicinal_value": schedule_item.get("medicinal_value"),
                    }
                )
                reminders.append(reminder)
            except (ValueError, AttributeError):
                continue
    
    return reminders


def generate_water_reminders(
    user_id: int,
    interval_hours: int = 2,
    daily_target_liters: float = 2.5,
) -> List[Reminder]:
    """Generate water intake reminders throughout the day."""
    reminders = []
    now = datetime.utcnow()
    today = now.date()
    
    # Start from 7 AM, every N hours
    start_hour = 7
    current_time = datetime.combine(today, datetime.min.time().replace(hour=start_hour))
    
    reminder_count = 0
    cups_per_reminder = daily_target_liters / (24 // interval_hours)
    
    while current_time.time().hour < 22:  # Stop at 10 PM
        if current_time > now:  # Only future reminders
            reminder = Reminder(
                user_id=user_id,
                reminder_type=ReminderType.WATER,
                title="Time to hydrate",
                description=f"Drink a glass of water! ({cups_per_reminder:.1f}L equivalent)",
                scheduled_time=current_time,
                data={
                    "glasses_recommended": 1,
                    "liters_equivalent": round(cups_per_reminder, 2),
                }
            )
            reminders.append(reminder)
            reminder_count += 1
        
        current_time += timedelta(hours=interval_hours)
    
    return reminders


def generate_workout_reminders(
    user_id: int,
    workouts: List[Dict],
    reminder_minutes_before: int = 15,
) -> List[Reminder]:
    """Generate workout reminders from scheduled exercises."""
    reminders = []
    today = datetime.utcnow().date()
    
    for workout in workouts:
        try:
            time_str = workout.get("time", "")
            time_obj = parse_schedule_time(time_str)
            if time_obj is None:
                continue

            scheduled_time = datetime.combine(today, time_obj)
            reminder_time = scheduled_time - timedelta(minutes=reminder_minutes_before)
            
            reminder = Reminder(
                user_id=user_id,
                reminder_type=ReminderType.WORKOUT,
                title=f"Workout time: {workout.get('exercise_name', 'exercise')}",
                description=f"{workout.get('duration_minutes', 30)} mins of {workout.get('intensity', 'moderate')} intensity",
                scheduled_time=reminder_time,
                data={
                    "exercise_name": workout.get("exercise_name"),
                    "duration_minutes": workout.get("duration_minutes"),
                    "intensity": workout.get("intensity"),
                    "type": workout.get("type"),
                }
            )
            reminders.append(reminder)
        except (ValueError, AttributeError):
            continue
    
    return reminders


def generate_sleep_reminder(
    user_id: int,
    sleep_time: str = "22:00",  # 10 PM
) -> Optional[Reminder]:
    """Generate sleep reminder for user."""
    try:
        today = datetime.utcnow().date()
        time_parts = sleep_time.split(":")
        hour, minute = int(time_parts[0]), int(time_parts[1])
        
        scheduled_time = datetime.combine(
            today,
            datetime.min.time().replace(hour=hour, minute=minute),
        )
        
        return Reminder(
            user_id=user_id,
            reminder_type=ReminderType.SLEEP,
            title="Sleep time approaching",
            description="Time to wind down and get ready for bed. Aim for 7-9 hours of sleep.",
            scheduled_time=scheduled_time,
            data={"recommended_sleep_hours": 8}
        )
    except (ValueError, AttributeError):
        return None


def generate_mood_check_reminder(
    user_id: int,
    check_time: str = "20:00",  # 8 PM
) -> Optional[Reminder]:
    """Generate mood check-in reminder for user."""
    try:
        today = datetime.utcnow().date()
        time_parts = check_time.split(":")
        hour, minute = int(time_parts[0]), int(time_parts[1])
        
        scheduled_time = datetime.combine(
            today,
            datetime.min.time().replace(hour=hour, minute=minute),
        )
        
        return Reminder(
            user_id=user_id,
            reminder_type=ReminderType.MOOD,
            title="Mood check-in",
            description="How are you feeling today? Log your mood and energy levels.",
            scheduled_time=scheduled_time,
            data={"categories": ["happy", "neutral", "stressed", "tired"]}
        )
    except (ValueError, AttributeError):
        return None


# --- REMINDER NOTIFICATIONS ---

def create_notification_from_reminder(reminder: Reminder) -> ReminderNotification:
    """Convert a reminder to a notification."""
    
    notification_templates = {
        ReminderType.MEAL: {
            "title": f"Meal Time: {reminder.data.get('meal_type', 'Meal') if reminder.data else 'Meal'}",
            "body": reminder.description,
            "buttons": ["Complete", "Snooze 10 min"],
        },
        ReminderType.WATER: {
            "title": "Hydration Break",
            "body": reminder.description,
            "buttons": ["Logged", "Snooze 15 min"],
        },
        ReminderType.WORKOUT: {
            "title": f"Workout Ready: {reminder.data.get('exercise_name', 'Exercise') if reminder.data else 'Exercise'}",
            "body": reminder.description,
            "buttons": ["Starting", "Snooze 5 min"],
        },
        ReminderType.SLEEP: {
            "title": "Time for Sleep",
            "body": reminder.description,
            "buttons": ["Going to bed", "Snooze 15 min"],
        },
        ReminderType.MOOD: {
            "title": "Check In",
            "body": reminder.description,
            "buttons": ["Log Mood", "Later"],
        },
    }
    
    template = notification_templates.get(reminder.reminder_type, {
        "title": reminder.title,
        "body": reminder.description,
        "buttons": ["Done"],
    })
    
    action_buttons = [
        {"label": btn, "action": f"reminder_{reminder.reminder_type.value}_{btn.lower().replace(' ', '_')}"}
        for btn in template.get("buttons", [])
    ]
    
    return ReminderNotification(
        reminder_id=reminder.id,
        title=template["title"],
        body=template["body"],
        notification_type=reminder.reminder_type,
        action_buttons=action_buttons,
        sound=True,
        vibrate=True,
        priority="high",
    )


def get_due_reminders(
    reminders: List[Reminder],
    check_time: Optional[datetime] = None,
) -> List[Reminder]:
    """Get reminders that are due or overdue."""
    if check_time is None:
        check_time = datetime.utcnow()
    
    due = []
    for reminder in reminders:
        if reminder.status == ReminderStatus.PENDING and reminder.scheduled_time <= check_time:
            due.append(reminder)
    
    return due


def get_reminders_for_today(
    reminders: List[Reminder],
) -> List[Reminder]:
    """Get all reminders scheduled for today."""
    today = datetime.utcnow().date()
    return [
        r for r in reminders
        if r.scheduled_time.date() == today and r.status == ReminderStatus.PENDING
    ]


def calculate_reminder_statistics(
    completed_reminders: List[ReminderHistory],
    days: int = 7,
) -> Dict:
    """Calculate reminder completion statistics."""
    if not completed_reminders:
        return {
            "total_reminders": 0,
            "completion_rate": 0.0,
            "average_completion_time_minutes": 0,
            "by_type": {},
        }
    
    # Filter to recent days
    cutoff = datetime.utcnow() - timedelta(days=days)
    recent = [r for r in completed_reminders if r.completed_at >= cutoff]
    
    # Count by type
    by_type = {}
    total_completion_minutes = 0
    
    for reminder in recent:
        rem_type = reminder.reminder_type.value
        if rem_type not in by_type:
            by_type[rem_type] = {"count": 0, "avg_time": 0}
        
        by_type[rem_type]["count"] += 1
        total_completion_minutes += reminder.completion_time_minutes
    
    avg_completion = total_completion_minutes / len(recent) if recent else 0
    
    return {
        "total_reminders": len(recent),
        "completion_rate": 100.0,  # All are completed in this list
        "average_completion_time_minutes": round(avg_completion, 1),
        "by_type": by_type,
        "days_tracked": days,
    }


def get_reminder_insights(
    reminders: List[Reminder],
    completed: List[ReminderHistory],
) -> List[str]:
    """Generate insights based on reminder activity."""
    insights = []
    
    if not reminders and not completed:
        insights.append("📱 Start setting reminders to track your health goals!")
        return insights
    
    # Completion statistics
    stats = calculate_reminder_statistics(completed, days=7)
    
    if stats["total_reminders"] > 0:
        if stats["completion_rate"] >= 90:
            insights.append(f"✅ Excellent reminder adherence! {stats['total_reminders']} reminders completed this week.")
        elif stats["completion_rate"] >= 70:
            insights.append(f"📊 Good consistency. {stats['total_reminders']} reminders completed this week.")
        else:
            insights.append(f"⚠️ Low reminder completion. {stats['total_reminders']} reminders completed this week.")
    
    # By type analysis
    by_type = stats.get("by_type", {})
    
    if "meal" in by_type and by_type["meal"]["count"] > 0:
        insights.append(f"🍽️ Meal reminders: {by_type['meal']['count']} completed")
    
    if "water" in by_type and by_type["water"]["count"] > 0:
        insights.append(f"💧 Water reminders: {by_type['water']['count']} logged")
    
    if "workout" in by_type and by_type["workout"]["count"] > 0:
        insights.append(f"🏋️ Workout reminders: {by_type['workout']['count']} completed")
    
    if stats["average_completion_time_minutes"] > 15:
        insights.append(f"⏱️ Average response time: {int(stats['average_completion_time_minutes'])} minutes")
    else:
        insights.append(f"⚡ Quick responder! Avg {int(stats['average_completion_time_minutes'])} min response time")
    
    return insights if insights else ["📱 Keep up with your reminders!"]


def format_time_for_display(dt: datetime) -> str:
    """Format datetime for display."""
    return dt.strftime("%H:%M")


def is_in_quiet_hours(
    check_time: datetime,
    quiet_start: str = "22:00",
    quiet_end: str = "07:00",
) -> bool:
    """Check if given time is in quiet hours."""
    try:
        start_parts = quiet_start.split(":")
        end_parts = quiet_end.split(":")
        
        start_hour = int(start_parts[0])
        end_hour = int(end_parts[0])
        
        current_hour = check_time.hour
        
        # Handle overnight quiet hours (e.g., 22:00 to 07:00)
        if start_hour > end_hour:
            return current_hour >= start_hour or current_hour < end_hour
        else:
            return start_hour <= current_hour < end_hour
    except (ValueError, IndexError):
        return False
