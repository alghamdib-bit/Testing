"""
SPL Exchange Connector — Real email access via Exchange Web Services (EWS).

Handles reading, searching, and sending emails through SPL's on-premise
Exchange server (splonline.com.sa). Uses exchangelib for EWS access with
NTLM/Basic auth. Falls back to IMAP if EWS is unavailable, and to demo
data if no credentials are configured.

Authentication notes:
  - On-premise Exchange with MFA: EWS via NTLM often bypasses MFA
  - If EWS fails, IMAP on port 143 is available as fallback
  - App password can be used if the org provides one
"""

import json
import os
from datetime import datetime, timedelta
from typing import Any

from dotenv import load_dotenv

load_dotenv()

try:
    from exchangelib import (
        Account,
        Configuration,
        Credentials,
        DELEGATE,
        EWSDateTime,
        EWSTimeZone,
        Mailbox,
        Message,
        HTMLBody,
    )
    EXCHANGELIB_AVAILABLE = True
except BaseException:
    EXCHANGELIB_AVAILABLE = False

try:
    from imap_tools import MailBox, AND
    IMAP_TOOLS_AVAILABLE = True
except BaseException:
    IMAP_TOOLS_AVAILABLE = False

from business_team import config


class ExchangeConnector:
    """SPL Exchange email access via EWS (primary) or IMAP (fallback)."""

    EWS_SERVER = "mail.splonline.com.sa"
    IMAP_HOST = "splonline.com.sa"
    IMAP_PORT = 143
    SMTP_HOST = "splonline.com.sa"
    SMTP_PORT = 587
    TIMEZONE = "Asia/Riyadh"

    def __init__(self):
        self.email = os.getenv("SPL_EMAIL", "")
        self.password = os.getenv("SPL_PASSWORD", "")
        self.display_name = os.getenv("SPL_DISPLAY_NAME", "")
        self.is_configured = bool(self.email and self.password)
        self.email_log_file = config.DATA_DIR / "spl_email_log.json"
        if not self.email_log_file.exists():
            self.email_log_file.write_text("[]")
        self._account = None

    def _get_ews_account(self):
        """Get or create the EWS account connection."""
        if self._account:
            return self._account

        if not self.is_configured or not EXCHANGELIB_AVAILABLE:
            return None

        try:
            creds = Credentials(username=self.email, password=self.password)
            ews_config = Configuration(
                server=self.EWS_SERVER,
                credentials=creds,
            )
            self._account = Account(
                primary_smtp_address=self.email,
                config=ews_config,
                autodiscover=False,
                access_type=DELEGATE,
            )
            return self._account
        except Exception:
            # Try with autodiscover as fallback
            try:
                creds = Credentials(username=self.email, password=self.password)
                self._account = Account(
                    primary_smtp_address=self.email,
                    credentials=creds,
                    autodiscover=True,
                    access_type=DELEGATE,
                )
                return self._account
            except Exception:
                return None

    @staticmethod
    def get_tool_definitions() -> list[dict]:
        return [
            {
                "name": "spl_read_inbox",
                "description": "Read recent emails from SPL Exchange work inbox.",
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
                "name": "spl_search_emails",
                "description": "Search SPL Exchange emails by sender, subject, or keywords.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "from_addr": {
                            "type": "string",
                            "description": "Filter by sender email or name",
                        },
                        "subject": {
                            "type": "string",
                            "description": "Filter by subject keyword",
                        },
                        "body_contains": {
                            "type": "string",
                            "description": "Search for text in email body",
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
                "name": "spl_send_email",
                "description": "Send an email from SPL Exchange work account.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "to": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Recipient email addresses",
                        },
                        "subject": {"type": "string"},
                        "body": {"type": "string", "description": "Email body (plain text or HTML)"},
                        "cc": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "CC recipients",
                        },
                        "is_html": {
                            "type": "boolean",
                            "description": "Whether body is HTML",
                            "default": False,
                        },
                    },
                    "required": ["to", "subject", "body"],
                },
            },
            {
                "name": "spl_get_folders",
                "description": "List all folders in SPL Exchange mailbox.",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
            {
                "name": "spl_log_summary",
                "description": "Log a summary of an SPL work email for the Secretary's records.",
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
                        "category": {
                            "type": "string",
                            "description": "Work category (e.g., project, hr, it, finance, meeting)",
                        },
                    },
                    "required": ["subject", "sender", "summary", "priority"],
                },
            },
            {
                "name": "spl_get_calendar",
                "description": "Get upcoming calendar events from SPL Exchange calendar.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "days_ahead": {
                            "type": "integer",
                            "description": "Number of days ahead to look",
                            "default": 1,
                        },
                    },
                    "required": [],
                },
            },
        ]

    # ---- EWS Methods ----

    def spl_read_inbox(
        self, limit: int = 20, unread_only: bool = False, since_days: int = 1
    ) -> list[dict]:
        """Read emails from SPL Exchange inbox."""
        account = self._get_ews_account()
        if account:
            return self._ews_read_inbox(account, limit, unread_only, since_days)

        # Fallback to IMAP
        if self.is_configured and IMAP_TOOLS_AVAILABLE:
            return self._imap_read_inbox(limit, unread_only, since_days)

        return [{"source": "demo", "note": "SPL Exchange not configured — showing demo data",
                 **e} for e in self._demo_emails()[:limit]]

    def _ews_read_inbox(
        self, account, limit: int, unread_only: bool, since_days: int
    ) -> list[dict]:
        """Read inbox via EWS."""
        try:
            tz = EWSTimeZone.timezone(self.TIMEZONE)
            since = EWSDateTime.now(tz=tz) - timedelta(days=since_days)

            inbox = account.inbox
            if unread_only:
                items = inbox.filter(
                    datetime_received__gte=since, is_read=False
                ).order_by("-datetime_received")[:limit]
            else:
                items = inbox.filter(
                    datetime_received__gte=since
                ).order_by("-datetime_received")[:limit]

            emails = []
            for item in items:
                body_text = ""
                if item.text_body:
                    body_text = item.text_body[:500]
                elif item.body:
                    body_text = str(item.body)[:500]

                emails.append({
                    "source": "spl_exchange",
                    "id": str(item.id) if item.id else "",
                    "subject": item.subject or "(no subject)",
                    "from": str(item.sender.email_address) if item.sender else "",
                    "from_name": str(item.sender.name) if item.sender and item.sender.name else "",
                    "to": [str(r.email_address) for r in (item.to_recipients or [])],
                    "cc": [str(r.email_address) for r in (item.cc_recipients or [])],
                    "date": item.datetime_received.isoformat() if item.datetime_received else "",
                    "body_preview": body_text,
                    "has_attachments": item.has_attachments or False,
                    "is_read": item.is_read or False,
                    "importance": str(item.importance) if item.importance else "normal",
                })
            return emails

        except Exception as e:
            return [{"error": f"EWS read failed: {str(e)}"}]

    def _imap_read_inbox(
        self, limit: int, unread_only: bool, since_days: int
    ) -> list[dict]:
        """Read inbox via IMAP fallback."""
        try:
            with MailBox(self.IMAP_HOST, self.IMAP_PORT).login(
                self.email, self.password
            ) as mailbox:
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
                        "source": "spl_imap",
                        "uid": str(msg.uid),
                        "subject": msg.subject or "(no subject)",
                        "from": str(msg.from_),
                        "to": [str(t) for t in msg.to],
                        "date": msg.date.isoformat() if msg.date else "",
                        "body_preview": body_text[:500],
                        "has_attachments": len(msg.attachments) > 0,
                    })
                return emails

        except Exception as e:
            return [{"error": f"IMAP read failed: {str(e)}"}]

    def spl_search_emails(
        self,
        from_addr: str = "",
        subject: str = "",
        body_contains: str = "",
        since_days: int = 7,
        limit: int = 10,
    ) -> list[dict]:
        """Search SPL Exchange emails."""
        account = self._get_ews_account()
        if not account:
            if self.is_configured and IMAP_TOOLS_AVAILABLE:
                return self._imap_search(from_addr, subject, since_days, limit)
            return [{"source": "demo", "note": "SPL Exchange not configured"}]

        try:
            tz = EWSTimeZone.timezone(self.TIMEZONE)
            since = EWSDateTime.now(tz=tz) - timedelta(days=since_days)

            queryset = account.inbox.filter(datetime_received__gte=since)
            if from_addr:
                queryset = queryset.filter(sender__email_address__icontains=from_addr)
            if subject:
                queryset = queryset.filter(subject__icontains=subject)
            if body_contains:
                queryset = queryset.filter(body__icontains=body_contains)

            results = []
            for item in queryset.order_by("-datetime_received")[:limit]:
                results.append({
                    "source": "spl_exchange",
                    "subject": item.subject or "(no subject)",
                    "from": str(item.sender.email_address) if item.sender else "",
                    "date": item.datetime_received.isoformat() if item.datetime_received else "",
                    "body_preview": (item.text_body or "")[:300],
                    "importance": str(item.importance) if item.importance else "normal",
                })
            return results

        except Exception as e:
            return [{"error": f"EWS search failed: {str(e)}"}]

    def _imap_search(
        self, from_addr: str, subject: str, since_days: int, limit: int
    ) -> list[dict]:
        """Search via IMAP fallback."""
        try:
            with MailBox(self.IMAP_HOST, self.IMAP_PORT).login(
                self.email, self.password
            ) as mailbox:
                since_date = datetime.now() - timedelta(days=since_days)
                criteria = AND(date_gte=since_date.date())
                if from_addr:
                    criteria = AND(date_gte=since_date.date(), from_=from_addr)
                if subject:
                    criteria = AND(date_gte=since_date.date(), subject=subject)

                results = []
                for msg in mailbox.fetch(criteria, limit=limit, reverse=True):
                    results.append({
                        "source": "spl_imap",
                        "subject": msg.subject or "(no subject)",
                        "from": str(msg.from_),
                        "date": msg.date.isoformat() if msg.date else "",
                        "body_preview": (msg.text or "")[:300],
                    })
                return results

        except Exception as e:
            return [{"error": f"IMAP search failed: {str(e)}"}]

    def spl_send_email(
        self,
        to: list[str],
        subject: str,
        body: str,
        cc: list[str] | None = None,
        is_html: bool = False,
    ) -> dict:
        """Send email via SPL Exchange."""
        account = self._get_ews_account()
        if not account:
            if self.is_configured:
                return self._smtp_send(to, subject, body, cc)
            return {"status": "demo_mode", "message": f"Would send to {to}: {subject}"}

        try:
            msg = Message(
                account=account,
                subject=subject,
                body=HTMLBody(body) if is_html else body,
                to_recipients=[Mailbox(email_address=addr) for addr in to],
            )
            if cc:
                msg.cc_recipients = [Mailbox(email_address=addr) for addr in cc]

            msg.send()
            return {
                "status": "sent",
                "to": to,
                "cc": cc or [],
                "subject": subject,
                "via": "ews",
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _smtp_send(
        self, to: list[str], subject: str, body: str, cc: list[str] | None = None
    ) -> dict:
        """Send via SMTP fallback."""
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        try:
            msg = MIMEMultipart()
            msg["From"] = f"{self.display_name} <{self.email}>"
            msg["To"] = ", ".join(to)
            msg["Subject"] = subject
            if cc:
                msg["Cc"] = ", ".join(cc)
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(self.SMTP_HOST, self.SMTP_PORT) as server:
                server.starttls()
                server.login(self.email, self.password)
                all_recipients = to + (cc or [])
                server.send_message(msg, to_addrs=all_recipients)

            return {"status": "sent", "to": to, "subject": subject, "via": "smtp"}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def spl_get_folders(self) -> list[dict]:
        """List Exchange mailbox folders."""
        account = self._get_ews_account()
        if not account:
            return [
                {"name": "Inbox", "source": "demo"},
                {"name": "Sent Items", "source": "demo"},
                {"name": "Drafts", "source": "demo"},
            ]

        try:
            folders = []
            for folder in account.root.walk():
                folders.append({
                    "name": folder.name,
                    "total_count": folder.total_count or 0,
                    "unread_count": folder.unread_count or 0,
                })
            return folders

        except Exception as e:
            return [{"error": str(e)}]

    def spl_log_summary(
        self,
        subject: str,
        sender: str,
        summary: str,
        priority: str,
        action_required: bool = False,
        action_items: list[str] | None = None,
        category: str = "",
    ) -> dict:
        """Log an SPL email summary."""
        log = json.loads(self.email_log_file.read_text())
        entry = {
            "source": "spl_exchange",
            "subject": subject,
            "sender": sender,
            "summary": summary,
            "priority": priority,
            "action_required": action_required,
            "action_items": action_items or [],
            "category": category,
            "logged_at": datetime.now().isoformat(),
        }
        log.append(entry)
        self.email_log_file.write_text(json.dumps(log, indent=2))
        return {"status": "logged", "entry": entry}

    def spl_get_calendar(self, days_ahead: int = 1) -> list[dict]:
        """Get upcoming Exchange calendar events."""
        account = self._get_ews_account()
        if not account:
            return self._demo_calendar()

        try:
            tz = EWSTimeZone.timezone(self.TIMEZONE)
            now = EWSDateTime.now(tz=tz)
            end = now + timedelta(days=days_ahead)

            events = []
            for item in account.calendar.view(start=now, end=end):
                events.append({
                    "source": "spl_exchange",
                    "subject": item.subject or "(no title)",
                    "start": item.start.isoformat() if item.start else "",
                    "end": item.end.isoformat() if item.end else "",
                    "location": str(item.location) if item.location else "",
                    "organizer": str(item.organizer.email_address) if item.organizer else "",
                    "is_all_day": item.is_all_day or False,
                    "required_attendees": [
                        str(a.mailbox.email_address)
                        for a in (item.required_attendees or [])
                        if a.mailbox
                    ],
                })
            return events

        except Exception as e:
            return [{"error": f"EWS calendar failed: {str(e)}"}]

    def handle_tool_call(self, tool_name: str, tool_input: dict) -> Any:
        dispatch = {
            "spl_read_inbox": lambda: self.spl_read_inbox(**tool_input),
            "spl_search_emails": lambda: self.spl_search_emails(**tool_input),
            "spl_send_email": lambda: self.spl_send_email(**tool_input),
            "spl_get_folders": lambda: self.spl_get_folders(**tool_input),
            "spl_log_summary": lambda: self.spl_log_summary(**tool_input),
            "spl_get_calendar": lambda: self.spl_get_calendar(**tool_input),
        }
        handler = dispatch.get(tool_name)
        if handler:
            return handler()
        return {"error": f"Unknown SPL Exchange tool: {tool_name}"}

    @staticmethod
    def _demo_emails() -> list[dict]:
        now = datetime.now()
        return [
            {
                "uid": "demo_spl1",
                "subject": "Weekly IT Status Report",
                "from": "it.support@splonline.com.sa",
                "from_name": "IT Support",
                "date": now.isoformat(),
                "body_preview": "Dear Team, please find attached the weekly IT status report. "
                                "All systems are operational. Network uptime: 99.8%.",
                "importance": "normal",
                "is_read": True,
            },
            {
                "uid": "demo_spl2",
                "subject": "Urgent: Digital Channel Downtime Alert",
                "from": "monitoring@splonline.com.sa",
                "from_name": "System Monitor",
                "date": now.isoformat(),
                "body_preview": "Alert: Mobile app experiencing intermittent connectivity issues. "
                                "Engineering team is investigating. ETA for resolution: 2 hours.",
                "importance": "high",
                "is_read": False,
            },
            {
                "uid": "demo_spl3",
                "subject": "Project Alpha — Sprint Review Meeting",
                "from": "pm.office@splonline.com.sa",
                "from_name": "PMO",
                "date": (now - timedelta(hours=3)).isoformat(),
                "body_preview": "Reminder: Sprint review meeting today at 2:00 PM. "
                                "Please prepare your team's progress updates.",
                "importance": "normal",
                "is_read": True,
            },
        ]

    @staticmethod
    def _demo_calendar() -> list[dict]:
        today = datetime.now().strftime("%Y-%m-%d")
        return [
            {
                "source": "demo",
                "subject": "Daily Standup",
                "start": f"{today}T09:00:00",
                "end": f"{today}T09:30:00",
                "location": "Teams Meeting",
                "is_all_day": False,
            },
            {
                "source": "demo",
                "subject": "Sprint Review",
                "start": f"{today}T14:00:00",
                "end": f"{today}T15:00:00",
                "location": "Conference Room B",
                "is_all_day": False,
            },
            {
                "source": "demo",
                "subject": "Digital Channels Weekly Sync",
                "start": f"{today}T16:00:00",
                "end": f"{today}T16:30:00",
                "location": "Teams Meeting",
                "is_all_day": False,
            },
        ]
