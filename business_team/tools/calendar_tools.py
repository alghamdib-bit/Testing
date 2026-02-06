"""
Calendar tools for the Secretary Agent.

Manages calendar events, scheduling, and conflict detection.
"""

import json
from datetime import datetime, timedelta
from typing import Any

from business_team import config


class CalendarTools:
    """Tools for managing calendar events and schedules."""

    def __init__(self, db=None):
        self.db = db
        self.calendar_file = config.DATA_DIR / "calendar.json"
        if not self.db and not self.calendar_file.exists():
            self.calendar_file.write_text(json.dumps(self._get_demo_events(), indent=2))

    @staticmethod
    def get_tool_definitions() -> list[dict]:
        return [
            {
                "name": "get_calendar_events",
                "description": "Retrieve calendar events for a date range.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "start_date": {
                            "type": "string",
                            "description": "Start date in ISO format (YYYY-MM-DD)",
                        },
                        "end_date": {
                            "type": "string",
                            "description": "End date in ISO format (YYYY-MM-DD)",
                        },
                    },
                    "required": ["start_date"],
                },
            },
            {
                "name": "add_calendar_event",
                "description": "Add a new event to the calendar.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Event title"},
                        "date": {"type": "string", "description": "Date (YYYY-MM-DD)"},
                        "start_time": {
                            "type": "string",
                            "description": "Start time (HH:MM)",
                        },
                        "end_time": {
                            "type": "string",
                            "description": "End time (HH:MM)",
                        },
                        "location": {
                            "type": "string",
                            "description": "Event location",
                        },
                        "attendees": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of attendee names/emails",
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["high", "medium", "low"],
                        },
                        "notes": {"type": "string", "description": "Event notes"},
                    },
                    "required": ["title", "date", "start_time", "end_time"],
                },
            },
            {
                "name": "check_conflicts",
                "description": "Check for scheduling conflicts on a given date/time.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string", "description": "Date (YYYY-MM-DD)"},
                        "start_time": {
                            "type": "string",
                            "description": "Start time (HH:MM)",
                        },
                        "end_time": {
                            "type": "string",
                            "description": "End time (HH:MM)",
                        },
                    },
                    "required": ["date", "start_time", "end_time"],
                },
            },
            {
                "name": "get_today_schedule",
                "description": "Get today's full schedule with all events.",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        ]

    def get_calendar_events(
        self, start_date: str, end_date: str | None = None
    ) -> list[dict]:
        """Get events within a date range."""
        if self.db:
            return self.db.get_events(start_date, end_date)
        events = json.loads(self.calendar_file.read_text())
        if not end_date:
            end_date = start_date
        filtered = [
            e for e in events if start_date <= e.get("date", "") <= end_date
        ]
        return sorted(filtered, key=lambda e: (e.get("date", ""), e.get("start_time", "")))

    def add_calendar_event(
        self,
        title: str,
        date: str,
        start_time: str,
        end_time: str,
        location: str = "",
        attendees: list[str] | None = None,
        priority: str = "medium",
        notes: str = "",
    ) -> dict:
        """Add a new calendar event."""
        if self.db:
            event = self.db.create_event(
                title=title, date=date, start_time=start_time, end_time=end_time,
                location=location, attendees=attendees or [], priority=priority, notes=notes,
            )
            return {"status": "created", "event": event}
        events = json.loads(self.calendar_file.read_text())
        event = {
            "id": f"evt_{len(events) + 1:04d}",
            "title": title,
            "date": date,
            "start_time": start_time,
            "end_time": end_time,
            "location": location,
            "attendees": attendees or [],
            "priority": priority,
            "notes": notes,
            "created_at": datetime.now().isoformat(),
        }
        events.append(event)
        self.calendar_file.write_text(json.dumps(events, indent=2))
        return {"status": "created", "event": event}

    def check_conflicts(self, date: str, start_time: str, end_time: str) -> dict:
        """Check for scheduling conflicts."""
        if self.db:
            return self.db.check_conflicts(date, start_time, end_time)
        events = self.get_calendar_events(date)
        conflicts = []
        for evt in events:
            evt_start = evt.get("start_time", "")
            evt_end = evt.get("end_time", "")
            if evt_start < end_time and evt_end > start_time:
                conflicts.append(evt)
        return {
            "has_conflicts": len(conflicts) > 0,
            "conflicts": conflicts,
        }

    def get_today_schedule(self) -> list[dict]:
        """Get today's schedule."""
        if self.db:
            return self.db.get_today_schedule()
        today = datetime.now().strftime("%Y-%m-%d")
        return self.get_calendar_events(today)

    def handle_tool_call(self, tool_name: str, tool_input: dict) -> Any:
        dispatch = {
            "get_calendar_events": lambda: self.get_calendar_events(**tool_input),
            "add_calendar_event": lambda: self.add_calendar_event(**tool_input),
            "check_conflicts": lambda: self.check_conflicts(**tool_input),
            "get_today_schedule": lambda: self.get_today_schedule(**tool_input),
        }
        handler = dispatch.get(tool_name)
        if handler:
            return handler()
        return {"error": f"Unknown calendar tool: {tool_name}"}

    @staticmethod
    def _get_demo_events() -> list[dict]:
        """Generate demo calendar events."""
        today = datetime.now()
        return [
            {
                "id": "evt_0001",
                "title": "Morning Standup",
                "date": today.strftime("%Y-%m-%d"),
                "start_time": "09:00",
                "end_time": "09:30",
                "location": "Conference Room A",
                "attendees": ["Team Lead", "Dev Team"],
                "priority": "medium",
                "notes": "Daily sync",
            },
            {
                "id": "evt_0002",
                "title": "SPL Digital Channels Review",
                "date": today.strftime("%Y-%m-%d"),
                "start_time": "10:00",
                "end_time": "11:00",
                "location": "Board Room",
                "attendees": ["CTO", "Digital Team", "Analytics"],
                "priority": "high",
                "notes": "Monthly performance review of all digital channels",
            },
            {
                "id": "evt_0003",
                "title": "Lunch with TechVentures",
                "date": today.strftime("%Y-%m-%d"),
                "start_time": "12:30",
                "end_time": "14:00",
                "location": "Executive Dining",
                "attendees": ["CEO", "BizDev Lead", "TechVentures Team"],
                "priority": "high",
                "notes": "Partnership discussion",
            },
            {
                "id": "evt_0004",
                "title": "Project Alpha Status Update",
                "date": today.strftime("%Y-%m-%d"),
                "start_time": "14:30",
                "end_time": "15:30",
                "location": "Virtual - Teams",
                "attendees": ["PM", "Dev Leads", "QA"],
                "priority": "medium",
                "notes": "Review milestone 3 delay and replan",
            },
            {
                "id": "evt_0005",
                "title": "Weekly Planning",
                "date": (today + timedelta(days=1)).strftime("%Y-%m-%d"),
                "start_time": "09:00",
                "end_time": "10:30",
                "location": "Conference Room B",
                "attendees": ["All Managers"],
                "priority": "medium",
                "notes": "Plan next week priorities",
            },
            {
                "id": "evt_0006",
                "title": "Board Meeting",
                "date": (today + timedelta(days=2)).strftime("%Y-%m-%d"),
                "start_time": "10:00",
                "end_time": "12:00",
                "location": "Board Room",
                "attendees": ["Board Members", "C-Suite"],
                "priority": "high",
                "notes": "Q4 results and 2026 strategy",
            },
        ]
