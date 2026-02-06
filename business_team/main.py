#!/usr/bin/env python3
"""
Business Team Multi-Agent System — Main Entry Point

A multi-agent system powered by Claude for business office management.
The Office Manager agent supervises AND develops Secretary, Business Analyst, and Projects Manager.

Usage:
    python -m business_team.main [command]

Commands:
  Supervision:
    daily-brief       Generate today's daily brief
    weekly-brief      Generate the weekly consolidated brief
    check-emails      Check and summarize recent emails
    calendar          Show today's calendar
    todos             Show to-do list status
    spl-dashboard     Generate SPL Digital Channels dashboard
    spl-presentation  Generate SPL board presentation
    project-status    Show project portfolio status
    weekly-report     Generate weekly project report
    monthly-report    Generate monthly project report
    status-board      Generate the Kanban project board
    team-status       Show all agent statuses

  Email Polling:
    poll              Poll all inboxes once and show new emails
    poll-start        Start continuous email polling (Ctrl+C to stop)
    poll-status       Show poller status and account info
    poll-notifications Show recent email notifications
    poll-reset        Reset poller state (forget seen emails)

  Development:
    audit             Full team audit (capabilities, health, gaps)
    test-agents       Run standardized tests on all agents
    dev-log           Show agent development change log
    develop <msg>     Ask Office Manager to develop/improve an agent
    reload <agent>    Reload an agent after code changes

  General:
    ask <message>     Send a request to the Office Manager
    interactive       Start interactive chat mode (default)
"""

import argparse
import json
import sys
from datetime import datetime

from business_team.agents import OfficeManagerAgent
from business_team.database import Database
from business_team.email_poller import EmailPoller
from business_team.memory import AgentMemory
from business_team.scheduler import Scheduler


def print_header(title: str) -> None:
    width = 60
    print("\n" + "=" * width)
    print(f"  {title}")
    print(f"  {datetime.now().strftime('%A, %B %d, %Y — %H:%M')}")
    print("=" * width + "\n")


def print_result(result: str) -> None:
    print(result)
    print("\n" + "-" * 60)


# ---- Supervision Commands ----

def cmd_daily_brief(manager: OfficeManagerAgent) -> None:
    print_header("DAILY BRIEF")
    print("Gathering reports from all team members...")
    result = manager.generate_daily_brief()
    print_result(result)


def cmd_weekly_brief(manager: OfficeManagerAgent) -> None:
    print_header("WEEKLY BRIEF")
    print("Compiling weekly reports from all team members...")
    result = manager.generate_weekly_brief()
    print_result(result)


def cmd_check_emails(manager: OfficeManagerAgent) -> None:
    print_header("EMAIL CHECK")
    manager.secretary.reset_conversation()
    result = manager.secretary.check_inbox()
    print_result(result)


def cmd_calendar(manager: OfficeManagerAgent) -> None:
    print_header("TODAY'S CALENDAR")
    manager.secretary.reset_conversation()
    result = manager.secretary.get_calendar_briefing()
    print_result(result)


def cmd_todos(manager: OfficeManagerAgent) -> None:
    print_header("TO-DO LIST")
    manager.secretary.reset_conversation()
    result = manager.secretary.get_todo_report()
    print_result(result)


def cmd_spl_dashboard(manager: OfficeManagerAgent) -> None:
    print_header("SPL DIGITAL CHANNELS DASHBOARD")
    manager.analyst.reset_conversation()
    result = manager.analyst.generate_channel_report()
    print_result(result)


def cmd_spl_presentation(manager: OfficeManagerAgent) -> None:
    print_header("SPL BOARD PRESENTATION")
    manager.analyst.reset_conversation()
    result = manager.analyst.create_board_presentation()
    print_result(result)


def cmd_project_status(manager: OfficeManagerAgent) -> None:
    print_header("PROJECT PORTFOLIO STATUS")
    manager.projects_manager.reset_conversation()
    result = manager.projects_manager.get_portfolio_status()
    print_result(result)


