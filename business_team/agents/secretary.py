"""
Secretary Agent

Responsibilities:
- Read, summarize, and log emails from Gmail (personal) and SPL Exchange (work)
- Manage calendar events from Google Calendar (personal) and Exchange (work)
- Maintain the to-do list
- Flag urgent items to the Office Manager
- Produce daily inbox digests combining all sources
"""

from typing import Any

from .base_agent import BaseAgent
from business_team.tools.email_tools import EmailTools
from business_team.tools.calendar_tools import CalendarTools
from business_team.tools.todo_tools import TodoTools
from business_team.tools.gmail_connector import GmailConnector
from business_team.tools.google_calendar_connector import GoogleCalendarConnector
from business_team.tools.exchange_connector import ExchangeConnector

SECRETARY_SYSTEM_PROMPT = """You are the Secretary Agent for Bandar Alhattab, a senior business manager at SPL (Saudi Post).

You manage TWO email accounts and TWO calendars:

**PERSONAL (Gmail + Google Calendar)**
- Gmail: Read/search/send personal emails
- Google Calendar: Personal appointments, family events, personal reminders

**WORK (SPL Exchange)**
- SPL Exchange: Read/search/send work emails (basalghamdi@splonline.com.sa)
- SPL Calendar: Work meetings, project reviews, standups

**LOCAL**
- To-Do List: Unified task list combining personal and work items
- Local Calendar: Quick event management (syncs with above)

YOUR RESPONSIBILITIES:
1. **Email Management**: Read and summarize emails from BOTH accounts. Clearly label each email as [PERSONAL] or [WORK].
2. **Calendar Management**: Track events from ALL calendars. Merge them into a unified daily view.
3. **To-Do List**: Maintain the manager's to-do list, add items from emails and meetings, track completion.

CRITICAL RULES:
- Always identify the SOURCE of each email (Gmail/SPL) when reporting.
- Flag HIGH priority items immediately (deadlines within 24h, executive requests, financial matters).
- When logging emails, always extract action items and assign [PERSONAL] or [WORK] tags.
- Check for calendar conflicts ACROSS both calendars (a work meeting and personal appointment at the same time).
- For daily digests, present a UNIFIED timeline merging all calendar sources.
- Keep running counts: unread emails (per account), pending todos, upcoming meetings.

TOOL PREFIXES:
- gmail_* tools → Personal Gmail account
- gcal_* tools → Personal Google Calendar
- spl_* tools → SPL work account (email + calendar)
- read_emails, send_email, etc. → Legacy/local tools
- get_calendar_events, etc. → Local calendar
- get_todos, add_todo, etc. → To-do list

OUTPUT FORMAT:
Structure your reports clearly with sections. Use bullet points for action items.
Always end reports with a "PRIORITY ALERTS" section if there are urgent items."""


