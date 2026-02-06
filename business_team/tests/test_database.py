"""
Tests for business_team.database -- the SQLite database layer.

Run with:
    python -m pytest business_team/tests/test_database.py -v

Every test uses the ``tmp_path`` fixture so that each test gets its own
isolated, temporary SQLite database file.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from business_team.database import Database


# =====================================================================
# Fixtures
# =====================================================================

@pytest.fixture()
def db(tmp_path: Path) -> Database:
    """Yield an initialised Database backed by a temp file."""
    database = Database(db_path=tmp_path / "test.db")
    database.initialize()
    yield database
    database.close()


def _seed_project(db: Database, **overrides) -> dict:
    """Helper: insert a project with sensible defaults, merging *overrides*."""
    defaults = {
        "name": "Seed Project",
        "owner": "Tester",
        "start_date": "2026-01-01",
        "target_end_date": "2026-12-31",
    }
    defaults.update(overrides)
    return db.create_project(**defaults)


def _seed_task(db: Database, project_id: str = "proj_001", **overrides) -> dict:
    """Helper: insert a task with sensible defaults."""
    defaults = {
        "project_id": project_id,
        "title": "Seed Task",
        "assignee": "Dev A",
    }
    defaults.update(overrides)
    return db.create_task(**defaults)


# =====================================================================
# Project tests
# =====================================================================

class TestProjects:

    def test_create_project(self, db: Database) -> None:
        proj = db.create_project(
            name="Alpha",
            owner="Ahmad",
            start_date="2026-01-01",
            target_end_date="2026-06-30",
            description="A test project",
            milestones=[{"name": "M1", "due_date": "2026-03-01", "status": "pending"}],
        )
        assert proj["id"] == "proj_001"
        assert proj["name"] == "Alpha"
        assert proj["owner"] == "Ahmad"
        assert proj["status"] == "active"
        assert proj["progress_percent"] == 0
        assert isinstance(proj["milestones"], list)
        assert len(proj["milestones"]) == 1

    def test_get_projects(self, db: Database) -> None:
        _seed_project(db, name="P1")
        _seed_project(db, name="P2")
        _seed_project(db, name="P3")
        projects = db.get_projects()
        assert len(projects) == 3
        names = [p["name"] for p in projects]
        assert "P1" in names and "P2" in names and "P3" in names

    def test_get_project_by_id(self, db: Database) -> None:
        created = _seed_project(db, name="Find Me")
        found = db.get_project(created["id"])
        assert found is not None
        assert found["name"] == "Find Me"

        missing = db.get_project("proj_999")
        assert missing is None

    def test_update_project(self, db: Database) -> None:
        proj = _seed_project(db)
        updated = db.update_project(proj["id"], status="at_risk", progress_percent=55)
        assert updated["status"] == "at_risk"
        assert updated["progress_percent"] == 55

        # Adding notes appends to history
        updated2 = db.update_project(proj["id"], notes="Needs attention")
        assert len(updated2["notes_history"]) == 1
        assert updated2["notes_history"][0]["text"] == "Needs attention"

    def test_filter_projects_by_status(self, db: Database) -> None:
        _seed_project(db, name="Active1", status="active")
        _seed_project(db, name="AtRisk", status="at_risk")
        _seed_project(db, name="Active2", status="active")

        active = db.get_projects(status="active")
        assert len(active) == 2
        at_risk = db.get_projects(status="at_risk")
        assert len(at_risk) == 1
        assert at_risk[0]["name"] == "AtRisk"


# =====================================================================
# Task tests
# =====================================================================

class TestTasks:

    def test_create_task(self, db: Database) -> None:
        proj = _seed_project(db)
        task = db.create_task(
            project_id=proj["id"],
            title="Build Widget",
            assignee="Dev A",
            priority="high",
            due_date="2026-03-15",
        )
        assert task["id"] == "task_0001"
        assert task["project_id"] == proj["id"]
        assert task["priority"] == "high"
        assert task["status"] == "todo"

    def test_get_tasks(self, db: Database) -> None:
        proj = _seed_project(db)
        _seed_task(db, project_id=proj["id"], title="T1")
        _seed_task(db, project_id=proj["id"], title="T2")
        tasks = db.get_tasks()
        assert len(tasks) == 2

    def test_filter_tasks_by_project(self, db: Database) -> None:
        p1 = _seed_project(db, name="P1")
        p2 = _seed_project(db, name="P2")
        _seed_task(db, project_id=p1["id"], title="T1-P1")
        _seed_task(db, project_id=p2["id"], title="T2-P2")
        _seed_task(db, project_id=p1["id"], title="T3-P1")

        tasks_p1 = db.get_tasks(project_id=p1["id"])
        assert len(tasks_p1) == 2
        assert all(t["project_id"] == p1["id"] for t in tasks_p1)

    def test_update_task_status(self, db: Database) -> None:
        proj = _seed_project(db)
        task = _seed_task(db, project_id=proj["id"])
        updated = db.update_task(task["id"], status="in_progress", progress_percent=40)
        assert updated["status"] == "in_progress"
        assert updated["progress_percent"] == 40


# =====================================================================
# Todo tests
# =====================================================================

class TestTodos:

    def test_create_todo(self, db: Database) -> None:
        todo = db.create_todo(
            title="Review budget",
            priority="high",
            assignee="Manager",
            category="finance",
            due_date="2026-02-10",
        )
        assert todo["id"] == "todo_0001"
        assert todo["title"] == "Review budget"
        assert todo["priority"] == "high"
        assert todo["status"] == "pending"

    def test_get_todos(self, db: Database) -> None:
        db.create_todo(title="A", priority="high")
        db.create_todo(title="B", priority="low")
        todos = db.get_todos()
        assert len(todos) == 2

    def test_update_todo(self, db: Database) -> None:
        todo = db.create_todo(title="Fix it", priority="medium")
        updated = db.update_todo(todo["id"], status="completed", notes="All done")
        assert updated["status"] == "completed"
        assert updated["notes"] == "All done"

    def test_get_todo_summary(self, db: Database) -> None:
        db.create_todo(title="A", priority="high", status="pending")
        db.create_todo(title="B", priority="high", status="in_progress")
        db.create_todo(title="C", priority="medium", status="pending")
        db.create_todo(title="D", priority="low", status="completed")

        summary = db.get_todo_summary()
        assert summary["total"] == 4
        assert summary["by_status"]["pending"] == 2
        assert summary["by_status"]["in_progress"] == 1
        assert summary["by_status"]["completed"] == 1
        assert summary["by_priority"]["high"] == 2
        assert summary["by_priority"]["medium"] == 1
        assert summary["by_priority"]["low"] == 1


# =====================================================================
# Email log tests
# =====================================================================

class TestEmailLog:

    def test_log_email(self, db: Database) -> None:
        entry = db.log_email(
            subject="Q4 Budget",
            sender="cfo@company.com",
            summary="Review the budget",
            priority="high",
            action_required=True,
            action_items=["Review", "Comment"],
        )
        assert entry["subject"] == "Q4 Budget"
        assert entry["action_required"] is True
        assert entry["action_items"] == ["Review", "Comment"]
        assert entry["email_id"].startswith("email_")

    def test_get_email_log(self, db: Database) -> None:
        db.log_email(subject="A", sender="a@a.com", summary="s", priority="high")
        db.log_email(subject="B", sender="b@b.com", summary="s", priority="low")
        logs = db.get_email_log()
        assert len(logs) == 2

    def test_filter_email_log_by_priority(self, db: Database) -> None:
        db.log_email(subject="Urgent", sender="a@a.com", summary="s", priority="high")
        db.log_email(subject="FYI", sender="b@b.com", summary="s", priority="low")
        db.log_email(subject="Alert", sender="c@c.com", summary="s", priority="high")

        high = db.get_email_log(priority="high")
        assert len(high) == 2
        assert all(e["priority"] == "high" for e in high)


# =====================================================================
# Calendar event tests
# =====================================================================

class TestCalendarEvents:

    def test_create_event(self, db: Database) -> None:
        evt = db.create_event(
            title="Standup",
            date="2026-02-10",
            start_time="09:00",
            end_time="09:30",
            location="Room A",
            attendees=["Alice", "Bob"],
        )
        assert evt["id"] == "evt_0001"
        assert evt["title"] == "Standup"
        assert evt["attendees"] == ["Alice", "Bob"]

    def test_get_events_by_date(self, db: Database) -> None:
        db.create_event(title="E1", date="2026-02-10", start_time="09:00", end_time="10:00")
        db.create_event(title="E2", date="2026-02-10", start_time="11:00", end_time="12:00")
        db.create_event(title="E3", date="2026-02-11", start_time="09:00", end_time="10:00")

        events = db.get_events(start_date="2026-02-10")
        assert len(events) == 2

        events_range = db.get_events(start_date="2026-02-10", end_date="2026-02-11")
        assert len(events_range) == 3


# =====================================================================
# Migration tests
# =====================================================================

class TestMigration:

    @staticmethod
    def _write_json(path: Path, data: list | dict) -> None:
        path.write_text(json.dumps(data, indent=2))

    def test_migrate_from_json(self, tmp_path: Path) -> None:
        """Create temp JSON files, migrate, verify data in the database."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        # -- projects.json
        self._write_json(data_dir / "projects.json", [
            {
                "id": "proj_001",
                "name": "Alpha",
                "description": "Desc",
                "owner": "Ahmad",
                "status": "active",
                "progress_percent": 55,
                "start_date": "2025-10-01",
                "target_end_date": "2026-03-31",
                "milestones": [{"name": "M1", "due_date": "2026-01-15", "status": "completed"}],
                "notes_history": [],
                "created_at": "2025-10-01T00:00:00",
                "updated_at": "2026-02-06T12:00:00",
            },
        ])

        # -- tasks.json
        self._write_json(data_dir / "tasks.json", [
            {
                "id": "task_0001",
                "project_id": "proj_001",
                "title": "Fix API",
                "assignee": "Dev A",
                "priority": "high",
                "status": "in_progress",
                "progress_percent": 60,
                "due_date": "2026-02-10",
                "created_at": "2026-02-06T12:00:00",
                "updated_at": "2026-02-06T12:00:00",
            },
        ])

        # -- todos.json
        self._write_json(data_dir / "todos.json", [
            {
                "id": "todo_0001",
                "title": "Review budget",
                "description": "CFO review",
                "priority": "high",
                "status": "pending",
                "due_date": "2026-02-06",
                "assignee": "Manager",
                "category": "finance",
                "created_at": "2026-02-06T00:00:00",
                "updated_at": "2026-02-06T00:00:00",
            },
        ])

        # -- email_log.json
        self._write_json(data_dir / "email_log.json", [
            {
                "email_id": "demo_001",
                "subject": "Budget Review",
                "sender": "cfo@company.com",
                "summary": "Review Q4",
                "priority": "high",
                "action_required": True,
                "action_items": ["Review", "Comment"],
                "logged_at": "2026-02-06T10:00:00",
            },
        ])

        # -- calendar.json
        self._write_json(data_dir / "calendar.json", [
            {
                "id": "evt_0001",
                "title": "Standup",
                "date": "2026-02-06",
                "start_time": "09:00",
                "end_time": "09:30",
                "location": "Room A",
                "attendees": ["Alice"],
                "priority": "medium",
                "notes": "Daily sync",
            },
        ])

        # --- Run migration ---
        db = Database(db_path=tmp_path / "migrated.db")
        db.initialize()
        result = db.migrate_from_json(data_dir=data_dir)

        # Verify counts
        assert result["projects"]["imported"] == 1
        assert result["tasks"]["imported"] == 1
        assert result["todos"]["imported"] == 1
        assert result["email_log"]["imported"] == 1
        assert result["calendar_events"]["imported"] == 1

        # Spot-check data
        proj = db.get_project("proj_001")
        assert proj is not None
        assert proj["name"] == "Alpha"
        assert proj["milestones"][0]["name"] == "M1"

        task = db.get_task("task_0001")
        assert task is not None
        assert task["title"] == "Fix API"

        todos = db.get_todos()
        assert len(todos) == 1
        assert todos[0]["title"] == "Review budget"

        emails = db.get_email_log()
        assert len(emails) == 1
        assert emails[0]["action_items"] == ["Review", "Comment"]

        events = db.get_events("2026-02-06")
        assert len(events) == 1
        assert events[0]["attendees"] == ["Alice"]

        db.close()

    def test_migrate_idempotent(self, tmp_path: Path) -> None:
        """Running migration twice must not create duplicates."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        self._write_json(data_dir / "projects.json", [
            {
                "id": "proj_001",
                "name": "Alpha",
                "description": "",
                "owner": "Ahmad",
                "status": "active",
                "progress_percent": 0,
                "start_date": "2025-10-01",
                "target_end_date": "2026-03-31",
                "milestones": [],
                "notes_history": [],
                "created_at": "2025-10-01T00:00:00",
                "updated_at": "2025-10-01T00:00:00",
            },
        ])
        self._write_json(data_dir / "tasks.json", [
            {
                "id": "task_0001",
                "project_id": "proj_001",
                "title": "T1",
                "assignee": "X",
                "priority": "medium",
                "status": "todo",
                "progress_percent": 0,
                "due_date": "",
                "created_at": "2026-01-01T00:00:00",
                "updated_at": "2026-01-01T00:00:00",
            },
        ])
        self._write_json(data_dir / "todos.json", [])
        self._write_json(data_dir / "email_log.json", [])
        self._write_json(data_dir / "calendar.json", [])

        db = Database(db_path=tmp_path / "idempotent.db")
        db.initialize()

        r1 = db.migrate_from_json(data_dir=data_dir)
        assert r1["projects"]["imported"] == 1
        assert r1["tasks"]["imported"] == 1

        # Second run -- everything should be skipped
        r2 = db.migrate_from_json(data_dir=data_dir)
        assert r2["projects"]["imported"] == 0
        assert r2["projects"]["skipped"] == 1
        assert r2["tasks"]["imported"] == 0
        assert r2["tasks"]["skipped"] == 1

        # Final check: still exactly one of each
        assert len(db.get_projects()) == 1
        assert len(db.get_tasks()) == 1

        db.close()


# =====================================================================
# Infrastructure tests
# =====================================================================

class TestInfrastructure:

    def test_database_context_manager(self, tmp_path: Path) -> None:
        """Using ``with Database(...) as db:`` initialises and closes cleanly."""
        db_path = tmp_path / "ctx.db"
        with Database(db_path=db_path) as db:
            # Should be able to use the database inside the context.
            proj = db.create_project(name="CM Test", owner="Bot", start_date="2026-01-01", target_end_date="2026-12-31")
            assert proj["id"] == "proj_001"
        # After exiting the context, the connection should be closed.
        assert db._conn is None

    def test_database_initializes_tables(self, tmp_path: Path) -> None:
        """``initialize()`` creates all expected tables."""
        db = Database(db_path=tmp_path / "init.db")
        db.initialize()
        cur = db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        # Filter out internal SQLite tables (e.g. sqlite_sequence).
        tables = sorted(
            row[0] for row in cur.fetchall() if not row[0].startswith("sqlite_")
        )
        expected = sorted([
            "activity_log",
            "calendar_events",
            "email_log",
            "projects",
            "schema_version",
            "tasks",
            "todos",
        ])
        assert tables == expected
        db.close()