def cmd_weekly_report(manager: OfficeManagerAgent) -> None:
    print_header("WEEKLY PROJECT REPORT")
    manager.projects_manager.reset_conversation()
    result = manager.projects_manager.generate_weekly_update()
    print_result(result)


def cmd_monthly_report(manager: OfficeManagerAgent) -> None:
    print_header("MONTHLY PROJECT REPORT")
    manager.projects_manager.reset_conversation()
    result = manager.projects_manager.generate_monthly_update()
    print_result(result)


def cmd_status_board(manager: OfficeManagerAgent) -> None:
    print_header("PROJECT STATUS BOARD")
    manager.projects_manager.reset_conversation()
    result = manager.projects_manager.think(
        "Generate the project status board showing all tasks in Kanban format.\n"
        "1. Get all projects\n"
        "2. Get all tasks\n"
        "3. Generate the status board HTML\n"
        "Use filename 'project_status_board'"
    )
    print_result(result)


def cmd_team_status(manager: OfficeManagerAgent) -> None:
    print_header("TEAM STATUS")
    status = manager.get_team_status()
    print(json.dumps(status, indent=2))


# ---- Email Polling Commands ----

def cmd_poll(poller: EmailPoller) -> None:
    print_header("EMAIL POLL")
    result = poller.poll_once()
    print(result["summary"])
    if result.get("gmail_new"):
        print(f"\n  Gmail ({len(result['gmail_new'])} new):")
        for e in result["gmail_new"]:
            pri = " [URGENT]" if e.get("_priority") == "high" else ""
            print(f"    {pri} {e.get('subject', '?')} — from {e.get('from', '?')}")
    if result.get("spl_new"):
        print(f"\n  SPL Exchange ({len(result['spl_new'])} new):")
        for e in result["spl_new"]:
            pri = " [URGENT]" if e.get("_priority") == "high" else ""
            print(f"    {pri} {e.get('subject', '?')} — from {e.get('from', '?')}")
    if result.get("urgent_items"):
        print(f"\n  !! {len(result['urgent_items'])} URGENT item(s) detected!")
    if not result.get("gmail_new") and not result.get("spl_new"):
        print("  No new emails detected.")
    if result.get("gmail_error"):
        print(f"  Gmail error: {result['gmail_error']}")
    if result.get("spl_error"):
        print(f"  SPL error: {result['spl_error']}")
    print()


def cmd_poll_start(poller: EmailPoller) -> None:
    print_header("EMAIL POLLER — CONTINUOUS MODE")
    poller.run_continuous()


def cmd_poll_status(poller: EmailPoller) -> None:
    print_header("EMAIL POLLER STATUS")
    status = poller.get_status()
    print(f"  Interval:         {status['interval_minutes']} minutes")
    print(f"  Total polls:      {status['total_polls']}")
    print(f"  Emails detected:  {status['total_new_emails_detected']}")
    print()
    print(f"  Gmail account:    {status['gmail_account']}")
    print(f"  Gmail configured: {status['gmail_configured']}")
    print(f"  Gmail last check: {status['gmail_last_checked'] or 'never'}")
    print(f"  Gmail tracked:    {status['gmail_tracked_uids']} UIDs")
    print()
    print(f"  SPL account:      {status['spl_account']}")
    print(f"  SPL configured:   {status['spl_configured']}")
    print(f"  SPL last check:   {status['spl_last_checked'] or 'never'}")
    print(f"  SPL tracked:      {status['spl_tracked_uids']} UIDs")
    print()


