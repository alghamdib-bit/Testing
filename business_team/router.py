"""
Smart Request Router -- Classifies requests and routes to the best agent.

Replaces keyword-based routing with weighted scoring across keyword matches
and pattern matches to determine which agent should handle a given request.

Usage:
    from business_team.router import SmartRouter, RoutingDecision
    router = SmartRouter()
    decision = router.route("check my emails and schedule a meeting")
    print(decision.agent_name, decision.confidence)
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RoutingDecision:
    """Result of routing analysis.

    Attributes:
        agent_name: The primary agent selected to handle the request.
        confidence: A float between 0.0 and 1.0 indicating match strength.
        reasoning: A human-readable explanation of the routing decision.
        request_type: One of 'question', 'action', 'report', 'development'.
        secondary_agents: Additional agents that might assist.
    """

    agent_name: str
    confidence: float  # 0.0 to 1.0
    reasoning: str
    request_type: str  # "question", "action", "report", "development"
    secondary_agents: list[str] = field(default_factory=list)


class SmartRouter:
    """Intelligent request router for the business team.

    Scores each agent based on keyword and pattern matches against the
    incoming request, then selects the highest-scoring agent. Falls back
    to chief_of_staff when no strong match is found.
    """

    # Agent capability definitions
    AGENT_CAPABILITIES = {
        "secretary": {
            "keywords": [
                "email",
                "mail",
                "inbox",
                "send",
                "compose",
                "reply",
                "calendar",
                "schedule",
                "meeting",
                "appointment",
                "event",
                "todo",
                "task list",
                "reminder",
                "to-do",
                "to do",
                "digest",
                "briefing",
                "summary",
            ],
            "patterns": [
                "check my",
                "read my",
                "what meetings",
                "am i free",
                "schedule a",
                "add to calendar",
                "add todo",
                "pending tasks",
                "daily digest",
                "morning brief",
                "inbox",
            ],
            "description": "Email, calendar, and to-do management",
        },
        "business_analyst": {
            "keywords": [
                "spl",
                "channel",
                "digital",
                "dashboard",
                "analytics",
                "kpi",
                "metric",
                "performance",
                "presentation",
                "powerpoint",
                "pptx",
                "slide",
                "traffic",
                "conversion",
                "bounce rate",
                "website",
                "mobile app",
                "customer portal",
                "api services",
            ],
            "patterns": [
                "spl report",
                "channel performance",
                "create dashboard",
                "create presentation",
                "digital channels",
                "how is the website",
                "mobile app stats",
                "prepare slides",
            ],
            "description": "SPL Digital Channels monitoring and reporting",
        },
        "projects_manager": {
            "keywords": [
                "project",
                "milestone",
                "sprint",
                "progress",
                "timeline",
                "deadline",
                "deliverable",
                "status board",
                "kanban",
                "weekly report",
                "monthly report",
                "resource",
                "allocation",
                "backlog",
                "velocity",
                "burndown",
            ],
            "patterns": [
                "project status",
                "how is project",
                "update on project",
                "project report",
                "task status",
                "who is working on",
                "create project",
                "add task",
                "weekly update",
                "monthly update",
            ],
            "description": "Project tracking, task management, and reporting",
        },
        "chief_of_staff": {
            "keywords": [
                "develop",
                "improve",
                "upgrade",
                "enhance",
                "modify",
                "agent",
                "capability",
                "prompt",
                "audit",
                "health check",
                "test agent",
                "reload",
                "backup",
                "restore",
                "team",
                "coordinate",
                "plan",
                "strategy",
            ],
            "patterns": [
                "improve the",
                "add capability",
                "modify agent",
                "change prompt",
                "create tool",
                "teach the",
                "run audit",
                "test all",
                "team status",
                "daily brief",
                "weekly brief",
            ],
            "description": (
                "Team supervision, agent development, executive briefings"
            ),
        },
    }

    REQUEST_TYPE_KEYWORDS = {
        "question": [
            "what",
            "how",
            "when",
            "where",
            "who",
            "is",
            "are",
            "can",
            "?",
        ],
        "action": [
            "create",
            "send",
            "add",
            "update",
            "delete",
            "schedule",
            "generate",
            "make",
        ],
        "report": [
            "report",
            "summary",
            "status",
            "dashboard",
            "brief",
            "digest",
            "overview",
        ],
        "development": [
            "develop",
            "improve",
            "upgrade",
            "modify",
            "fix",
            "enhance",
            "build",
        ],
    }

    def route(self, request: str) -> RoutingDecision:
        """Analyze a request and determine the best agent to handle it.

        Args:
            request: The user's natural-language request string.

        Returns:
            A RoutingDecision with the selected agent, confidence score,
            reasoning, request type, and any secondary agents.
        """
        request_lower = request.lower()
        request_type = self._classify_request_type(request_lower)

        scores = {}
        for agent_name, capabilities in self.AGENT_CAPABILITIES.items():
            score = self._score_agent(request_lower, capabilities)
            scores[agent_name] = score

        # Sort by score descending
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        best_agent = ranked[0][0]
        best_score = ranked[0][1]

        # Normalize confidence to 0-1 range
        max_possible = 10.0  # approximate max score
        confidence = min(best_score / max_possible, 1.0)

        # If confidence is very low, default to chief_of_staff
        if confidence < 0.1:
            best_agent = "chief_of_staff"
            confidence = 0.5
            reasoning = (
                "No strong match found; routing to Chief of Staff "
                "for triage."
            )
        else:
            reasoning = (
                f"Matched {best_agent} with score {best_score:.1f} "
                f"based on keyword/pattern analysis."
            )

        # Secondary agents (score > 0 and not the primary)
        secondary = [
            name for name, score in ranked[1:] if score > 0
        ]

        return RoutingDecision(
            agent_name=best_agent,
            confidence=confidence,
            reasoning=reasoning,
            request_type=request_type,
            secondary_agents=secondary[:2],
        )

    def _score_agent(
        self, request: str, capabilities: dict
    ) -> float:
        """Score how well an agent matches a request.

        Keyword matches contribute 1.0 points each.
        Pattern matches contribute 2.0 points each (they are more specific).

        Args:
            request: The lowered request string.
            capabilities: A dict with 'keywords' and 'patterns' lists.

        Returns:
            A float score (higher = better match).
        """
        score = 0.0

        # Keyword matching (1 point each)
        for keyword in capabilities["keywords"]:
            if keyword in request:
                score += 1.0

        # Pattern matching (2 points each -- more specific)
        for pattern in capabilities["patterns"]:
            if pattern in request:
                score += 2.0

        return score

    def _classify_request_type(self, request: str) -> str:
        """Classify the type of request.

        Args:
            request: The lowered request string.

        Returns:
            One of 'question', 'action', 'report', 'development'.
            Defaults to 'question' if no keywords match.
        """
        scores = {}
        for rtype, keywords in self.REQUEST_TYPE_KEYWORDS.items():
            scores[rtype] = sum(
                1 for kw in keywords if kw in request
            )

        if not any(scores.values()):
            return "question"
        return max(scores, key=scores.get)

    def route_multi(self, request: str) -> list[RoutingDecision]:
        """Route a request that may need multiple agents.

        Returns the primary routing decision, plus any secondary agents
        that scored high enough to be worth involving.

        Args:
            request: The user's natural-language request string.

        Returns:
            A list of RoutingDecision objects. The first element is the
            primary decision; subsequent elements are secondary agents.
        """
        primary = self.route(request)
        results = [primary]

        # Check if secondary agents have significant scores
        request_lower = request.lower()
        for agent_name in primary.secondary_agents:
            caps = self.AGENT_CAPABILITIES.get(agent_name, {})
            score = self._score_agent(request_lower, caps)
            if score >= 2.0:  # Significant enough to involve
                results.append(
                    RoutingDecision(
                        agent_name=agent_name,
                        confidence=min(score / 10.0, 1.0),
                        reasoning=f"Secondary match for {agent_name}",
                        request_type=primary.request_type,
                        secondary_agents=[],
                    )
                )

        return results
