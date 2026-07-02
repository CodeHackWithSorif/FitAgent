from typing import List, Dict

def simulate_alarm_sync(daily_schedule: List[any]) -> List[Dict[str, str]]:
    """
    Takes the structured daily schedule from the planning engine
    and simulates the generation of device alarms/push notifications.
    """
    mock_alarms = []
    for item in daily_schedule:
        # We simulate the exact payload a companion mobile app would receive
        alarm_payload = {
            "trigger_time": item.time,
            "notification_title": f"FitAgent: {item.title}",
            "notification_body": f"Time for your {item.activity_type}! {item.description}",
            "sound": "default_chime",
            "vibrate": "true"
        }
        mock_alarms.append(alarm_payload)
        
    return mock_alarms
