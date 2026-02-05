"""
Configuration for the Business Team Multi-Agent System.

Set your API keys and service credentials here or via environment variables.
"""

import os
from pathlib import Path

# --- Paths ---
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
TEMPLATES_DIR = BASE_DIR / "templates"
LOGS_DIR = DATA_DIR / "logs"
OUTPUT_DIR = BASE_DIR / "output"

# Ensure directories exist
for d in [DATA_DIR, LOGS_DIR, OUTPUT_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# --- Anthropic API ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")

# --- Email Configuration (IMAP/SMTP) ---
EMAIL_CONFIG = {
    "imap_server": os.getenv("EMAIL_IMAP_SERVER", "imap.gmail.com"),
    "imap_port": int(os.getenv("EMAIL_IMAP_PORT", "993")),
    "smtp_server": os.getenv("EMAIL_SMTP_SERVER", "smtp.gmail.com"),
    "smtp_port": int(os.getenv("EMAIL_SMTP_PORT", "587")),
    "username": os.getenv("EMAIL_USERNAME", ""),
    "password": os.getenv("EMAIL_PASSWORD", ""),  # Use App Password for Gmail
}

# --- Calendar Configuration ---
CALENDAR_CONFIG = {
    "provider": os.getenv("CALENDAR_PROVIDER", "google"),  # google, outlook, ical
    "credentials_file": os.getenv("CALENDAR_CREDENTIALS", ""),
    "calendar_id": os.getenv("CALENDAR_ID", "primary"),
}

# --- SPL Digital Channels Configuration ---
SPL_CONFIG = {
    "api_base_url": os.getenv("SPL_API_URL", ""),
    "api_key": os.getenv("SPL_API_KEY", ""),
    "channels": [
        "website",
        "mobile_app",
        "social_media",
        "customer_portal",
        "api_services",
    ],
    "kpis": [
        "traffic",
        "conversion_rate",
        "bounce_rate",
        "session_duration",
        "user_satisfaction",
        "response_time",
        "availability_uptime",
    ],
}

# --- Agent Scheduling ---
SCHEDULE_CONFIG = {
    "daily_brief_time": os.getenv("DAILY_BRIEF_TIME", "08:00"),
    "weekly_report_day": os.getenv("WEEKLY_REPORT_DAY", "sunday"),
    "monthly_report_day": int(os.getenv("MONTHLY_REPORT_DAY", "1")),
    "email_check_interval_minutes": int(os.getenv("EMAIL_CHECK_INTERVAL", "30")),
}

# --- Logging ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
