"""
Office Manager Agent (Supervisor)

Responsibilities:
- Supervise and coordinate Secretary, Business Analyst, and Projects Manager
- Provide the daily briefing with priorities and action items
- Generate weekly briefings with consolidated team reports
- Maintain priority and alarm systems
- Plan and delegate work across the team
- Serve as the primary interface between the agent team and the human manager
"""

import json
from datetime import datetime
from typing import Any

from .base_agent import BaseAgent
from .secretary import SecretaryAgent
from .business_analyst import BusinessAnalystAgent
from .projects_manager import ProjectsManagerAgent
from business_team import config

OFFICE_MANAGER_SYSTEM_PROMPT = """You are the Office Manager Agent — the senior supervisor of a business management team. You coordinate three agents:

1. **Secretary**: Handles emails, calendar, and to-do lists
2. **Business Analyst**: Monitors SPL Digital Channels, creates presentations and dashboards
3. **Projects Manager**: Tracks all projects, tasks, and generates progress reports

YOUR RESPONSIBILITIES:
- **Daily Brief**: Every morning, compile a comprehensive brief covering:
  - Today's schedule and key meetings
  - Email highlights and urgent items
  - Project status updates and risks
  - SPL channel health summary
  - Priority action items for the day

- **Weekly Brief**: Every week, produce a consolidated report:
  - Week's achievements across all areas
  - Project progress and milestones
  - SPL channel performance trends
  - Upcoming priorities and deadlines
  - Risk escalations

- **Priority Management**:
  - Classify all items as: CRITICAL, HIGH, MEDIUM, LOW
  - CRITICAL = needs immediate action (deadlines today, system outages, executive requests)
  - HIGH = needs action within 24h
  - MEDIUM = needs action this week
  - LOW = can be scheduled later

- **Alarm System**:
  - RED ALARM: Critical issues requiring immediate attention
  - YELLOW ALARM: Issues that could escalate if not addressed
  - Monitor and report on alarm status

- **Action Planning**:
  - Break down complex requests into delegated tasks
  - Assign work to the appropriate team member
  - Track completion and follow up

OUTPUT FORMAT for Daily Brief:
```
=== DAILY BRIEF — [Date] ===

ALARMS: [RED/YELLOW/NONE]
[List any active alarms]

PRIORITY ACTIONS:
1. [CRITICAL] ...
2. [HIGH] ...
3. [HIGH] ...

SCHEDULE:
[Today's calendar]

EMAIL HIGHLIGHTS:
[Key emails and action items]

PROJECT UPDATES:
[Status of active projects]

SPL CHANNELS:
[Health summary]

PLAN FOR TODAY:
[Recommended actions and delegation]
```

You receive reports FROM the other agents. Synthesize their information into clear, actionable briefings for your manager. Be decisive and prioritize ruthlessly. Your manager relies on you to surface what matters most."""


