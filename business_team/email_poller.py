"""
Email Poller — Periodic inbox monitoring for Gmail and SPL Exchange.

Checks both inboxes at configurable intervals, detects new emails,
flags urgent items, and stores notifications for the Secretary/Office Manager.

Usage:
    # One-shot poll (check once and exit)
    python -m business_team.email_poller --once

    # Continuous polling (every 30 min by default)
    python -m business_team.email_poller

    # Custom interval
    python -m business_team.email_poller --interval 15
"""

import json
import os
import signal
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

from business_team import config
from business_team.tools.gmail_connector import GmailConnector
from business_team.tools.exchange_connector import ExchangeConnector


class EmailPoller:
    """Monitors Gmail and SPL Exchange inboxes for new emails."""

    def __init__(self, interval_minutes: int = 0):
        self.interval = interval_minutes or int(os.getenv("EMAIL_CHECK_INTERVAL", "30"))
        self.gmail = GmailConnector()
        self.exchange = ExchangeConnector()

        # State files
        self.state_file = config.DATA_DIR / "poller_state.json"
        self.notifications_file = config.DATA_DIR / "email_notifications.json"

        self._load_state()
        self._ensure_notifications()
        self._running = False

    def _load_state(self):
        """Load or initialize poller state (last-checked times, seen UIDs)."""
        if self.state_file.exists():
            self.state = json.loads(self.state_file.read_text())
        else:
            self.state = {
                "gmail_last_checked": None,
                "spl_last_checked": None,
                "gmail_seen_uids": [],
                "spl_seen_uids": [],
                "total_polls": 0,
                "total_new_emails": 0,
            }
            self._save_state()

    def _save_state(self):
        """Persist poller state."""
        self.state_file.write_text(json.dumps(self.state, indent=2))

    def _ensure_notifications(self):
        """Ensure notifications file exists."""
        if not self.notifications_file.exists():
            self.notifications_file.write_text("[]")

    def _add_notification(self, notification: dict):
        """Add a notification to the queue."""
        notifications = json.loads(self.notifications_file.read_text())
        notifications.append(notification)
        # Keep last 200 notifications
        if len(notifications) > 200:
            notifications = notifications[-200:]
        self.notifications_file.write_text(json.dumps(notifications, indent=2))

    def _classify_priority(self, email: dict) -> str:
        """Classify email priority based on content signals."""
        subject = (email.get("subject") or "").lower()
        body = (email.get("body_preview") or "").lower()
        importance = (email.get("importance") or "").lower()
        combined = subject + " " + body

        # High priority signals
        high_signals = [
            "urgent", "asap", "critical", "emergency", "deadline",
            "action required", "immediate", "escalat", "ceo", "cto",
            "board meeting", "p1", "blocker", "downtime", "outage",
        ]
        if importance == "high" or any(s in combined for s in high_signals):
            return "high"

        # Medium priority signals
        medium_signals = [
            "review", "feedback", "approval", "meeting", "update",
            "report", "milestone", "decision", "budget", "schedule",
        ]
        if any(s in combined for s in medium_signals):
            return "medium"

        return "low"

    def poll_gmail(self) -> list[dict]:
        """Check Gmail for new emails since last poll."""
        now = datetime.now().isoformat()
        seen_uids = set(self.state.get("gmail_seen_uids", []))

        # Determine how far back to look
        last_checked = self.state.get("gmail_last_checked")
        if last_checked:
            since_days = max(1, (datetime.now() - datetime.fromisoformat(last_checked)).days + 1)
        else:
            since_days = 1

        emails = self.gmail.gmail_read_inbox(limit=50, since_days=since_days)

        new_emails = []
        for email in emails:
            uid = email.get("uid") or email.get("id", "")
            if not uid or uid.startswith("demo_"):
                # Demo data — skip UID tracking but include in results
                if not last_checked:
                    new_emails.append(email)
                continue
            if uid not in seen_uids:
                seen_uids.add(uid)
                email["_priority"] = self._classify_priority(email)
                email["_source"] = "gmail"
                email["_detected_at"] = now
                new_emails.append(email)

        self.state["gmail_last_checked"] = now
        self.state["gmail_seen_uids"] = list(seen_uids)[-500:]  # Keep last 500 UIDs
        return new_emails

    def poll_spl(self) -> list[dict]:
        """Check SPL Exchange for new emails since last poll."""
        now = datetime.now().isoformat()
        seen_uids = set(self.state.get("spl_seen_uids", []))

        last_checked = self.state.get("spl_last_checked")
        if last_checked:
            since_days = max(1, (datetime.now() - datetime.fromisoformat(last_checked)).days + 1)
        else:
            since_days = 1

        emails = self.exchange.spl_read_inbox(limit=50, since_days=since_days)

        new_emails = []
        for email in emails:
            uid = email.get("uid") or email.get("id", "")
            if not uid or uid.startswith("demo_"):
                if not last_checked:
                    new_emails.append(email)
                continue
            if uid not in seen_uids:
                seen_uids.add(uid)
                email["_priority"] = self._classify_priority(email)
                email["_source"] = "spl_exchange"
                email["_detected_at"] = now
                new_emails.append(email)

        self.state["spl_last_checked"] = now
        self.state["spl_seen_uids"] = list(seen_uids)[-500:]
        return new_emails

    def poll_once(self) -> dict:
        """Run a single poll cycle across all accounts."""
        poll_start = datetime.now()
        results = {
            "poll_time": poll_start.isoformat(),
            "gmail_new": [],
            "spl_new": [],
            "urgent_items": [],
            "summary": "",
        }

        # Poll Gmail
        try:
            gmail_new = self.poll_gmail()
            results["gmail_new"] = gmail_new
        except Exception as e:
            results["gmail_error"] = str(e)
            gmail_new = []

        # Poll SPL Exchange
        try:
            spl_new = self.poll_spl()
            results["spl_new"] = spl_new
        except Exception as e:
            results["spl_error"] = str(e)
            spl_new = []

        # Identify urgent items
        all_new = gmail_new + spl_new
        urgent = [e for e in all_new if e.get("_priority") == "high"]
        results["urgent_items"] = urgent

        # Update state
        self.state["total_polls"] = self.state.get("total_polls", 0) + 1
        self.state["total_new_emails"] = self.state.get("total_new_emails", 0) + len(all_new)
        self._save_state()

        # Build summary
        gmail_count = len(gmail_new)
        spl_count = len(spl_new)
        urgent_count = len(urgent)

        if all_new:
            summary_parts = []
            if gmail_count:
                summary_parts.append(f"{gmail_count} new Gmail")
            if spl_count:
                summary_parts.append(f"{spl_count} new SPL")
            summary = f"[{poll_start.strftime('%H:%M')}] {' + '.join(summary_parts)} email(s)"
            if urgent_count:
                summary += f" — {urgent_count} URGENT"
                urgent_subjects = [e.get("subject", "?") for e in urgent]
                summary += f": {'; '.join(urgent_subjects)}"
            results["summary"] = summary

            # Store notification
            self._add_notification({
                "type": "email_poll",
                "time": poll_start.isoformat(),
                "gmail_count": gmail_count,
                "spl_count": spl_count,
                "urgent_count": urgent_count,
                "urgent_subjects": [e.get("subject", "") for e in urgent],
                "all_subjects": [
                    {"source": e.get("_source", "?"), "subject": e.get("subject", "?"),
                     "from": e.get("from", ""), "priority": e.get("_priority", "low")}
                    for e in all_new
                ],
            })
        else:
            results["summary"] = f"[{poll_start.strftime('%H:%M')}] No new emails"

        return results

    def run_continuous(self):
        """Run polling in a loop with configured interval."""
        self._running = True

        def handle_stop(signum, frame):
            self._running = False
            print("\nStopping email poller...")

        signal.signal(signal.SIGINT, handle_stop)
        signal.signal(signal.SIGTERM, handle_stop)

        print(f"Email Poller started — checking every {self.interval} minutes")
        print(f"  Gmail:    {'configured' if self.gmail.is_configured else 'demo mode'} ({self.gmail.email or 'not set'})")
        print(f"  SPL:      {'configured' if self.exchange.is_configured else 'demo mode'} ({self.exchange.email or 'not set'})")
        print(f"  Interval: {self.interval} min")
        print(f"  Press Ctrl+C to stop\n")

        while self._running:
            try:
                result = self.poll_once()
                print(result["summary"])

                if result.get("urgent_items"):
                    for item in result["urgent_items"]:
                        src = "[WORK]" if item.get("_source") == "spl_exchange" else "[PERSONAL]"
                        print(f"  !! URGENT {src} from {item.get('from', '?')}: {item.get('subject', '?')}")

                if result.get("gmail_error"):
                    print(f"  Gmail error: {result['gmail_error']}")
                if result.get("spl_error"):
                    print(f"  SPL error: {result['spl_error']}")

            except Exception as e:
                print(f"  Poll error: {e}")

            # Sleep in small increments to allow clean shutdown
            for _ in range(self.interval * 60):
                if not self._running:
                    break
                time.sleep(1)

        print("Email Poller stopped.")
        self._save_state()

    def get_notifications(self, limit: int = 20, unread_only: bool = False) -> list[dict]:
        """Retrieve recent notifications."""
        notifications = json.loads(self.notifications_file.read_text())
        if unread_only:
            notifications = [n for n in notifications if not n.get("read")]
        return notifications[-limit:]

    def mark_notifications_read(self) -> int:
        """Mark all notifications as read."""
        notifications = json.loads(self.notifications_file.read_text())
        count = 0
        for n in notifications:
            if not n.get("read"):
                n["read"] = True
                count += 1
        self.notifications_file.write_text(json.dumps(notifications, indent=2))
        return count

    def get_status(self) -> dict:
        """Get poller status summary."""
        return {
            "interval_minutes": self.interval,
            "gmail_configured": self.gmail.is_configured,
            "gmail_account": self.gmail.email or "(not set)",
            "gmail_last_checked": self.state.get("gmail_last_checked"),
            "gmail_tracked_uids": len(self.state.get("gmail_seen_uids", [])),
            "spl_configured": self.exchange.is_configured,
            "spl_account": self.exchange.email or "(not set)",
            "spl_last_checked": self.state.get("spl_last_checked"),
            "spl_tracked_uids": len(self.state.get("spl_seen_uids", [])),
            "total_polls": self.state.get("total_polls", 0),
            "total_new_emails_detected": self.state.get("total_new_emails", 0),
        }

    def reset_state(self) -> dict:
        """Reset poller state (forget seen UIDs, timestamps)."""
        self.state = {
            "gmail_last_checked": None,
            "spl_last_checked": None,
            "gmail_seen_uids": [],
            "spl_seen_uids": [],
            "total_polls": 0,
            "total_new_emails": 0,
        }
        self._save_state()
        return {"status": "reset", "message": "Poller state cleared"}


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Email Poller for Business Team")
    parser.add_argument("--once", action="store_true", help="Poll once and exit")
    parser.add_argument("--interval", type=int, default=0, help="Poll interval in minutes")
    parser.add_argument("--status", action="store_true", help="Show poller status")
    parser.add_argument("--notifications", action="store_true", help="Show recent notifications")
    parser.add_argument("--reset", action="store_true", help="Reset poller state")
    args = parser.parse_args()

    poller = EmailPoller(interval_minutes=args.interval)

    if args.status:
        status = poller.get_status()
        print(json.dumps(status, indent=2))
    elif args.notifications:
        notifs = poller.get_notifications(limit=20)
        if not notifs:
            print("No notifications yet.")
        else:
            for n in notifs:
                t = n.get("time", "")[:19]
                gc = n.get("gmail_count", 0)
                sc = n.get("spl_count", 0)
                uc = n.get("urgent_count", 0)
                print(f"  [{t}] Gmail: {gc} new, SPL: {sc} new, Urgent: {uc}")
                for s in n.get("all_subjects", []):
                    tag = "[WORK]" if s["source"] == "spl_exchange" else "[PERSONAL]"
                    pri = f" !!{s['priority'].upper()}" if s["priority"] == "high" else ""
                    print(f"    {tag}{pri} {s['subject']} — from {s['from']}")
    elif args.reset:
        result = poller.reset_state()
        print(result["message"])
    elif args.once:
        result = poller.poll_once()
        print(result["summary"])
        if result.get("gmail_new"):
            print(f"\n  Gmail ({len(result['gmail_new'])} new):")
            for e in result["gmail_new"]:
                pri = f" [!!{e.get('_priority', '').upper()}]" if e.get("_priority") == "high" else ""
                print(f"    {pri} {e.get('subject', '?')} — from {e.get('from', '?')}")
        if result.get("spl_new"):
            print(f"\n  SPL ({len(result['spl_new'])} new):")
            for e in result["spl_new"]:
                pri = f" [!!{e.get('_priority', '').upper()}]" if e.get("_priority") == "high" else ""
                print(f"    {pri} {e.get('subject', '?')} — from {e.get('from', '?')}")
        if not result.get("gmail_new") and not result.get("spl_new"):
            print("  No new emails detected.")
    else:
        poller.run_continuous()


if __name__ == "__main__":
    main()
