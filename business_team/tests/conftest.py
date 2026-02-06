"""Shared fixtures for integration tests.

Provides mock Claude API responses and a configurable mock_api fixture
so that tests can exercise the full agent think() loop without making
real API calls.
"""

import json
import pytest
from types import SimpleNamespace
from unittest.mock import patch, MagicMock


def make_text_response(text, stop_reason="end_turn"):
    """Create a mock Claude API response with text content."""
    block = SimpleNamespace(type="text", text=text)
    return SimpleNamespace(content=[block], stop_reason=stop_reason)


def make_tool_use_response(tool_name, tool_input, tool_id="toolu_test_001"):
    """Create a mock Claude API response requesting tool use."""
    block = SimpleNamespace(
        type="tool_use", name=tool_name, input=tool_input, id=tool_id
    )
    return SimpleNamespace(content=[block], stop_reason="tool_use")


def make_multi_tool_response(tools):
    """Create a response with multiple tool calls.

    Args:
        tools: list of (name, input, id) tuples
    """
    blocks = [
        SimpleNamespace(type="tool_use", name=name, input=inp, id=tid)
        for name, inp, tid in tools
    ]
    return SimpleNamespace(content=blocks, stop_reason="tool_use")


@pytest.fixture
def mock_api():
    """Fixture that patches anthropic.Anthropic and returns a configurable mock.

    Usage:
        def test_example(mock_api):
            mock_api.responses = [
                make_tool_use_response("read_emails", {"limit": 5}),
                make_text_response("Found 5 emails"),
            ]
            # Now create agent and call think()
    """
    with patch("anthropic.Anthropic") as MockAnthropicClass:
        mock_client = MagicMock()
        MockAnthropicClass.return_value = mock_client

        # Create a holder for responses
        holder = SimpleNamespace(
            responses=[],
            call_count=0,
            client=mock_client,
        )

        def create_side_effect(**kwargs):
            if holder.call_count < len(holder.responses):
                resp = holder.responses[holder.call_count]
                holder.call_count += 1
                return resp
            # Default: return end_turn with empty text
            return make_text_response("")

        mock_client.messages.create.side_effect = create_side_effect
        yield holder