def cmd_poll_notifications(poller: EmailPoller) -> None:
    print_header("EMAIL NOTIFICATIONS")
    notifs = poller.get_notifications(limit=20)
    if not notifs:
        print("  No notifications yet. Run 'poll' to check inboxes.")
    else:
        for n in notifs:
            t = n.get("time", "")[:19]
            gc = n.get("gmail_count", 0)
            sc = n.get("spl_count", 0)
            uc = n.get("urgent_count", 0)
            urgent_tag = f" — {uc} URGENT" if uc else ""
            print(f"  [{t}] Gmail: {gc}, SPL: {sc}{urgent_tag}")
            for s in n.get("all_subjects", []):
                tag = "[WORK]" if s["source"] == "spl_exchange" else "[PERSONAL]"
                pri = " !!" if s["priority"] == "high" else ""
                print(f"    {tag}{pri} {s['subject']} — {s['from']}")
    poller.mark_notifications_read()
    print()


def cmd_poll_reset(poller: EmailPoller) -> None:
    print_header("RESET POLLER")
    result = poller.reset_state()
    print(f"  {result['message']}")
    print("  Poller will treat all emails as new on next poll.")
    print()


# ---- Scheduler Commands ----

def cmd_schedule(scheduler: Scheduler) -> None:
    print_header("SCHEDULED JOBS")
    jobs = scheduler.get_upcoming_jobs()
    if not jobs:
        print("  No jobs scheduled.")
    else:
        for job in jobs:
            print(f"  {job['job_name']:20s}  next: {job.get('next_run', 'N/A')}  interval: {job.get('interval', '?')} {job.get('unit', '')}")
    print()


def cmd_schedule_start(scheduler: Scheduler) -> None:
    print_header("SCHEDULER — FOREGROUND MODE")
    scheduler.start()


def cmd_schedule_status(scheduler: Scheduler) -> None:
    print_header("SCHEDULER STATUS")
    jobs = scheduler.get_upcoming_jobs()
    for job in jobs:
        print(f"  {job['job_name']:20s}  next: {job.get('next_run', 'N/A')}")
    log = scheduler.get_log(limit=5)
    if log:
        print("\n  Last 5 executions:")
        for entry in log:
            ts = entry.get("timestamp", "")[:19]
            print(f"    [{ts}] {entry.get('job_name', '?')}: {entry.get('status', '?')} - {entry.get('details', '')[:60]}")
    print()


def cmd_schedule_log(scheduler: Scheduler) -> None:
    print_header("SCHEDULER LOG")
    log = scheduler.get_log(limit=20)
    if not log:
        print("  No scheduler log entries yet.")
    else:
        for entry in log:
            ts = entry.get("timestamp", "")[:19]
            print(f"  [{ts}] {entry.get('job_name', ''):20s} {entry.get('status', ''):8s} {entry.get('details', '')[:50]}")
    print()


def cmd_schedule_run(scheduler: Scheduler, job_name: str) -> None:
    print_header(f"RUN JOB: {job_name}")
    result = scheduler.run_now(job_name)
    print(f"  {result}")
    print()


def cmd_migrate(db: Database) -> None:
    print_header("DATABASE MIGRATION")
    print("  Migrating JSON flat files to SQLite database...")
    result = db.migrate_from_json()
    print("\n  Migration Results:")
    for entity, counts in result.items():
        imported = counts.get("imported", 0)
        skipped = counts.get("skipped", 0)
        print(f"    {entity:20s}  imported: {imported}  skipped: {skipped}")
    print(f"\n  Database: {db.db_path}")
    print()


# ---- Development Commands ----

def cmd_audit(manager: OfficeManagerAgent) -> None:
    print_header("TEAM AUDIT")
    print("Analyzing all agents: capabilities, health, and improvement opportunities...")
    result = manager.audit_team()
    print_result(result)


def cmd_test_agents(manager: OfficeManagerAgent) -> None:
    print_header("AGENT TESTING")
    print("Running standardized tests on all agents...")
    result = manager.test_all_agents()
    print_result(result)


