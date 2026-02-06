"""
Projects Manager Agent

Responsibilities:
- Maintain the project portfolio dashboard
- Track project milestones, tasks, and progress
- Produce weekly and monthly project reports
- Manage the team task board (Kanban-style)
- Flag at-risk projects and overdue tasks
- Coordinate with Secretary and Analyst for cross-functional updates
"""

from typing import Any

from .base_agent import BaseAgent
from business_team.tools.project_tools import ProjectTools
from business_team.tools.reporting_tools import ReportingTools

PM_SYSTEM_PROMPT = """You are the Projects Manager Agent responsible for all project tracking and reporting. Your responsibilities are:

1. **Project Dashboard**: Maintain a live view of all projects with status, progress, milestones, and risks.
2. **Task Management**: Track all tasks across projects, monitor assignments, and flag blockers.
3. **Weekly Reports**: Produce structured weekly reports with highlights, status updates, risks, and next-week priorities.
4. **Monthly Reports**: Create comprehensive monthly reports with executive summaries, detailed project breakdowns, and team metrics.
5. **Status Board**: Maintain a Kanban-style project status board for the team.

PROJECT TRACKING RULES:
- Projects have statuses: ACTIVE, ON_HOLD, COMPLETED, AT_RISK
- Tasks have statuses: TODO, IN_PROGRESS, REVIEW, DONE, BLOCKED
- Priority levels: HIGH, MEDIUM, LOW
- Always calculate and report: overall progress %, tasks completed vs total, milestones on track
- Flag any project with >10% schedule slippage as AT_RISK
- Flag any task overdue by >2 days

REPORTING FORMAT:
Weekly reports must include:
- Key highlights (what was achieved)
- Project-by-project status with progress bars
- Risks and blockers
- Next week priorities

Monthly reports must include:
- Executive summary
- Detailed project breakdowns with milestones
- Team metrics (tasks completed, velocity, etc.)
- Risk register
- Next month outlook

You have access to project management tools and report generation tools. Use them to produce data-driven reports."""


class ProjectsManagerAgent(BaseAgent):
    """Projects Manager agent for project tracking and reporting."""

    def __init__(self, db=None, memory=None):
        super().__init__(
            name="projects_manager",
            role="Projects Manager - Project Tracking & Reporting",
            system_prompt=PM_SYSTEM_PROMPT,
            memory=memory,
            db=db,
        )
        self.project_tools = ProjectTools(db=db)
        self.reporting_tools = ReportingTools()

        all_tools = (
            ProjectTools.get_tool_definitions()
            + ReportingTools.get_tool_definitions()
        )
        self.register_tools(all_tools)

    def execute_tool(self, tool_name: str, tool_input: dict) -> Any:
        """Route tool calls to the appropriate handler."""
        if tool_name in (
            "get_projects", "get_project_detail", "create_project",
            "update_project", "get_tasks", "create_task", "update_task",
            "get_project_summary",
        ):
            return self.project_tools.handle_tool_call(tool_name, tool_input)
        if tool_name in (
            "generate_weekly_report", "generate_monthly_report",
            "generate_project_status_board",
        ):
            return self.reporting_tools.handle_tool_call(tool_name, tool_input)

        self.logger.warning(f"Unknown tool: {tool_name}")
        return {"error": f"Unknown tool: {tool_name}"}

    def get_portfolio_status(self) -> str:
        """Get the full project portfolio status."""
        return self.think(
            "Give me a complete portfolio status. Steps:\n"
            "1. Get all projects using get_projects\n"
            "2. Get the project summary using get_project_summary\n"
            "3. Get all tasks using get_tasks\n"
            "4. Analyze: which projects are on track, at risk, or blocked\n"
            "5. List all overdue tasks\n"
            "6. Generate a project status board using generate_project_status_board\n"
            "Use filename 'project_status_board' for the board.\n"
            "Provide a clear summary with priorities and action items."
        )

    def generate_weekly_update(self) -> str:
        """Generate the weekly project report."""
        return self.think(
            "Generate the weekly project report. Steps:\n"
            "1. Get all projects and their current status\n"
            "2. Get all tasks and analyze progress this week\n"
            "3. Get the project summary for high-level metrics\n"
            "4. Identify this week's highlights (completed tasks, milestones)\n"
            "5. Identify risks and blockers\n"
            "6. Define next week's priorities\n"
            "7. Generate the weekly report HTML using generate_weekly_report\n"
            "Use filename 'weekly_report' for the output.\n"
            "Include all projects with their status, progress, and key notes."
        )

    def generate_monthly_update(self) -> str:
        """Generate the monthly project report."""
        return self.think(
            "Generate the monthly project report. Steps:\n"
            "1. Get all projects with detailed status\n"
            "2. For each project, get tasks and milestones\n"
            "3. Write an executive summary covering overall portfolio health\n"
            "4. Detail each project: status, progress, completed milestones, issues, next goals\n"
            "5. Calculate team metrics: tasks completed, velocity\n"
            "6. Generate the monthly report HTML using generate_monthly_report\n"
            "Use filename 'monthly_report' for the output.\n"
            "Make the executive summary concise but insightful."
        )

    def update_task_status(self, task_id: str, new_status: str, notes: str = "") -> str:
        """Update a specific task."""
        return self.think(
            f"Update task {task_id} to status '{new_status}'."
            + (f" Add note: {notes}" if notes else "")
            + " Then show me the updated task details and any impact on the project."
        )

    def create_new_project(self, name: str, description: str, owner: str, end_date: str) -> str:
        """Create a new project."""
        return self.think(
            f"Create a new project:\n"
            f"- Name: {name}\n"
            f"- Description: {description}\n"
            f"- Owner: {owner}\n"
            f"- Target end date: {end_date}\n"
            f"- Start date: today\n"
            "Create the project and confirm the details. "
            "Then update the project status board with the new project."
        )

    def get_team_workload(self) -> str:
        """Analyze team workload distribution."""
        return self.think(
            "Analyze the team workload. Get all tasks and:\n"
            "1. Group tasks by assignee\n"
            "2. Count total, in-progress, and blocked tasks per person\n"
            "3. Identify who is overloaded and who has capacity\n"
            "4. Flag any single points of failure\n"
            "Provide a clear workload summary with recommendations."
        )
