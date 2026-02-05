"""
Secretary Agent

Responsibilities:
- Read, summarize, and log emails
- Manage calendar events and schedule
- Maintain the to-do list
- Flag urgent items to the Office Manager
- Produce daily inbox digests
"""

from typing import Any

from .base_agent import BaseAgent
from business_team.tools.email_tools import EmailTools
from business_team.tools.calendar_tools import CalendarTools
from business_team.tools.todo_tools import TodoTools

SECRETARY_SYSTEM_PROMPT = """You are the Secretary Agent for a senior business manager. Your responsibilities are:

1. **Email Management**: Read, summarize, and log all incoming emails. Identify priority, action items, and deadlines.
2. **Calendar Management**: Track all calendar events, detect conflicts, and prepare daily schedules.
3. **To-Do List**: Maintain the manager's to-do list, add items from emails and meetings, track completion.

CRITICAL RULES:
- Always summarize emails concisely (2-3 sentences max per email).
- Flag HIGH priority items immediately (deadlines within 24h, executive requests, financial matters).
- When logging emails, always extract action items.
- Check for calendar conflicts when new meetings are mentioned.
- Report the daily schedule every morning.
- Keep running counts: unread emails, pending todos, upcoming meetings.

OUTPUT FORMAT:
Structure your reports clearly with sections. Use bullet points for action items.
Always end reports with a "PRIORITY ALERTS" section if there are urgent items.

You have access to email, calendar, and to-do tools. Use them to gather data before making reports."""


class SecretaryAgent(BaseAgent):
    """Secretary agent managing emails, calendar, and to-do lists."""

    def __init__(self):
        super().__init__(
            name="secretary",
            role="Secretary - Email, Calendar & To-Do Management",
            system_prompt=SECRETARY_SYSTEM_PROMPT,
        )
        self.email_tools = EmailTools()
        self.calendar_tools = CalendarTools()
        self.todo_tools = TodoTools()

        # Register all tools with the Claude API
        all_tools = (
            EmailTools.get_tool_definitions()
            + CalendarTools.get_tool_definitions()
            + TodoTools.get_tool_definitions()
        )
        self.register_tools(all_tools)

    def execute_tool(self, tool_name: str, tool_input: dict) -> Any:
        """Route tool calls to the appropriate tool handler."""
        # Email tools
        if tool_name in ("read_emails", "log_email_summary", "send_email", "get_email_log"):
            return self.email_tools.handle_tool_call(tool_name, tool_input)
        # Calendar tools
        if tool_name in ("get_calendar_events", "add_calendar_event", "check_conflicts", "get_today_schedule"):
            return self.calendar_tools.handle_tool_call(tool_name, tool_input)
        # Todo tools
        if tool_name in ("get_todos", "add_todo", "update_todo", "get_todo_summary"):
            return self.todo_tools.handle_tool_call(tool_name, tool_input)

        self.logger.warning(f"Unknown tool: {tool_name}")
        return {"error": f"Unknown tool: {tool_name}"}

    def check_inbox(self) -> str:
        """Run the email check workflow."""
        return self.think(
            "Check my emails now. Read all recent emails, summarize each one, "
            "log them with appropriate priority levels, and identify any action items. "
            "Also check if any emails mention meetings that should be added to the calendar."
        )

    def get_daily_digest(self) -> str:
        """Produce the morning daily digest."""
        return self.think(
            "Prepare my daily digest. I need:\n"
            "1. Today's calendar schedule with all events\n"
            "2. Unread email summary with priorities\n"
            "3. Pending to-do items sorted by priority\n"
            "4. Any scheduling conflicts\n"
            "5. PRIORITY ALERTS for anything urgent\n"
            "Format it as a clear, structured daily briefing."
        )

    def get_todo_report(self) -> str:
        """Get the current to-do status."""
        return self.think(
            "Give me a complete to-do list report. Show all items grouped by priority, "
            "highlight any overdue items, and provide a summary count."
        )

    def get_calendar_briefing(self, date: str = "") -> str:
        """Get calendar briefing for a specific date or today."""
        prompt = f"Show me the calendar for {date}." if date else "Show me today's full calendar schedule."
        prompt += " Include all events with times, locations, attendees, and any conflicts."
        return self.think(prompt)

    def process_new_email(self, email_data: dict) -> str:
        """Process a specific new email."""
        return self.think(
            f"Process this new email:\n"
            f"From: {email_data.get('from', 'Unknown')}\n"
            f"Subject: {email_data.get('subject', 'No subject')}\n"
            f"Body: {email_data.get('body', '')}\n\n"
            "Summarize it, log it with the right priority, extract action items, "
            "and check if any meetings need to be added to the calendar."
        )