class SecretaryAgent(BaseAgent):
    """Secretary agent managing emails, calendar, and to-do lists across multiple accounts."""

    def __init__(self, db=None, memory=None):
        super().__init__(
            name="secretary",
            role="Secretary - Multi-Account Email, Calendar & To-Do Management",
            system_prompt=SECRETARY_SYSTEM_PROMPT,
            memory=memory,
            db=db,
        )
        # Legacy/local tools (always available, provide demo fallback)
        self.email_tools = EmailTools(db=db)
        self.calendar_tools = CalendarTools(db=db)
        self.todo_tools = TodoTools(db=db)

        # Real connectors (gracefully degrade to demo if not configured)
        self.gmail = GmailConnector()
        self.gcal = GoogleCalendarConnector()
        self.exchange = ExchangeConnector()

        # Register all tools from all sources
        all_tools = (
            EmailTools.get_tool_definitions()
            + CalendarTools.get_tool_definitions()
            + TodoTools.get_tool_definitions()
            + GmailConnector.get_tool_definitions()
            + GoogleCalendarConnector.get_tool_definitions()
            + ExchangeConnector.get_tool_definitions()
        )
        self.register_tools(all_tools)

    def execute_tool(self, tool_name: str, tool_input: dict) -> Any:
        """Route tool calls to the appropriate tool handler."""
        # Gmail connector tools
        if tool_name.startswith("gmail_"):
            return self.gmail.handle_tool_call(tool_name, tool_input)
        # Google Calendar connector tools
        if tool_name.startswith("gcal_"):
            return self.gcal.handle_tool_call(tool_name, tool_input)
        # SPL Exchange connector tools
        if tool_name.startswith("spl_"):
            return self.exchange.handle_tool_call(tool_name, tool_input)
        # Legacy email tools
        if tool_name in ("read_emails", "log_email_summary", "send_email", "get_email_log"):
            return self.email_tools.handle_tool_call(tool_name, tool_input)
        # Local calendar tools
        if tool_name in ("get_calendar_events", "add_calendar_event", "check_conflicts", "get_today_schedule"):
            return self.calendar_tools.handle_tool_call(tool_name, tool_input)
        # Todo tools
        if tool_name in ("get_todos", "add_todo", "update_todo", "get_todo_summary"):
            return self.todo_tools.handle_tool_call(tool_name, tool_input)

        self.logger.warning(f"Unknown tool: {tool_name}")
        return {"error": f"Unknown tool: {tool_name}"}

    def check_inbox(self) -> str:
        """Run the email check workflow across all accounts."""
        return self.think(
            "Check my emails from ALL accounts now:\n"
            "1. Read recent Gmail emails (personal) using gmail_read_inbox\n"
            "2. Read recent SPL Exchange emails (work) using spl_read_inbox\n"
            "3. Summarize each email, clearly marking [PERSONAL] or [WORK]\n"
            "4. Log important ones with appropriate priority\n"
            "5. Identify any action items or meetings to add\n"
            "Present a unified inbox summary."
        )

    def get_daily_digest(self) -> str:
        """Produce the morning daily digest from all sources."""
        return self.think(
            "Prepare my comprehensive daily digest. I need:\n"
            "1. TODAY'S UNIFIED SCHEDULE:\n"
            "   - Get Google Calendar events (gcal_get_today)\n"
            "   - Get SPL Exchange calendar (spl_get_calendar)\n"
            "   - Get local calendar events (get_today_schedule)\n"
            "   - Merge ALL into one timeline sorted by time\n"
            "2. EMAIL SUMMARY:\n"
            "   - Read Gmail inbox (gmail_read_inbox)\n"
            "   - Read SPL Exchange inbox (spl_read_inbox)\n"
            "   - Summarize unread/important emails from both, tagged [PERSONAL] or [WORK]\n"
            "3. TO-DO STATUS:\n"
            "   - Get todo summary (get_todo_summary)\n"
            "   - Show pending items by priority\n"
            "4. CONFLICTS: Check for any cross-calendar conflicts\n"
            "5. PRIORITY ALERTS: Flag anything urgent\n"
            "Format it as a clear, structured morning briefing."
        )

    def get_todo_report(self) -> str:
        """Get the current to-do status."""
        return self.think(
            "Give me a complete to-do list report. Show all items grouped by priority, "
            "highlight any overdue items, and provide a summary count."
        )

    def get_calendar_briefing(self, date: str = "") -> str:
        """Get calendar briefing combining all sources."""
        prompt = f"Show me the calendar for {date}." if date else "Show me today's full calendar schedule."
        prompt += (
            "\nCombine events from:\n"
            "1. Google Calendar (personal) using gcal_get_today or gcal_get_events\n"
            "2. SPL Exchange calendar (work) using spl_get_calendar\n"
            "3. Local calendar using get_today_schedule\n"
            "Present a unified timeline with source labels. Flag any conflicts."
        )
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

    def check_gmail(self) -> str:
        """Check only Gmail inbox."""
        return self.think(
            "Check my personal Gmail inbox using gmail_read_inbox. "
            "Show me all recent emails with summaries and priorities."
        )

    def check_work_email(self) -> str:
        """Check only SPL Exchange inbox."""
        return self.think(
            "Check my SPL work inbox using spl_read_inbox. "
            "Show me all recent work emails with summaries and priorities."
        )
