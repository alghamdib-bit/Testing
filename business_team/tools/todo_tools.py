"""
To-do list tools for the Secretary Agent.

Manages personal and team to-do items with priorities and deadlines.
"""

import json
from datetime import datetime
from typing import Any

from business_team import config


class TodoTools:
    """Tools for managing to-do lists."""

    def __init__(self):
        self.todo_file = config.DATA_DIR / "todos.json"
        if not self.todo_file.exists():
            self.todo_file.write_text(json.dumps(self._get_demo_todos(), indent=2))

    @staticmethod
    def get_tool_definitions() -> list[dict]:
        return [
            {
                "name": "get_todos",
                "description": "Retrieve to-do items, optionally filtered by status, priority, or assignee.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["pending", "in_progress", "completed", "overdue"],
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["high", "medium", "low"],
                        },
                        "assignee": {
                            "type": "string",
                            "description": "Filter by assigned person",
                        },
                    },
                    "required": [],
                },
            },
            {
                "name": "add_todo",
                "description": "Add a new to-do item.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Task title"},
                        "description": {
                            "type": "string",
                            "description": "Task description",
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["high", "medium", "low"],
                        },
                        "due_date": {
                            "type": "string",
                            "description": "Due date (YYYY-MM-DD)",
                        },
                        "assignee": {
                            "type": "string",
                            "description": "Person responsible",
                        },
                        "category": {
                            "type": "string",
                            "description": "Category (e.g., email_followup, meeting_prep, project, admin)",
                        },
                    },
                    "required": ["title", "priority"],
                },
            },
            {
                "name": "update_todo",
                "description": "Update an existing to-do item's status or details.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "todo_id": {
                            "type": "string",
                            "description": "The to-do item ID",
                        },
                        "status": {
                            "type": "string",
                            "enum": ["pending", "in_progress", "completed"],
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["high", "medium", "low"],
                        },
                        "notes": {
                            "type": "string",
                            "description": "Additional notes",
                        },
                    },
                    "required": ["todo_id"],
                },
            },
            {
                "name": "get_todo_summary",
                "description": "Get a summary of all to-dos grouped by status and priority.",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        ]

    def get_todos(
        self,
        status: str | None = None,
        priority: str | None = None,
        assignee: str | None = None,
    ) -> list[dict]:
        """Get to-do items with optional filters."""
        todos = json.loads(self.todo_file.read_text())
        if status:
            todos = [t for t in todos if t.get("status") == status]
        if priority:
            todos = [t for t in todos if t.get("priority") == priority]
        if assignee:
            todos = [
                t
                for t in todos
                if assignee.lower() in t.get("assignee", "").lower()
            ]
        return todos

    def add_todo(
        self,
        title: str,
        priority: str,
        description: str = "",
        due_date: str = "",
        assignee: str = "",
        category: str = "general",
    ) -> dict:
        """Add a new to-do item."""
        todos = json.loads(self.todo_file.read_text())
        todo = {
            "id": f"todo_{len(todos) + 1:04d}",
            "title": title,
            "description": description,
            "priority": priority,
            "status": "pending",
            "due_date": due_date,
            "assignee": assignee,
            "category": category,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        todos.append(todo)
        self.todo_file.write_text(json.dumps(todos, indent=2))
        return {"status": "created", "todo": todo}

    def update_todo(
        self,
        todo_id: str,
        status: str | None = None,
        priority: str | None = None,
        notes: str | None = None,
    ) -> dict:
        """Update a to-do item."""
        todos = json.loads(self.todo_file.read_text())
        for todo in todos:
            if todo["id"] == todo_id:
                if status:
                    todo["status"] = status
                if priority:
                    todo["priority"] = priority
                if notes:
                    todo.setdefault("notes", [])
                    todo["notes"].append(
                        {"text": notes, "timestamp": datetime.now().isoformat()}
                    )
                todo["updated_at"] = datetime.now().isoformat()
                self.todo_file.write_text(json.dumps(todos, indent=2))
                return {"status": "updated", "todo": todo}
        return {"status": "not_found", "todo_id": todo_id}

    def get_todo_summary(self) -> dict:
        """Get a summary of all to-dos."""
        todos = json.loads(self.todo_file.read_text())
        summary = {
            "total": len(todos),
            "by_status": {},
            "by_priority": {},
            "overdue": [],
        }
        today = datetime.now().strftime("%Y-%m-%d")
        for t in todos:
            s = t.get("status", "pending")
            p = t.get("priority", "medium")
            summary["by_status"][s] = summary["by_status"].get(s, 0) + 1
            summary["by_priority"][p] = summary["by_priority"].get(p, 0) + 1
            if t.get("due_date") and t["due_date"] < today and s != "completed":
                summary["overdue"].append(t)
        return summary

    def handle_tool_call(self, tool_name: str, tool_input: dict) -> Any:
        dispatch = {
            "get_todos": lambda: self.get_todos(**tool_input),
            "add_todo": lambda: self.add_todo(**tool_input),
            "update_todo": lambda: self.update_todo(**tool_input),
            "get_todo_summary": lambda: self.get_todo_summary(**tool_input),
        }
        handler = dispatch.get(tool_name)
        if handler:
            return handler()
        return {"error": f"Unknown todo tool: {tool_name}"}

    @staticmethod
    def _get_demo_todos() -> list[dict]:
        today = datetime.now().strftime("%Y-%m-%d")
        return [
            {
                "id": "todo_0001",
                "title": "Review Q4 budget proposal",
                "description": "Review and comment on CFO's Q4 budget proposal",
                "priority": "high",
                "status": "pending",
                "due_date": today,
                "assignee": "Manager",
                "category": "email_followup",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            },
            {
                "id": "todo_0002",
                "title": "Prepare board meeting presentation",
                "description": "Department update slides for Tuesday board meeting",
                "priority": "high",
                "status": "in_progress",
                "due_date": today,
                "assignee": "Business Analyst",
                "category": "meeting_prep",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            },
            {
                "id": "todo_0003",
                "title": "Update project dashboard",
                "description": "Refresh all project status indicators",
                "priority": "medium",
                "status": "pending",
                "due_date": today,
                "assignee": "Projects Manager",
                "category": "project",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            },
            {
                "id": "todo_0004",
                "title": "Follow up on TechVentures partnership",
                "description": "Send agenda for Thursday meeting",
                "priority": "medium",
                "status": "pending",
                "due_date": today,
                "assignee": "Secretary",
                "category": "email_followup",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            },
        ]
