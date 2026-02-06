"""
Email tools for the Secretary Agent.

Provides IMAP email reading, summarization logging, and SMTP sending.
"""

import email
import imaplib
import json
import smtplib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

from business_team import config


class EmailTools:
    """Tools for reading, summarizing, and managing emails."""

    def __init__(self, db=None):
        self.db = db
        self.cfg = config.EMAIL_CONFIG
        self.email_log_file = config.DATA_DIR / "email_log.json"
        if not self.db and not self.email_log_file.exists():
            self.email_log_file.write_text("[]")

    # -- Tool definitions for Claude API --

    @staticmethod
    def get_tool_definitions() -> list[dict]:
        return [
            {
                "name": "read_emails",
                "description": "Read recent emails from the inbox. Returns subject, sender, date, and body preview for each email.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "folder": {
                            "type": "string",
                            "description": "Email folder to read from",
                            "default": "INBOX",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of emails to retrieve",
                            "default": 20,
                        },
                        "since_hours": {
                            "type": "integer",
                            "description": "Only fetch emails from the last N hours",
                            "default": 24,
                        },
                    },
                    "required": [],
                },
            },
            {
                "name": "log_email_summary",
                "description": "Log a summary of an email for future reference and reporting.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "email_id": {
                            "type": "string",
                            "description": "Unique identifier for the email",
                        },
                        "subject": {
                            "type": "string",
                            "description": "Email subject",
                        },
                        "sender": {
                            "type": "string",
                            "description": "Email sender",
                        },
                        "summary": {
                            "type": "string",
                            "description": "Concise summary of the email content",
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["high", "medium", "low"],
                            "description": "Priority level",
                        },
                        "action_required": {
                            "type": "boolean",
                            "description": "Whether action is required",
                        },
                        "action_items": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of action items from the email",
                        },
                    },
                    "required": ["subject", "sender", "summary", "priority"],
                },
            },
            {
                "name": "send_email",
                "description": "Send an email via SMTP.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "to": {
                            "type": "string",
                            "description": "Recipient email address",
                        },
                        "subject": {"type": "string", "description": "Email subject"},
                        "body": {
                            "type": "string",
                            "description": "Email body (HTML supported)",
                        },
                        "is_html": {
                            "type": "boolean",
                            "description": "Whether the body is HTML",
                            "default": False,
                        },
                    },
                    "required": ["to", "subject", "body"],
                },
            },
            {
                "name": "get_email_log",
                "description": "Retrieve the email summary log for reporting.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "since_date": {
                            "type": "string",
                            "description": "ISO date string - only return logs since this date",
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["high", "medium", "low"],
                            "description": "Filter by priority",
                        },
                    },
                    "required": [],
                },
            },
        ]

    # -- Tool implementations --

    def read_emails(
        self, folder: str = "INBOX", limit: int = 20, since_hours: int = 24
    ) -> list[dict]:
        """Connect to IMAP and fetch recent emails."""
        if not self.cfg["username"]:
            return self._get_demo_emails(limit)

        try:
            mail = imaplib.IMAP4_SSL(self.cfg["imap_server"], self.cfg["imap_port"])
            mail.login(self.cfg["username"], self.cfg["password"])
            mail.select(folder)

            since_date = (datetime.now() - timedelta(hours=since_hours)).strftime(
                "%d-%b-%Y"
            )
            _, message_ids = mail.search(None, f'(SINCE "{since_date}")')

            emails = []
            ids = message_ids[0].split()[-limit:]
            for eid in ids:
                _, msg_data = mail.fetch(eid, "(RFC822)")
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)

                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode(
                                errors="replace"
                            )
                            break
                else:
                    body = msg.get_payload(decode=True).decode(errors="replace")

                emails.append(
                    {
                        "id": eid.decode(),
                        "subject": msg["Subject"] or "(no subject)",
                        "from": msg["From"] or "",
                        "date": msg["Date"] or "",
                        "body_preview": body[:500],
                    }
                )

            mail.logout()
            return emails

        except Exception as e:
            return [{"error": str(e)}]

    def log_email_summary(
        self,
        subject: str,
        sender: str,
        summary: str,
        priority: str,
        email_id: str = "",
        action_required: bool = False,
        action_items: list[str] | None = None,
    ) -> dict:
        """Log an email summary to the persistent log."""
        if self.db:
            entry = self.db.log_email(
                subject=subject, sender=sender, summary=summary, priority=priority,
                email_id=email_id or None, action_required=action_required,
                action_items=action_items or [],
            )
            return {"status": "logged", "entry": entry}
        log = json.loads(self.email_log_file.read_text())
        entry = {
            "email_id": email_id,
            "subject": subject,
            "sender": sender,
            "summary": summary,
            "priority": priority,
            "action_required": action_required,
            "action_items": action_items or [],
            "logged_at": datetime.now().isoformat(),
        }
        log.append(entry)
        self.email_log_file.write_text(json.dumps(log, indent=2))
        return {"status": "logged", "entry": entry}

    def send_email(
        self, to: str, subject: str, body: str, is_html: bool = False
    ) -> dict:
        """Send an email via SMTP."""
        if not self.cfg["username"]:
            return {
                "status": "demo_mode",
                "message": f"Would send email to {to}: {subject}",
            }

        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = self.cfg["username"]
            msg["To"] = to
            msg["Subject"] = subject
            subtype = "html" if is_html else "plain"
            msg.attach(MIMEText(body, subtype))

            with smtplib.SMTP(self.cfg["smtp_server"], self.cfg["smtp_port"]) as server:
                server.starttls()
                server.login(self.cfg["username"], self.cfg["password"])
                server.send_message(msg)

            return {"status": "sent", "to": to, "subject": subject}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_email_log(
        self, since_date: str | None = None, priority: str | None = None
    ) -> list[dict]:
        """Retrieve email log entries with optional filtering."""
        if self.db:
            return self.db.get_email_log(since_date=since_date, priority=priority)
        log = json.loads(self.email_log_file.read_text())
        if since_date:
            log = [e for e in log if e.get("logged_at", "") >= since_date]
        if priority:
            log = [e for e in log if e.get("priority") == priority]
        return log

    def handle_tool_call(self, tool_name: str, tool_input: dict) -> Any:
        """Route a tool call to the correct method."""
        dispatch = {
            "read_emails": lambda: self.read_emails(**tool_input),
            "log_email_summary": lambda: self.log_email_summary(**tool_input),
            "send_email": lambda: self.send_email(**tool_input),
            "get_email_log": lambda: self.get_email_log(**tool_input),
        }
        handler = dispatch.get(tool_name)
        if handler:
            return handler()
        return {"error": f"Unknown email tool: {tool_name}"}

    # -- Demo data --

    @staticmethod
    def _get_demo_emails(limit: int) -> list[dict]:
        """Return sample emails for demo/testing purposes."""
        demos = [
            {
                "id": "demo_001",
                "subject": "Q4 Budget Review - Action Required",
                "from": "cfo@company.com",
                "date": datetime.now().isoformat(),
                "body_preview": "Please review the attached Q4 budget proposal and provide your comments by end of week. Key changes include a 15% increase in digital marketing spend and reallocation of resources to the new API platform.",
            },
            {
                "id": "demo_002",
                "subject": "SPL Digital Channels - Weekly Performance Summary",
                "from": "analytics@spl.com",
                "date": datetime.now().isoformat(),
                "body_preview": "Website traffic up 12% WoW. Mobile app downloads exceeded target by 8%. Customer portal satisfaction score at 4.2/5. API response times improved to 180ms average. Social media engagement up 23%.",
            },
            {
                "id": "demo_003",
                "subject": "Project Alpha - Milestone 3 Delayed",
                "from": "pm@company.com",
                "date": datetime.now().isoformat(),
                "body_preview": "Due to vendor dependency issues, Milestone 3 of Project Alpha will be delayed by 2 weeks. Revised timeline attached. Need to discuss resource reallocation in tomorrow's standup.",
            },
            {
                "id": "demo_004",
                "subject": "Board Meeting Agenda - Next Tuesday",
                "from": "exec.assistant@company.com",
                "date": datetime.now().isoformat(),
                "body_preview": "Reminder: Board meeting next Tuesday at 10 AM. Agenda items: Q4 results, 2026 strategy, digital transformation update, and new partnerships. Please prepare your department updates.",
            },
            {
                "id": "demo_005",
                "subject": "New Partnership Opportunity - TechVentures",
                "from": "bizdev@company.com",
                "date": datetime.now().isoformat(),
                "body_preview": "TechVentures has expressed interest in a strategic partnership for our digital channels. Initial meeting scheduled for Thursday. They offer complementary API infrastructure that could enhance our SPL platform.",
            },
        ]
        return demos[:limit]
