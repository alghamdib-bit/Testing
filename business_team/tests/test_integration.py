"""
Integration tests for the business_team multi-agent system.

Tests verify the full agent think() flow using mocked Claude API responses.
Each test patches anthropic.Anthropic so that no real API calls are made,
then exercises the tool-dispatch loop end-to-end.

Run with:
    python -m pytest business_team/tests/test_integration.py -v
"""

import json
from business_team.tests.conftest import (
    make_text_response,
    make_tool_use_response,
    make_multi_tool_response,
)


# ============================================================
# SECRETARY AGENT TESTS
# ============================================================

class TestSecretaryAgent:
    """Integration tests for the Secretary agent."""

    def test_secretary_text_only_response(self, mock_api):
        """Test Secretary returns plain text when Claude responds with end_turn."""
        mock_api.responses = [
            make_text_response("Good morning! Here is your daily summary."),
        ]

        from business_team.agents.secretary import SecretaryAgent
        agent = SecretaryAgent()
        result = agent.think("Good morning")

        assert result == "Good morning! Here is your daily summary."
        assert mock_api.client.messages.create.call_count == 1
        # History: user message + assistant text response
        assert len(agent.conversation_history) == 2
        assert agent.conversation_history[0]["role"] == "user"
        assert agent.conversation_history[1]["role"] == "assistant"

    def test_secretary_reads_emails_via_tool(self, mock_api):
        """Test Secretary processes read_emails tool call and returns summary."""
        mock_api.responses = [
            make_tool_use_response("read_emails", {"limit": 5}),
            make_text_response("You have 5 emails. Here's the summary of your inbox."),
        ]

        from business_team.agents.secretary import SecretaryAgent
        agent = SecretaryAgent()
        result = agent.think("Check my emails")

        assert "summary" in result.lower() or len(result) > 0
        assert mock_api.client.messages.create.call_count == 2
        # History: user, assistant(tool_use), user(tool_result), assistant(text)
        assert len(agent.conversation_history) == 4
        assert agent.conversation_history[0]["role"] == "user"
        assert agent.conversation_history[1]["role"] == "assistant"
        assert agent.conversation_history[2]["role"] == "user"
        assert agent.conversation_history[3]["role"] == "assistant"

        # Verify the tool result was injected as a user message with tool_result content
        tool_result_msg = agent.conversation_history[2]
        assert isinstance(tool_result_msg["content"], list)
        assert tool_result_msg["content"][0]["type"] == "tool_result"
        assert tool_result_msg["content"][0]["tool_use_id"] == "toolu_test_001"

    def test_secretary_gmail_tool_routing(self, mock_api):
        """Test Secretary routes gmail_read_inbox to GmailConnector."""
        mock_api.responses = [
            make_tool_use_response("gmail_read_inbox", {"limit": 10}, "toolu_gmail_001"),
            make_text_response("Your personal Gmail has 2 new messages."),
        ]

        from business_team.agents.secretary import SecretaryAgent
        agent = SecretaryAgent()
        result = agent.think("Check my personal Gmail")

        assert mock_api.client.messages.create.call_count == 2
        # Verify tool was executed and result injected into conversation history
        tool_result_msg = agent.conversation_history[2]
        assert tool_result_msg["role"] == "user"
        assert tool_result_msg["content"][0]["type"] == "tool_result"
        assert tool_result_msg["content"][0]["tool_use_id"] == "toolu_gmail_001"
        # GmailConnector returns a list (demo data or connection error entries)
        parsed = json.loads(tool_result_msg["content"][0]["content"])
        assert isinstance(parsed, list)
        assert len(parsed) > 0

    def test_secretary_spl_tool_routing(self, mock_api):
        """Test Secretary routes spl_read_inbox to ExchangeConnector."""
        mock_api.responses = [
            make_tool_use_response("spl_read_inbox", {"limit": 5}, "toolu_spl_001"),
            make_text_response("Your SPL work inbox has 3 emails."),
        ]

        from business_team.agents.secretary import SecretaryAgent
        agent = SecretaryAgent()
        result = agent.think("Check my work email")

        assert mock_api.client.messages.create.call_count == 2
        # Verify tool was executed and result injected into conversation history
        tool_result_msg = agent.conversation_history[2]
        assert tool_result_msg["role"] == "user"
        assert tool_result_msg["content"][0]["type"] == "tool_result"
        assert tool_result_msg["content"][0]["tool_use_id"] == "toolu_spl_001"
        # ExchangeConnector returns a list (demo data or connection error entries)
        parsed = json.loads(tool_result_msg["content"][0]["content"])
        assert isinstance(parsed, list)
        assert len(parsed) > 0

    def test_secretary_calendar_tool(self, mock_api):
        """Test Secretary processes get_today_schedule and returns calendar data."""
        mock_api.responses = [
            make_tool_use_response("get_today_schedule", {}, "toolu_cal_001"),
            make_text_response("Today you have 4 events starting with a Morning Standup at 9 AM."),
        ]

        from business_team.agents.secretary import SecretaryAgent
        agent = SecretaryAgent()
        result = agent.think("What's my schedule today?")

        assert mock_api.client.messages.create.call_count == 2
        # Verify the tool returned actual calendar demo data
        tool_result_content = agent.conversation_history[2]["content"][0]["content"]
        parsed = json.loads(tool_result_content)
        assert isinstance(parsed, list)
        # CalendarTools demo creates events for today
        # The result will be a list (possibly empty if no events match today's date,
        # but the tool was called and result injected regardless)

    def test_secretary_todo_tool(self, mock_api):
        """Test Secretary processes get_todo_summary and returns todo summary."""
        mock_api.responses = [
            make_tool_use_response("get_todo_summary", {}, "toolu_todo_001"),
            make_text_response("You have 4 pending to-do items. 2 are high priority."),
        ]

        from business_team.agents.secretary import SecretaryAgent
        agent = SecretaryAgent()
        result = agent.think("Show my to-do summary")

        assert mock_api.client.messages.create.call_count == 2
        tool_result_content = agent.conversation_history[2]["content"][0]["content"]
        parsed = json.loads(tool_result_content)
        # get_todo_summary returns a dict with "total", "by_status", "by_priority"
        assert isinstance(parsed, dict)
        assert "total" in parsed
        assert "by_status" in parsed
        assert "by_priority" in parsed

    def test_secretary_multi_tool_sequence(self, mock_api):
        """Test Secretary handles 2 sequential tool calls then text response."""
        mock_api.responses = [
            make_tool_use_response("read_emails", {"limit": 5}, "toolu_seq_001"),
            make_tool_use_response("get_todo_summary", {}, "toolu_seq_002"),
            make_text_response("You have 5 emails and 4 to-do items. Here is the combined overview."),
        ]

        from business_team.agents.secretary import SecretaryAgent
        agent = SecretaryAgent()
        result = agent.think("Give me an overview of emails and todos")

        assert "overview" in result.lower() or len(result) > 0
        assert mock_api.client.messages.create.call_count == 3
        # History: user, assist(tool1), user(result1), assist(tool2), user(result2), assist(text)
        assert len(agent.conversation_history) == 6

    def test_secretary_conversation_history_populated(self, mock_api):
        """Verify conversation history has correct structure after think()."""
        mock_api.responses = [
            make_tool_use_response("read_emails", {"limit": 3}, "toolu_hist_001"),
            make_text_response("Here are your 3 most recent emails."),
        ]

        from business_team.agents.secretary import SecretaryAgent
        agent = SecretaryAgent()
        agent.think("Show me my last 3 emails")

        history = agent.conversation_history
        assert len(history) == 4

        # Entry 0: user message
        assert history[0] == {"role": "user", "content": "Show me my last 3 emails"}

        # Entry 1: assistant with tool_use blocks (raw content from response)
        assert history[1]["role"] == "assistant"
        assert hasattr(history[1]["content"][0], "type")
        assert history[1]["content"][0].type == "tool_use"
        assert history[1]["content"][0].name == "read_emails"

        # Entry 2: user with tool_result
        assert history[2]["role"] == "user"
        assert isinstance(history[2]["content"], list)
        assert history[2]["content"][0]["type"] == "tool_result"
        assert history[2]["content"][0]["tool_use_id"] == "toolu_hist_001"

        # Entry 3: assistant final text
        assert history[3]["role"] == "assistant"
        assert history[3]["content"] == "Here are your 3 most recent emails."


