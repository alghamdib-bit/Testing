"""
Gmail Connector — Real email access via IMAP + SMTP using App Password.

Handles reading, searching, and sending Gmail using the imap_tools library.
Falls back to demo data if credentials are not configured.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Any

from dotenv import load_dotenv

load_dotenv()

try:
    from imap_tools import MailBox, AND, OR
    IMAP_TOOLS_AVAILABLE = True
except BaseException:
    IMAP_TOOLS_AVAILABLE = False

from business_team import config


class GmailConnector:
    """Real Gmail access via IMAP/SMTP with App Password."""

    IMAP_HOST = "imap.gmail.com"
    SMTP_HOST = "smtp.gmail.com"
    SMTP_PORT = 465

    def __init__(self):
        self.email = os.getenv("GMAIL_ADDRESS", "")
        self.app_password = os.getenv("GMAIL_APP_PASSWORD", "")
        self.is_configured = bool(self.email and self.app_password and IMAP_TOOLS_AVAILABLE)
        self.email_log_file = config.DATA_DIR / "gmail_log.json"
        if not self.email_log_file.exists():
            self.email_log_file.write_text("[]")

    @staticmethod
    def get_tool_definitions() -> list[dict]:
        return [
            {
                "name": "gmail_read_inbox",
                "description": "Read recent emails from Gmail inbox. Returns sender, subject, date, and body preview.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum emails to fetch",
                            "default": 20,
                        },
                        "unread_only": {
                            "type": "boolean",
                            "description": "Only fetch unread emails",
                            "default": False,
                        },
                        "since_days": {
                            "type": "integer",
                            "description": "Only fetch emails from the last N days",
                            "default": 1,
                        },
                    },
                    "required": [],
                },
            },
            {
                "name": "gmail_search",
                "description": "Search Gmail with a query (e.g., from, subject, keywords).",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "from_addr": {
                            "type": "string",
                            "description": "Filter by sender email/name",
                        },
                        "subject": {
                            "type": "string",
                            "description": "Filter by subject keyword",
                        },
                        "since_days": {
                            "type": "integer",
                            "description": "Only search within last N days",
                            "default": 7,
                        },
                        "limit": {
                            "type": "integer",
                            "default": 10,
                        },
                    },
                    "required": [],
                },
            },
            {
                "name": "gmail_send",
                "description": "Send an email from Gmail.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "to": {"type": "string", "description": "Recipient email"},
                        "subject": {"type": "string"},
                        "body": {"type": "string"},
                    },
                    "required": ["to", "subject", "body"],
                },
            },
            {
                "name": "gmail_get_folders",
                "description": "List all Gmail folders/labels.",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
            {
                "name": "gmail_log_summary",
                "description": "Log a summary of a Gmail email for the Secretary's records.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "subject": {"type": "string"},
                        "sender": {"type": "string"},
                        "summary": {"type": "string"},
                        "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                        "action_required": {"type": "boolean", "default": False},
                        "action_items": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["subject", "sender", "summary", "priority"],
                },
            },
        ]

    def gmail_read_inbox(
        self, limit: int = 20, unread_only: bool = False, since_days: int = 1
    ) -> list[dict]:
        """Read emails from Gmail inbox."""
        if not self.is_configured:
            return [{"source": "demo", "note": "Gmail not configured — showing demo data",
                      **e} for e in self._demo_emails()[:limit]]

        try:
            with MailBox(self.IMAP_HOST).login(self.email, self.app_password) as mailbox:
                since_date = datetime.now() - timedelta(days=since_days)
                criteria = AND(date_gte=since_date.date())
                if unread_only:
                    criteria = AND(date_gte=since_date.date(), seen=False)

                emails = []
                for msg in mailbox.fetch(criteria, limit=limit, reverse=True):
                    body_text = msg.text or ""
                    if not body_text and msg.html:
                        body_text = msg.html[:500]

                    emails.append({
                        "source": "gmail",
                        "uid": str(msg.uid),
                        "subject": msg.subject or "(no subject)",
                        "from": str(msg.from_),
                        "to": [str(t) for t in msg.to],
                        "date": msg.date.isoformat() if msg.date else "",
                        "body_preview": body_text[:500],
                        "has_attachments": len(msg.attachments) > 0,
                        "attachment_names": [a.filename for a in msg.attachments],
                        "seen": msg.flags and "\\Seen" in msg.flags,
                    })
                return emails

        except Exception as e:
            return [{"error": f"Gmail connection failed: {str(e)}"}]

    def gmail_search(
        self,
        from_addr: str = "",
        subject: str = "",
        since_days: int = 7,
        limit: int = 10,
    ) -> list[dict]:
        """Search Gmail with filters."""
        if not self.is_configured:
            return [{"source": "demo", "note": "Gmail not configured"}]

        try:
            with MailBox(self.IMAP_HOST).login(self.email, self.app_password) as mailbox:
                since_date = datetime.now() - timedelta(days=since_days)
                criteria = AND(date_gte=since_date.date())
                if from_addr:
                    criteria = AND(date_gte=since_date.date(), from_=from_addr)
                if subject:
                    criteria = AND(date_gte=since_date.date(), subject=subject)

                results = []
                for msg in mailbox.fetch(criteria, limit=limit, reverse=True):
                    results.append({
                        "subject": msg.subject or "(no subject)",
                        "from": str(msg.from_),
                        "date": msg.date.isoformat() if msg.date else "",
                        "body_preview": (msg.text or "")[:300],
                    })
                return results

        except Exception as e:
            return [{"error": f"Gmail search failed: {str(e)}"}]

    def gmail_send(self, to: str, subject: str, body: str) -> dict:
        """Send email via Gmail SMTP."""
        if not self.is_configured:
            return {"status": "demo_mode", "message": f"Would send to {to}: {subject}"}

        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        try:
            msg = MIMEMultipart()
            msg["From"] = self.email
            msg["To"] = to
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP_SSL(self.SMTP_HOST, self.SMTP_PORT) as server:
                server.login(self.email, self.app_password)
                server.send_message(msg)

            return {"status": "sent", "to": to, "subject": subject}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def gmail_get_folders(self) -> list[dict]:
        """List Gmail folders/labels."""
        if not self.is_configured:
            return [{"name": "INBOX"}, {"name": "Sent"}, {"name": "Drafts"}]

        try:
            with MailBox(self.IMAP_HOST).login(self.email, self.app_password) as mailbox:
                return [{"name": f.name, "flags": str(f.flags)} for f in mailbox.folder.list()]
        except Exception as e:
            return [{"error": str(e)}]

    def gmail_log_summary(
        self,
        subject: str,
        sender: str,
        summary: str,
        priority: str,
        action_required: bool = False,
        action_items: list[str] | None = None,
    ) -> dict:
        """Log an email summary."""
        log = json.loads(self.email_log_file.read_text())
        entry = {
            "source": "gmail",
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

    def handle_tool_call(self, tool_name: str, tool_input: dict) -> Any:
        dispatch = {
            "gmail_read_inbox": lambda: self.gmail_read_inbox(**tool_input),
            "gmail_search": lambda: self.gmail_search(**tool_input),
            "gmail_send": lambda: self.gmail_send(**tool_input),
            "gmail_get_folders": lambda: self.gmail_get_folders(**tool_input),
            "gmail_log_summary": lambda: self.gmail_log_summary(**tool_input),
        }
        handler = dispatch.get(tool_name)
        if handler:
            return handler()
        return {"error": f"Unknown Gmail tool: {tool_name}"}

    @staticmethod
    def _demo_emails() -> list[dict]:
        return [
            {
                "uid": "demo_g1",
                "subject": "Family dinner this Friday",
                "from": "family@gmail.com",
                "date": datetime.now().isoformat(),
                "body_preview": "Hi Bandar, reminder about family dinner this Friday at 7pm.",
                "has_attachments": False,
            },
            {
                "uid": "demo_g2",
                "subject": "Your Google Cloud invoice",
                "from": "billing@google.com",
                "date": datetime.now().isoformat(),
                "body_preview": "Your January invoice for Google Cloud services is ready.",
                "has_attachments": True,
            },
        ]
