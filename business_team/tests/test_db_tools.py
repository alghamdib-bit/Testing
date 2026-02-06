"""Tests that tool modules work correctly when backed by SQLite."""

import pytest
from pathlib import Path

from business_team.database import Database
from business_team.tools.project_tools import ProjectTools
from business_team.tools.todo_tools import TodoTools
from business_team.tools.calendar_tools import CalendarTools
from business_team.tools.email_tools import EmailTools


@pytest.fixture
def db(tmp_path):
    database = Database(db_path=tmp_path / "test.db")
    database.initialize()
    yield database
    database.close()


# ---- ProjectTools with SQLite ----

class TestProjectToolsWithDB:
    def test_create_project(self, db):
        pt = ProjectTools(db=db)
        result = pt.create_project(
            name="Test Project", owner="Bot",
            start_date="2026-01-01", target_end_date="2026-12-31",
        )
        assert result["status"] == "created"
        assert result["project"]["name"] == "Test Project"

    def test_get_projects(self, db):
        pt = ProjectTools(db=db)
        pt.create_project(name="A", owner="X", start_date="2026-01-01", target_end_date="2026-06-01")
        pt.create_project(name="B", owner="Y", start_date="2026-01-01", target_end_date="2026-06-01")
        projects = pt.get_projects()
        assert len(projects) == 2

    def test_get_projects_filter_status(self, db):
        pt = ProjectTools(db=db)
        pt.create_project(name="A", owner="X", start_date="2026-01-01", target_end_date="2026-06-01")
        projects = pt.get_projects(status="completed")
        assert len(projects) == 0

    def test_get_project_detail(self, db):
        pt = ProjectTools(db=db)
        r = pt.create_project(name="A", owner="X", start_date="2026-01-01", target_end_date="2026-06-01")
        pid = r["project"]["id"]
        pt.create_task(project_id=pid, title="Task 1", assignee="Dev")
        detail = pt.get_project_detail(pid)
        assert detail["name"] == "A"
        assert len(detail["tasks"]) == 1

    def test_update_project(self, db):
        pt = ProjectTools(db=db)
        r = pt.create_project(name="A", owner="X", start_date="2026-01-01", target_end_date="2026-06-01")
        pid = r["project"]["id"]
        updated = pt.update_project(pid, status="completed", progress_percent=100)
        assert updated["status"] == "updated"
        assert updated["project"]["progress_percent"] == 100

    def test_create_task(self, db):
        pt = ProjectTools(db=db)
        r = pt.create_project(name="A", owner="X", start_date="2026-01-01", target_end_date="2026-06-01")
        pid = r["project"]["id"]
        result = pt.create_task(project_id=pid, title="Fix bug", assignee="Dev")
        assert result["status"] == "created"
        assert result["task"]["title"] == "Fix bug"

    def test_get_tasks(self, db):
        pt = ProjectTools(db=db)
        r = pt.create_project(name="A", owner="X", start_date="2026-01-01", target_end_date="2026-06-01")
        pid = r["project"]["id"]
        pt.create_task(project_id=pid, title="T1", assignee="Dev")
        pt.create_task(project_id=pid, title="T2", assignee="QA")
        tasks = pt.get_tasks(project_id=pid)
        assert len(tasks) == 2

    def test_update_task(self, db):
        pt = ProjectTools(db=db)
        r = pt.create_project(name="A", owner="X", start_date="2026-01-01", target_end_date="2026-06-01")
        pid = r["project"]["id"]
        t = pt.create_task(project_id=pid, title="T1", assignee="Dev")
        tid = t["task"]["id"]
        updated = pt.update_task(tid, status="done", progress_percent=100)
        assert updated["status"] == "updated"
        assert updated["task"]["status"] == "done"

    def test_get_project_summary(self, db):
        pt = ProjectTools(db=db)
        pt.create_project(name="A", owner="X", start_date="2026-01-01", target_end_date="2026-06-01")
        summary = pt.get_project_summary()
        assert summary["total_projects"] == 1


# ---- TodoTools with SQLite ----