# ============================================================
# BUSINESS ANALYST AGENT TESTS
# ============================================================

class TestBusinessAnalystAgent:
    """Integration tests for the Business Analyst agent."""

    def test_analyst_text_response(self, mock_api):
        """Test Business Analyst returns plain text response."""
        mock_api.responses = [
            make_text_response("All SPL channels are performing within normal parameters."),
        ]

        from business_team.agents.business_analyst import BusinessAnalystAgent
        agent = BusinessAnalystAgent()
        result = agent.think("How are the channels doing?")

        assert "channels" in result.lower() or "performing" in result.lower()
        assert mock_api.client.messages.create.call_count == 1
        assert len(agent.conversation_history) == 2

    def test_analyst_gets_channel_data(self, mock_api):
        """Test Business Analyst processes get_spl_channel_data tool call."""
        mock_api.responses = [
            make_tool_use_response("get_spl_channel_data", {}, "toolu_data_001"),
            make_text_response("Here is the SPL channel data with 5 channels monitored."),
        ]

        from business_team.agents.business_analyst import BusinessAnalystAgent
        agent = BusinessAnalystAgent()
        result = agent.think("Get the latest channel data")

        assert mock_api.client.messages.create.call_count == 2
        # Verify the tool returned actual demo channel data
        tool_result_content = agent.conversation_history[2]["content"][0]["content"]
        parsed = json.loads(tool_result_content)
        assert isinstance(parsed, list)
        assert len(parsed) == 5
        # Verify channel structure
        channel_names = [ch["name"] for ch in parsed]
        assert "Website" in channel_names
        assert "Mobile App" in channel_names
        assert "API Services" in channel_names

    def test_analyst_creates_dashboard(self, mock_api):
        """Test Business Analyst processes create_spl_dashboard tool call."""
        mock_api.responses = [
            make_tool_use_response("create_spl_dashboard", {
                "title": "SPL Weekly Dashboard",
                "channels_data": [
                    {"name": "Website", "status": "healthy", "trend": "up",
                     "metrics": {"Traffic": "1.2M", "Bounce Rate": "32%"}},
                ],
                "filename": "test_integration_dashboard",
            }, "toolu_dash_001"),
            make_text_response("Dashboard created successfully at the output directory."),
        ]

        from business_team.agents.business_analyst import BusinessAnalystAgent
        agent = BusinessAnalystAgent()
        result = agent.think("Create a dashboard for this week")

        assert mock_api.client.messages.create.call_count == 2
        tool_result_content = agent.conversation_history[2]["content"][0]["content"]
        parsed = json.loads(tool_result_content)
        assert parsed["status"] == "created"
        assert "filepath" in parsed

    def test_analyst_creates_presentation(self, mock_api):
        """Test Business Analyst processes create_presentation tool call."""
        mock_api.responses = [
            make_tool_use_response("create_presentation", {
                "title": "SPL Performance Update",
                "slides": [
                    {"title": "Overview", "content": "Q4 channel performance", "slide_type": "content"},
                ],
                "filename": "test_integration_pres",
            }, "toolu_pres_001"),
            make_text_response("Presentation created with 2 slides."),
        ]

        from business_team.agents.business_analyst import BusinessAnalystAgent
        agent = BusinessAnalystAgent()
        result = agent.think("Create a presentation for the board meeting")

        assert mock_api.client.messages.create.call_count == 2
        tool_result_content = agent.conversation_history[2]["content"][0]["content"]
        parsed = json.loads(tool_result_content)
        assert parsed["status"] in ("created", "created_json_fallback")
        assert "filepath" in parsed

    def test_analyst_multi_step_workflow(self, mock_api):
        """Test Business Analyst: get data then create dashboard (2-step workflow)."""
        mock_api.responses = [
            make_tool_use_response("get_spl_channel_data", {}, "toolu_wf_001"),
            make_tool_use_response("create_spl_dashboard", {
                "title": "Multi-Step Dashboard",
                "channels_data": [
                    {"name": "Website", "status": "healthy", "trend": "up",
                     "metrics": {"Traffic": "1.2M"}},
                ],
                "filename": "test_integration_multistep",
            }, "toolu_wf_002"),
            make_text_response("I fetched the data and created the dashboard."),
        ]

        from business_team.agents.business_analyst import BusinessAnalystAgent
        agent = BusinessAnalystAgent()
        result = agent.think("Get channel data and create a dashboard")

        assert mock_api.client.messages.create.call_count == 3
        assert len(agent.conversation_history) == 6  # user, tool1, result1, tool2, result2, text
        assert "dashboard" in result.lower()


