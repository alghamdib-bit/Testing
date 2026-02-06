"""
Base Agent class that all business team agents inherit from.

Provides shared functionality: Claude API interaction, logging,
inter-agent messaging, tool registration, and API resilience.
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import anthropic

from business_team import config
from business_team.config import ConfigurationError


class BaseAgent:
    """Base class for all agents in the business team."""

    def __init__(self, name: str, role: str, system_prompt: str, memory=None, db=None):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.memory = memory
        self.db = db
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        self.model = config.CLAUDE_MODEL
        self.conversation_history: list[dict] = []
        self.tools: list[dict] = []
        self.logger = self._setup_logger()
        self.inbox: list[dict] = []  # Messages from other agents

    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger(f"agent.{self.name}")
        logger.setLevel(getattr(logging, config.LOG_LEVEL))
        log_file = config.LOGS_DIR / f"{self.name}.log"
        handler = logging.FileHandler(log_file)
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        if not logger.handlers:
            logger.addHandler(handler)
        return logger

    def register_tools(self, tools: list[dict]) -> None:
        """Register tools that this agent can use."""
        self.tools = tools
        self.logger.info(f"Registered {len(tools)} tools")

    def send_message(self, to_agent: "BaseAgent", subject: str, content: str) -> None:
        """Send a message to another agent."""
        message = {
            "from": self.name,
            "to": to_agent.name,
            "subject": subject,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }
        to_agent.inbox.append(message)
        self.logger.info(f"Sent message to {to_agent.name}: {subject}")

    def read_inbox(self) -> list[dict]:
        """Read and clear the inbox."""
        messages = self.inbox.copy()
        self.inbox.clear()
        return messages

    def _call_api_with_retry(self, kwargs: dict[str, Any], max_retries: int | None = None) -> Any:
        """
        Call the Anthropic API with retry logic and error handling.

        Handles:
        - AuthenticationError: raises ConfigurationError immediately (no retry)
        - BadRequestError: logs and returns error string (no retry)
        - RateLimitError: retries with exponential backoff
        - APIConnectionError: retries with exponential backoff
        - APIStatusError (5xx): retries with exponential backoff
        - On final retry exhaustion: returns error string
        """
        if max_retries is None:
            max_retries = config.API_MAX_RETRIES

        last_exception = None

        for attempt in range(max_retries):
            try:
                response = self.client.messages.create(**kwargs)
                return response
            except anthropic.AuthenticationError as e:
                self.logger.error(f"Authentication failed: {e}")
                raise ConfigurationError(
                    "ANTHROPIC_API_KEY is invalid or expired.\n"
                    "Update your API key in .env:\n"
                    "  ANTHROPIC_API_KEY=sk-ant-...\n"
                    "Get one at: https://console.anthropic.com/settings/keys"
                ) from e
            except anthropic.BadRequestError as e:
                self.logger.error(f"Bad request (not retrying): {e}")
                return f"[API Error] Bad request: {e}"
            except anthropic.RateLimitError as e:
                last_exception = e
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                self.logger.warning(
                    f"Rate limited (attempt {attempt + 1}/{max_retries}), "
                    f"retrying in {wait_time}s..."
                )
                if attempt < max_retries - 1:
                    time.sleep(wait_time)
            except anthropic.APIConnectionError as e:
                last_exception = e
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                self.logger.warning(
                    f"Connection error (attempt {attempt + 1}/{max_retries}), "
                    f"retrying in {wait_time}s..."
                )
                if attempt < max_retries - 1:
                    time.sleep(wait_time)
            except anthropic.APIStatusError as e:
                if e.status_code >= 500:
                    last_exception = e
                    wait_time = 2 ** attempt  # 1s, 2s, 4s
                    self.logger.warning(
                        f"Server error {e.status_code} (attempt {attempt + 1}/{max_retries}), "
                        f"retrying in {wait_time}s..."
                    )
                    if attempt < max_retries - 1:
                        time.sleep(wait_time)
                else:
                    self.logger.error(f"API status error {e.status_code}: {e}")
                    return f"[API Error] Status {e.status_code}: {e}"

        # All retries exhausted
        self.logger.error(
            f"API call failed after {max_retries} retries: {last_exception}"
        )
        return f"[API Error] Failed after {max_retries} retries: {last_exception}"

    def _truncate_conversation_history(self) -> None:
        """
        Truncate conversation history if it exceeds the configured limit.
        Keeps the first message and the last N turns to preserve context.
        """
        max_messages = config.MAX_CONVERSATION_TURNS * 2
        if len(self.conversation_history) > max_messages:
            keep_recent = max_messages // 2
            first_message = self.conversation_history[0]
            recent_messages = self.conversation_history[-keep_recent:]
            self.conversation_history = [first_message] + recent_messages
            self.logger.info(
                f"Conversation history truncated: kept first message + "
                f"last {keep_recent} messages"
            )

    def validate_ready(self) -> dict:
        """
        Check that the agent is properly configured and ready to operate.

        Returns a dict with:
        - ready (bool): whether the agent is ready
        - issues (list[str]): list of configuration issues found
        """
        issues = []

        if not config.ANTHROPIC_API_KEY:
            issues.append("ANTHROPIC_API_KEY is not set")

        if not self.model:
            issues.append("Claude model is not configured")

        if not self.system_prompt:
            issues.append("System prompt is empty")

        if not self.tools:
            issues.append("No tools registered")

        return {
            "ready": len(issues) == 0,
            "issues": issues,
            "agent": self.name,
            "role": self.role,
        }

    def think(self, user_message: str) -> str:
        """
        Send a message to Claude and get a response.
        Handles tool use in a loop until the agent produces a final text response.
        Includes conversation overflow protection and API retry logic.
        """
        self.conversation_history.append({"role": "user", "content": user_message})

        # Conversation overflow protection
        self._truncate_conversation_history()

        # Build effective system prompt with memory context
        effective_system_prompt = self.system_prompt
        if self.memory:
            context = self.memory.get_context_summary()
            if context and context != "No prior context available.":
                effective_system_prompt = (
                    self.system_prompt + "\n\n## CONTEXTUAL MEMORY\n" + context
                )

        while True:
            kwargs: dict[str, Any] = {
                "model": self.model,
                "max_tokens": 4096,
                "system": effective_system_prompt,
                "messages": self.conversation_history,
            }
            if self.tools:
                kwargs["tools"] = self.tools

            response = self._call_api_with_retry(kwargs)

            # If _call_api_with_retry returned a string, it means an error occurred
            if isinstance(response, str):
                self.logger.error(f"API call returned error: {response}")
                self.conversation_history.append(
                    {"role": "assistant", "content": response}
                )
                return response

            self.logger.info(f"API response stop_reason: {response.stop_reason}")

            # Collect text and tool_use blocks
            text_parts = []
            tool_calls = []
            for block in response.content:
                if block.type == "text":
                    text_parts.append(block.text)
                elif block.type == "tool_use":
                    tool_calls.append(block)

            # If the model wants to use tools, process them
            if response.stop_reason == "tool_use" and tool_calls:
                # Add assistant's response (with tool_use blocks) to history
                self.conversation_history.append(
                    {"role": "assistant", "content": response.content}
                )

                # Execute each tool and collect results
                tool_results = []
                for tool_call in tool_calls:
                    result = self.execute_tool(tool_call.name, tool_call.input)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_call.id,
                            "content": json.dumps(result)
                            if isinstance(result, (dict, list))
                            else str(result),
                        }
                    )

                self.conversation_history.append(
                    {"role": "user", "content": tool_results}
                )
                # Loop back to get the next response
                continue

            # Final text response
            final_text = "\n".join(text_parts) if text_parts else ""
            self.conversation_history.append(
                {"role": "assistant", "content": final_text}
            )
            self.logger.info(f"Response: {final_text[:200]}...")

            # Log interaction to memory
            if self.memory:
                self.memory.add_interaction(
                    self.name, user_message, final_text[:200]
                )

            return final_text

    def execute_tool(self, tool_name: str, tool_input: dict) -> Any:
        """
        Execute a registered tool by name. Subclasses override this
        to wire tool names to actual functions.
        """
        self.logger.warning(f"Unhandled tool call: {tool_name}")
        return {"error": f"Tool '{tool_name}' not implemented"}

    def log_activity(self, activity_type: str, details: str) -> None:
        """Log an agent activity to the shared activity log."""
        if self.db:
            self.db.log_activity(self.name, activity_type, details)
        else:
            entry = {
                "agent": self.name,
                "type": activity_type,
                "details": details,
                "timestamp": datetime.now().isoformat(),
            }
            log_file = config.DATA_DIR / "activity_log.json"
            activities = []
            if log_file.exists():
                activities = json.loads(log_file.read_text())
            activities.append(entry)
            log_file.write_text(json.dumps(activities, indent=2))
        self.logger.info(f"Activity logged: {activity_type}")

    def get_status(self) -> dict:
        """Return current agent status."""
        return {
            "name": self.name,
            "role": self.role,
            "inbox_count": len(self.inbox),
            "conversation_turns": len(self.conversation_history),
            "timestamp": datetime.now().isoformat(),
        }

    def reset_conversation(self) -> None:
        """Clear conversation history to free context."""
        self.conversation_history.clear()
        self.logger.info("Conversation history reset")
