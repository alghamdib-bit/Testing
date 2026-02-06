"""
SQLite database layer for the Business Team Multi-Agent System.

Provides a ``Database`` class that can replace the JSON flat-file storage
used by the various agent tools, together with a migration helper that
reads existing JSON data files and inserts them into the database.

Only uses ``sqlite3`` from the standard library -- no extra packages.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from business_team import config

# Path to the SQL migration file shipped with the package.
_MIGRATION_FILE = Path(__file__).parent / "migrations" / "001_initial_schema.sql"


class Database:
    """SQLite database for the Business Team system."""

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def __init__(self, db_path: str | Path | None = None):
        """Initialise with *db_path*.  Defaults to ``config.DATA_DIR / 'business_team.db'``."""
        if db_path is None:
            db_path = config.DATA_DIR / "business_team.db"
        self.db_path = Path(db_path)
        self._conn: sqlite3.Connection | None = None

    # ---- connection helpers ------------------------------------------

    @property
    def conn(self) -> sqlite3.Connection:
        """Lazy-open a connection (thread-safe, WAL mode, row-factory)."""
        if self._conn is None:
            self._conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
            )
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def initialize(self) -> None:
        """Create all tables by running the migration SQL (idempotent)."""
        sql = _MIGRATION_FILE.read_text()
        self.conn.executescript(sql)

    def close(self) -> None:
        """Close the underlying database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # ---- context-manager ---------------------------------------------

    def __enter__(self) -> "Database":
        self.initialize()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _row_to_dict(self, row: sqlite3.Row) -> dict:
        """Convert a ``sqlite3.Row`` to a plain dict, deserialising JSON columns."""
        d = dict(row)
        # Transparently decode known JSON-text columns.
        for key in (
            "milestones",
            "notes_history",
            "action_items",
            "attendees",
        ):
            if key in d and isinstance(d[key], str):
                try:
                    d[key] = json.loads(d[key])
                except (json.JSONDecodeError, TypeError):
                    pass
        # SQLite stores booleans as 0/1 -- convert ``action_required``.
        if "action_required" in d:
            d["action_required"] = bool(d["action_required"])
        return d

    def _next_id(self, prefix: str, table: str, id_col: str = "id") -> str:
        """Generate the next sequential ID for *table* (e.g. ``proj_009``)."""
        cur = self.conn.execute(f"SELECT {id_col} FROM {table} ORDER BY {id_col} DESC LIMIT 1")
        row = cur.fetchone()
        if row is None:
            seq = 1
        else:
            last_id: str = row[0]
            # Extract numeric suffix after the last underscore.
            try:
                seq = int(last_id.rsplit("_", 1)[1]) + 1
            except (IndexError, ValueError):
                seq = 1
        # Determine zero-padding width from the prefix convention.
        width = 4 if prefix != "proj" else 3
        return f"{prefix}_{seq:0{width}d}"

    @staticmethod
    def _now_iso() -> str:
        return datetime.now().isoformat()

    # ------------------------------------------------------------------
    # Projects CRUD
    # ------------------------------------------------------------------

    def get_projects(self, status: str | None = None) -> list[dict]:
        """Return all projects, optionally filtered by *status*."""
        if status:
            cur = self.conn.execute(
                "SELECT * FROM projects WHERE status = ? ORDER BY id", (status,)
            )
        else:
            cur = self.conn.execute("SELECT * FROM projects ORDER BY id")
        return [self._row_to_dict(r) for r in cur.fetchall()]

    def get_project(self, project_id: str) -> dict | None:
        """Return a single project by ID, or ``None``."""
        cur = self.conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = cur.fetchone()
        return self._row_to_dict(row) if row else None

    def create_project(self, name: str, owner: str, **kwargs: Any) -> dict:
        """Insert a new project and return it as a dict."""
        now = self._now_iso()
        proj_id = kwargs.pop("id", None) or self._next_id("proj", "projects")
        project = {
            "id": proj_id,
            "name": name,
            "description": kwargs.get("description", ""),
            "owner": owner,
            "status": kwargs.get("status", "active"),
            "progress_percent": kwargs.get("progress_percent", 0),
            "start_date": kwargs.get("start_date", datetime.now().strftime("%Y-%m-%d")),
            "target_end_date": kwargs.get("target_end_date", ""),
            "milestones": json.dumps(kwargs.get("milestones", [])),
            "notes_history": json.dumps(kwargs.get("notes_history", [])),
            "created_at": kwargs.get("created_at", now),
            "updated_at": kwargs.get("updated_at", now),
        }
        self.conn.execute(
            """INSERT INTO projects
               (id, name, description, owner, status, progress_percent,
                start_date, target_end_date, milestones, notes_history,
                created_at, updated_at)
               VALUES (:id, :name, :description, :owner, :status, :progress_percent,
                       :start_date, :target_end_date, :milestones, :notes_history,
                       :created_at, :updated_at)""",
            project,
        )
        self.conn.commit()
        return self.get_project(proj_id)  # type: ignore[return-value]

    def update_project(self, project_id: str, **kwargs: Any) -> dict:
        """Update fields on an existing project.  Returns the updated dict."""
        existing = self.get_project(project_id)
        if existing is None:
            return {"error": f"Project {project_id} not found"}

        now = self._now_iso()

        if "status" in kwargs and kwargs["status"]:
            existing["status"] = kwargs["status"]
        if "progress_percent" in kwargs and kwargs["progress_percent"] is not None:
            existing["progress_percent"] = kwargs["progress_percent"]
        if "name" in kwargs and kwargs["name"]:
            existing["name"] = kwargs["name"]
        if "description" in kwargs:
            existing["description"] = kwargs["description"]
        if "notes" in kwargs and kwargs["notes"]:
            history = existing.get("notes_history", [])
            if isinstance(history, str):
                history = json.loads(history)
            history.append({"text": kwargs["notes"], "timestamp": now})
            existing["notes_history"] = history

        self.conn.execute(
            """UPDATE projects
               SET name = ?, description = ?, owner = ?, status = ?,
                   progress_percent = ?, start_date = ?, target_end_date = ?,
                   milestones = ?, notes_history = ?, updated_at = ?
               WHERE id = ?""",
            (
                existing["name"],
                existing["description"],
                existing["owner"],
                existing["status"],
                existing["progress_percent"],
                existing["start_date"],
                existing["target_end_date"],
                json.dumps(existing["milestones"]),
                json.dumps(existing["notes_history"]),
                now,
                project_id,
            ),
        )
        self.conn.commit()
        return self.get_project(project_id)  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Tasks CRUD
    # ------------------------------------------------------------------

    def get_tasks(
        self,
        project_id: str | None = None,
        status: str | None = None,
        assignee: str | None = None,
    ) -> list[dict]:
        """Return tasks with optional filters."""
        clauses: list[str] = []
        params: list[Any] = []
        if project_id:
            clauses.append("project_id = ?")
            params.append(project_id)
        if status:
            clauses.append("status = ?")
            params.append(status)
        if assignee:
            clauses.append("LOWER(assignee) LIKE ?")
            params.append(f"%{assignee.lower()}%")
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        cur = self.conn.execute(f"SELECT * FROM tasks{where} ORDER BY id", params)
        return [self._row_to_dict(r) for r in cur.fetchall()]

    def get_task(self, task_id: str) -> dict | None:
        cur = self.conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cur.fetchone()
        return self._row_to_dict(row) if row else None

    def create_task(self, project_id: str, title: str, assignee: str, **kwargs: Any) -> dict:
        now = self._now_iso()
        task_id = kwargs.pop("id", None) or self._next_id("task", "tasks")
        task = {
            "id": task_id,
            "project_id": project_id,
            "title": title,
            "description": kwargs.get("description", ""),
            "assignee": assignee,
            "priority": kwargs.get("priority", "medium"),
            "status": kwargs.get("status", "todo"),
            "progress_percent": kwargs.get("progress_percent", 0),
            "due_date": kwargs.get("due_date", ""),
            "notes_history": json.dumps(kwargs.get("notes_history", [])),
            "created_at": kwargs.get("created_at", now),
            "updated_at": kwargs.get("updated_at", now),
        }
        self.conn.execute(
            """INSERT INTO tasks
               (id, project_id, title, description, assignee, priority,
                status, progress_percent, due_date, notes_history,
                created_at, updated_at)
               VALUES (:id, :project_id, :title, :description, :assignee, :priority,
                       :status, :progress_percent, :due_date, :notes_history,
                       :created_at, :updated_at)""",
            task,
        )
        self.conn.commit()
        return self.get_task(task_id)  # type: ignore[return-value]

    def update_task(self, task_id: str, **kwargs: Any) -> dict:
        existing = self.get_task(task_id)
        if existing is None:
            return {"error": f"Task {task_id} not found"}

        now = self._now_iso()

        if "status" in kwargs and kwargs["status"]:
            existing["status"] = kwargs["status"]
        if "progress_percent" in kwargs and kwargs["progress_percent"] is not None:
            existing["progress_percent"] = kwargs["progress_percent"]
        if "priority" in kwargs and kwargs["priority"]:
            existing["priority"] = kwargs["priority"]
        if "notes" in kwargs and kwargs["notes"]:
            history = existing.get("notes_history", [])
            if isinstance(history, str):
                history = json.loads(history)
            history.append({"text": kwargs["notes"], "timestamp": now})
            existing["notes_history"] = history

        self.conn.execute(
            """UPDATE tasks
               SET status = ?, progress_percent = ?, priority = ?,
                   notes_history = ?, updated_at = ?
               WHERE id = ?""",
            (
                existing["status"],
                existing["progress_percent"],
                existing["priority"],
                json.dumps(existing["notes_history"]),
                now,
                task_id,
            ),
        )
        self.conn.commit()
        return self.get_task(task_id)  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Todos CRUD
    # ------------------------------------------------------------------

    def get_todos(
        self,
        status: str | None = None,
        priority: str | None = None,
        assignee: str | None = None,
    ) -> list[dict]:
        clauses: list[str] = []
        params: list[Any] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        if priority:
            clauses.append("priority = ?")
            params.append(priority)
        if assignee:
            clauses.append("LOWER(assignee) LIKE ?")
            params.append(f"%{assignee.lower()}%")
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        cur = self.conn.execute(f"SELECT * FROM todos{where} ORDER BY id", params)
        return [self._row_to_dict(r) for r in cur.fetchall()]

    def get_todo(self, todo_id: str) -> dict | None:
        cur = self.conn.execute("SELECT * FROM todos WHERE id = ?", (todo_id,))
        row = cur.fetchone()
        return self._row_to_dict(row) if row else None

    def create_todo(self, title: str, priority: str = "medium", **kwargs: Any) -> dict:
        now = self._now_iso()
        todo_id = kwargs.pop("id", None) or self._next_id("todo", "todos")
        todo = {
            "id": todo_id,
            "title": title,
            "description": kwargs.get("description", ""),
            "priority": priority,
            "status": kwargs.get("status", "pending"),
            "due_date": kwargs.get("due_date", ""),
            "assignee": kwargs.get("assignee", ""),
            "category": kwargs.get("category", "general"),
            "notes": kwargs.get("notes", ""),
            "created_at": kwargs.get("created_at", now),
            "updated_at": kwargs.get("updated_at", now),
        }
        self.conn.execute(
            """INSERT INTO todos
               (id, title, description, priority, status, due_date,
                assignee, category, notes, created_at, updated_at)
               VALUES (:id, :title, :description, :priority, :status, :due_date,
                       :assignee, :category, :notes, :created_at, :updated_at)""",
            todo,
        )
        self.conn.commit()
        return self.get_todo(todo_id)  # type: ignore[return-value]

    def update_todo(self, todo_id: str, **kwargs: Any) -> dict:
        existing = self.get_todo(todo_id)
        if existing is None:
            return {"error": f"Todo {todo_id} not found"}

        now = self._now_iso()

        if "status" in kwargs and kwargs["status"]:
            existing["status"] = kwargs["status"]
        if "priority" in kwargs and kwargs["priority"]:
            existing["priority"] = kwargs["priority"]
        if "title" in kwargs and kwargs["title"]:
            existing["title"] = kwargs["title"]
        if "notes" in kwargs and kwargs["notes"]:
            existing["notes"] = kwargs["notes"]

        self.conn.execute(
            """UPDATE todos
               SET title = ?, priority = ?, status = ?, notes = ?, updated_at = ?
               WHERE id = ?""",
            (
                existing["title"],
                existing["priority"],
                existing["status"],
                existing["notes"],
                now,
                todo_id,
            ),
        )
        self.conn.commit()
        return self.get_todo(todo_id)  # type: ignore[return-value]

    def get_todo_summary(self) -> dict:
        """Aggregate counts mirroring ``TodoTools.get_todo_summary``."""
        todos = self.get_todos()
        today = datetime.now().strftime("%Y-%m-%d")
        summary: dict[str, Any] = {
            "total": len(todos),
            "by_status": {},
            "by_priority": {},
            "overdue": [],
        }
        for t in todos:
            s = t.get("status", "pending")
            p = t.get("priority", "medium")
            summary["by_status"][s] = summary["by_status"].get(s, 0) + 1
            summary["by_priority"][p] = summary["by_priority"].get(p, 0) + 1
            if t.get("due_date") and t["due_date"] < today and s != "completed":
                summary["overdue"].append(t)
        return summary

    # ------------------------------------------------------------------
    # Email Log
    # ------------------------------------------------------------------

    def log_email(
        self,
        subject: str,
        sender: str,
        summary: str,
        priority: str,
        **kwargs: Any,
    ) -> dict:
        now = self._now_iso()
        email_id = kwargs.pop("email_id", None) or kwargs.pop("id", None) or self._next_id("email", "email_log", "email_id")
        entry = {
            "email_id": email_id,
            "subject": subject,
            "sender": sender,
            "summary": summary,
            "priority": priority,
            "action_required": 1 if kwargs.get("action_required") else 0,
            "action_items": json.dumps(kwargs.get("action_items", [])),
            "logged_at": kwargs.get("logged_at", now),
        }
        self.conn.execute(
            """INSERT INTO email_log
               (email_id, subject, sender, summary, priority,
                action_required, action_items, logged_at)
               VALUES (:email_id, :subject, :sender, :summary, :priority,
                       :action_required, :action_items, :logged_at)""",
            entry,
        )
        self.conn.commit()
        return self._get_email(email_id)  # type: ignore[return-value]

    def _get_email(self, email_id: str) -> dict | None:
        cur = self.conn.execute("SELECT * FROM email_log WHERE email_id = ?", (email_id,))
        row = cur.fetchone()
        return self._row_to_dict(row) if row else None

    def get_email_log(
        self,
        since_date: str | None = None,
        priority: str | None = None,
    ) -> list[dict]:
        clauses: list[str] = []
        params: list[Any] = []
        if since_date:
            clauses.append("logged_at >= ?")
            params.append(since_date)
        if priority:
            clauses.append("priority = ?")
            params.append(priority)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        cur = self.conn.execute(
            f"SELECT * FROM email_log{where} ORDER BY logged_at", params
        )
        return [self._row_to_dict(r) for r in cur.fetchall()]

    # ------------------------------------------------------------------
    # Calendar Events
    # ------------------------------------------------------------------

    def get_events(self, start_date: str, end_date: str | None = None) -> list[dict]:
        if not end_date:
            end_date = start_date
        cur = self.conn.execute(
            "SELECT * FROM calendar_events WHERE date BETWEEN ? AND ? ORDER BY date, start_time",
            (start_date, end_date),
        )
        return [self._row_to_dict(r) for r in cur.fetchall()]

    def get_event(self, event_id: str) -> dict | None:
        cur = self.conn.execute("SELECT * FROM calendar_events WHERE id = ?", (event_id,))
        row = cur.fetchone()
        return self._row_to_dict(row) if row else None

    def create_event(
        self,
        title: str,
        date: str,
        start_time: str,
        end_time: str,
        **kwargs: Any,
    ) -> dict:
        now = self._now_iso()
        evt_id = kwargs.pop("id", None) or self._next_id("evt", "calendar_events")
        event = {
            "id": evt_id,
            "title": title,
            "date": date,
            "start_time": start_time,
            "end_time": end_time,
            "location": kwargs.get("location", ""),
            "attendees": json.dumps(kwargs.get("attendees", [])),
            "priority": kwargs.get("priority", "medium"),
            "notes": kwargs.get("notes", ""),
            "created_at": kwargs.get("created_at", now),
        }
        self.conn.execute(
            """INSERT INTO calendar_events
               (id, title, date, start_time, end_time, location,
                attendees, priority, notes, created_at)
               VALUES (:id, :title, :date, :start_time, :end_time, :location,
                       :attendees, :priority, :notes, :created_at)""",
            event,
        )
        self.conn.commit()
        return self.get_event(evt_id)  # type: ignore[return-value]

    def update_event(self, event_id: str, **kwargs: Any) -> dict:
        """Update fields on an existing calendar event."""
        existing = self.get_event(event_id)
        if existing is None:
            return {"error": f"Event {event_id} not found"}

        for field in ("title", "date", "start_time", "end_time", "location", "notes"):
            if field in kwargs and kwargs[field] is not None:
                existing[field] = kwargs[field]

        self.conn.execute(
            """UPDATE calendar_events
               SET title = ?, date = ?, start_time = ?, end_time = ?,
                   location = ?, notes = ?
               WHERE id = ?""",
            (
                existing["title"], existing["date"],
                existing["start_time"], existing["end_time"],
                existing["location"], existing["notes"],
                event_id,
            ),
        )
        self.conn.commit()
        return self.get_event(event_id)  # type: ignore[return-value]

    def check_conflicts(self, date: str, start_time: str, end_time: str) -> dict:
        """Check for scheduling conflicts on a given date/time."""
        events = self.get_events(date)
        conflicts = [
            evt for evt in events
            if evt.get("start_time", "") < end_time and evt.get("end_time", "") > start_time
        ]
        return {"has_conflicts": len(conflicts) > 0, "conflicts": conflicts}

    def get_today_schedule(self) -> list[dict]:
        """Get today's full schedule."""
        return self.get_events(datetime.now().strftime("%Y-%m-%d"))

    # ------------------------------------------------------------------
    # Activity Log
    # ------------------------------------------------------------------

    def log_activity(self, agent: str, activity_type: str, details: str) -> dict:
        now = self._now_iso()
        cur = self.conn.execute(
            """INSERT INTO activity_log (agent, activity_type, details, created_at)
               VALUES (?, ?, ?, ?)""",
            (agent, activity_type, details, now),
        )
        self.conn.commit()
        row_id = cur.lastrowid
        row = self.conn.execute(
            "SELECT * FROM activity_log WHERE id = ?", (row_id,)
        ).fetchone()
        return dict(row) if row else {}

    def get_activities(self, agent: str | None = None, limit: int = 50) -> list[dict]:
        if agent:
            cur = self.conn.execute(
                "SELECT * FROM activity_log WHERE agent = ? ORDER BY id DESC LIMIT ?",
                (agent, limit),
            )
        else:
            cur = self.conn.execute(
                "SELECT * FROM activity_log ORDER BY id DESC LIMIT ?", (limit,)
            )
        return [dict(r) for r in cur.fetchall()]

    # ------------------------------------------------------------------
    # Migration from JSON flat files
    # ------------------------------------------------------------------

    def migrate_from_json(self, data_dir: str | Path | None = None) -> dict:
        """Read existing JSON data files and insert rows.  Idempotent --
        existing IDs are skipped so running twice produces no duplicates.

        Returns a summary dict with counts per entity.
        """
        if data_dir is None:
            data_dir = config.DATA_DIR
        data_dir = Path(data_dir)
        counts: dict[str, dict[str, int]] = {}

        # --- projects.json ---
        counts["projects"] = self._migrate_projects(data_dir / "projects.json")

        # --- tasks.json ---
        counts["tasks"] = self._migrate_tasks(data_dir / "tasks.json")

        # --- todos.json ---
        counts["todos"] = self._migrate_todos(data_dir / "todos.json")

        # --- email_log.json ---
        counts["email_log"] = self._migrate_email_log(data_dir / "email_log.json")

        # --- calendar.json ---
        counts["calendar_events"] = self._migrate_calendar(data_dir / "calendar.json")

        return counts

    # ---- per-entity migration helpers --------------------------------

    def _migrate_projects(self, path: Path) -> dict[str, int]:
        if not path.exists():
            return {"imported": 0, "skipped": 0}
        projects = json.loads(path.read_text())
        imported = skipped = 0
        for p in projects:
            if self.get_project(p["id"]):
                skipped += 1
                continue
            self.create_project(
                name=p["name"],
                owner=p["owner"],
                id=p["id"],
                description=p.get("description", ""),
                status=p.get("status", "active"),
                progress_percent=p.get("progress_percent", 0),
                start_date=p.get("start_date", ""),
                target_end_date=p.get("target_end_date", ""),
                milestones=p.get("milestones", []),
                notes_history=p.get("notes_history", []),
                created_at=p.get("created_at", ""),
                updated_at=p.get("updated_at", ""),
            )
            imported += 1
        return {"imported": imported, "skipped": skipped}

    def _migrate_tasks(self, path: Path) -> dict[str, int]:
        if not path.exists():
            return {"imported": 0, "skipped": 0}
        tasks = json.loads(path.read_text())
        imported = skipped = 0
        for t in tasks:
            if self.get_task(t["id"]):
                skipped += 1
                continue
            self.create_task(
                project_id=t["project_id"],
                title=t["title"],
                assignee=t.get("assignee", ""),
                id=t["id"],
                description=t.get("description", ""),
                priority=t.get("priority", "medium"),
                status=t.get("status", "todo"),
                progress_percent=t.get("progress_percent", 0),
                due_date=t.get("due_date", ""),
                notes_history=t.get("notes_history", []),
                created_at=t.get("created_at", ""),
                updated_at=t.get("updated_at", ""),
            )
            imported += 1
        return {"imported": imported, "skipped": skipped}

    def _migrate_todos(self, path: Path) -> dict[str, int]:
        if not path.exists():
            return {"imported": 0, "skipped": 0}
        todos = json.loads(path.read_text())
        imported = skipped = 0
        for t in todos:
            if self.get_todo(t["id"]):
                skipped += 1
                continue
            self.create_todo(
                title=t["title"],
                priority=t.get("priority", "medium"),
                id=t["id"],
                description=t.get("description", ""),
                status=t.get("status", "pending"),
                due_date=t.get("due_date", ""),
                assignee=t.get("assignee", ""),
                category=t.get("category", "general"),
                notes=t.get("notes", ""),
                created_at=t.get("created_at", ""),
                updated_at=t.get("updated_at", ""),
            )
            imported += 1
        return {"imported": imported, "skipped": skipped}

    def _migrate_email_log(self, path: Path) -> dict[str, int]:
        if not path.exists():
            return {"imported": 0, "skipped": 0}
        entries = json.loads(path.read_text())
        imported = skipped = 0
        for e in entries:
            eid = e.get("email_id", "")
            # Email log entries with empty IDs need generated IDs.
            if not eid:
                eid = self._next_id("email", "email_log", "email_id")
            if self._get_email(eid):
                skipped += 1
                continue
            self.log_email(
                subject=e["subject"],
                sender=e["sender"],
                summary=e.get("summary", ""),
                priority=e.get("priority", "medium"),
                email_id=eid,
                action_required=e.get("action_required", False),
                action_items=e.get("action_items", []),
                logged_at=e.get("logged_at", ""),
            )
            imported += 1
        return {"imported": imported, "skipped": skipped}

    def _migrate_calendar(self, path: Path) -> dict[str, int]:
        if not path.exists():
            return {"imported": 0, "skipped": 0}
        events = json.loads(path.read_text())
        imported = skipped = 0
        for ev in events:
            if self.get_event(ev["id"]):
                skipped += 1
                continue
            self.create_event(
                title=ev["title"],
                date=ev["date"],
                start_time=ev["start_time"],
                end_time=ev["end_time"],
                id=ev["id"],
                location=ev.get("location", ""),
                attendees=ev.get("attendees", []),
                priority=ev.get("priority", "medium"),
                notes=ev.get("notes", ""),
                created_at=ev.get("created_at", ""),
            )
            imported += 1
        return {"imported": imported, "skipped": skipped}
