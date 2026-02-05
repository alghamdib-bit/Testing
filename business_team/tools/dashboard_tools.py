"""
Dashboard tools for the Business Analyst Agent.

Generates HTML dashboards for SPL Digital Channels monitoring
and general business intelligence visualizations.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, BaseLoader

from business_team import config


class DashboardTools:
    """Tools for creating HTML dashboards and reports."""

    def __init__(self):
        self.output_dir = config.OUTPUT_DIR / "dashboards"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.templates_dir = config.TEMPLATES_DIR
        try:
            self.env = Environment(loader=FileSystemLoader(str(self.templates_dir)))
        except Exception:
            self.env = Environment(loader=BaseLoader())

    @staticmethod
    def get_tool_definitions() -> list[dict]:
        return [
            {
                "name": "create_spl_dashboard",
                "description": "Create an HTML dashboard showing SPL Digital Channels KPIs with charts and metrics.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Dashboard title",
                        },
                        "channels_data": {
                            "type": "array",
                            "description": "Array of channel performance data",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "metrics": {
                                        "type": "object",
                                        "description": "Key-value pairs of metric name to value",
                                    },
                                    "status": {
                                        "type": "string",
                                        "enum": ["healthy", "warning", "critical"],
                                    },
                                    "trend": {
                                        "type": "string",
                                        "enum": ["up", "down", "flat"],
                                    },
                                },
                            },
                        },
                        "period": {
                            "type": "string",
                            "description": "Reporting period (e.g., 'Week 5, 2026')",
                        },
                        "filename": {"type": "string"},
                    },
                    "required": ["title", "channels_data", "filename"],
                },
            },
            {
                "name": "create_custom_dashboard",
                "description": "Create a custom HTML dashboard from provided sections and data.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "sections": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "heading": {"type": "string"},
                                    "content_html": {
                                        "type": "string",
                                        "description": "HTML content for this section",
                                    },
                                },
                            },
                        },
                        "filename": {"type": "string"},
                    },
                    "required": ["title", "sections", "filename"],
                },
            },
            {
                "name": "get_spl_channel_data",
                "description": "Get current SPL Digital Channels performance data (demo data if API not configured).",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        ]

    def create_spl_dashboard(
        self,
        title: str,
        channels_data: list[dict],
        filename: str,
        period: str = "",
    ) -> dict:
        """Create an SPL Digital Channels HTML dashboard."""
        if not period:
            period = datetime.now().strftime("Week %W, %Y")

        html = self._render_spl_dashboard(title, channels_data, period)
        filepath = self.output_dir / f"{filename}.html"
        filepath.write_text(html)
        return {"status": "created", "filepath": str(filepath)}

    def create_custom_dashboard(
        self, title: str, sections: list[dict], filename: str
    ) -> dict:
        """Create a custom HTML dashboard."""
        html = self._render_custom_dashboard(title, sections)
        filepath = self.output_dir / f"{filename}.html"
        filepath.write_text(html)
        return {"status": "created", "filepath": str(filepath)}

    def get_spl_channel_data(self) -> list[dict]:
        """Get SPL channel data (demo if API not configured)."""
        if config.SPL_CONFIG.get("api_base_url"):
            return self._fetch_live_data()
        return self._get_demo_channel_data()

    def _render_spl_dashboard(
        self, title: str, channels_data: list[dict], period: str
    ) -> str:
        """Render the SPL dashboard HTML."""
        status_colors = {
            "healthy": "#28a745",
            "warning": "#ffc107",
            "critical": "#dc3545",
        }
        trend_icons = {"up": "&#9650;", "down": "&#9660;", "flat": "&#9654;"}

        channel_cards = ""
        for ch in channels_data:
            status = ch.get("status", "healthy")
            color = status_colors.get(status, "#6c757d")
            trend = ch.get("trend", "flat")
            icon = trend_icons.get(trend, "")
            metrics_html = ""
            for k, v in ch.get("metrics", {}).items():
                metrics_html += f'<div class="metric"><span class="metric-label">{k}</span><span class="metric-value">{v}</span></div>\n'

            channel_cards += f"""
            <div class="channel-card" style="border-left: 4px solid {color};">
                <div class="channel-header">
                    <h3>{ch.get('name', 'Channel')}</h3>
                    <span class="status-badge" style="background: {color};">{status.upper()}</span>
                    <span class="trend-icon">{icon}</span>
                </div>
                <div class="metrics-grid">
                    {metrics_html}
                </div>
            </div>
            """

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f0f2f5; color: #333; }}
        .dashboard-header {{
            background: linear-gradient(135deg, #003d6b, #0066b2);
            color: white; padding: 30px 40px; margin-bottom: 30px;
        }}
        .dashboard-header h1 {{ font-size: 28px; margin-bottom: 5px; }}
        .dashboard-header .period {{ opacity: 0.8; font-size: 14px; }}
        .dashboard-header .timestamp {{ opacity: 0.6; font-size: 12px; margin-top: 5px; }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 0 20px; }}
        .channels-grid {{
            display: grid; grid-template-columns: repeat(auto-fit, minmax(380px, 1fr));
            gap: 20px; margin-bottom: 30px;
        }}
        .channel-card {{
            background: white; border-radius: 8px; padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1); transition: transform 0.2s;
        }}
        .channel-card:hover {{ transform: translateY(-2px); box-shadow: 0 4px 16px rgba(0,0,0,0.15); }}
        .channel-header {{ display: flex; align-items: center; gap: 10px; margin-bottom: 15px; }}
        .channel-header h3 {{ flex: 1; font-size: 18px; color: #003d6b; }}
        .status-badge {{
            color: white; padding: 3px 10px; border-radius: 12px;
            font-size: 11px; font-weight: 600; letter-spacing: 0.5px;
        }}
        .trend-icon {{ font-size: 16px; }}
        .metrics-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
        .metric {{
            display: flex; flex-direction: column; padding: 8px 12px;
            background: #f8f9fa; border-radius: 6px;
        }}
        .metric-label {{ font-size: 11px; color: #6c757d; text-transform: uppercase; letter-spacing: 0.5px; }}
        .metric-value {{ font-size: 18px; font-weight: 600; color: #003d6b; }}
        .footer {{ text-align: center; padding: 20px; color: #999; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="dashboard-header">
        <div class="container">
            <h1>{title}</h1>
            <div class="period">{period}</div>
            <div class="timestamp">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
        </div>
    </div>
    <div class="container">
        <div class="channels-grid">
            {channel_cards}
        </div>
    </div>
    <div class="footer">SPL Digital Channels Dashboard &mdash; Auto-generated by Business Analyst Agent</div>
</body>
</html>"""

    def _render_custom_dashboard(self, title: str, sections: list[dict]) -> str:
        """Render a custom dashboard HTML."""
        sections_html = ""
        for sec in sections:
            sections_html += f"""
            <div class="section">
                <h2>{sec.get('heading', '')}</h2>
                <div class="section-content">{sec.get('content_html', '')}</div>
            </div>
            """

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f0f2f5; color: #333; }}
        .header {{
            background: linear-gradient(135deg, #003d6b, #0066b2);
            color: white; padding: 30px 40px;
        }}
        .header h1 {{ font-size: 28px; }}
        .container {{ max-width: 1200px; margin: 30px auto; padding: 0 20px; }}
        .section {{
            background: white; border-radius: 8px; padding: 25px;
            margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .section h2 {{ color: #003d6b; margin-bottom: 15px; font-size: 20px; border-bottom: 2px solid #e9ecef; padding-bottom: 10px; }}
        .section-content {{ line-height: 1.6; }}
        table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
        th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid #e9ecef; }}
        th {{ background: #f8f9fa; font-weight: 600; color: #003d6b; }}
        .footer {{ text-align: center; padding: 20px; color: #999; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="header"><h1>{title}</h1></div>
    <div class="container">{sections_html}</div>
    <div class="footer">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} &mdash; Business Team Agent System</div>
</body>
</html>"""

    def _fetch_live_data(self) -> list[dict]:
        """Placeholder for live API data fetching."""
        return self._get_demo_channel_data()

    @staticmethod
    def _get_demo_channel_data() -> list[dict]:
        """Demo SPL Digital Channels data."""
        return [
            {
                "name": "Website",
                "status": "healthy",
                "trend": "up",
                "metrics": {
                    "Traffic": "1.2M visits",
                    "Bounce Rate": "32%",
                    "Avg Session": "4m 12s",
                    "Conversion": "3.8%",
                    "Page Load": "1.2s",
                    "Uptime": "99.97%",
                },
            },
            {
                "name": "Mobile App",
                "status": "healthy",
                "trend": "up",
                "metrics": {
                    "Downloads": "45K",
                    "DAU": "128K",
                    "Crash Rate": "0.3%",
                    "Rating": "4.6/5",
                    "Sessions": "892K",
                    "Retention": "72%",
                },
            },
            {
                "name": "Customer Portal",
                "status": "warning",
                "trend": "flat",
                "metrics": {
                    "Active Users": "34K",
                    "Satisfaction": "4.1/5",
                    "Tickets": "1,240",
                    "Avg Resolution": "2.4h",
                    "Self-Service": "67%",
                    "Uptime": "99.8%",
                },
            },
            {
                "name": "API Services",
                "status": "healthy",
                "trend": "up",
                "metrics": {
                    "Requests": "8.4M/day",
                    "Avg Latency": "180ms",
                    "Error Rate": "0.02%",
                    "Uptime": "99.99%",
                    "Partners": "24",
                    "Endpoints": "142",
                },
            },
            {
                "name": "Social Media",
                "status": "healthy",
                "trend": "up",
                "metrics": {
                    "Followers": "285K",
                    "Engagement": "4.7%",
                    "Reach": "1.8M",
                    "Sentiment": "82% +ve",
                    "Response Time": "45min",
                    "Posts/Week": "18",
                },
            },
        ]

    def handle_tool_call(self, tool_name: str, tool_input: dict) -> Any:
        dispatch = {
            "create_spl_dashboard": lambda: self.create_spl_dashboard(**tool_input),
            "create_custom_dashboard": lambda: self.create_custom_dashboard(**tool_input),
            "get_spl_channel_data": lambda: self.get_spl_channel_data(**tool_input),
        }
        handler = dispatch.get(tool_name)
        if handler:
            return handler()
        return {"error": f"Unknown dashboard tool: {tool_name}"}