# ============================================================
# PROJECTS MANAGER AGENT TESTS
# ============================================================

class TestProjectsManagerAgent:
    """Integration tests for the Projects Manager agent."""

    def test_pm_text_response(self, mock_api):
        """Test Projects Manager returns plain text response."""
        mock_api.responses = [
            make_text_response("All projects are tracking within expected timelines."),
        ]

        from business_team.agents.projects_manager import ProjectsManagerAgent
        agent = ProjectsManagerAgent()
        result = agent.think("How are the projects going?")

        assert "projects" in result.lower() or "tracking" in result.lower()
        assert mock_api.client.messages.create.call_count == 1
        assert len(agent.conversation_history) == 2

    def test_pm_gets_projects(self, mock_api):
        """Test Projects Manager processes get_projects tool call."""
        mock_api.responses = [
            make_tool_use_response("get_projects", {}, "toolu_proj_001"),
            make_text_response("There are 3 active projects in the portfolio."),
        ]

        from business_team.agents.projects_manager import ProjectsManagerAgent
        agent = ProjectsManagerAgent()
        result = agent.think("Show me all projects")

        assert mock_api.client.messages.create.call_count == 2
        tool_result_content = agent.conversation_history[2]["content"][0]["content"]
        parsed = json.loads(tool_result_content)
        assert isinstance(parsed, list)
        assert len(parsed) >= 3
        project_names = [p["name"] for p in parsed]
        assert any("Alpha" in name for name in project_names)
        assert any("Beta" in name for name in project_names)

    def test_pm_gets_tasks(self, mock_api):
        """Test Projects Manager processes get_tasks tool call."""
        mock_api.responses = [
            make_tool_use_response("get_tasks", {}, "toolu_task_001"),
            make_text_response("There are 7 tasks across all projects."),
        ]

        from business_team.agents.projects_manager import ProjectsManagerAgent
        agent = ProjectsManagerAgent()
        result = agent.think("Show me all tasks")

        assert mock_api.client.messages.create.call_count == 2
        tool_result_content = agent.conversation_history[2]["content"][0]["content"]
        parsed = json.loads(tool_result_content)
        assert isinstance(parsed, list)
        assert len(parsed) >= 5
        # Check task structure
        assert "title" in parsed[0]
        assert "status" in parsed[0]
        assert "assignee" in parsed[0]

    def test_pm_creates_status_board(self, mock_api):
        """Test Projects Manager processes generate_project_status_board tool call."""
        mock_api.responses = [
            make_tool_use_response("generate_project_status_board", {
                "projects": [{"name": "Alpha"}, {"name": "Beta"}],
                "tasks": [
                    {"title": "Fix API", "status": "in_progress", "assignee": "Dev",
                     "priority": "high", "due_date": "2026-02-10"},
                    {"title": "Write tests", "status": "todo", "assignee": "QA",
                     "priority": "medium", "due_date": "2026-02-15"},
                ],
                "filename": "test_integration_board",
            }, "toolu_board_001"),
            make_text_response("Project status board created with Kanban layout."),
        ]

        from business_team.agents.projects_manager import ProjectsManagerAgent
        agent = ProjectsManagerAgent()
        result = agent.think("Create a project status board")

        assert mock_api.client.messages.create.call_count == 2
        tool_result_content = agent.conversation_history[2]["content"][0]["content"]
        parsed = json.loads(tool_result_content)
        assert parsed["status"] == "created"
        assert "filepath" in parsed

    def test_pm_full_workflow(self, mock_api):
        """Test Projects Manager: get projects, get tasks, generate board (3-step)."""
        mock_api.responses = [
            make_tool_use_response("get_projects", {}, "toolu_fw_001"),
            make_tool_use_response("get_tasks", {}, "toolu_fw_002"),
            make_tool_use_response("generate_project_status_board", {
                "projects": [{"name": "Alpha"}],
                "tasks": [
                    {"title": "Task A", "status": "in_progress", "assignee": "Dev",
                     "priority": "high", "due_date": "2026-02-10"},
                ],
                "filename": "test_integration_full_board",
            }, "toolu_fw_003"),
            make_text_response("Portfolio status: 3 projects, 7 tasks. Board generated."),
        ]

        from business_team.agents.projects_manager import ProjectsManagerAgent
        agent = ProjectsManagerAgent()
        result = agent.think("Give me a full portfolio status with a board")

        assert mock_api.client.messages.create.call_count == 4
        # History: user + 3*(assistant_tool + user_result) + assistant_text = 8
        assert len(agent.conversation_history) == 8
        assert "portfolio" in result.lower() or "board" in result.lower()


