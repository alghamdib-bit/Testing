#!/usr/bin/env python3
"""
Business Team Multi-Agent System — Main Entry Point

A multi-agent system powered by Claude for business office management.
The Office Manager agent supervises Secretary, Business Analyst, and Projects Manager.

Usage:
    python -m business_team.main [command]

Commands:
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
    ask <message>     Send a request to the Office Manager
    interactive       Start interactive chat mode
"""

import argparse
import json
import sys
from datetime import datetime

from business_team.agents import OfficeManagerAgent


def print_header(title: str) -> None:
    width = 60
    print("\n" + "=" * width)
    print(f"  {title}")
    print(f"  {datetime.now().strftime('%A, %B %d, %Y — %H:%M')}")
    print("=" * width + "\n")


def print_result(result: str) -> None:
    print(result)
    print("\n" + "-" * 60)


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


def cmd_ask(manager: OfficeManagerAgent, message: str) -> None:
    print_header("OFFICE MANAGER RESPONSE")
    result = manager.handle_manager_request(message)
    print_result(result)


def cmd_interactive(manager: OfficeManagerAgent) -> None:
    print_header("INTERACTIVE MODE")
    print("Type your requests to the Office Manager. Type 'quit' to exit.\n")

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
        if user_input.lower() == "daily brief":
            cmd_daily_brief(manager)
            continue
        if user_input.lower() == "weekly brief":
            cmd_weekly_brief(manager)
            continue
        if user_input.lower() == "team status":
            cmd_team_status(manager)
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
            "ask",
            "interactive",
        ],
        help="Command to execute",
    )
    parser.add_argument(
        "message",
        nargs="*",
        help="Message for the 'ask' command",
    )

    args = parser.parse_args()

    print("\nInitializing Business Team Agent System...")
    manager = OfficeManagerAgent()
    print("All agents ready.\n")

    commands = {
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
        "interactive": lambda: cmd_interactive(manager),
    }

    if args.command == "ask":
        if not args.message:
            print("Error: 'ask' command requires a message.")
            print("Usage: python -m business_team.main ask 'your question here'")
            sys.exit(1)
        cmd_ask(manager, " ".join(args.message))
    elif args.command in commands:
        commands[args.command]()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
