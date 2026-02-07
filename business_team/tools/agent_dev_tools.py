"""
Agent Development Tools for the Chief of Staff.

Allows the Chief of Staff to read, modify, and extend agent source code,
system prompts, and tool registrations. This makes the Chief of Staff
capable of developing and improving its own team.
"""

import ast
import json
import re
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Any

from business_team import config

AGENTS_DIR = config.BASE_DIR / "agents"
TOOLS_DIR = config.BASE_DIR / "tools"


class AgentDevTools:
    """Tools for developing, modifying, and extending agents."""

    def __init__(self):
        self.dev_log_file = config.DATA_DIR / "dev_log.json"
        self.prompts_dir = config.DATA_DIR / "prompts"
        self.prompts_dir.mkdir(parents=True, exist_ok=True)
        if not self.dev_log_file.exists():
            self.dev_log_file.write_text("[]")

    @staticmethod
    def get_tool_definitions() -> list[dict]:
        return [
            {
                "name": "read_agent_source",
                "description": "Read the full source code of any agent in the team. Use this to understand an agent's current implementation before modifying it.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "agent_name": {
                            "type": "string",
                            "enum": ["secretary", "business_analyst", "projects_manager", "chief_of_staff", "base_agent"],
                            "description": "Which agent's source to read",
                        },
                    },
                    "required": ["agent_name"],
                },
            },
            {
                "name": "read_tool_source",
                "description": "Read the full source code of any tool module. Use this to understand existing tools before creating new ones.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "tool_module": {
                            "type": "string",
                            "enum": [
                                "email_tools", "calendar_tools", "todo_tools",
                                "presentation_tools", "dashboard_tools",
                                "project_tools", "reporting_tools",
                            ],
                            "description": "Which tool module to read",
                        },
                    },
                    "required": ["tool_module"],
                },
            },
            {
                "name": "list_agent_tools",
                "description": "List all tools currently registered to an agent, with their names and descriptions.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "agent_name": {
                            "type": "string",
                            "enum": ["secretary", "business_analyst", "projects_manager"],
                        },
                    },
                    "required": ["agent_name"],
                },
            },
            {
                "name": "get_agent_system_prompt",
                "description": "Get an agent's current system prompt.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "agent_name": {
                            "type": "string",
                            "enum": ["secretary", "business_analyst", "projects_manager", "chief_of_staff"],
                        },
                    },
                    "required": ["agent_name"],
                },
            },
            {
                "name": "update_agent_system_prompt",
                "description": "Update an agent's system prompt to change its behavior, add new instructions, or refine its role. The agent will use the new prompt on its next conversation reset.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "agent_name": {
                            "type": "string",
                            "enum": ["secretary", "business_analyst", "projects_manager"],
                        },
                        "new_prompt": {
                            "type": "string",
                            "description": "The complete new system prompt for the agent",
                        },
                        "reason": {
                            "type": "string",
                            "description": "Reason for the prompt change (logged for audit)",
                        },
                    },
                    "required": ["agent_name", "new_prompt", "reason"],
                },
            },
            {
                "name": "append_to_agent_prompt",
                "description": "Append additional instructions to an agent's existing system prompt without replacing it.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "agent_name": {
                            "type": "string",
                            "enum": ["secretary", "business_analyst", "projects_manager"],
                        },
                        "additional_instructions": {
                            "type": "string",
                            "description": "New instructions to append to the existing prompt",
                        },
                        "reason": {
                            "type": "string",
                            "description": "Reason for the addition",
                        },
                    },
                    "required": ["agent_name", "additional_instructions", "reason"],
                },
            },
            {
                "name": "create_new_tool",
                "description": "Create a new tool (Python function + Claude tool definition) and save it as a module that can be registered to any agent.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "tool_name": {
                            "type": "string",
                            "description": "Name of the new tool (snake_case)",
                        },
                        "description": {
                            "type": "string",
                            "description": "What the tool does",
                        },
                        "parameters": {
                            "type": "object",
                            "description": "JSON Schema for the tool's input parameters",
                        },
                        "implementation_code": {
                            "type": "string",
                            "description": "Python code implementing the tool function. Should be a complete method body.",
                        },
                        "target_agent": {
                            "type": "string",
                            "enum": ["secretary", "business_analyst", "projects_manager"],
                            "description": "Which agent should receive this tool",
                        },
                    },
                    "required": ["tool_name", "description", "parameters", "implementation_code", "target_agent"],
                },
            },
            {
                "name": "modify_agent_code",
                "description": "Apply a code modification to an agent's source file. Provide the section to find and the replacement code.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "agent_name": {
                            "type": "string",
                            "enum": ["secretary", "business_analyst", "projects_manager"],
                        },
                        "find_code": {
                            "type": "string",
                            "description": "The exact code section to find and replace",
                        },
                        "replace_code": {
                            "type": "string",
                            "description": "The replacement code",
                        },
                        "reason": {
                            "type": "string",
                            "description": "Reason for the modification",
                        },
                    },
                    "required": ["agent_name", "find_code", "replace_code", "reason"],
                },
            },
            {
                "name": "add_method_to_agent",
                "description": "Add a new method to an agent class. The method will be appended to the class definition.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "agent_name": {
                            "type": "string",
                            "enum": ["secretary", "business_analyst", "projects_manager"],
                        },
                        "method_code": {
                            "type": "string",
                            "description": "Complete Python method code (with def, docstring, body). Use 4-space indentation.",
                        },
                        "reason": {
                            "type": "string",
                            "description": "Reason for adding this method",
                        },
                    },
                    "required": ["agent_name", "method_code", "reason"],
                },
            },
            {
                "name": "get_dev_log",
                "description": "Get the development log showing all changes made to agents.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Max entries to return",
                            "default": 20,
                        },
                    },
                    "required": [],
                },
            },
            {
                "name": "analyze_agent_capabilities",
                "description": "Analyze an agent's current capabilities: tools, methods, prompt directives. Identify gaps and suggest improvements.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "agent_name": {
                            "type": "string",
                            "enum": ["secretary", "business_analyst", "projects_manager"],
                        },
                    },
                    "required": ["agent_name"],
                },
            },
            {
                "name": "backup_agent",
                "description": "Create a backup of an agent's source code before making changes.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "agent_name": {
                            "type": "string",
                            "enum": ["secretary", "business_analyst", "projects_manager"],
                        },
                    },
                    "required": ["agent_name"],
                },
            },
            {
                "name": "restore_agent_backup",
                "description": "Restore an agent from its most recent backup.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "agent_name": {
                            "type": "string",
                            "enum": ["secretary", "business_analyst", "projects_manager"],
                        },
                    },
                    "required": ["agent_name"],
                },
            },
        ]

    # -- Implementation --

    def read_agent_source(self, agent_name: str) -> dict:
        """Read an agent's full source code."""
        filepath = AGENTS_DIR / f"{agent_name}.py"
        if not filepath.exists():
            return {"error": f"Agent file not found: {filepath}"}
        source = filepath.read_text()
        return {
            "agent_name": agent_name,
            "filepath": str(filepath),
            "source": source,
            "line_count": len(source.splitlines()),
        }

    def read_tool_source(self, tool_module: str) -> dict:
        """Read a tool module's source code."""
        filepath = TOOLS_DIR / f"{tool_module}.py"
        if not filepath.exists():
            return {"error": f"Tool module not found: {filepath}"}
        source = filepath.read_text()
        return {
            "tool_module": tool_module,
            "filepath": str(filepath),
            "source": source,
            "line_count": len(source.splitlines()),
        }

    def list_agent_tools(self, agent_name: str, agent_instance=None) -> dict:
        """List all tools registered to an agent."""
        if agent_instance and hasattr(agent_instance, "tools"):
            tools_summary = []
            for tool in agent_instance.tools:
                tools_summary.append({
                    "name": tool.get("name", ""),
                    "description": tool.get("description", ""),
                    "parameters": list(
                        tool.get("input_schema", {}).get("properties", {}).keys()
                    ),
                })
            return {
                "agent_name": agent_name,
                "tool_count": len(tools_summary),
                "tools": tools_summary,
            }

        # Fallback: parse from source
        source_data = self.read_agent_source(agent_name)
        if "error" in source_data:
            return source_data
        tools = re.findall(r'"name":\s*"(\w+)"', source_data["source"])
        return {"agent_name": agent_name, "tools_found_in_source": tools}

    def get_agent_system_prompt(self, agent_name: str, agent_instance=None) -> dict:
        """Get an agent's current system prompt."""
        # Check for runtime override first
        override_file = self.prompts_dir / f"{agent_name}_prompt.txt"
        if override_file.exists():
            return {
                "agent_name": agent_name,
                "source": "runtime_override",
                "prompt": override_file.read_text(),
            }

        if agent_instance:
            return {
                "agent_name": agent_name,
                "source": "live_instance",
                "prompt": agent_instance.system_prompt,
            }

        # Parse from source
        source_data = self.read_agent_source(agent_name)
        if "error" in source_data:
            return source_data
        match = re.search(
            r'(?:SYSTEM_PROMPT|_SYSTEM_PROMPT)\s*=\s*"""(.*?)"""',
            source_data["source"],
            re.DOTALL,
        )
        if match:
            return {
                "agent_name": agent_name,
                "source": "source_file",
                "prompt": match.group(1).strip(),
            }
        return {"error": "Could not extract system prompt from source"}

    def update_agent_system_prompt(
        self, agent_name: str, new_prompt: str, reason: str, agent_instance=None
    ) -> dict:
        """Update an agent's system prompt."""
        # Save as runtime override
        override_file = self.prompts_dir / f"{agent_name}_prompt.txt"
        # Backup current prompt
        old_prompt = ""
        if override_file.exists():
            old_prompt = override_file.read_text()
        elif agent_instance:
            old_prompt = agent_instance.system_prompt

        override_file.write_text(new_prompt)

        # Apply to live instance if available
        if agent_instance:
            agent_instance.system_prompt = new_prompt
            agent_instance.reset_conversation()

        self._log_dev_action("update_prompt", agent_name, reason, {
            "old_prompt_length": len(old_prompt),
            "new_prompt_length": len(new_prompt),
        })

        return {
            "status": "updated",
            "agent_name": agent_name,
            "prompt_length": len(new_prompt),
            "applied_live": agent_instance is not None,
        }

    def append_to_agent_prompt(
        self, agent_name: str, additional_instructions: str, reason: str, agent_instance=None
    ) -> dict:
        """Append instructions to an agent's prompt."""
        current = self.get_agent_system_prompt(agent_name, agent_instance)
        if "error" in current:
            return current

        current_prompt = current["prompt"]
        new_prompt = current_prompt + "\n\n" + additional_instructions

        return self.update_agent_system_prompt(agent_name, new_prompt, reason, agent_instance)

    def create_new_tool(
        self,
        tool_name: str,
        description: str,
        parameters: dict,
        implementation_code: str,
        target_agent: str,
    ) -> dict:
        """Create a new tool and save it for registration."""
        # Save tool definition
        custom_tools_dir = config.DATA_DIR / "custom_tools"
        custom_tools_dir.mkdir(parents=True, exist_ok=True)

        tool_def = {
            "name": tool_name,
            "description": description,
            "input_schema": {
                "type": "object",
                "properties": parameters,
                "required": [k for k, v in parameters.items() if not k.startswith("_optional")],
            },
        }

        tool_data = {
            "definition": tool_def,
            "implementation": implementation_code,
            "target_agent": target_agent,
            "created_at": datetime.now().isoformat(),
        }

        tool_file = custom_tools_dir / f"{tool_name}.json"
        tool_file.write_text(json.dumps(tool_data, indent=2))

        # Also create a Python implementation file
        impl_file = custom_tools_dir / f"{tool_name}.py"
        impl_code = textwrap.dedent(f'''
        """Custom tool: {tool_name} — {description}"""

        def {tool_name}(**kwargs):
            """
            {description}
            """
        {textwrap.indent(implementation_code, "    ")}
        ''').strip()
        impl_file.write_text(impl_code)

        self._log_dev_action("create_tool", target_agent, f"Created tool: {tool_name}", {
            "tool_name": tool_name,
            "description": description,
        })

        return {
            "status": "created",
            "tool_name": tool_name,
            "definition_file": str(tool_file),
            "implementation_file": str(impl_file),
            "target_agent": target_agent,
            "note": "Tool saved. Use register_custom_tools on the agent to activate it.",
        }

    def modify_agent_code(
        self, agent_name: str, find_code: str, replace_code: str, reason: str
    ) -> dict:
        """Apply a code modification to an agent's source file."""
        filepath = AGENTS_DIR / f"{agent_name}.py"
        if not filepath.exists():
            return {"error": f"Agent file not found: {filepath}"}

        source = filepath.read_text()
        if find_code not in source:
            return {
                "error": "find_code not found in source. Check exact whitespace and content.",
                "hint": "Use read_agent_source first to see the exact code.",
            }

        # Backup before modifying
        self.backup_agent(agent_name)

        new_source = source.replace(find_code, replace_code, 1)
        filepath.write_text(new_source)

        self._log_dev_action("modify_code", agent_name, reason, {
            "find_code_length": len(find_code),
            "replace_code_length": len(replace_code),
        })

        return {
            "status": "modified",
            "agent_name": agent_name,
            "filepath": str(filepath),
            "backup_created": True,
        }

    def add_method_to_agent(
        self, agent_name: str, method_code: str, reason: str
    ) -> dict:
        """Add a new method to an agent class."""
        filepath = AGENTS_DIR / f"{agent_name}.py"
        if not filepath.exists():
            return {"error": f"Agent file not found: {filepath}"}

        source = filepath.read_text()

        # Backup before modifying
        self.backup_agent(agent_name)

        # Ensure proper indentation (methods need 4 spaces inside class)
        indented_method = ""
        for line in method_code.splitlines():
            if line.strip():
                indented_method += "    " + line + "\n"
            else:
                indented_method += "\n"

        # Append method at the end of the file (inside the last class)
        new_source = source.rstrip() + "\n\n" + indented_method

        filepath.write_text(new_source)

        self._log_dev_action("add_method", agent_name, reason, {
            "method_lines": len(method_code.splitlines()),
        })

        return {
            "status": "added",
            "agent_name": agent_name,
            "filepath": str(filepath),
        }

    def analyze_agent_capabilities(self, agent_name: str, agent_instance=None) -> dict:
        """Analyze an agent's capabilities and identify gaps."""
        source_data = self.read_agent_source(agent_name)
        if "error" in source_data:
            return source_data

        source = source_data["source"]

        # Parse methods
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            return {"error": f"Syntax error in agent source: {e}"}

        methods = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                docstring = ast.get_docstring(node) or ""
                methods.append({
                    "name": node.name,
                    "docstring": docstring[:100],
                    "line": node.lineno,
                    "args": [a.arg for a in node.args.args if a.arg != "self"],
                })

        # Parse tool definitions
        tool_names = re.findall(r'"name":\s*"(\w+)"', source)

        # Get prompt info
        prompt_data = self.get_agent_system_prompt(agent_name, agent_instance)

        return {
            "agent_name": agent_name,
            "source_lines": source_data["line_count"],
            "methods": methods,
            "method_count": len(methods),
            "tool_names": tool_names,
            "tool_count": len(tool_names),
            "has_custom_prompt_override": (self.prompts_dir / f"{agent_name}_prompt.txt").exists(),
            "prompt_length": len(prompt_data.get("prompt", "")),
        }

    def backup_agent(self, agent_name: str) -> dict:
        """Backup an agent's source code."""
        filepath = AGENTS_DIR / f"{agent_name}.py"
        if not filepath.exists():
            return {"error": f"Agent file not found: {filepath}"}

        backup_dir = config.DATA_DIR / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"{agent_name}_{timestamp}.py"
        backup_file.write_text(filepath.read_text())

        # Also maintain a "latest" symlink-style copy
        latest_file = backup_dir / f"{agent_name}_latest.py"
        latest_file.write_text(filepath.read_text())

        return {
            "status": "backed_up",
            "agent_name": agent_name,
            "backup_file": str(backup_file),
        }

    def restore_agent_backup(self, agent_name: str) -> dict:
        """Restore from the latest backup."""
        backup_dir = config.DATA_DIR / "backups"
        latest_file = backup_dir / f"{agent_name}_latest.py"
        if not latest_file.exists():
            return {"error": f"No backup found for {agent_name}"}

        filepath = AGENTS_DIR / f"{agent_name}.py"
        filepath.write_text(latest_file.read_text())

        self._log_dev_action("restore_backup", agent_name, "Restored from backup", {})

        return {
            "status": "restored",
            "agent_name": agent_name,
            "restored_from": str(latest_file),
        }

    def get_dev_log(self, limit: int = 20) -> list[dict]:
        """Get the development log."""
        log = json.loads(self.dev_log_file.read_text())
        return log[-limit:]

    def _log_dev_action(self, action: str, agent_name: str, reason: str, details: dict) -> None:
        """Log a development action."""
        log = json.loads(self.dev_log_file.read_text())
        log.append({
            "action": action,
            "agent_name": agent_name,
            "reason": reason,
            "details": details,
            "timestamp": datetime.now().isoformat(),
        })
        self.dev_log_file.write_text(json.dumps(log, indent=2))

    def handle_tool_call(self, tool_name: str, tool_input: dict, agents: dict | None = None) -> Any:
        """Route tool calls. Agents dict maps name -> instance for live operations."""
        agents = agents or {}
        agent_name = tool_input.get("agent_name", "")
        agent_instance = agents.get(agent_name)

        dispatch = {
            "read_agent_source": lambda: self.read_agent_source(**tool_input),
            "read_tool_source": lambda: self.read_tool_source(**tool_input),
            "list_agent_tools": lambda: self.list_agent_tools(agent_name, agent_instance),
            "get_agent_system_prompt": lambda: self.get_agent_system_prompt(agent_name, agent_instance),
            "update_agent_system_prompt": lambda: self.update_agent_system_prompt(
                agent_name, tool_input["new_prompt"], tool_input.get("reason", ""), agent_instance
            ),
            "append_to_agent_prompt": lambda: self.append_to_agent_prompt(
                agent_name, tool_input["additional_instructions"], tool_input.get("reason", ""), agent_instance
            ),
            "create_new_tool": lambda: self.create_new_tool(**tool_input),
            "modify_agent_code": lambda: self.modify_agent_code(**tool_input),
            "add_method_to_agent": lambda: self.add_method_to_agent(**tool_input),
            "get_dev_log": lambda: self.get_dev_log(**tool_input),
            "analyze_agent_capabilities": lambda: self.analyze_agent_capabilities(agent_name, agent_instance),
            "backup_agent": lambda: self.backup_agent(**tool_input),
            "restore_agent_backup": lambda: self.restore_agent_backup(**tool_input),
        }
        handler = dispatch.get(tool_name)
        if handler:
            return handler()
        return {"error": f"Unknown dev tool: {tool_name}"}
