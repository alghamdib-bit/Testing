"""
Reporting tools for the Projects Manager Agent.

Generates weekly and monthly reports in HTML format,
combining data from projects, tasks, and team activity.
"""

import json
from datetime import datetime, timedelta
from typing import Any

from business_team import config


class ReportingTools:
    """Tools for generating periodic reports."""

    def __init__(self):
        self.output_dir = config.OUTPUT_DIR / "reports"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def get_tool_definitions() -> list[dict]:
        return [
            {
                "name": "generate_weekly_report",
                "description": "Generate a weekly project status report in HTML format.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "week_number": {"type": "integer"},
                        "year": {"type": "integer"},
                        "projects_summary": {
                            "type": "object",
                            "description": "Summary data for all projects",
                        },
                        "highlights": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Key highlights of the week",
                        },
                        "risks": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Risks and blockers",
                        },
                        "next_week_priorities": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Priorities for next week",
                        },
                        "filename": {"type": "string"},
                    },
                    "required": ["projects_summary", "highlights", "filename"],
                },
            },
            {
                "name": "generate_monthly_report",
                "description": "Generate a comprehensive monthly project report in HTML.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "month": {"type": "integer"},
                        "year": {"type": "integer"},
                        "executive_summary": {"type": "string"},
                        "projects_detail": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "status": {"type": "string"},
                                    "progress": {"type": "integer"},
                                    "milestones_completed": {"type": "array", "items": {"type": "string"}},
                                    "issues": {"type": "array", "items": {"type": "string"}},
                                    "next_month_goals": {"type": "array", "items": {"type": "string"}},
                                },
                            },
                        },
                        "team_metrics": {
                            "type": "object",
                            "description": "Team performance metrics",
                        },
                        "filename": {"type": "string"},
                    },
                    "required": ["executive_summary", "projects_detail", "filename"],
                },
            },
            {
                "name": "generate_project_status_board",
                "description": "Generate an HTML project status board (Kanban-style) showing all tasks.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "projects": {
                            "type": "array",
                            "items": {"type": "object"},
                        },
                        "tasks": {
                            "type": "array",
                            "items": {"type": "object"},
                        },
                        "filename": {"type": "string"},
                    },
                    "required": ["projects", "tasks", "filename"],
                },
            },
        ]

    def generate_weekly_report(
        self,
        projects_summary: dict,
        highlights: list[str],
        filename: str,
        week_number: int | None = None,
        year: int | None = None,
        risks: list[str] | None = None,
        next_week_priorities: list[str] | None = None,
    ) -> dict:
        now = datetime.now()
        week_number = week_number or int(now.strftime("%W"))
        year = year or now.year
        risks = risks or []
        next_week_priorities = next_week_priorities or []

        highlights_html = "".join(f"<li>{h}</li>" for h in highlights)
        risks_html = "".join(f"<li>{r}</li>" for r in risks) if risks else "<li>No major risks this week</li>"
        priorities_html = "".join(f"<li>{p}</li>" for p in next_week_priorities) if next_week_priorities else "<li>To be determined</li>"

        # Project status table
        proj_rows = ""
        for proj_id, data in projects_summary.items() if isinstance(projects_summary, dict) else []:
            if isinstance(data, dict):
                status = data.get("status", "active")
                progress = data.get("progress", 0)
                status_color = {"active": "#28a745", "at_risk": "#dc3545", "on_hold": "#ffc107", "completed": "#17a2b8"}.get(status, "#6c757d")
                proj_rows += f"""<tr>
                    <td>{proj_id}</td>
                    <td><span style="color: {status_color}; font-weight: 600;">{status.upper()}</span></td>
                    <td>
                        <div style="background: #e9ecef; border-radius: 10px; overflow: hidden;">
                            <div style="background: {status_color}; width: {progress}%; height: 20px; border-radius: 10px; text-align: center; color: white; font-size: 12px; line-height: 20px;">{progress}%</div>
                        </div>
                    </td>
                    <td>{data.get('notes', '')}</td>
                </tr>"""

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Weekly Report - Week {week_number}, {year}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', sans-serif; background: #f5f5f5; color: #333; }}
        .header {{ background: linear-gradient(135deg, #1a365d, #2d5aa0); color: white; padding: 30px 40px; }}
        .header h1 {{ font-size: 26px; }}
        .header p {{ opacity: 0.8; margin-top: 5px; }}
        .container {{ max-width: 1000px; margin: 30px auto; padding: 0 20px; }}
        .section {{ background: white; border-radius: 8px; padding: 25px; margin-bottom: 20px; box-shadow: 0 2px 6px rgba(0,0,0,0.08); }}
        .section h2 {{ color: #1a365d; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; margin-bottom: 15px; }}
        ul {{ padding-left: 20px; }}
        li {{ margin-bottom: 8px; line-height: 1.5; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #e2e8f0; }}
        th {{ background: #f7fafc; font-weight: 600; color: #1a365d; }}
        .footer {{ text-align: center; padding: 20px; color: #999; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Weekly Project Report</h1>
        <p>Week {week_number}, {year} | Generated: {now.strftime('%B %d, %Y')}</p>
    </div>
    <div class="container">
        <div class="section">
            <h2>Key Highlights</h2>
            <ul>{highlights_html}</ul>
        </div>
        <div class="section">
            <h2>Project Status</h2>
            <table>
                <tr><th>Project</th><th>Status</th><th>Progress</th><th>Notes</th></tr>
                {proj_rows}
            </table>
        </div>
        <div class="section">
            <h2>Risks & Blockers</h2>
            <ul>{risks_html}</ul>
        </div>
        <div class="section">
            <h2>Next Week Priorities</h2>
            <ul>{priorities_html}</ul>
        </div>
    </div>
    <div class="footer">Auto-generated by Projects Manager Agent</div>
</body>
</html>"""

        filepath = self.output_dir / f"{filename}.html"
        filepath.write_text(html)
        return {"status": "created", "filepath": str(filepath)}

    def generate_monthly_report(
        self,
        executive_summary: str,
        projects_detail: list[dict],
        filename: str,
        month: int | None = None,
        year: int | None = None,
        team_metrics: dict | None = None,
    ) -> dict:
        now = datetime.now()
        month = month or now.month
        year = year or now.year
        month_name = datetime(year, month, 1).strftime("%B %Y")

        projects_html = ""
        for proj in projects_detail:
            status = proj.get("status", "active")
            progress = proj.get("progress", 0)
            milestones = "".join(f"<li>{m}</li>" for m in proj.get("milestones_completed", []))
            issues = "".join(f"<li>{i}</li>" for i in proj.get("issues", []))
            goals = "".join(f"<li>{g}</li>" for g in proj.get("next_month_goals", []))
            status_color = {"active": "#28a745", "at_risk": "#dc3545", "on_hold": "#ffc107", "completed": "#17a2b8"}.get(status, "#6c757d")

            projects_html += f"""
            <div class="project-card">
                <div class="project-header">
                    <h3>{proj.get('name', 'Unnamed')}</h3>
                    <span class="badge" style="background: {status_color};">{status.upper()}</span>
                    <span class="progress-text">{progress}%</span>
                </div>
                <div class="progress-bar"><div class="progress-fill" style="width: {progress}%; background: {status_color};"></div></div>
                <div class="project-details">
                    <div><strong>Milestones Completed:</strong><ul>{milestones or '<li>None</li>'}</ul></div>
                    <div><strong>Issues:</strong><ul>{issues or '<li>None</li>'}</ul></div>
                    <div><strong>Next Month Goals:</strong><ul>{goals or '<li>TBD</li>'}</ul></div>
                </div>
            </div>"""

        metrics_html = ""
        if team_metrics:
            for k, v in team_metrics.items():
                metrics_html += f'<div class="metric-card"><div class="metric-label">{k}</div><div class="metric-value">{v}</div></div>'

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Monthly Report - {month_name}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', sans-serif; background: #f5f5f5; color: #333; }}
        .header {{ background: linear-gradient(135deg, #1a365d, #2d5aa0); color: white; padding: 40px; }}
        .header h1 {{ font-size: 30px; }}
        .container {{ max-width: 1100px; margin: 30px auto; padding: 0 20px; }}
        .section {{ background: white; border-radius: 8px; padding: 25px; margin-bottom: 20px; box-shadow: 0 2px 6px rgba(0,0,0,0.08); }}
        .section h2 {{ color: #1a365d; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; margin-bottom: 15px; }}
        .project-card {{ border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; margin-bottom: 15px; }}
        .project-header {{ display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }}
        .project-header h3 {{ flex: 1; color: #1a365d; }}
        .badge {{ color: white; padding: 2px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; }}
        .progress-text {{ font-weight: 600; color: #1a365d; }}
        .progress-bar {{ background: #e9ecef; border-radius: 10px; height: 8px; margin-bottom: 15px; }}
        .progress-fill {{ height: 100%; border-radius: 10px; }}
        .project-details ul {{ padding-left: 20px; margin: 5px 0 10px; }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; }}
        .metric-card {{ background: #f7fafc; padding: 15px; border-radius: 8px; text-align: center; }}
        .metric-label {{ font-size: 12px; color: #718096; text-transform: uppercase; }}
        .metric-value {{ font-size: 24px; font-weight: 600; color: #1a365d; margin-top: 5px; }}
        .footer {{ text-align: center; padding: 20px; color: #999; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Monthly Project Report</h1>
        <p>{month_name}</p>
    </div>
    <div class="container">
        <div class="section">
            <h2>Executive Summary</h2>
            <p style="line-height: 1.8;">{executive_summary}</p>
        </div>
        {f'<div class="section"><h2>Team Metrics</h2><div class="metrics-grid">{metrics_html}</div></div>' if metrics_html else ''}
        <div class="section">
            <h2>Project Details</h2>
            {projects_html}
        </div>
    </div>
    <div class="footer">Auto-generated by Projects Manager Agent | {now.strftime('%B %d, %Y')}</div>
</body>
</html>"""

        filepath = self.output_dir / f"{filename}.html"
        filepath.write_text(html)
        return {"status": "created", "filepath": str(filepath)}

    def generate_project_status_board(
        self, projects: list[dict], tasks: list[dict], filename: str
    ) -> dict:
        """Generate a Kanban-style project status board."""
        columns = {"todo": [], "in_progress": [], "review": [], "done": [], "blocked": []}
        for t in tasks:
            col = t.get("status", "todo")
            if col in columns:
                columns[col].append(t)

        col_labels = {
            "todo": ("To Do", "#6c757d"),
            "in_progress": ("In Progress", "#0066b2"),
            "review": ("In Review", "#ffc107"),
            "done": ("Done", "#28a745"),
            "blocked": ("Blocked", "#dc3545"),
        }

        board_html = ""
        for col_key, (label, color) in col_labels.items():
            cards = ""
            for t in columns[col_key]:
                priority_color = {"high": "#dc3545", "medium": "#ffc107", "low": "#28a745"}.get(t.get("priority", "medium"), "#6c757d")
                cards += f"""
                <div class="task-card">
                    <div class="task-title">{t.get('title', '')}</div>
                    <div class="task-meta">
                        <span class="priority-dot" style="background: {priority_color};"></span>
                        <span>{t.get('assignee', 'Unassigned')}</span>
                        <span>Due: {t.get('due_date', 'N/A')}</span>
                    </div>
                </div>"""

            board_html += f"""
            <div class="board-column">
                <div class="column-header" style="border-top: 3px solid {color};">
                    <h3>{label}</h3>
                    <span class="count">{len(columns[col_key])}</span>
                </div>
                <div class="column-body">{cards}</div>
            </div>"""

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Project Status Board</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', sans-serif; background: #f0f2f5; }}
        .header {{ background: linear-gradient(135deg, #1a365d, #2d5aa0); color: white; padding: 25px 40px; }}
        .board {{ display: flex; gap: 15px; padding: 20px; overflow-x: auto; min-height: calc(100vh - 100px); }}
        .board-column {{ flex: 1; min-width: 250px; background: #f7fafc; border-radius: 8px; }}
        .column-header {{ padding: 15px; display: flex; justify-content: space-between; align-items: center; }}
        .column-header h3 {{ font-size: 14px; text-transform: uppercase; color: #1a365d; }}
        .count {{ background: #e2e8f0; padding: 2px 8px; border-radius: 10px; font-size: 12px; }}
        .column-body {{ padding: 0 10px 10px; }}
        .task-card {{ background: white; border-radius: 6px; padding: 12px; margin-bottom: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        .task-title {{ font-weight: 600; font-size: 13px; margin-bottom: 8px; color: #2d3748; }}
        .task-meta {{ display: flex; gap: 8px; align-items: center; font-size: 11px; color: #718096; }}
        .priority-dot {{ width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }}
    </style>
</head>
<body>
    <div class="header"><h1>Project Status Board</h1><p>Updated: {datetime.now().strftime('%B %d, %Y %H:%M')}</p></div>
    <div class="board">{board_html}</div>
</body>
</html>"""

        filepath = self.output_dir / f"{filename}.html"
        filepath.write_text(html)
        return {"status": "created", "filepath": str(filepath)}

    def handle_tool_call(self, tool_name: str, tool_input: dict) -> Any:
        dispatch = {
            "generate_weekly_report": lambda: self.generate_weekly_report(**tool_input),
            "generate_monthly_report": lambda: self.generate_monthly_report(**tool_input),
            "generate_project_status_board": lambda: self.generate_project_status_board(**tool_input),
        }
        handler = dispatch.get(tool_name)
        if handler:
            return handler()
        return {"error": f"Unknown reporting tool: {tool_name}"}