def cmd_dev_log(manager: OfficeManagerAgent) -> None:
    print_header("DEVELOPMENT LOG")
    log = manager.dev_tools.get_dev_log(30)
    if not log:
        print("No development actions logged yet.")
    else:
        for entry in log:
            ts = entry.get("timestamp", "")[:19]
            action = entry.get("action", "")
            agent = entry.get("agent_name", "")
            reason = entry.get("reason", "")
            print(f"  [{ts}] {action} on {agent}: {reason}")
    print()


def cmd_develop(manager: OfficeManagerAgent, message: str) -> None:
    print_header("AGENT DEVELOPMENT")
    result = manager.develop_agent(message)
    print_result(result)


def cmd_reload(manager: OfficeManagerAgent, agent_name: str) -> None:
    print_header(f"RELOAD AGENT: {agent_name}")
    result = manager.reload_agent(agent_name)
    print(json.dumps(result, indent=2))


# ---- General Commands ----

def cmd_ask(manager: OfficeManagerAgent, message: str) -> None:
    print_header("OFFICE MANAGER RESPONSE")
    result = manager.handle_manager_request(message)
    print_result(result)


def cmd_interactive(manager: OfficeManagerAgent, poller: EmailPoller, scheduler: Scheduler = None) -> None:
    print_header("INTERACTIVE MODE")
    print("Type your requests to the Office Manager. Type 'quit' to exit.")
    print("The Office Manager can supervise agents AND develop/improve them.\n")
    print("Quick commands: 'daily brief', 'weekly brief', 'team status',")
    print("  'audit', 'test agents', 'dev log', 'reload <agent>',")
    print("  'poll', 'poll status', 'poll notifications',")
    print("  'schedule', 'schedule status', 'schedule log'\n")

    while True:
        try:
            user_input = input("\nYou > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        # Quick commands
        lower = user_input.lower()
        if lower == "daily brief":
            cmd_daily_brief(manager)
            continue
        if lower == "weekly brief":
            cmd_weekly_brief(manager)
            continue
        if lower == "team status":
            cmd_team_status(manager)
            continue
        if lower == "audit":
            cmd_audit(manager)
            continue
        if lower == "test agents":
            cmd_test_agents(manager)
            continue
        if lower == "dev log":
            cmd_dev_log(manager)
            continue
        if lower.startswith("reload "):
            agent_name = lower.replace("reload ", "").strip()
            cmd_reload(manager, agent_name)
            continue
        # Polling quick commands
        if lower == "poll":
            cmd_poll(poller)
            continue
        if lower == "poll status":
            cmd_poll_status(poller)
            continue
        if lower in ("poll notifications", "notifications"):
            cmd_poll_notifications(poller)
            continue
        if lower == "poll reset":
            cmd_poll_reset(poller)
            continue
        if lower == "check emails":
            cmd_check_emails(manager)
            continue
        # Scheduler quick commands
        if lower == "schedule" and scheduler:
            cmd_schedule(scheduler)
            continue
        if lower == "schedule status" and scheduler:
            cmd_schedule_status(scheduler)
            continue
        if lower == "schedule log" and scheduler:
            cmd_schedule_log(scheduler)
            continue
        if lower.startswith("schedule run ") and scheduler:
            job_name = lower.replace("schedule run ", "").strip()
            cmd_schedule_run(scheduler, job_name)
            continue

        result = manager.handle_manager_request(user_input)
        print_result(result)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Business Team Multi-Agent System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="interactive",
        choices=[
            # Supervision
            "daily-brief",
            "weekly-brief",
            "check-emails",
            "calendar",
            "todos",
            "spl-dashboard",
            "spl-presentation",
            "project-status",
            "weekly-report",
            "monthly-report",
            "status-board",
            "team-status",
            # Email Polling
            "poll",
            "poll-start",
            "poll-status",
            "poll-notifications",
            "poll-reset",
            # Development
            "audit",
            "test-agents",
            "dev-log",
            "develop",
            "reload",
            # Scheduler
            "schedule",
            "schedule-start",
            "schedule-status",
            "schedule-log",
            "schedule-run",
            # Database
            "migrate",
            # General
            "ask",
            "interactive",
        ],
        help="Command to execute",
    )
    parser.add_argument(
        "message",
        nargs="*",
        help="Message for 'ask'/'develop' commands, or agent name for 'reload'",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=0,
        help="Polling interval in minutes (for poll-start)",
    )

    args = parser.parse_args()

    # Polling commands don't need the full agent system
    polling_commands = {"poll", "poll-start", "poll-status", "poll-notifications", "poll-reset"}
    if args.command in polling_commands:
        poller = EmailPoller(interval_minutes=args.interval)
        if args.command == "poll":
            cmd_poll(poller)
        elif args.command == "poll-start":
            cmd_poll_start(poller)
        elif args.command == "poll-status":
            cmd_poll_status(poller)
        elif args.command == "poll-notifications":
            cmd_poll_notifications(poller)
        elif args.command == "poll-reset":
            cmd_poll_reset(poller)
        return

    # Migrate command only needs the database
    if args.command == "migrate":
        db = Database()
        db.initialize()
        cmd_migrate(db)
        db.close()
        return

    # Initialize database, memory, and full agent system
    db = Database()
    db.initialize()
    memory = AgentMemory()

    print("\nInitializing Business Team Agent System...")
    manager = OfficeManagerAgent(db=db, memory=memory)
    poller = EmailPoller()
    scheduler = Scheduler(manager=manager, poller=poller)
    print("All agents ready. Office Manager has supervisor + developer capabilities.\n")

    commands = {
        # Supervision
        "daily-brief": lambda: cmd_daily_brief(manager),
        "weekly-brief": lambda: cmd_weekly_brief(manager),
        "check-emails": lambda: cmd_check_emails(manager),
        "calendar": lambda: cmd_calendar(manager),
        "todos": lambda: cmd_todos(manager),
        "spl-dashboard": lambda: cmd_spl_dashboard(manager),
        "spl-presentation": lambda: cmd_spl_presentation(manager),
        "project-status": lambda: cmd_project_status(manager),
        "weekly-report": lambda: cmd_weekly_report(manager),
        "monthly-report": lambda: cmd_monthly_report(manager),
        "status-board": lambda: cmd_status_board(manager),
        "team-status": lambda: cmd_team_status(manager),
        # Development
        "audit": lambda: cmd_audit(manager),
        "test-agents": lambda: cmd_test_agents(manager),
        "dev-log": lambda: cmd_dev_log(manager),
        # Scheduler
        "schedule": lambda: cmd_schedule(scheduler),
        "schedule-start": lambda: cmd_schedule_start(scheduler),
        "schedule-status": lambda: cmd_schedule_status(scheduler),
        "schedule-log": lambda: cmd_schedule_log(scheduler),
        # General
        "interactive": lambda: cmd_interactive(manager, poller, scheduler),
    }

    if args.command == "ask":
        if not args.message:
            print("Error: 'ask' command requires a message.")
            print("Usage: python -m business_team.main ask 'your question here'")
            sys.exit(1)
        cmd_ask(manager, " ".join(args.message))
    elif args.command == "develop":
        if not args.message:
            print("Error: 'develop' command requires a description.")
            print("Usage: python -m business_team.main develop 'improve secretary email parsing'")
            sys.exit(1)
        cmd_develop(manager, " ".join(args.message))
    elif args.command == "reload":
        if not args.message:
            print("Error: 'reload' command requires an agent name.")
            print("Usage: python -m business_team.main reload secretary")
            sys.exit(1)
        cmd_reload(manager, args.message[0])
    elif args.command == "schedule-run":
        if not args.message:
            print("Error: 'schedule-run' command requires a job name.")
            print("Usage: python -m business_team.main schedule-run daily_brief")
            sys.exit(1)
        cmd_schedule_run(scheduler, args.message[0])
    elif args.command in commands:
        commands[args.command]()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
