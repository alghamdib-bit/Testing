"""
Agent Monitoring & Testing Tools for the Office Manager.

Provides the ability to test agents, evaluate their output quality,
track performance over time, and identify improvement opportunities.
"""

import json
import time
from datetime import datetime
from typing import Any

from business_team import config


class AgentMonitorTools:
    """Tools for testing, evaluating, and monitoring agent performance."""

    def __init__(self):
        self.perf_log_file = config.DATA_DIR / "agent_performance.json"
        self.test_results_file = config.DATA_DIR / "test_results.json"
        if not self.perf_log_file.exists():
            self.perf_log_file.write_text("[]")
        if not self.test_results_file.exists():
            self.test_results_file.write_text("[]")

    @staticmethod
    def get_tool_definitions() -> list[dict]:
        return [
            {
                "name": "test_agent",
                "description": "Send a test prompt to an agent and evaluate the response. Returns the response, timing, and tool usage metrics.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "agent_name": {
                            "type": "string",
                            "enum": ["secretary", "business_analyst", "projects_manager"],
                            "description": "Agent to test",
                        },
                        "test_prompt": {
                            "type": "string",
                            "description": "The prompt to send to the agent",
                        },
                        "expected_keywords": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Keywords expected in the response (for quality check)",
                        },
                    },
                    "required": ["agent_name", "test_prompt"],
                },
            },
            {
                "name": "evaluate_agent_output",
                "description": "Evaluate a piece of agent output for quality, completeness, and adherence to standards.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "agent_name": {
                            "type": "string",
                            "description": "Which agent produced the output",
                        },
                        "output": {
                            "type": "string",
                            "description": "The agent's output to evaluate",
                        },
                        "criteria": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Evaluation criteria (e.g., 'includes action items', 'has priority labels')",
                        },
                    },
                    "required": ["agent_name", "output", "criteria"],
                },
            },
            {
                "name": "log_agent_performance",
                "description": "Log a performance metric for an agent (response time, quality score, etc.).",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "agent_name": {
                            "type": "string",
                        },
                        "metric_name": {
                            "type": "string",
                            "description": "e.g., 'response_time_ms', 'quality_score', 'tool_calls_count'",
                        },
                        "metric_value": {
                            "type": "number",
                        },
                        "context": {
                            "type": "string",
                            "description": "What task was being performed",
                        },
                    },
                    "required": ["agent_name", "metric_name", "metric_value"],
                },
            },
            {
                "name": "get_performance_report",
                "description": "Get a performance report for one or all agents.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "agent_name": {
                            "type": "string",
                            "description": "Specific agent, or omit for all",
                        },
                    },
                    "required": [],
                },
            },
            {
                "name": "run_agent_health_check",
                "description": "Run a comprehensive health check on an agent: verify tools are registered, prompt is loaded, and basic operations work.",
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
                "name": "get_test_results",
                "description": "Get historical test results for agents.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "agent_name": {
                            "type": "string",
                        },
                        "limit": {
                            "type": "integer",
                            "default": 10,
                        },
                    },
                    "required": [],
                },
            },
        ]

    def test_agent(
        self,
        agent_name: str,
        test_prompt: str,
        expected_keywords: list[str] | None = None,
        agent_instance=None,
    ) -> dict:
        """Send a test prompt to an agent and measure the result."""
        if not agent_instance:
            return {"error": f"No live instance available for {agent_name}"}

        expected_keywords = expected_keywords or []

        agent_instance.reset_conversation()
        start = time.time()
        try:
            response = agent_instance.think(test_prompt)
            elapsed_ms = int((time.time() - start) * 1000)
        except Exception as e:
            return {"error": f"Agent failed: {str(e)}"}

        # Check for expected keywords
        keywords_found = [kw for kw in expected_keywords if kw.lower() in response.lower()]
        keywords_missing = [kw for kw in expected_keywords if kw.lower() not in response.lower()]

        result = {
            "agent_name": agent_name,
            "test_prompt": test_prompt,
            "response_preview": response[:500],
            "response_length": len(response),
            "response_time_ms": elapsed_ms,
            "keywords_found": keywords_found,
            "keywords_missing": keywords_missing,
            "keyword_score": len(keywords_found) / len(expected_keywords) if expected_keywords else 1.0,
            "timestamp": datetime.now().isoformat(),
        }

        # Save test result
        results = json.loads(self.test_results_file.read_text())
        results.append(result)
        self.test_results_file.write_text(json.dumps(results, indent=2))

        # Log performance metrics
        self.log_agent_performance(agent_name, "response_time_ms", elapsed_ms, test_prompt[:50])
        self.log_agent_performance(agent_name, "response_length", len(response), test_prompt[:50])

        return result

    def evaluate_agent_output(
        self, agent_name: str, output: str, criteria: list[str]
    ) -> dict:
        """Evaluate agent output against criteria."""
        results = []
        for criterion in criteria:
            # Simple keyword/pattern matching for automated checks
            criterion_lower = criterion.lower()
            passed = False

            if "includes" in criterion_lower or "has" in criterion_lower:
                # Extract what should be included
                keywords = criterion_lower.replace("includes ", "").replace("has ", "").split()
                passed = any(kw in output.lower() for kw in keywords)
            elif "structured" in criterion_lower or "format" in criterion_lower:
                # Check for structure indicators
                passed = any(marker in output for marker in ["#", "- ", "* ", "1.", "**"])
            elif "action" in criterion_lower:
                passed = any(kw in output.lower() for kw in ["action", "todo", "task", "follow up", "next step"])
            elif "priority" in criterion_lower:
                passed = any(kw in output.lower() for kw in ["critical", "high", "medium", "low", "priority", "urgent"])
            else:
                # Default: check if the criterion words appear
                words = criterion_lower.split()
                passed = any(w in output.lower() for w in words if len(w) > 3)

            results.append({
                "criterion": criterion,
                "passed": passed,
            })

        passed_count = sum(1 for r in results if r["passed"])
        return {
            "agent_name": agent_name,
            "total_criteria": len(criteria),
            "passed": passed_count,
            "failed": len(criteria) - passed_count,
            "score": passed_count / len(criteria) if criteria else 1.0,
            "details": results,
        }

    def log_agent_performance(
        self,
        agent_name: str,
        metric_name: str,
        metric_value: float,
        context: str = "",
    ) -> dict:
        """Log a performance metric."""
        log = json.loads(self.perf_log_file.read_text())
        entry = {
            "agent_name": agent_name,
            "metric_name": metric_name,
            "metric_value": metric_value,
            "context": context,
            "timestamp": datetime.now().isoformat(),
        }
        log.append(entry)
        # Keep last 500 entries
        if len(log) > 500:
            log = log[-500:]
        self.perf_log_file.write_text(json.dumps(log, indent=2))
        return entry

    def get_performance_report(self, agent_name: str | None = None) -> dict:
        """Get aggregated performance report."""
        log = json.loads(self.perf_log_file.read_text())
        if agent_name:
            log = [e for e in log if e.get("agent_name") == agent_name]

        if not log:
            return {"message": "No performance data available"}

        # Group by agent and metric
        report: dict[str, dict] = {}
        for entry in log:
            agent = entry["agent_name"]
            metric = entry["metric_name"]
            value = entry["metric_value"]

            report.setdefault(agent, {})
            report[agent].setdefault(metric, {"values": [], "count": 0})
            report[agent][metric]["values"].append(value)
            report[agent][metric]["count"] += 1

        # Calculate aggregates
        for agent in report:
            for metric in report[agent]:
                values = report[agent][metric]["values"]
                report[agent][metric]["avg"] = sum(values) / len(values)
                report[agent][metric]["min"] = min(values)
                report[agent][metric]["max"] = max(values)
                del report[agent][metric]["values"]  # Don't return raw values

        return report

    def run_agent_health_check(self, agent_name: str, agent_instance=None) -> dict:
        """Run a health check on an agent."""
        checks = {}

        # Check 1: Instance exists
        checks["instance_available"] = agent_instance is not None

        if not agent_instance:
            return {"agent_name": agent_name, "healthy": False, "checks": checks}

        # Check 2: Tools registered
        checks["tools_registered"] = len(getattr(agent_instance, "tools", [])) > 0
        checks["tool_count"] = len(getattr(agent_instance, "tools", []))

        # Check 3: System prompt loaded
        checks["prompt_loaded"] = bool(getattr(agent_instance, "system_prompt", ""))
        checks["prompt_length"] = len(getattr(agent_instance, "system_prompt", ""))

        # Check 4: Logger working
        checks["logger_active"] = hasattr(agent_instance, "logger")

        # Check 5: API client configured
        checks["api_client_ready"] = hasattr(agent_instance, "client") and agent_instance.client is not None

        healthy = all([
            checks["instance_available"],
            checks["tools_registered"],
            checks["prompt_loaded"],
            checks["api_client_ready"],
        ])

        return {
            "agent_name": agent_name,
            "healthy": healthy,
            "checks": checks,
            "timestamp": datetime.now().isoformat(),
        }

    def get_test_results(
        self, agent_name: str | None = None, limit: int = 10
    ) -> list[dict]:
        """Get test results history."""
        results = json.loads(self.test_results_file.read_text())
        if agent_name:
            results = [r for r in results if r.get("agent_name") == agent_name]
        return results[-limit:]

    def handle_tool_call(self, tool_name: str, tool_input: dict, agents: dict | None = None) -> Any:
        """Route tool calls."""
        agents = agents or {}
        agent_name = tool_input.get("agent_name", "")
        agent_instance = agents.get(agent_name)

        dispatch = {
            "test_agent": lambda: self.test_agent(
                agent_name, tool_input["test_prompt"],
                tool_input.get("expected_keywords"), agent_instance
            ),
            "evaluate_agent_output": lambda: self.evaluate_agent_output(**tool_input),
            "log_agent_performance": lambda: self.log_agent_performance(**tool_input),
            "get_performance_report": lambda: self.get_performance_report(
                tool_input.get("agent_name")
            ),
            "run_agent_health_check": lambda: self.run_agent_health_check(agent_name, agent_instance),
            "get_test_results": lambda: self.get_test_results(**tool_input),
        }
        handler = dispatch.get(tool_name)
        if handler:
            return handler()
        return {"error": f"Unknown monitor tool: {tool_name}"}
