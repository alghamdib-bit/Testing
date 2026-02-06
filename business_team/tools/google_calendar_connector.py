"""
Google Calendar Connector — Real calendar access via Google Calendar API (OAuth2).

Handles reading events, creating events, and checking availability.
On first run, opens a browser for OAuth consent. Token is cached for future use.
Falls back to demo data if credentials are not configured.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    GOOGLE_API_AVAILABLE = True
except BaseException:
    GOOGLE_API_AVAILABLE = False

from business_team import config

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
]


class GoogleCalendarConnector:
    """Real Google Calendar access via OAuth2 API."""

    def __init__(self):
        self.credentials_file = os.getenv(
            "GOOGLE_CREDENTIALS_FILE",
            str(config.BASE_DIR / "credentials.json"),
        )
        self.token_file = str(config.BASE_DIR / "token.json")
        self.is_configured = (
            GOOGLE_API_AVAILABLE
            and Path(self.credentials_file).exists()
        )
        self._service = None

    def _get_service(self):
        """Get or create the Google Calendar API service."""
        if self._service:
            return self._service

        if not self.is_configured:
            return None

        creds = None
        if Path(self.token_file).exists():
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES
                )
                creds = flow.run_local_server(port=0)
            Path(self.token_file).write_text(creds.to_json())

        self._service = build("calendar", "v3", credentials=creds)
        return self._service

    @staticmethod
    def get_tool_definitions() -> list[dict]:
        return [
            {
                "name": "gcal_get_events",
                "description": "Get upcoming Google Calendar events for a date range.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "days_ahead": {
                            "type": "integer",
                            "description": "Number of days ahead to look",
                            "default": 1,
                        },
                        "max_results": {
                            "type": "integer",
                            "default": 20,
                        },
                    },
                    "required": [],
                },
            },
            {
                "name": "gcal_get_today",
                "description": "Get all of today's Google Calendar events.",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
            {
                "name": "gcal_create_event",
                "description": "Create a new event on Google Calendar.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string", "description": "Event title"},
                        "date": {"type": "string", "description": "Date YYYY-MM-DD"},
                        "start_time": {"type": "string", "description": "Start time HH:MM"},
                        "end_time": {"type": "string", "description": "End time HH:MM"},
                        "description": {"type": "string", "description": "Event description"},
                        "location": {"type": "string"},
                        "attendees": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of attendee email addresses",
                        },
                    },
                    "required": ["summary", "date", "start_time", "end_time"],
                },
            },
            {
                "name": "gcal_check_availability",
                "description": "Check if a time slot is free on Google Calendar.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string", "description": "Date YYYY-MM-DD"},
                        "start_time": {"type": "string", "description": "Start HH:MM"},
                        "end_time": {"type": "string", "description": "End HH:MM"},
                    },
                    "required": ["date", "start_time", "end_time"],
                },
            },
            {
                "name": "gcal_list_calendars",
                "description": "List all available Google Calendars.",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        ]

    def gcal_get_events(self, days_ahead: int = 1, max_results: int = 20) -> list[dict]:
        """Get upcoming events."""
        service = self._get_service()
        if not service:
            return self._demo_events(days_ahead)

        try:
            now = datetime.utcnow()
            time_min = now.isoformat() + "Z"
            time_max = (now + timedelta(days=days_ahead)).isoformat() + "Z"

            result = service.events().list(
                calendarId="primary",
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            ).execute()

            events = []
            for evt in result.get("items", []):
                start = evt["start"].get("dateTime", evt["start"].get("date", ""))
                end = evt["end"].get("dateTime", evt["end"].get("date", ""))
                events.append({
                    "source": "google_calendar",
                    "id": evt.get("id", ""),
                    "title": evt.get("summary", "(no title)"),
                    "start": start,
                    "end": end,
                    "location": evt.get("location", ""),
                    "description": evt.get("description", "")[:200],
                    "attendees": [
                        a.get("email", "") for a in evt.get("attendees", [])
                    ],
                    "status": evt.get("status", ""),
                    "html_link": evt.get("htmlLink", ""),
                })
            return events

        except Exception as e:
            return [{"error": f"Google Calendar API failed: {str(e)}"}]

    def gcal_get_today(self) -> list[dict]:
        """Get today's events."""
        service = self._get_service()
        if not service:
            return self._demo_events(0)

        try:
            now = datetime.utcnow()
            start_of_day = now.replace(hour=0, minute=0, second=0).isoformat() + "Z"
            end_of_day = now.replace(hour=23, minute=59, second=59).isoformat() + "Z"

            result = service.events().list(
                calendarId="primary",
                timeMin=start_of_day,
                timeMax=end_of_day,
                singleEvents=True,
                orderBy="startTime",
            ).execute()

            events = []
            for evt in result.get("items", []):
                start = evt["start"].get("dateTime", evt["start"].get("date", ""))
                end = evt["end"].get("dateTime", evt["end"].get("date", ""))
                events.append({
                    "source": "google_calendar",
                    "id": evt.get("id", ""),
                    "title": evt.get("summary", "(no title)"),
                    "start": start,
                    "end": end,
                    "location": evt.get("location", ""),
                    "attendees": [
                        a.get("email", "") for a in evt.get("attendees", [])
                    ],
                })
            return events

        except Exception as e:
            return [{"error": f"Google Calendar failed: {str(e)}"}]

    def gcal_create_event(
        self,
        summary: str,
        date: str,
        start_time: str,
        end_time: str,
        description: str = "",
        location: str = "",
        attendees: list[str] | None = None,
    ) -> dict:
        """Create a calendar event."""
        service = self._get_service()
        if not service:
            return {"status": "demo_mode", "message": f"Would create: {summary} on {date}"}

        try:
            # Build ISO datetime with timezone (default to Asia/Riyadh)
            tz = "Asia/Riyadh"
            start_dt = f"{date}T{start_time}:00"
            end_dt = f"{date}T{end_time}:00"

            event_body = {
                "summary": summary,
                "start": {"dateTime": start_dt, "timeZone": tz},
                "end": {"dateTime": end_dt, "timeZone": tz},
            }
            if description:
                event_body["description"] = description
            if location:
                event_body["location"] = location
            if attendees:
                event_body["attendees"] = [{"email": a} for a in attendees]

            created = service.events().insert(
                calendarId="primary", body=event_body
            ).execute()

            return {
                "status": "created",
                "event_id": created.get("id", ""),
                "html_link": created.get("htmlLink", ""),
                "summary": summary,
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def gcal_check_availability(
        self, date: str, start_time: str, end_time: str
    ) -> dict:
        """Check if a time slot is free."""
        service = self._get_service()
        if not service:
            return {"available": True, "source": "demo"}

        try:
            tz = "Asia/Riyadh"
            time_min = f"{date}T{start_time}:00+03:00"
            time_max = f"{date}T{end_time}:00+03:00"

            result = service.events().list(
                calendarId="primary",
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
            ).execute()

            conflicts = result.get("items", [])
            return {
                "available": len(conflicts) == 0,
                "conflicts": [
                    {"title": e.get("summary", ""), "start": e["start"].get("dateTime", "")}
                    for e in conflicts
                ],
            }

        except Exception as e:
            return {"error": str(e)}

    def gcal_list_calendars(self) -> list[dict]:
        """List available calendars."""
        service = self._get_service()
        if not service:
            return [{"id": "primary", "summary": "Primary Calendar", "source": "demo"}]

        try:
            result = service.calendarList().list().execute()
            return [
                {
                    "id": cal.get("id", ""),
                    "summary": cal.get("summary", ""),
                    "primary": cal.get("primary", False),
                    "access_role": cal.get("accessRole", ""),
                }
                for cal in result.get("items", [])
            ]
        except Exception as e:
            return [{"error": str(e)}]

    def handle_tool_call(self, tool_name: str, tool_input: dict) -> Any:
        dispatch = {
            "gcal_get_events": lambda: self.gcal_get_events(**tool_input),
            "gcal_get_today": lambda: self.gcal_get_today(**tool_input),
            "gcal_create_event": lambda: self.gcal_create_event(**tool_input),
            "gcal_check_availability": lambda: self.gcal_check_availability(**tool_input),
            "gcal_list_calendars": lambda: self.gcal_list_calendars(**tool_input),
        }
        handler = dispatch.get(tool_name)
        if handler:
            return handler()
        return {"error": f"Unknown Google Calendar tool: {tool_name}"}

    @staticmethod
    def _demo_events(days: int) -> list[dict]:
        today = datetime.now()
        return [
            {
                "source": "demo",
                "id": "demo_gc1",
                "title": "Personal - Gym",
                "start": f"{today.strftime('%Y-%m-%d')}T06:00:00",
                "end": f"{today.strftime('%Y-%m-%d')}T07:00:00",
                "location": "Fitness Center",
            },
            {
                "source": "demo",
                "id": "demo_gc2",
                "title": "Family Dinner",
                "start": f"{today.strftime('%Y-%m-%d')}T19:00:00",
                "end": f"{today.strftime('%Y-%m-%d')}T21:00:00",
                "location": "Home",
            },
        ]