class OfficeManagerAgent(BaseAgent):
    """Office Manager — supervises all other agents and provides executive briefings."""

    def __init__(self):
        super().__init__(
            name="office_manager",
            role="Office Manager - Supervisor & Executive Briefings",
            system_prompt=OFFICE_MANAGER_SYSTEM_PROMPT,
        )
        # Initialize subordinate agents
        self.secretary = SecretaryAgent()
        self.analyst = BusinessAnalystAgent()
        self.projects_manager = ProjectsManagerAgent()

        self.alarms: list[dict] = []
        self.daily_log_file = config.DATA_DIR / "daily_briefs.json"
        if not self.daily_log_file.exists():
            self.daily_log_file.write_text("[]")

    def gather_team_reports(self) -> dict:
        """Collect reports from all three subordinate agents."""
        reports = {}

        self.logger.info("Gathering report from Secretary...")
        self.secretary.reset_conversation()
        reports["secretary"] = self.secretary.get_daily_digest()

        self.logger.info("Gathering report from Business Analyst...")
        self.analyst.reset_conversation()
        reports["analyst"] = self.analyst.generate_channel_report()

        self.logger.info("Gathering report from Projects Manager...")
        self.projects_manager.reset_conversation()
        reports["projects_manager"] = self.projects_manager.get_portfolio_status()

        return reports

    def generate_daily_brief(self) -> str:
        """
        Generate the comprehensive daily brief by:
        1. Collecting reports from all agents
        2. Synthesizing into a unified briefing
        3. Setting priorities and alarms
        """
        self.logger.info("=== Generating Daily Brief ===")

        # Gather reports from team
        reports = self.gather_team_reports()

        # Feed reports to the Office Manager's Claude instance for synthesis
        self.reset_conversation()
        prompt = (
            "I have gathered reports from all three team members. "
            "Synthesize them into my daily brief using the standard format.\n\n"
            f"--- SECRETARY REPORT ---\n{reports['secretary']}\n\n"
            f"--- BUSINESS ANALYST REPORT ---\n{reports['analyst']}\n\n"
            f"--- PROJECTS MANAGER REPORT ---\n{reports['projects_manager']}\n\n"
            "Now produce the daily brief with:\n"
            "1. Any ALARMS (red or yellow)\n"
            "2. Prioritized action items (CRITICAL, HIGH, MEDIUM, LOW)\n"
            "3. Today's schedule\n"
            "4. Email highlights\n"
            "5. Project updates\n"
            "6. SPL channels health summary\n"
            "7. Your recommended plan for today\n"
            "Be concise and decisive."
        )

        brief = self.think(prompt)

        # Log the daily brief
        self._log_brief("daily", brief)

        return brief

    def generate_weekly_brief(self) -> str:
        """
        Generate the weekly consolidated brief by:
        1. Getting weekly report from Projects Manager
        2. Getting weekly dashboard from Business Analyst
        3. Getting email/todo summary from Secretary
        4. Synthesizing everything
        """
        self.logger.info("=== Generating Weekly Brief ===")

        reports = {}

        self.secretary.reset_conversation()
        reports["secretary"] = self.secretary.think(
            "Provide a weekly summary of:\n"
            "1. All emails received this week with priorities and action items\n"
            "2. All calendar events that occurred or are upcoming\n"
            "3. To-do list progress: completed, pending, overdue\n"
            "Format as a structured weekly summary."
        )

        self.analyst.reset_conversation()
        reports["analyst"] = self.analyst.think(
            "Provide a weekly SPL Digital Channels summary:\n"
            "1. Get current channel data\n"
            "2. Create a weekly dashboard\n"
            "3. Highlight any channels that changed status\n"
            "4. Provide week-over-week trend analysis\n"
            "5. Top recommendations\n"
            "Use filename 'weekly_spl_dashboard' for the dashboard."
        )

        self.projects_manager.reset_conversation()
        reports["projects_manager"] = self.projects_manager.generate_weekly_update()

        self.reset_conversation()
        prompt = (
            "I have gathered weekly reports from all team members. "
            "Synthesize them into a comprehensive weekly brief.\n\n"
            f"--- SECRETARY WEEKLY SUMMARY ---\n{reports['secretary']}\n\n"
            f"--- BUSINESS ANALYST WEEKLY SUMMARY ---\n{reports['analyst']}\n\n"
            f"--- PROJECTS MANAGER WEEKLY REPORT ---\n{reports['projects_manager']}\n\n"
            "Produce the weekly brief with:\n"
            "1. WEEK HIGHLIGHTS: Top 5 things that happened\n"
            "2. ALARMS AND RISKS: Issues needing escalation\n"
            "3. PROJECT PORTFOLIO: Status of each project\n"
            "4. SPL CHANNELS: Weekly health and trends\n"
            "5. ACTION ITEMS: Carried over and new\n"
            "6. NEXT WEEK PRIORITIES: Recommended focus areas\n"
            "Be strategic and prioritize by impact."
        )

        brief = self.think(prompt)
        self._log_brief("weekly", brief)
        return brief

    def set_alarm(self, level: str, message: str, source: str = "") -> dict:
        """Set a red or yellow alarm."""
        alarm = {
            "level": level,
            "message": message,
            "source": source,
            "timestamp": datetime.now().isoformat(),
            "resolved": False,
        }
        self.alarms.append(alarm)
        self.logger.warning(f"ALARM [{level.upper()}]: {message}")
        return alarm

    def resolve_alarm(self, index: int) -> dict:
        """Resolve an active alarm."""
        if 0 <= index < len(self.alarms):
            self.alarms[index]["resolved"] = True
            self.alarms[index]["resolved_at"] = datetime.now().isoformat()
            return self.alarms[index]
        return {"error": "Invalid alarm index"}

    def get_active_alarms(self) -> list[dict]:
        """Get all unresolved alarms."""
        return [a for a in self.alarms if not a.get("resolved")]

    def delegate_task(self, task_description: str) -> str:
        """Analyze a request and delegate to the appropriate agent."""
        self.reset_conversation()
        prompt = (
            f"The manager has a new request: '{task_description}'\n\n"
            "Analyze this request and determine:\n"
            "1. Which team member(s) should handle it: Secretary, Business Analyst, or Projects Manager?\n"
            "2. What specific actions should they take?\n"
            "3. What is the priority level?\n"
            "4. What is the expected timeline?\n\n"
            "Provide a clear delegation plan."
        )
        plan = self.think(prompt)

        # Execute delegation based on keywords in the plan
        task_lower = task_description.lower()
        results = {"plan": plan, "delegated_to": [], "results": {}}

        if any(kw in task_lower for kw in ("email", "calendar", "schedule", "todo", "meeting")):
            self.secretary.reset_conversation()
            results["delegated_to"].append("secretary")
            results["results"]["secretary"] = self.secretary.think(
                f"The Office Manager has delegated this task to you: {task_description}"
            )

        if any(kw in task_lower for kw in ("spl", "channel", "dashboard", "presentation", "kpi", "analytics")):
            self.analyst.reset_conversation()
            results["delegated_to"].append("business_analyst")
            results["results"]["analyst"] = self.analyst.think(
                f"The Office Manager has delegated this task to you: {task_description}"
            )

        if any(kw in task_lower for kw in ("project", "task", "milestone", "report", "status", "progress")):
            self.projects_manager.reset_conversation()
            results["delegated_to"].append("projects_manager")
            results["results"]["projects_manager"] = self.projects_manager.think(
                f"The Office Manager has delegated this task to you: {task_description}"
            )

        return json.dumps(results, indent=2)

    def get_team_status(self) -> dict:
        """Get the status of all team agents."""
        return {
            "office_manager": self.get_status(),
            "secretary": self.secretary.get_status(),
            "business_analyst": self.analyst.get_status(),
            "projects_manager": self.projects_manager.get_status(),
            "active_alarms": self.get_active_alarms(),
            "timestamp": datetime.now().isoformat(),
        }

    def handle_manager_request(self, request: str) -> str:
        """
        Main entry point for the human manager to interact with the system.
        The Office Manager analyzes the request and routes accordingly.
        """
        self.reset_conversation()
        prompt = (
            f"The manager says: '{request}'\n\n"
            "Determine the best course of action. You can:\n"
            "- Answer directly if it's a question about status\n"
            "- Delegate to Secretary for email/calendar/todo requests\n"
            "- Delegate to Business Analyst for SPL channels/presentation requests\n"
            "- Delegate to Projects Manager for project/task requests\n"
            "- Coordinate multiple agents for complex requests\n\n"
            "What would you like to do? Explain your plan first, then I'll execute it."
        )
        plan = self.think(prompt)

        # Auto-delegate based on the plan
        return self.delegate_task(request) if "delegate" in plan.lower() else plan

    def _log_brief(self, brief_type: str, content: str) -> None:
        """Log a brief to the persistent log."""
        briefs = json.loads(self.daily_log_file.read_text())
        briefs.append(
            {
                "type": brief_type,
                "content": content,
                "timestamp": datetime.now().isoformat(),
            }
        )
        # Keep last 90 entries
        if len(briefs) > 90:
            briefs = briefs[-90:]
        self.daily_log_file.write_text(json.dumps(briefs, indent=2))
