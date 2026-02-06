#!/usr/bin/env python3
"""
Resilience Test Suite — Tests API error handling, retry logic, and validation.

All tests are fully offline (mocked). No real API calls are made.

Run:  python -m pytest business_team/tests/test_resilience.py -v
"""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, PropertyMock

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import anthropic

from business_team import config
from business_team.config import ConfigurationError, validate_config
from business_team.agents.base_agent import BaseAgent


def _make_mock_response(text="Hello, world!", stop_reason="end_turn"):
    """Helper to create a mock API response object."""
    text_block = SimpleNamespace(type="text", text=text)
    response = SimpleNamespace(
        content=[text_block],
        stop_reason=stop_reason,
    )
    return response


def _create_agent(**overrides):
    """Helper to create a BaseAgent with mocked Anthropic client."""
    with patch("business_team.agents.base_agent.anthropic.Anthropic"):
        agent = BaseAgent(
            name=overrides.get("name", "test_agent"),
            role=overrides.get("role", "tester"),
            system_prompt=overrides.get("system_prompt", "You are a test agent."),
        )
    agent.client = MagicMock()
    return agent


class TestValidateConfig(unittest.TestCase):
    """Tests for config.validate_config()."""

    def test_validate_config_raises_when_api_key_empty(self):
        """validate_config() should raise ConfigurationError when ANTHROPIC_API_KEY is empty."""
        with patch.object(config, "ANTHROPIC_API_KEY", ""):
            with self.assertRaises(ConfigurationError) as ctx:
                validate_config()
            self.assertIn("ANTHROPIC_API_KEY is not set", str(ctx.exception))

    def test_validate_config_passes_when_api_key_set(self):
        """validate_config() should not raise when ANTHROPIC_API_KEY is set."""
        with patch.object(config, "ANTHROPIC_API_KEY", "sk-ant-test-key-12345"):
            # Should not raise
            validate_config()

    def test_validate_config_error_message_has_instructions(self):
        """ConfigurationError message should include setup instructions."""
        with patch.object(config, "ANTHROPIC_API_KEY", ""):
            with self.assertRaises(ConfigurationError) as ctx:
                validate_config()
            msg = str(ctx.exception)
            self.assertIn(".env", msg)
            self.assertIn("console.anthropic.com", msg)


class TestConfigConstants(unittest.TestCase):
    """Tests for new config constants."""

    def test_max_conversation_turns_default(self):
        """MAX_CONVERSATION_TURNS should default to 50."""
        self.assertEqual(config.MAX_CONVERSATION_TURNS, 50)

    def test_api_max_retries_default(self):
        """API_MAX_RETRIES should default to 3."""
        self.assertEqual(config.API_MAX_RETRIES, 3)

    def test_configuration_error_is_exception(self):
        """ConfigurationError should be a subclass of Exception."""
        self.assertTrue(issubclass(ConfigurationError, Exception))


