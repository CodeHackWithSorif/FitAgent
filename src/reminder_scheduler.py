
import sys
from datetime import datetime
from typing import List

ICS_HEADER = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//FitAgent//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
"""
ICS_FOOTER = "END:VCALENDAR\n"


def format_ics_datetime(dt: datetime, use_utc: bool = False) -> str:
    if use_utc:
        return dt.strftime("%Y%m%dT%H%M%SZ")
    return dt.strftime("%Y%m%dT%H%M%S")


def build_ics_event(reminder) -> str:
    uid = f"fitagent-{reminder.id}-{int(reminder.scheduled_time.timestamp())}@fitagent"
    dtstamp = format_ics_datetime(datetime.utcnow(), use_utc=True)
    dtstart = format_ics_datetime(reminder.scheduled_time)
    summary = reminder.title.replace("\n", " ").replace(",", " ")
    description = reminder.description.replace("\n", " ").replace(",", " ")
    return (
        "BEGIN:VEVENT\n"
        f"UID:{uid}\n"
        f"DTSTAMP:{dtstamp}\n"
        f"DTSTART:{dtstart}\n"
        f"SUMMARY:{summary}\n"
        f"DESCRIPTION:{description}\n"
        "CATEGORIES:FitAgent\n"
        "END:VEVENT\n"
    )


def build_ics_calendar(reminders: List) -> str:
    events = "".join(build_ics_event(r) for r in reminders)
    return f"{ICS_HEADER}{events}{ICS_FOOTER}"


def build_windows_task_script(reminders: List) -> str:
    commands = ["@echo off\n"]
    commands.append("REM Run this file as administrator to install FitAgent reminder tasks.\n")
    for reminder in reminders:
        task_name = f"FitAgent_Reminder_{reminder.id}"
        run_time = reminder.scheduled_time.strftime("%H:%M")
        run_date = reminder.scheduled_time.strftime("%Y/%m/%d")
        safe_title = reminder.title.replace('"', '\\"')
        safe_description = reminder.description.replace('"', '\\"')
        powershell_command = (
            f"powershell.exe -NoProfile -WindowStyle Hidden -Command \"Add-Type -AssemblyName PresentationFramework;"
            f"[System.Windows.MessageBox]::Show(\"{safe_description}\", \"{safe_title}\")\""
        )
        commands.append(
            f"schtasks /Create /SC ONCE /TN \"{task_name}\" /TR \"{powershell_command}\" /ST {run_time} /SD {run_date} /F\n"
        )
    commands.append("echo Tasks created. Use Task Scheduler to view or edit them.\n")
    return "".join(commands)


def build_cron_job_script(reminders: List) -> str:
    lines = ["#!/bin/bash\n"]
    lines.append("# This file contains commands you can add to your crontab.\n")
    lines.append("# Run `crontab -e` and paste the lines below to schedule reminders.\n")
    for reminder in reminders:
        schedule = reminder.scheduled_time
        safe_title = reminder.title.replace('"', '\\"')
        safe_description = reminder.description.replace('"', '\\"')
        if sys.platform == 'darwin':
            command = (
                f"osascript -e \"display notification \\\"{safe_description}\\\" with title \\\"{safe_title}\\\"\""
            )
        else:
            command = f"notify-send \"{safe_title}\" \"{safe_description}\""
        lines.append(
            f"{schedule.minute} {schedule.hour} {schedule.day} {schedule.month} * {command}\n"
        )
    return "".join(lines)


