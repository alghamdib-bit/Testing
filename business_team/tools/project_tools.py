"""
Project management tools for the Projects Manager Agent.

Handles project CRUD, task management, milestone tracking,
and team member assignment.
"""

import json
from datetime import datetime
from typing import Any

from business_team import config


class ProjectTools:
    """Tools for managing projects and tasks."""

    def __init__(self, db=None):
        self.db = db
        self.projects_file = config.DATA_DIR / "projects.json"
        self.tasks_file = config.DATA_DIR / "tasks.json"
        if not self.db:
            if not self.projects_file.exists():
                self.projects_file.write_text(
                    json.dumps(self._get_demo_projects(), indent=2)
                )
            if not self.tasks_file.exists():
                self.tasks_file.write_text(
                    json.dumps(self._get_demo_tasks(), indent=2)
                )

    @staticmethod
    def get_tool_definitions() -> list[dict]:
        return [
            {
                "name": "get_projects",
                "description": "Get all projects or filter by status.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": [
                                "active",
                                "on_hold",
                                "completed",
                                "at_risk",
                            ],
                        },
                    },
                    "required": [],
                },
            },
            {
                "name": "get_project_detail",
                "description": "Get detailed information about a specific project including tasks and milestones.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string"},
                    },
                    "required": ["project_id"],
                },
            },
            {
                "name": "create_project",
                "description": "Create a new project with milestones.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "owner": {"type": "string"},
                        "start_date": {"type": "string"},
                        "target_end_date": {"type": "string"},
                        "milestones": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "due_date": {"type": "string"},
                                },
                            },
                        },
                    },
                    "required": ["name", "owner", "start_date", "target_end_date"],
                },
            },
            {
                "name": "update_project",
                "description": "Update a project's status, progress, or details.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string"},
                        "status": {
                            "type": "string",
                            "enum": ["active", "on_hold", "completed", "at_risk"],
                        },
                        "progress_percent": {
                            "type": "integer",
                            "description": "Overall progress 0-100",
                        },
                        "notes": {"type": "string"},
                    },
                    "required": ["project_id"],
                },
            },
            {
                "name": "get_tasks",
                "description": "Get tasks, optionally filtered by project, assignee, or status.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string"},
                        "assignee": {"type": "string"},
                        "status": {
                            "type": "string",
                            "enum": [
                                "todo",
                                "in_progress",
                                "review",
                                "done",
                                "blocked",
                            ],
                        },
                    },
                    "required": [],
                },
            },
            {
                "name": "create_task",
                "description": "Create a new task within a project.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string"},
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "assignee": {"type": "string"},
                        "priority": {
                            "type": "string",
                            "enum": ["high", "medium", "low"],
                        },
                        "due_date": {"type": "string"},
                    },
                    "required": ["project_id", "title", "assignee"],
                },
            },
            {
                "name": "update_task",
                "description": "Update a task's status or details.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string"},
                        "status": {
                            "type": "string",
                            "enum": [
                                "todo",
                                "in_progress",
                                "review",
                                "done",
                                "blocked",
                            ],
                        },
                        "progress_percent": {"type": "integer"},
                        "notes": {"type": "string"},
                    },
                    "required": ["task_id"],
                },
            },
            {
                "name": "get_project_summary",
                "description": "Get a high-level summary of all projects for reporting.",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        ]

    def get_projects(self, status: str | None = None) -> list[dict]:
        if self.db:
            return self.db.get_projects(status=status)
        projects = json.loads(self.projects_file.read_text())
        if status:
            projects = [p for p in projects if p.get("status") == status]
        return projects

    def get_project_detail(self, project_id: str) -> dict:
        if self.db:
            project = self.db.get_project(project_id)
            if not project:
                return {"error": f"Project {project_id} not found"}
            project["tasks"] = self.db.get_tasks(project_id=project_id)
            return project
        projects = json.loads(self.projects_file.read_text())
        tasks = json.loads(self.tasks_file.read_text())
        project = next((p for p in projects if p["id"] == project_id), None)
        if not project:
            return {"error": f"Project {project_id} not found"}
        project_tasks = [t for t in tasks if t.get("project_id") == project_id]
        project["tasks"] = project_tasks
        return project

    def create_project(
        self,
        name: str,
        owner: str,
        start_date: str,
        target_end_date: str,
        description: str = "",
        milestones: list[dict] | None = None,
    ) -> dict:
        if self.db:
            project = self.db.create_project(
                name=name, owner=owner, start_date=start_date,
                target_end_date=target_end_date, description=description,
                milestones=milestones or [],
            )
            return {"status": "created", "project": project}
        projects = json.loads(self.projects_file.read_text())
        project = {
            "id": f"proj_{len(projects) + 1:03d}",
            "name": name,
            "description": description,
            "owner": owner,
            "status": "active",
            "progress_percent": 0,
            "start_date": start_date,
            "target_end_date": target_end_date,
            "milestones": milestones or [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "notes_history": [],
        }
        projects.append(project)
        self.projects_file.write_text(json.dumps(projects, indent=2))
        return {"status": "created", "project": project}

    def update_project(
        self,
        project_id: str,
        status: str | None = None,
        progress_percent: int | None = None,
        notes: str | None = None,
    ) -> dict:
        if self.db:
            result = self.db.update_project(
                project_id, status=status,
                progress_percent=progress_percent, notes=notes,
            )
            if "error" in result:
                return result
            return {"status": "updated", "project": result}
        projects = json.loads(self.projects_file.read_text())
        for proj in projects:
            if proj["id"] == project_id:
                if status:
                    proj["status"] = status
                if progress_percent is not None:
                    proj["progress_percent"] = progress_percent
                if notes:
                    proj.setdefault("notes_history", []).append(
                        {"text": notes, "timestamp": datetime.now().isoformat()}
                    )
                proj["updated_at"] = datetime.now().isoformat()
                self.projects_file.write_text(json.dumps(projects, indent=2))
                return {"status": "updated", "project": proj}
        return {"error": f"Project {project_id} not found"}

    def get_tasks(
        self,
        project_id: str | None = None,
        assignee: str | None = None,
        status: str | None = None,
    ) -> list[dict]:
        if self.db:
            return self.db.get_tasks(project_id=project_id, status=status, assignee=assignee)
        tasks = json.loads(self.tasks_file.read_text())
        if project_id:
            tasks = [t for t in tasks if t.get("project_id") == project_id]
        if assignee:
            tasks = [
                t for t in tasks if assignee.lower() in t.get("assignee", "").lower()
            ]
        if status:
            tasks = [t for t in tasks if t.get("status") == status]
        return tasks

    def create_task(
        self,
        project_id: str,
        title: str,
        assignee: str,
        description: str = "",
        priority: str = "medium",
        due_date: str = "",
    ) -> dict:
        if self.db:
            task = self.db.create_task(
                project_id=project_id, title=title, assignee=assignee,
                description=description, priority=priority, due_date=due_date,
            )
            return {"status": "created", "task": task}
        tasks = json.loads(self.tasks_file.read_text())
        task = {
            "id": f"task_{len(tasks) + 1:04d}",
            "project_id": project_id,
            "title": title,
            "description": description,
            "assignee": assignee,
            "priority": priority,
            "status": "todo",
            "progress_percent": 0,
            "due_date": due_date,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        tasks.append(task)
        self.tasks_file.write_text(json.dumps(tasks, indent=2))
        return {"status": "created", "task": task}

    def update_task(
        self,
        task_id: str,
        status: str | None = None,
        progress_percent: int | None = None,
        notes: str | None = None,
    ) -> dict:
        if self.db:
            result = self.db.update_task(
                task_id, status=status,
                progress_percent=progress_percent, notes=notes,
            )
            if "error" in result:
                return result
            return {"status": "updated", "task": result}
        tasks = json.loads(self.tasks_file.read_text())
        for task in tasks:
            if task["id"] == task_id:
                if status:
                    task["status"] = status
                if progress_percent is not None:
                    task["progress_percent"] = progress_percent
                if notes:
                    task.setdefault("notes_history", []).append(
                        {"text": notes, "timestamp": datetime.now().isoformat()}
                    )
                task["updated_at"] = datetime.now().isoformat()
                self.tasks_file.write_text(json.dumps(tasks, indent=2))
                return {"status": "updated", "task": task}
        return {"error": f"Task {task_id} not found"}

    def get_project_summary(self) -> dict:
        if self.db:
            projects = self.db.get_projects()
            tasks = self.db.get_tasks()
        else:
            projects = json.loads(self.projects_file.read_text())
            tasks = json.loads(self.tasks_file.read_text())
        summary = {
            "total_projects": len(projects),
            "by_status": {},
            "at_risk_projects": [],
            "total_tasks": len(tasks),
            "tasks_by_status": {},
            "overdue_tasks": [],
        }
        today = datetime.now().strftime("%Y-%m-%d")
        for p in projects:
            s = p.get("status", "active")
            summary["by_status"][s] = summary["by_status"].get(s, 0) + 1
            if s == "at_risk":
                summary["at_risk_projects"].append(
                    {"id": p["id"], "name": p["name"], "progress": p.get("progress_percent", 0)}
                )
        for t in tasks:
            s = t.get("status", "todo")
            summary["tasks_by_status"][s] = summary["tasks_by_status"].get(s, 0) + 1
            if t.get("due_date") and t["due_date"] < today and s != "done":
                summary["overdue_tasks"].append(t)
        return summary

    def handle_tool_call(self, tool_name: str, tool_input: dict) -> Any:
        dispatch = {
            "get_projects": lambda: self.get_projects(**tool_input),
            "get_project_detail": lambda: self.get_project_detail(**tool_input),
            "create_project": lambda: self.create_project(**tool_input),
            "update_project": lambda: self.update_project(**tool_input),
            "get_tasks": lambda: self.get_tasks(**tool_input),
            "create_task": lambda: self.create_task(**tool_input),
            "update_task": lambda: self.update_task(**tool_input),
            "get_project_summary": lambda: self.get_project_summary(**tool_input),
        }
        handler = dispatch.get(tool_name)
        if handler:
            return handler()
        return {"error": f"Unknown project tool: {tool_name}"}

    @staticmethod
    def _get_demo_projects() -> list[dict]:
        return [
            {
                "id": "proj_001",
                "name": "Project Alpha - Digital Platform Upgrade",
                "description": "Complete overhaul of the SPL digital platform including new API gateway and modernized frontend.",
                "owner": "Ahmad",
                "status": "at_risk",
                "progress_percent": 55,
                "start_date": "2025-10-01",
                "target_end_date": "2026-03-31",
                "milestones": [
                    {"name": "Requirements Complete", "due_date": "2025-11-15", "status": "completed"},
                    {"name": "Design Approved", "due_date": "2025-12-20", "status": "completed"},
                    {"name": "Core Development", "due_date": "2026-02-15", "status": "in_progress"},
                    {"name": "Testing & QA", "due_date": "2026-03-15", "status": "pending"},
                    {"name": "Go Live", "due_date": "2026-03-31", "status": "pending"},
                ],
                "created_at": "2025-10-01T00:00:00",
                "updated_at": datetime.now().isoformat(),
            },
            {
                "id": "proj_002",
                "name": "Project Beta - Mobile App v3",
                "description": "Next generation mobile app with AI-powered features and redesigned UX.",
                "owner": "Fatima",
                "status": "active",
                "progress_percent": 35,
                "start_date": "2025-12-01",
                "target_end_date": "2026-06-30",
                "milestones": [
                    {"name": "UX Research", "due_date": "2026-01-15", "status": "completed"},
                    {"name": "Prototype Ready", "due_date": "2026-02-28", "status": "in_progress"},
                    {"name": "Development Sprint 1", "due_date": "2026-04-15", "status": "pending"},
                    {"name": "Beta Launch", "due_date": "2026-06-01", "status": "pending"},
                    {"name": "Production Release", "due_date": "2026-06-30", "status": "pending"},
                ],
                "created_at": "2025-12-01T00:00:00",
                "updated_at": datetime.now().isoformat(),
            },
            {
                "id": "proj_003",
                "name": "Project Gamma - Data Analytics Platform",
                "description": "Enterprise data analytics and BI platform for all business units.",
                "owner": "Khalid",
                "status": "active",
                "progress_percent": 70,
                "start_date": "2025-08-15",
                "target_end_date": "2026-02-28",
                "milestones": [
                    {"name": "Data Pipeline Setup", "due_date": "2025-10-30", "status": "completed"},
                    {"name": "Dashboard Development", "due_date": "2025-12-30", "status": "completed"},
                    {"name": "User Training", "due_date": "2026-02-15", "status": "in_progress"},
                    {"name": "Full Rollout", "due_date": "2026-02-28", "status": "pending"},
                ],
                "created_at": "2025-08-15T00:00:00",
                "updated_at": datetime.now().isoformat(),
            },
        ]

    @staticmethod
    def _get_demo_tasks() -> list[dict]:
        return [
            {"id": "task_0001", "project_id": "proj_001", "title": "Fix API gateway timeout issues", "assignee": "Dev Team Lead", "priority": "high", "status": "in_progress", "progress_percent": 60, "due_date": "2026-02-10", "created_at": datetime.now().isoformat(), "updated_at": datetime.now().isoformat()},
            {"id": "task_0002", "project_id": "proj_001", "title": "Update vendor integration modules", "assignee": "Backend Dev", "priority": "high", "status": "blocked", "progress_percent": 30, "due_date": "2026-02-12", "created_at": datetime.now().isoformat(), "updated_at": datetime.now().isoformat()},
            {"id": "task_0003", "project_id": "proj_001", "title": "Frontend migration to React 19", "assignee": "Frontend Lead", "priority": "medium", "status": "in_progress", "progress_percent": 45, "due_date": "2026-02-20", "created_at": datetime.now().isoformat(), "updated_at": datetime.now().isoformat()},
            {"id": "task_0004", "project_id": "proj_002", "title": "Complete UX wireframes for chat feature", "assignee": "UX Designer", "priority": "high", "status": "review", "progress_percent": 90, "due_date": "2026-02-08", "created_at": datetime.now().isoformat(), "updated_at": datetime.now().isoformat()},
            {"id": "task_0005", "project_id": "proj_002", "title": "Set up CI/CD pipeline for mobile builds", "assignee": "DevOps", "priority": "medium", "status": "done", "progress_percent": 100, "due_date": "2026-02-01", "created_at": datetime.now().isoformat(), "updated_at": datetime.now().isoformat()},
            {"id": "task_0006", "project_id": "proj_003", "title": "Create executive BI dashboard", "assignee": "Data Analyst", "priority": "high", "status": "in_progress", "progress_percent": 75, "due_date": "2026-02-10", "created_at": datetime.now().isoformat(), "updated_at": datetime.now().isoformat()},
            {"id": "task_0007", "project_id": "proj_003", "title": "Conduct user training sessions", "assignee": "Training Lead", "priority": "medium", "status": "todo", "progress_percent": 0, "due_date": "2026-02-15", "created_at": datetime.now().isoformat(), "updated_at": datetime.now().isoformat()},
        ]
