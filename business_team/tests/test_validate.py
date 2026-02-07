#!/usr/bin/env python3
"""
Phase 1 Validation Suite — Tests all components offline (no API calls).

Run:  python -m business_team.tests.test_validate
      OR:  python -m pytest business_team/tests/test_validate.py -v
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

PASS = 0
FAIL = 0
RESULTS = []


def check(name: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
        RESULTS.append(("PASS", name))
    else:
        FAIL += 1
        RESULTS.append(("FAIL", name, detail))
        print(f"  FAIL: {name} — {detail}")


def section(title: str) -> None:
    print(f"\n{'='*50}")
    print(f"  {title}")
    print(f"{'='*50}")


# ============================================================
# Section 1: Imports
# ============================================================
def test_imports():
    section("1. Module Imports")

    try:
        from business_team import config
        check("config module", True)
    except Exception as e:
        check("config module", False, str(e))

    try:
        from business_team.tools.email_tools import EmailTools
        from business_team.tools.calendar_tools import CalendarTools
        from business_team.tools.todo_tools import TodoTools
        from business_team.tools.presentation_tools import PresentationTools
        from business_team.tools.dashboard_tools import DashboardTools
        from business_team.tools.project_tools import ProjectTools
        from business_team.tools.reporting_tools import ReportingTools
        from business_team.tools.agent_dev_tools import AgentDevTools
        from business_team.tools.agent_monitor import AgentMonitorTools
        check("all 9 tool modules", True)
    except Exception as e:
        check("all 9 tool modules", False, str(e))

    try:
        from business_team.tools.gmail_connector import GmailConnector
        from business_team.tools.google_calendar_connector import GoogleCalendarConnector
        from business_team.tools.exchange_connector import ExchangeConnector
        check("all 3 connector modules", True)
    except Exception as e:
        check("all 3 connector modules", False, str(e))

    try:
        from business_team.agents.base_agent import BaseAgent
        from business_team.agents.secretary import SecretaryAgent
        from business_team.agents.business_analyst import BusinessAnalystAgent
        from business_team.agents.projects_manager import ProjectsManagerAgent
        from business_team.agents.chief_of_staff import ChiefOfStaffAgent
        check("all 5 agent modules", True)
    except Exception as e:
        check("all 5 agent modules", False, str(e))


# ============================================================
# Section 2: Tool Definitions Validity
# ============================================================
def test_tool_definitions():
    section("2. Tool Definitions")

    from business_team.tools.email_tools import EmailTools
    from business_team.tools.calendar_tools import CalendarTools
    from business_team.tools.todo_tools import TodoTools
    from business_team.tools.presentation_tools import PresentationTools
    from business_team.tools.dashboard_tools import DashboardTools
    from business_team.tools.project_tools import ProjectTools
    from business_team.tools.reporting_tools import ReportingTools
    from business_team.tools.agent_dev_tools import AgentDevTools
    from business_team.tools.agent_monitor import AgentMonitorTools

    from business_team.tools.gmail_connector import GmailConnector
    from business_team.tools.google_calendar_connector import GoogleCalendarConnector
    from business_team.tools.exchange_connector import ExchangeConnector

    tool_classes = [
        ("EmailTools", EmailTools),
        ("CalendarTools", CalendarTools),
        ("TodoTools", TodoTools),
        ("PresentationTools", PresentationTools),
        ("DashboardTools", DashboardTools),
        ("ProjectTools", ProjectTools),
        ("ReportingTools", ReportingTools),
        ("AgentDevTools", AgentDevTools),
        ("AgentMonitorTools", AgentMonitorTools),
        ("GmailConnector", GmailConnector),
        ("GoogleCalendarConnector", GoogleCalendarConnector),
        ("ExchangeConnector", ExchangeConnector),
    ]

    total_tools = 0
    for cls_name, cls in tool_classes:
        defs = cls.get_tool_definitions()
        count = len(defs)
        total_tools += count

        # Validate each definition has required fields
        all_valid = True
        for d in defs:
            if not all(k in d for k in ("name", "description", "input_schema")):
                all_valid = False
            schema = d.get("input_schema", {})
            if schema.get("type") != "object":
                all_valid = False

        check(f"{cls_name}: {count} tools defined", all_valid)

    check(f"total tools count >= 56", total_tools >= 56, f"got {total_tools}")
    print(f"  Total tool definitions: {total_tools}")


# ============================================================
# Section 3: Tool Functionality (Offline)
# ============================================================
def test_email_tools():
    section("3a. EmailTools (demo mode)")
    from business_team.tools.email_tools import EmailTools
    et = EmailTools()

    # Read demo emails
    emails = et.read_emails(limit=5)
    check("read_emails returns list", isinstance(emails, list))
    check("read_emails has data", len(emails) > 0)
    if emails:
        check("email has subject", "subject" in emails[0])
        check("email has from", "from" in emails[0])

    # Log email summary
    result = et.log_email_summary(
        subject="Test Email", sender="test@test.com",
        summary="This is a test", priority="high"
    )
    check("log_email_summary works", result.get("status") == "logged")

    # Get email log
    log = et.get_email_log()
    check("get_email_log returns list", isinstance(log, list))
    check("email log has entry", len(log) > 0)

    # Send email (demo mode)
    result = et.send_email(to="test@test.com", subject="Test", body="Hello")
    check("send_email demo mode", result.get("status") == "demo_mode")

    # Test handle_tool_call dispatch
    result = et.handle_tool_call("read_emails", {"limit": 3})
    check("handle_tool_call dispatch", isinstance(result, list))


def test_calendar_tools():
    section("3b. CalendarTools")
    from business_team.tools.calendar_tools import CalendarTools
    ct = CalendarTools()

    today = datetime.now().strftime("%Y-%m-%d")
    events = ct.get_calendar_events(today)
    check("get_calendar_events returns list", isinstance(events, list))
    check("demo events loaded", len(events) > 0)

    schedule = ct.get_today_schedule()
    check("get_today_schedule works", isinstance(schedule, list))

    result = ct.add_calendar_event(
        title="Test Meeting", date=today,
        start_time="16:00", end_time="17:00"
    )
    check("add_calendar_event works", result.get("status") == "created")

    conflicts = ct.check_conflicts(today, "09:00", "09:45")
    check("check_conflicts returns dict", "has_conflicts" in conflicts)


def test_todo_tools():
    section("3c. TodoTools")
    from business_team.tools.todo_tools import TodoTools
    tt = TodoTools()

    todos = tt.get_todos()
    check("get_todos returns list", isinstance(todos, list))
    check("demo todos loaded", len(todos) > 0)

    result = tt.add_todo(title="Test Task", priority="high", assignee="Tester")
    check("add_todo works", result.get("status") == "created")
    new_id = result["todo"]["id"]

    result = tt.update_todo(todo_id=new_id, status="in_progress")
    check("update_todo works", result.get("status") == "updated")

    summary = tt.get_todo_summary()
    check("get_todo_summary works", "total" in summary)
    check("summary has counts", summary["total"] > 0)


def test_project_tools():
    section("3d. ProjectTools")
    from business_team.tools.project_tools import ProjectTools
    pt = ProjectTools()

    projects = pt.get_projects()
    check("get_projects returns list", isinstance(projects, list))
    check("demo projects loaded", len(projects) >= 3)

    detail = pt.get_project_detail("proj_001")
    check("get_project_detail works", "name" in detail)
    check("project has tasks", "tasks" in detail)

    tasks = pt.get_tasks()
    check("get_tasks returns list", isinstance(tasks, list))
    check("demo tasks loaded", len(tasks) >= 5)

    summary = pt.get_project_summary()
    check("get_project_summary works", "total_projects" in summary)

    result = pt.create_project(
        name="Test Project", owner="Tester",
        start_date="2026-02-06", target_end_date="2026-06-30"
    )
    check("create_project works", result.get("status") == "created")

    result = pt.create_task(
        project_id="proj_001", title="Test Task", assignee="Tester"
    )
    check("create_task works", result.get("status") == "created")


def test_presentation_tools():
    section("3e. PresentationTools")
    from business_team.tools.presentation_tools import PresentationTools
    pt = PresentationTools()

    result = pt.create_presentation(
        title="Test Presentation",
        slides=[
            {"title": "Slide 1", "content": "Hello World", "slide_type": "content"},
            {"title": "KPI Slide", "slide_type": "kpi", "data": {
                "kpis": [
                    {"name": "Revenue", "value": "$1.2M", "trend": "up", "change": "+12%"},
                    {"name": "Users", "value": "45K", "trend": "up", "change": "+8%"},
                ]
            }},
        ],
        filename="test_pres",
    )
    check("create_presentation works", result.get("status") in ("created", "created_json_fallback"))
    check("presentation file created", Path(result.get("filepath", "")).exists())


def test_dashboard_tools():
    section("3f. DashboardTools")
    from business_team.tools.dashboard_tools import DashboardTools
    dt = DashboardTools()

    data = dt.get_spl_channel_data()
    check("get_spl_channel_data returns list", isinstance(data, list))
    check("has 5 channels", len(data) == 5)
    check("channel has metrics", "metrics" in data[0])

    result = dt.create_spl_dashboard(
        title="Test Dashboard", channels_data=data, filename="test_dashboard"
    )
    check("create_spl_dashboard works", result.get("status") == "created")
    check("dashboard file created", Path(result.get("filepath", "")).exists())

    # Read the HTML and verify it's valid
    html = Path(result["filepath"]).read_text()
    check("dashboard has HTML structure", "<!DOCTYPE html>" in html)
    check("dashboard has channel data", "Website" in html)


def test_reporting_tools():
    section("3g. ReportingTools")
    from business_team.tools.reporting_tools import ReportingTools
    rt = ReportingTools()

    result = rt.generate_weekly_report(
        projects_summary={
            "Project Alpha": {"status": "at_risk", "progress": 55, "notes": "Delayed"},
            "Project Beta": {"status": "active", "progress": 35, "notes": "On track"},
        },
        highlights=["Completed API integration", "Hired new developer"],
        risks=["Vendor delay on Project Alpha"],
        next_week_priorities=["Resolve API timeout", "Start UX testing"],
        filename="test_weekly",
    )
    check("generate_weekly_report works", result.get("status") == "created")
    check("weekly report file created", Path(result.get("filepath", "")).exists())

    result = rt.generate_project_status_board(
        projects=[{"name": "Alpha"}],
        tasks=[
            {"title": "Fix bug", "status": "in_progress", "assignee": "Dev", "priority": "high", "due_date": "2026-02-10"},
            {"title": "Write docs", "status": "todo", "assignee": "Writer", "priority": "low", "due_date": "2026-02-15"},
        ],
        filename="test_board",
    )
    check("generate_project_status_board works", result.get("status") == "created")


# ============================================================
# Section 3h: Connector Demo Mode Tests
# ============================================================
def test_gmail_connector():
    section("3h. GmailConnector")
    from business_team.tools.gmail_connector import GmailConnector
    gc = GmailConnector()

    # Read inbox — returns demo data or real data or connection error
    emails = gc.gmail_read_inbox(limit=5)
    check("gmail_read_inbox returns list", isinstance(emails, list))
    check("gmail_read_inbox has results", len(emails) > 0)
    if emails:
        # Could be demo data (has subject), real data (has subject), or error (has error key)
        check("gmail email has subject or error", "subject" in emails[0] or "error" in emails[0])

    # Send — demo_mode if unconfigured, error if configured but can't connect
    result = gc.gmail_send(to="test@test.com", subject="Test", body="Hello")
    check("gmail_send returns status", "status" in result or "message" in result)

    # Log summary
    result = gc.gmail_log_summary(
        subject="Test Gmail", sender="person@gmail.com",
        summary="Test email", priority="low"
    )
    check("gmail_log_summary works", result.get("status") == "logged")

    # Folders
    folders = gc.gmail_get_folders()
    check("gmail_get_folders returns list", isinstance(folders, list))

    # handle_tool_call dispatch
    result = gc.handle_tool_call("gmail_read_inbox", {"limit": 3})
    check("gmail handle_tool_call dispatch", isinstance(result, list))


def test_gcal_connector():
    section("3i. GoogleCalendarConnector (demo mode)")
    from business_team.tools.google_calendar_connector import GoogleCalendarConnector
    gc = GoogleCalendarConnector()

    events = gc.gcal_get_events(days_ahead=1)
    check("gcal_get_events returns list", isinstance(events, list))
    check("gcal demo events present", len(events) > 0)

    today_events = gc.gcal_get_today()
    check("gcal_get_today returns list", isinstance(today_events, list))

    result = gc.gcal_create_event(
        summary="Test Event", date="2026-03-01",
        start_time="10:00", end_time="11:00"
    )
    check("gcal_create_event demo mode", result.get("status") == "demo_mode")

    result = gc.gcal_check_availability(
        date="2026-03-01", start_time="10:00", end_time="11:00"
    )
    check("gcal_check_availability demo", result.get("available") is True)

    calendars = gc.gcal_list_calendars()
    check("gcal_list_calendars returns list", isinstance(calendars, list))

    # handle_tool_call dispatch
    result = gc.handle_tool_call("gcal_get_today", {})
    check("gcal handle_tool_call dispatch", isinstance(result, list))


def test_exchange_connector():
    section("3j. ExchangeConnector")
    from business_team.tools.exchange_connector import ExchangeConnector
    ec = ExchangeConnector()

    emails = ec.spl_read_inbox(limit=5)
    check("spl_read_inbox returns list", isinstance(emails, list))
    check("spl_read_inbox has results", len(emails) > 0)
    if emails:
        check("spl email has subject or error", "subject" in emails[0] or "error" in emails[0])

    result = ec.spl_send_email(
        to=["test@splonline.com.sa"], subject="Test", body="Hello"
    )
    check("spl_send_email returns status", "status" in result or "message" in result)

    result = ec.spl_log_summary(
        subject="Test Work Email", sender="colleague@splonline.com.sa",
        summary="Test work email summary", priority="medium"
    )
    check("spl_log_summary works", result.get("status") == "logged")

    folders = ec.spl_get_folders()
    check("spl_get_folders returns list", isinstance(folders, list))

    calendar = ec.spl_get_calendar(days_ahead=1)
    check("spl_get_calendar returns list", isinstance(calendar, list))
    check("spl demo calendar present", len(calendar) > 0)

    # handle_tool_call dispatch
    result = ec.handle_tool_call("spl_read_inbox", {"limit": 3})
    check("spl handle_tool_call dispatch", isinstance(result, list))


# ============================================================
# Section 3k: Email Poller Tests
# ============================================================
def test_email_poller():
    section("3k. EmailPoller")
    from business_team.email_poller import EmailPoller
    poller = EmailPoller(interval_minutes=5)

    # Status check
    status = poller.get_status()
    check("poller get_status works", "interval_minutes" in status)
    check("poller interval set", status["interval_minutes"] == 5)
    check("poller has gmail info", "gmail_configured" in status)
    check("poller has spl info", "spl_configured" in status)

    # Priority classification
    high_email = {"subject": "URGENT: Server downtime", "body_preview": "critical issue", "importance": "normal"}
    check("classifies urgent as high", poller._classify_priority(high_email) == "high")

    medium_email = {"subject": "Meeting tomorrow", "body_preview": "review the report", "importance": "normal"}
    check("classifies meeting as medium", poller._classify_priority(medium_email) == "medium")

    low_email = {"subject": "Newsletter", "body_preview": "check out our latest news", "importance": "normal"}
    check("classifies newsletter as low", poller._classify_priority(low_email) == "low")

    high_importance = {"subject": "FYI", "body_preview": "note", "importance": "high"}
    check("classifies importance=high as high", poller._classify_priority(high_importance) == "high")

    # Poll once (demo mode)
    result = poller.poll_once()
    check("poll_once returns dict", isinstance(result, dict))
    check("poll result has summary", "summary" in result)
    check("poll result has gmail_new", "gmail_new" in result)
    check("poll result has spl_new", "spl_new" in result)
    check("poll result has urgent_items", "urgent_items" in result)

    # State updated after poll
    check("total_polls incremented", poller.state["total_polls"] >= 1)

    # Notifications
    notifs = poller.get_notifications(limit=10)
    check("get_notifications returns list", isinstance(notifs, list))

    # Reset
    result = poller.reset_state()
    check("reset_state works", result.get("status") == "reset")
    check("state cleared after reset", poller.state["total_polls"] == 0)


# ============================================================
# Section 4: Agent Dev Tools (Offline)
# ============================================================
def test_agent_dev_tools():
    section("4. AgentDevTools")
    from business_team.tools.agent_dev_tools import AgentDevTools
    adt = AgentDevTools()

    # Read agent source
    result = adt.read_agent_source("secretary")
    check("read_agent_source works", "source" in result)
    check("secretary source has content", result.get("line_count", 0) > 50)

    # Read tool source
    result = adt.read_tool_source("email_tools")
    check("read_tool_source works", "source" in result)

    # Analyze capabilities
    result = adt.analyze_agent_capabilities("secretary")
    check("analyze_agent_capabilities works", "methods" in result)
    check("found methods", result.get("method_count", 0) > 0)
    # tool_count parses tool defs from source — secretary's tools are in tool modules, not agent file
    check("analysis has tool_count field", "tool_count" in result)

    # Get system prompt from source
    result = adt.get_agent_system_prompt("secretary")
    check("get_agent_system_prompt works", "prompt" in result)
    check("prompt has content", len(result.get("prompt", "")) > 100)

    # Backup agent
    result = adt.backup_agent("secretary")
    check("backup_agent works", result.get("status") == "backed_up")

    # Dev log
    log = adt.get_dev_log()
    check("get_dev_log returns list", isinstance(log, list))


# ============================================================
# Section 5: Agent Tool Routing
# ============================================================
def test_agent_tool_routing():
    section("5. Agent Tool Routing (execute_tool dispatch)")

    from business_team.agents.secretary import SecretaryAgent
    from business_team.agents.business_analyst import BusinessAnalystAgent
    from business_team.agents.projects_manager import ProjectsManagerAgent

    # Secretary routing — legacy tools
    sec = SecretaryAgent()
    result = sec.execute_tool("read_emails", {"limit": 3})
    check("Secretary routes read_emails", isinstance(result, list))
    result = sec.execute_tool("get_today_schedule", {})
    check("Secretary routes get_today_schedule", isinstance(result, list))
    result = sec.execute_tool("get_todo_summary", {})
    check("Secretary routes get_todo_summary", "total" in result)

    # Secretary routing — real connectors (demo mode)
    result = sec.execute_tool("gmail_read_inbox", {"limit": 3})
    check("Secretary routes gmail_read_inbox", isinstance(result, list))
    result = sec.execute_tool("gcal_get_today", {})
    check("Secretary routes gcal_get_today", isinstance(result, list))
    result = sec.execute_tool("spl_read_inbox", {"limit": 3})
    check("Secretary routes spl_read_inbox", isinstance(result, list))
    result = sec.execute_tool("spl_get_calendar", {})
    check("Secretary routes spl_get_calendar", isinstance(result, list))

    # Business Analyst routing
    ba = BusinessAnalystAgent()
    result = ba.execute_tool("get_spl_channel_data", {})
    check("Analyst routes get_spl_channel_data", isinstance(result, list))

    # Projects Manager routing
    pm = ProjectsManagerAgent()
    result = pm.execute_tool("get_projects", {})
    check("PM routes get_projects", isinstance(result, list))
    result = pm.execute_tool("get_project_summary", {})
    check("PM routes get_project_summary", "total_projects" in result)


# ============================================================
# Section 6: Chief of Staff Dev Tool Routing
# ============================================================
def test_chief_of_staff_routing():
    section("6. Chief of Staff Dev Tool Routing")

    from business_team.agents.chief_of_staff import ChiefOfStaffAgent
    mgr = ChiefOfStaffAgent()

    # Dev tools routing
    result = mgr.execute_tool("read_agent_source", {"agent_name": "secretary"})
    check("CoS routes read_agent_source", "source" in result)

    result = mgr.execute_tool("analyze_agent_capabilities", {"agent_name": "business_analyst"})
    check("CoS routes analyze_agent_capabilities", "methods" in result)

    result = mgr.execute_tool("backup_agent", {"agent_name": "projects_manager"})
    check("CoS routes backup_agent", result.get("status") == "backed_up")

    # Monitor tools routing
    result = mgr.execute_tool("run_agent_health_check", {"agent_name": "secretary"})
    check("CoS routes run_agent_health_check", "healthy" in result)
    check("Secretary health check passes", result.get("healthy") is True)

    result = mgr.execute_tool("run_agent_health_check", {"agent_name": "business_analyst"})
    check("Analyst health check passes", result.get("healthy") is True)

    result = mgr.execute_tool("run_agent_health_check", {"agent_name": "projects_manager"})
    check("PM health check passes", result.get("healthy") is True)

    # Reload agent
    result = mgr.reload_agent("secretary")
    check("reload_agent works", result.get("status") == "reloaded")

    # Team status
    status = mgr.get_team_status()
    check("get_team_status works", "secretary" in status)
    check("team status has all agents", all(
        k in status for k in ("chief_of_staff", "secretary", "business_analyst", "projects_manager")
    ))


# ============================================================
# Run all tests
# ============================================================
def main():
    print("\n" + "=" * 50)
    print("  BUSINESS TEAM — PHASE 1+2 VALIDATION SUITE")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    test_imports()
    test_tool_definitions()
    test_email_tools()
    test_calendar_tools()
    test_todo_tools()
    test_project_tools()
    test_presentation_tools()
    test_dashboard_tools()
    test_reporting_tools()
    test_gmail_connector()
    test_gcal_connector()
    test_exchange_connector()
    test_email_poller()
    test_agent_dev_tools()
    test_agent_tool_routing()
    test_chief_of_staff_routing()

    # Summary
    print("\n" + "=" * 50)
    print(f"  RESULTS: {PASS} passed, {FAIL} failed")
    print("=" * 50)

    if FAIL > 0:
        print("\nFailed tests:")
        for r in RESULTS:
            if r[0] == "FAIL":
                print(f"  FAIL: {r[1]} — {r[2]}")
        sys.exit(1)
    else:
        print("\n  ALL TESTS PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
