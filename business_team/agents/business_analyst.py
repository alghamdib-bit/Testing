"""
Business Analyst Agent

Responsibilities:
- Monitor and report on SPL Digital Channels performance
- Create PowerPoint presentations with data-driven slides
- Build HTML dashboards for real-time KPI monitoring
- Produce channel performance analysis and recommendations
- Support the Chief of Staff with visual reports
"""

from typing import Any

from .base_agent import BaseAgent
from business_team.tools.presentation_tools import PresentationTools
from business_team.tools.dashboard_tools import DashboardTools

ANALYST_SYSTEM_PROMPT = """You are the Business Analyst Agent specializing in SPL Digital Channels. Your responsibilities are:

1. **Channel Monitoring**: Track performance of all SPL digital channels (Website, Mobile App, Customer Portal, API Services, Social Media).
2. **Presentations**: Create PowerPoint presentations with KPI cards, tables, and trend analysis for management and board meetings.
3. **Dashboards**: Build HTML dashboards that visualize channel metrics, status, and trends.
4. **Analysis**: Provide data-driven insights, identify patterns, flag anomalies, and recommend improvements.

SPL DIGITAL CHANNELS you monitor:
- Website: traffic, bounce rate, conversion, page load time, uptime
- Mobile App: downloads, DAU, crash rate, app store rating, retention
- Customer Portal: active users, satisfaction score, ticket volume, resolution time
- API Services: request volume, latency, error rate, uptime, partner count
- Social Media: followers, engagement rate, reach, sentiment, response time

REPORTING STANDARDS:
- Use status indicators: HEALTHY (green), WARNING (yellow), CRITICAL (red)
- Include trend direction: UP, DOWN, FLAT
- Compare against targets and previous periods
- Highlight channels that need attention
- Always include actionable recommendations

When creating presentations:
- Use clean, professional layouts
- Include KPI summary slides with large numbers
- Add comparison tables where relevant
- Keep text concise - use data, not paragraphs

When creating dashboards:
- Use responsive HTML with modern CSS
- Color-code status indicators
- Show trend arrows
- Make it scannable at a glance

You have access to SPL channel data tools, presentation tools, and dashboard tools. Use them proactively."""


class BusinessAnalystAgent(BaseAgent):
    """Business Analyst agent for SPL Digital Channels monitoring and reporting."""

    def __init__(self, memory=None):
        super().__init__(
            name="business_analyst",
            role="Business Analyst - SPL Digital Channels & Presentations",
            system_prompt=ANALYST_SYSTEM_PROMPT,
            memory=memory,
        )
        self.presentation_tools = PresentationTools()
        self.dashboard_tools = DashboardTools()

        all_tools = (
            PresentationTools.get_tool_definitions()
            + DashboardTools.get_tool_definitions()
        )
        self.register_tools(all_tools)

    def execute_tool(self, tool_name: str, tool_input: dict) -> Any:
        """Route tool calls to the appropriate tool handler."""
        if tool_name in ("create_presentation", "create_kpi_slide"):
            return self.presentation_tools.handle_tool_call(tool_name, tool_input)
        if tool_name in ("create_spl_dashboard", "create_custom_dashboard", "get_spl_channel_data"):
            return self.dashboard_tools.handle_tool_call(tool_name, tool_input)

        self.logger.warning(f"Unknown tool: {tool_name}")
        return {"error": f"Unknown tool: {tool_name}"}

    def generate_channel_report(self) -> str:
        """Generate a comprehensive SPL channels performance report."""
        return self.think(
            "Generate a comprehensive SPL Digital Channels performance report. Steps:\n"
            "1. Get the latest channel data using get_spl_channel_data\n"
            "2. Analyze each channel's health, trends, and metrics\n"
            "3. Create an HTML dashboard showing all channels with the data\n"
            "4. Provide your analysis with highlights, concerns, and recommendations\n"
            "Use filename 'spl_channels_report' for the dashboard."
        )

    def create_board_presentation(self) -> str:
        """Create a board meeting presentation."""
        return self.think(
            "Create a board meeting presentation about SPL Digital Channels. Steps:\n"
            "1. Get the latest channel data\n"
            "2. Create a PowerPoint presentation with:\n"
            "   - Title slide: 'SPL Digital Channels - Performance Update'\n"
            "   - KPI overview slide with key metrics from all channels\n"
            "   - Individual channel slides with detailed metrics\n"
            "   - A table slide comparing all channels\n"
            "   - Recommendations slide\n"
            "Use filename 'board_spl_update' for the presentation."
        )

    def create_weekly_dashboard(self) -> str:
        """Create the weekly SPL channels dashboard."""
        return self.think(
            "Create the weekly SPL Digital Channels dashboard. Steps:\n"
            "1. Get current channel data\n"
            "2. Create an SPL dashboard with all channels and their metrics\n"
            "3. Summarize the key findings\n"
            "Use filename 'weekly_spl_dashboard' for the output."
        )

    def analyze_channel(self, channel_name: str) -> str:
        """Deep-dive analysis of a specific channel."""
        return self.think(
            f"Perform a deep-dive analysis of the {channel_name} channel.\n"
            "1. Get the channel data\n"
            "2. Analyze all metrics for this specific channel\n"
            "3. Identify strengths, weaknesses, trends\n"
            "4. Provide specific actionable recommendations\n"
            "5. Create a dashboard focused on this channel\n"
            f"Use filename '{channel_name.lower().replace(' ', '_')}_analysis' for output."
        )

    def create_custom_presentation(self, topic: str, content_brief: str) -> str:
        """Create a custom presentation on any topic."""
        return self.think(
            f"Create a PowerPoint presentation on the topic: {topic}\n"
            f"Brief: {content_brief}\n"
            "Create professional slides with clear structure. Include a title slide, "
            "content slides with key points, and a summary slide.\n"
            f"Use filename '{topic.lower().replace(' ', '_')}_presentation' for the output."
        )