class TestCallApiWithRetry(unittest.TestCase):
    """Tests for BaseAgent._call_api_with_retry()."""

    def setUp(self):
        self.agent = _create_agent()

    def test_successful_api_call(self):
        """_call_api_with_retry should return the response on success."""
        mock_response = _make_mock_response("Success!")
        self.agent.client.messages.create.return_value = mock_response

        result = self.agent._call_api_with_retry({"model": "test", "messages": []})
        self.assertEqual(result, mock_response)
        self.agent.client.messages.create.assert_called_once()

    def test_authentication_error_raises_configuration_error(self):
        """AuthenticationError should be converted to ConfigurationError."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": {"message": "Invalid API key"}}
        self.agent.client.messages.create.side_effect = anthropic.AuthenticationError(
            message="Invalid API key",
            response=mock_response,
            body={"error": {"message": "Invalid API key"}},
        )

        with self.assertRaises(ConfigurationError) as ctx:
            self.agent._call_api_with_retry({"model": "test", "messages": []})
        self.assertIn("invalid or expired", str(ctx.exception))

    @patch("business_team.agents.base_agent.time.sleep")
    def test_rate_limit_error_retries(self, mock_sleep):
        """RateLimitError should trigger retries with exponential backoff."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"error": {"message": "Rate limited"}}
        rate_limit_error = anthropic.RateLimitError(
            message="Rate limited",
            response=mock_response,
            body={"error": {"message": "Rate limited"}},
        )
        self.agent.client.messages.create.side_effect = [
            rate_limit_error,
            rate_limit_error,
            rate_limit_error,
        ]

        result = self.agent._call_api_with_retry(
            {"model": "test", "messages": []}, max_retries=3
        )

        # Should return an error string after all retries exhausted
        self.assertIsInstance(result, str)
        self.assertIn("[API Error]", result)
        # Should have slept between retries (2 sleeps for 3 attempts)
        self.assertEqual(mock_sleep.call_count, 2)

    @patch("business_team.agents.base_agent.time.sleep")
    def test_connection_error_retries(self, mock_sleep):
        """APIConnectionError should trigger retries."""
        conn_error = anthropic.APIConnectionError(request=MagicMock())
        self.agent.client.messages.create.side_effect = [
            conn_error,
            conn_error,
            conn_error,
        ]

        result = self.agent._call_api_with_retry(
            {"model": "test", "messages": []}, max_retries=3
        )

        self.assertIsInstance(result, str)
        self.assertIn("[API Error]", result)
        self.assertEqual(mock_sleep.call_count, 2)

    @patch("business_team.agents.base_agent.time.sleep")
    def test_succeeds_after_one_retry(self, mock_sleep):
        """API call should succeed after retrying once on transient error."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"error": {"message": "Rate limited"}}
        rate_limit_error = anthropic.RateLimitError(
            message="Rate limited",
            response=mock_response,
            body={"error": {"message": "Rate limited"}},
        )
        success_response = _make_mock_response("Recovered!")

        self.agent.client.messages.create.side_effect = [
            rate_limit_error,
            success_response,
        ]

        result = self.agent._call_api_with_retry(
            {"model": "test", "messages": []}, max_retries=3
        )

        self.assertEqual(result, success_response)
        self.assertEqual(self.agent.client.messages.create.call_count, 2)
        mock_sleep.assert_called_once_with(1)  # 2^0 = 1 second

    def test_bad_request_error_no_retry(self):
        """BadRequestError should return error string without retrying."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": {"message": "Bad request"}}
        self.agent.client.messages.create.side_effect = anthropic.BadRequestError(
            message="Bad request",
            response=mock_response,
            body={"error": {"message": "Bad request"}},
        )

        result = self.agent._call_api_with_retry(
            {"model": "test", "messages": []}, max_retries=3
        )

        self.assertIsInstance(result, str)
        self.assertIn("[API Error]", result)
        self.assertIn("Bad request", result)
        # Should NOT have retried
        self.assertEqual(self.agent.client.messages.create.call_count, 1)

    @patch("business_team.agents.base_agent.time.sleep")
    def test_server_error_500_retries(self, mock_sleep):
        """APIStatusError with status >= 500 should trigger retries."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": {"message": "Internal server error"}}
        server_error = anthropic.APIStatusError(
            message="Internal server error",
            response=mock_response,
            body={"error": {"message": "Internal server error"}},
        )
        # Make status_code accessible as attribute
        server_error.status_code = 500

        self.agent.client.messages.create.side_effect = [
            server_error,
            server_error,
            server_error,
        ]

        result = self.agent._call_api_with_retry(
            {"model": "test", "messages": []}, max_retries=3
        )

        self.assertIsInstance(result, str)
        self.assertIn("[API Error]", result)
        self.assertEqual(self.agent.client.messages.create.call_count, 3)

    @patch("business_team.agents.base_agent.time.sleep")
    def test_exponential_backoff_timing(self, mock_sleep):
        """Verify exponential backoff waits: 1s, 2s, 4s."""
        conn_error = anthropic.APIConnectionError(request=MagicMock())
        self.agent.client.messages.create.side_effect = [
            conn_error,
            conn_error,
            conn_error,
            conn_error,
        ]

        self.agent._call_api_with_retry(
            {"model": "test", "messages": []}, max_retries=4
        )

        # 4 attempts = 3 sleep calls: 2^0=1, 2^1=2, 2^2=4
        self.assertEqual(mock_sleep.call_count, 3)
        mock_sleep.assert_any_call(1)
        mock_sleep.assert_any_call(2)
        mock_sleep.assert_any_call(4)


class TestConversationOverflow(unittest.TestCase):
    """Tests for conversation overflow protection."""

    def setUp(self):
        self.agent = _create_agent()

    def test_truncation_when_exceeding_limit(self):
        """Conversation history should be truncated when it exceeds MAX_CONVERSATION_TURNS * 2."""
        max_messages = config.MAX_CONVERSATION_TURNS * 2  # 100

        # Fill conversation history beyond the limit
        for i in range(max_messages + 20):
            role = "user" if i % 2 == 0 else "assistant"
            self.agent.conversation_history.append(
                {"role": role, "content": f"Message {i}"}
            )

        original_first = self.agent.conversation_history[0]
        self.agent._truncate_conversation_history()

        # Should be truncated
        self.assertLessEqual(len(self.agent.conversation_history), max_messages)
        # First message should be preserved
        self.assertEqual(self.agent.conversation_history[0], original_first)

    def test_no_truncation_when_under_limit(self):
        """Conversation history should not be modified when under the limit."""
        for i in range(10):
            role = "user" if i % 2 == 0 else "assistant"
            self.agent.conversation_history.append(
                {"role": role, "content": f"Message {i}"}
            )

        original_length = len(self.agent.conversation_history)
        self.agent._truncate_conversation_history()

        self.assertEqual(len(self.agent.conversation_history), original_length)

    def test_truncation_preserves_first_message(self):
        """After truncation, the first message in history should be the original first message."""
        first_msg = {"role": "user", "content": "IMPORTANT FIRST MESSAGE"}
        self.agent.conversation_history.append(first_msg)

        max_messages = config.MAX_CONVERSATION_TURNS * 2
        for i in range(max_messages + 50):
            role = "user" if i % 2 == 0 else "assistant"
            self.agent.conversation_history.append(
                {"role": role, "content": f"Message {i}"}
            )

        self.agent._truncate_conversation_history()

        self.assertEqual(self.agent.conversation_history[0]["content"], "IMPORTANT FIRST MESSAGE")

    def test_think_triggers_truncation(self):
        """think() should call _truncate_conversation_history."""
        mock_response = _make_mock_response("Response")
        self.agent.client.messages.create.return_value = mock_response

        with patch.object(self.agent, "_truncate_conversation_history") as mock_truncate:
            self.agent.think("Hello")
            mock_truncate.assert_called_once()


class TestValidateReady(unittest.TestCase):
    """Tests for BaseAgent.validate_ready()."""

    def test_validate_ready_with_missing_api_key(self):
        """validate_ready() should report missing API key."""
        agent = _create_agent()
        with patch.object(config, "ANTHROPIC_API_KEY", ""):
            result = agent.validate_ready()
        self.assertFalse(result["ready"])
        self.assertIn("ANTHROPIC_API_KEY is not set", result["issues"])

    def test_validate_ready_with_valid_config(self):
        """validate_ready() should return ready=True when fully configured."""
        agent = _create_agent()
        agent.tools = [{"name": "test_tool"}]
        with patch.object(config, "ANTHROPIC_API_KEY", "sk-ant-test-key"):
            result = agent.validate_ready()
        self.assertTrue(result["ready"])
        self.assertEqual(result["issues"], [])

    def test_validate_ready_with_no_tools(self):
        """validate_ready() should report missing tools."""
        agent = _create_agent()
        agent.tools = []
        with patch.object(config, "ANTHROPIC_API_KEY", "sk-ant-test-key"):
            result = agent.validate_ready()
        self.assertFalse(result["ready"])
        self.assertIn("No tools registered", result["issues"])

    def test_validate_ready_with_empty_system_prompt(self):
        """validate_ready() should report empty system prompt."""
        agent = _create_agent(system_prompt="")
        with patch.object(config, "ANTHROPIC_API_KEY", "sk-ant-test-key"):
            result = agent.validate_ready()
        self.assertFalse(result["ready"])
        self.assertIn("System prompt is empty", result["issues"])

    def test_validate_ready_with_empty_model(self):
        """validate_ready() should report missing model."""
        agent = _create_agent()
        agent.model = ""
        with patch.object(config, "ANTHROPIC_API_KEY", "sk-ant-test-key"):
            result = agent.validate_ready()
        self.assertFalse(result["ready"])
        self.assertIn("Claude model is not configured", result["issues"])

    def test_validate_ready_returns_agent_info(self):
        """validate_ready() should include agent name and role in response."""
        agent = _create_agent(name="my_agent", role="my_role")
        result = agent.validate_ready()
        self.assertEqual(result["agent"], "my_agent")
        self.assertEqual(result["role"], "my_role")


class TestThinkResilience(unittest.TestCase):
    """Tests for think() method resilience."""

    def setUp(self):
        self.agent = _create_agent()

    def test_think_returns_error_string_on_api_failure(self):
        """think() should return an error string (not raise) on API failure."""
        conn_error = anthropic.APIConnectionError(request=MagicMock())
        self.agent.client.messages.create.side_effect = conn_error

        with patch("business_team.agents.base_agent.time.sleep"):
            result = self.agent.think("Hello")

        self.assertIsInstance(result, str)
        self.assertIn("[API Error]", result)

    def test_think_raises_configuration_error_on_auth_failure(self):
        """think() should raise ConfigurationError on AuthenticationError."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": {"message": "Invalid API key"}}
        self.agent.client.messages.create.side_effect = anthropic.AuthenticationError(
            message="Invalid API key",
            response=mock_response,
            body={"error": {"message": "Invalid API key"}},
        )

        with self.assertRaises(ConfigurationError):
            self.agent.think("Hello")

    def test_think_adds_error_to_conversation_history(self):
        """think() should add error response to conversation history on API failure."""
        conn_error = anthropic.APIConnectionError(request=MagicMock())
        self.agent.client.messages.create.side_effect = conn_error

        with patch("business_team.agents.base_agent.time.sleep"):
            self.agent.think("Hello")

        # Should have user message + assistant error response
        self.assertEqual(len(self.agent.conversation_history), 2)
        self.assertEqual(self.agent.conversation_history[0]["role"], "user")
        self.assertEqual(self.agent.conversation_history[1]["role"], "assistant")
        self.assertIn("[API Error]", self.agent.conversation_history[1]["content"])

    def test_think_successful_response(self):
        """think() should return text on successful API call."""
        mock_response = _make_mock_response("Hello from Claude!")
        self.agent.client.messages.create.return_value = mock_response

        result = self.agent.think("Hi there")

        self.assertEqual(result, "Hello from Claude!")

    def test_think_bad_request_returns_error_string(self):
        """think() should return error string on BadRequestError (not raise)."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": {"message": "Bad request"}}
        self.agent.client.messages.create.side_effect = anthropic.BadRequestError(
            message="Bad request",
            response=mock_response,
            body={"error": {"message": "Bad request"}},
        )

        result = self.agent.think("Hello")

        self.assertIsInstance(result, str)
        self.assertIn("[API Error]", result)


class TestExistingMethodsPreserved(unittest.TestCase):
    """Tests to verify existing methods still work correctly."""

    def setUp(self):
        self.agent = _create_agent()

    def test_send_and_read_inbox(self):
        """send_message and read_inbox should work as before."""
        other = _create_agent(name="other_agent")
        self.agent.send_message(other, "Test Subject", "Test Content")

        messages = other.read_inbox()
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["subject"], "Test Subject")
        self.assertEqual(messages[0]["content"], "Test Content")

        # Inbox should be cleared
        self.assertEqual(len(other.read_inbox()), 0)

    def test_register_tools(self):
        """register_tools should set the tools list."""
        tools = [{"name": "tool1"}, {"name": "tool2"}]
        self.agent.register_tools(tools)
        self.assertEqual(self.agent.tools, tools)

    def test_execute_tool_returns_error_for_unknown(self):
        """execute_tool should return error dict for unimplemented tools."""
        result = self.agent.execute_tool("unknown_tool", {})
        self.assertIn("error", result)

    def test_get_status(self):
        """get_status should return expected fields."""
        status = self.agent.get_status()
        self.assertEqual(status["name"], "test_agent")
        self.assertEqual(status["role"], "tester")
        self.assertIn("inbox_count", status)
        self.assertIn("conversation_turns", status)
        self.assertIn("timestamp", status)

    def test_reset_conversation(self):
        """reset_conversation should clear history."""
        self.agent.conversation_history = [{"role": "user", "content": "hi"}]
        self.agent.reset_conversation()
        self.assertEqual(len(self.agent.conversation_history), 0)


if __name__ == "__main__":
    unittest.main()