class TestTodoToolsWithDB:
    def test_add_todo(self, db):
        tt = TodoTools(db=db)
        result = tt.add_todo(title="Fix bug", priority="high")
        assert result["status"] == "created"
        assert result["todo"]["title"] == "Fix bug"

    def test_get_todos(self, db):
        tt = TodoTools(db=db)
        tt.add_todo(title="A", priority="high")
        tt.add_todo(title="B", priority="low")
        todos = tt.get_todos()
        assert len(todos) == 2

    def test_get_todos_filter(self, db):
        tt = TodoTools(db=db)
        tt.add_todo(title="A", priority="high")
        tt.add_todo(title="B", priority="low")
        high = tt.get_todos(priority="high")
        assert len(high) == 1
        assert high[0]["title"] == "A"

    def test_get_todos_assignee_filter(self, db):
        tt = TodoTools(db=db)
        tt.add_todo(title="A", priority="high", assignee="Alice")
        tt.add_todo(title="B", priority="high", assignee="Bob")
        alice_todos = tt.get_todos(assignee="Alice")
        assert len(alice_todos) == 1
        assert alice_todos[0]["assignee"] == "Alice"

    def test_update_todo(self, db):
        tt = TodoTools(db=db)
        r = tt.add_todo(title="A", priority="high")
        tid = r["todo"]["id"]
        updated = tt.update_todo(tid, status="completed")
        assert updated["status"] == "updated"
        assert updated["todo"]["status"] == "completed"

    def test_update_todo_not_found(self, db):
        tt = TodoTools(db=db)
        result = tt.update_todo("todo_9999", status="completed")
        assert result["status"] == "not_found"

    def test_get_todo_summary(self, db):
        tt = TodoTools(db=db)
        tt.add_todo(title="A", priority="high")
        tt.add_todo(title="B", priority="low")
        summary = tt.get_todo_summary()
        assert summary["total"] == 2


# ---- CalendarTools with SQLite ----

class TestCalendarToolsWithDB:
    def test_add_event(self, db):
        ct = CalendarTools(db=db)
        result = ct.add_calendar_event(
            title="Standup", date="2026-02-10",
            start_time="09:00", end_time="09:30",
        )
        assert result["status"] == "created"
        assert result["event"]["title"] == "Standup"

    def test_get_events(self, db):
        ct = CalendarTools(db=db)
        ct.add_calendar_event(title="A", date="2026-02-10", start_time="09:00", end_time="10:00")
        ct.add_calendar_event(title="B", date="2026-02-10", start_time="11:00", end_time="12:00")
        events = ct.get_calendar_events("2026-02-10")
        assert len(events) == 2

    def test_check_conflicts(self, db):
        ct = CalendarTools(db=db)
        ct.add_calendar_event(title="Meeting", date="2026-02-10", start_time="09:00", end_time="10:00")
        result = ct.check_conflicts("2026-02-10", "09:30", "10:30")
        assert result["has_conflicts"] is True

    def test_no_conflicts(self, db):
        ct = CalendarTools(db=db)
        ct.add_calendar_event(title="Meeting", date="2026-02-10", start_time="09:00", end_time="10:00")
        result = ct.check_conflicts("2026-02-10", "10:00", "11:00")
        assert result["has_conflicts"] is False

    def test_get_today_schedule(self, db):
        ct = CalendarTools(db=db)
        # No events for today by default
        schedule = ct.get_today_schedule()
        assert isinstance(schedule, list)


# ---- EmailTools with SQLite ----

class TestEmailToolsWithDB:
    def test_log_email(self, db):
        et = EmailTools(db=db)
        result = et.log_email_summary(
            subject="Test", sender="a@b.com", summary="A test", priority="high",
        )
        assert result["status"] == "logged"

    def test_get_email_log(self, db):
        et = EmailTools(db=db)
        et.log_email_summary(subject="A", sender="x@y", summary="s1", priority="high")
        et.log_email_summary(subject="B", sender="x@y", summary="s2", priority="low")
        log = et.get_email_log()
        assert len(log) == 2

    def test_get_email_log_filter(self, db):
        et = EmailTools(db=db)
        et.log_email_summary(subject="A", sender="x@y", summary="s1", priority="high")
        et.log_email_summary(subject="B", sender="x@y", summary="s2", priority="low")
        high = et.get_email_log(priority="high")
        assert len(high) == 1


# ---- Database gaps ----

class TestDatabaseGaps:
    def test_update_event(self, db):
        db.create_event(title="Old", date="2026-02-10", start_time="09:00", end_time="10:00")
        events = db.get_events("2026-02-10")
        eid = events[0]["id"]
        updated = db.update_event(eid, title="New Title")
        assert updated["title"] == "New Title"

    def test_update_event_not_found(self, db):
        result = db.update_event("evt_9999")
        assert "error" in result

    def test_check_conflicts(self, db):
        db.create_event(title="A", date="2026-03-01", start_time="09:00", end_time="10:00")
        result = db.check_conflicts("2026-03-01", "09:30", "10:30")
        assert result["has_conflicts"] is True

    def test_get_today_schedule(self, db):
        result = db.get_today_schedule()
        assert isinstance(result, list)

    def test_get_todos_with_assignee(self, db):
        db.create_todo(title="A", priority="high", assignee="Alice")
        db.create_todo(title="B", priority="high", assignee="Bob")
        result = db.get_todos(assignee="alice")
        assert len(result) == 1
        assert result[0]["assignee"] == "Alice"
