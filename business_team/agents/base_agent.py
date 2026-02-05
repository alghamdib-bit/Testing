"""
Base Agent class that all business team agents inherit from.

Provides shared functionality: Claude API interaction, logging,
inter-agent messaging, and tool registration.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import anthropic

from business_team import config


class BaseAgent:
    """Base class for all agents in the business team."""

    def __init__(self, name: str, role: str, system_prompt: str):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
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

    def think(self, user_message: str) -> str:
        """
        Send a message to Claude and get a response.
        Handles tool use in a loop until the agent produces a final text response.
        """
        self.conversation_history.append({"role": "user", "content": user_message})

        while True:
            kwargs: dict[str, Any] = {
                "model": self.model,
                "max_tokens": 4096,
                "system": self.system_prompt,
                "messages": self.conversation_history,
            }
            if self.tools:
                kwargs["tools"] = self.tools

            response = self.client.messages.create(**kwargs)
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
