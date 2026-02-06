"""
Scheduled Operations for the Business Team.

Runs periodic tasks: daily briefs, email polling, weekly/monthly reports.

Usage:
    from business_team.scheduler import Scheduler
    scheduler = Scheduler(office_manager, email_poller)
    scheduler.start()  # blocks, runs in foreground
    # or
    scheduler.start_background()  # runs in background thread
    scheduler.stop()
"""

import json
import signal
import threading
import time
from datetime import datetime
from typing import Any, Callable

import schedule

from business_team import config


class Scheduler:
    """Manages scheduled operations for the business team."""

    def __init__(self, manager=None, poller=None):
        """Initialize with optional OfficeManagerAgent and EmailPoller instances.

        Args:
            manager: An OfficeManagerAgent instance (or None for testing).
            poller: An EmailPoller instance (or None for testing).
        """
        self.manager = manager
        self.poller = poller
        self._running = False
        self._thread = None
        self._schedule = schedule.Scheduler()
        self.log_file = config.DATA_DIR / "scheduler_log.json"
        self._setup_jobs()

    def _setup_jobs(self):
        """Configure all scheduled jobs from config."""
        brief_time = config.SCHEDULE_CONFIG["daily_brief_time"]
        self._schedule.every().day.at(brief_time).do(self._run_daily_brief)

        poll_interval = config.SCHEDULE_CONFIG["email_check_interval_minutes"]
        self._schedule.every(poll_interval).minutes.do(self._run_email_poll)

        report_day = config.SCHEDULE_CONFIG["weekly_report_day"]
        getattr(self._schedule.every(), report_day).at("18:00").do(
            self._run_weekly_report
        )

        # Monthly report on configured day at 09:00
        self._schedule.every().day.at("09:00").do(self._run_monthly_report_if_day)

    def _log_execution(self, job_name: str, status: str, details: str = ""):
        """Log a scheduled job execution to the JSON log file.

        Args:
            job_name: Identifier for the job (e.g. 'daily_brief').
            status: Either 'success' or 'error'.
            details: Additional information about the execution.
        """
        entry = {
            "job_name": job_name,
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat(),
        }

        # Read existing log
        log_entries = []
        if self.log_file.exists():
            try:
                log_entries = json.loads(self.log_file.read_text())
            except (json.JSONDecodeError, ValueError):
                log_entries = []

        log_entries.append(entry)

        # Keep last 500 entries
        if len(log_entries) > 500:
            log_entries = log_entries[-500:]

        self.log_file.write_text(json.dumps(log_entries, indent=2))

    def _run_daily_brief(self):
        """Execute the daily brief generation."""
        if self.manager:
            try:
                result = self.manager.generate_daily_brief()
                self._log_execution(
                    "daily_brief", "success", str(result)[:200]
                )
            except Exception as e:
                self._log_execution("daily_brief", "error", str(e))

    def _run_email_poll(self):
        """Execute email polling."""
        if self.poller:
            try:
                result = self.poller.poll_once()
                self._log_execution(
                    "email_poll", "success", result.get("summary", "")
                )
            except Exception as e:
                self._log_execution("email_poll", "error", str(e))

    def _run_weekly_report(self):
        """Execute weekly report generation."""
        if self.manager and hasattr(self.manager, "projects_manager"):
            try:
                result = self.manager.projects_manager.generate_weekly_update()
                self._log_execution(
                    "weekly_report", "success", str(result)[:200]
                )
            except Exception as e:
                self._log_execution("weekly_report", "error", str(e))

    def _run_monthly_report_if_day(self):
        """Only run monthly report if today is the configured day."""
        if datetime.now().day == config.SCHEDULE_CONFIG["monthly_report_day"]:
            if self.manager and hasattr(self.manager, "projects_manager"):
                try:
                    result = (
                        self.manager.projects_manager.generate_monthly_update()
                    )
                    self._log_execution(
                        "monthly_report", "success", str(result)[:200]
                    )
                except Exception as e:
                    self._log_execution("monthly_report", "error", str(e))

    def get_upcoming_jobs(self) -> list[dict]:
        """Return list of scheduled jobs with next run time.

        Returns:
            A list of dicts, each containing 'job_name', 'next_run', and
            'interval' information.
        """
        jobs = []
        for job in self._schedule.get_jobs():
            job_func_name = ""
            if hasattr(job, "job_func") and hasattr(job.job_func, "__name__"):
                job_func_name = job.job_func.__name__
            elif hasattr(job, "job_func") and hasattr(
                job.job_func, "func"
            ):
                # functools.partial or wrapped functions
                job_func_name = getattr(
                    job.job_func.func, "__name__", str(job.job_func)
                )
            else:
                job_func_name = str(job.job_func)

            # Map internal method names to friendly job names
            name_map = {
                "_run_daily_brief": "daily_brief",
                "_run_email_poll": "email_poll",
                "_run_weekly_report": "weekly_report",
                "_run_monthly_report_if_day": "monthly_report",
            }
            friendly_name = name_map.get(job_func_name, job_func_name)

            jobs.append(
                {
                    "job_name": friendly_name,
                    "next_run": str(job.next_run) if job.next_run else None,
                    "interval": str(job.interval),
                    "unit": job.unit,
                }
            )
        return jobs

    def get_log(self, limit: int = 20) -> list[dict]:
        """Return recent scheduler log entries.

        Args:
            limit: Maximum number of entries to return.

        Returns:
            A list of log entry dicts (most recent last).
        """
        if not self.log_file.exists():
            return []
        try:
            entries = json.loads(self.log_file.read_text())
            return entries[-limit:]
        except (json.JSONDecodeError, ValueError):
            return []

    def start(self):
        """Start the scheduler (blocking). Ctrl+C to stop."""
        self._running = True
        signal.signal(signal.SIGINT, lambda s, f: self.stop())
        signal.signal(signal.SIGTERM, lambda s, f: self.stop())
        print(f"Scheduler started at {datetime.now().strftime('%H:%M')}")
        print(
            f"  Daily brief: {config.SCHEDULE_CONFIG['daily_brief_time']}"
        )
        print(
            f"  Email poll: every "
            f"{config.SCHEDULE_CONFIG['email_check_interval_minutes']} min"
        )
        print(
            f"  Weekly report: "
            f"{config.SCHEDULE_CONFIG['weekly_report_day']}s at 18:00"
        )
        print(
            f"  Monthly report: day "
            f"{config.SCHEDULE_CONFIG['monthly_report_day']} at 09:00"
        )
        while self._running:
            self._schedule.run_pending()
            time.sleep(1)

    def start_background(self):
        """Start the scheduler in a background thread."""
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _run_loop(self):
        """Internal loop for background thread execution."""
        while self._running:
            self._schedule.run_pending()
            time.sleep(1)

    def stop(self):
        """Stop the scheduler."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        print("Scheduler stopped.")

    def run_now(self, job_name: str) -> str:
        """Manually trigger a job by name.

        Args:
            job_name: One of 'daily_brief', 'email_poll', 'weekly_report',
                      'monthly_report'.

        Returns:
            A message indicating whether the job was executed or not found.
        """
        dispatch = {
            "daily_brief": self._run_daily_brief,
            "email_poll": self._run_email_poll,
            "weekly_report": self._run_weekly_report,
            "monthly_report": self._run_monthly_report_if_day,
        }
        if job_name in dispatch:
            dispatch[job_name]()
            return f"Executed {job_name}"
        return f"Unknown job: {job_name}"