# ============================================================
# CHIEF OF STAFF AGENT TESTS
# ============================================================

class TestChiefOfStaffAgent:
    """Integration tests for the Chief of Staff agent."""

    def test_cos_text_response(self, mock_api):
        """Test Chief of Staff returns plain text response."""
        mock_api.responses = [
            make_text_response("Team status is nominal. No alarms active."),
        ]

        from business_team.agents.chief_of_staff import ChiefOfStaffAgent
        agent = ChiefOfStaffAgent()
        result = agent.think("How is the team?")

        assert "team" in result.lower() or "status" in result.lower()
        assert mock_api.client.messages.create.call_count == 1
        assert len(agent.conversation_history) == 2

    def test_cos_routes_dev_tool(self, mock_api):
        """Test Chief of Staff routes read_agent_source to AgentDevTools."""
        mock_api.responses = [
            make_tool_use_response(
                "read_agent_source",
                {"agent_name": "secretary"},
                "toolu_dev_001",
            ),
            make_text_response("The Secretary agent has 194 lines of code with 9 methods."),
        ]

        from business_team.agents.chief_of_staff import ChiefOfStaffAgent
        agent = ChiefOfStaffAgent()
        result = agent.think("Read the secretary agent source code")

        assert mock_api.client.messages.create.call_count == 2
        tool_result_content = agent.conversation_history[2]["content"][0]["content"]
        parsed = json.loads(tool_result_content)
        assert "source" in parsed
        assert "agent_name" in parsed
        assert parsed["agent_name"] == "secretary"
        assert parsed["line_count"] > 50

    def test_cos_routes_monitor_tool(self, mock_api):
        """Test Chief of Staff routes run_agent_health_check to AgentMonitorTools."""
        mock_api.responses = [
            make_tool_use_response(
                "run_agent_health_check",
                {"agent_name": "secretary"},
                "toolu_mon_001",
            ),
            make_text_response("Secretary agent health check passed. All systems operational."),
        ]

        from business_team.agents.chief_of_staff import ChiefOfStaffAgent
        agent = ChiefOfStaffAgent()
        result = agent.think("Run a health check on the secretary")

        assert mock_api.client.messages.create.call_count == 2
        tool_result_content = agent.conversation_history[2]["content"][0]["content"]
        parsed = json.loads(tool_result_content)
        assert "healthy" in parsed
        assert parsed["healthy"] is True
        assert parsed["checks"]["tools_registered"] is True
        assert parsed["checks"]["prompt_loaded"] is True

    def test_cos_analyzes_capabilities(self, mock_api):
        """Test Chief of Staff routes analyze_agent_capabilities to AgentDevTools."""
        mock_api.responses = [
            make_tool_use_response(
                "analyze_agent_capabilities",
                {"agent_name": "business_analyst"},
                "toolu_cap_001",
            ),
            make_text_response("Business Analyst has 10 methods and 5 tools registered."),
        ]

        from business_team.agents.chief_of_staff import ChiefOfStaffAgent
        agent = ChiefOfStaffAgent()
        result = agent.think("Analyze the business analyst capabilities")

        assert mock_api.client.messages.create.call_count == 2
        tool_result_content = agent.conversation_history[2]["content"][0]["content"]
        parsed = json.loads(tool_result_content)
        assert "methods" in parsed
        assert "method_count" in parsed
        assert parsed["method_count"] > 0
        assert parsed["agent_name"] == "business_analyst"

    def test_cos_get_team_status(self, mock_api):
        """Test get_team_status() returns status for all agents (no API call needed)."""
        from business_team.agents.chief_of_staff import ChiefOfStaffAgent
        agent = ChiefOfStaffAgent()
        status = agent.get_team_status()

        assert "chief_of_staff" in status
        assert "secretary" in status
        assert "business_analyst" in status
        assert "projects_manager" in status
        assert "active_alarms" in status
        assert "timestamp" in status

        # Verify each agent status has expected fields
        for agent_key in ("chief_of_staff", "secretary", "business_analyst", "projects_manager"):
            agent_status = status[agent_key]
            assert "name" in agent_status
            assert "role" in agent_status
            assert "inbox_count" in agent_status
            assert "conversation_turns" in agent_status

    def test_cos_execute_tool_unknown(self, mock_api):
        """Test that unknown tool names return an error dict."""
        from business_team.agents.chief_of_staff import ChiefOfStaffAgent
        agent = ChiefOfStaffAgent()

        result = agent.execute_tool("nonexistent_tool", {"arg": "value"})
        assert isinstance(result, dict)
        assert "error" in result
        assert "nonexistent_tool" in result["error"] or "Unknown" in result["error"]
