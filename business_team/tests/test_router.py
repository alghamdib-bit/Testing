"""
Tests for business_team.router.SmartRouter.

Run with:
    python -m pytest business_team/tests/test_router.py -v
"""

import sys
from pathlib import Path

import pytest

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from business_team.router import RoutingDecision, SmartRouter


@pytest.fixture
def router():
    """Provide a fresh SmartRouter instance."""
    return SmartRouter()


# ------------------------------------------------------------------
# 1. Route email request to secretary
# ------------------------------------------------------------------
def test_route_email_to_secretary(router):
    """'check my emails' should route to the secretary agent."""
    decision = router.route("check my emails")
    assert decision.agent_name == "secretary"
    assert decision.confidence > 0.0
    assert isinstance(decision.reasoning, str)
    assert len(decision.reasoning) > 0


# ------------------------------------------------------------------
# 2. Route SPL/dashboard request to business_analyst
# ------------------------------------------------------------------
def test_route_spl_to_analyst(router):
    """'spl dashboard analytics' should route to business_analyst."""
    decision = router.route("spl dashboard analytics")
    assert decision.agent_name == "business_analyst"
    assert decision.confidence > 0.0


# ------------------------------------------------------------------
# 3. Route project request to projects_manager
# ------------------------------------------------------------------
def test_route_project_to_pm(router):
    """'project status update' should route to projects_manager."""
    decision = router.route("project status update")
    assert decision.agent_name == "projects_manager"


# ------------------------------------------------------------------
# 4. Route development request to chief_of_staff
# ------------------------------------------------------------------
def test_route_develop_to_cos(router):
    """'improve the secretary agent' should route to chief_of_staff."""
    decision = router.route("improve the secretary agent")
    assert decision.agent_name == "chief_of_staff"


# ------------------------------------------------------------------
# 5. Vague/unknown request defaults to chief_of_staff
# ------------------------------------------------------------------
def test_route_unknown_defaults(router):
    """A completely vague request should default to chief_of_staff."""
    decision = router.route("xyzzy foobar baz")
    assert decision.agent_name == "chief_of_staff"
    assert decision.confidence == 0.5
    assert "No strong match" in decision.reasoning


# ------------------------------------------------------------------
# 6. Multi-agent routing for cross-domain request
# ------------------------------------------------------------------
def test_route_multi_agents(router):
    """'email about the project deadline' involves secretary + projects_manager."""
    decisions = router.route_multi("email about the project deadline")
    assert len(decisions) >= 1

    agent_names = [d.agent_name for d in decisions]
    # Primary should be one of the two relevant agents
    assert decisions[0].agent_name in ("secretary", "projects_manager")

    # If both agents scored high enough, both should appear
    if len(decisions) > 1:
        other_names = agent_names[1:]
        # The other relevant agent should be present
        assert (
            "secretary" in other_names
            or "projects_manager" in other_names
        )


# ------------------------------------------------------------------
# 7. Classify request type
# ------------------------------------------------------------------
def test_classify_request_type(router):
    """_classify_request_type identifies question, action, report, development."""
    assert router._classify_request_type("what is the status?") == "question"
    assert router._classify_request_type("create a new dashboard") == "action"
    assert router._classify_request_type("generate weekly report summary") == "report"
    assert router._classify_request_type("improve and upgrade the agent") == "development"


# ------------------------------------------------------------------
# 8. Confidence scoring — high match vs low match
# ------------------------------------------------------------------
def test_confidence_scoring(router):
    """A request with many matching keywords has higher confidence."""
    high_match = router.route(
        "check my email inbox and read my mail and compose a reply"
    )
    low_match = router.route("maybe send something")

    assert high_match.confidence > low_match.confidence
    assert high_match.agent_name == "secretary"


# ------------------------------------------------------------------
# 9. RoutingDecision dataclass fields
# ------------------------------------------------------------------
def test_routing_decision_fields():
    """RoutingDecision has all expected fields with correct types."""
    rd = RoutingDecision(
        agent_name="secretary",
        confidence=0.8,
        reasoning="Keyword match",
        request_type="action",
        secondary_agents=["projects_manager"],
    )
    assert rd.agent_name == "secretary"
    assert rd.confidence == 0.8
    assert rd.reasoning == "Keyword match"
    assert rd.request_type == "action"
    assert rd.secondary_agents == ["projects_manager"]


# ------------------------------------------------------------------
# 10. RoutingDecision default for secondary_agents
# ------------------------------------------------------------------
def test_routing_decision_default_secondary():
    """RoutingDecision.secondary_agents defaults to empty list."""
    rd = RoutingDecision(
        agent_name="secretary",
        confidence=0.5,
        reasoning="test",
        request_type="question",
    )
    assert rd.secondary_agents == []


# ------------------------------------------------------------------
# 11. request_type is included in routing decision
# ------------------------------------------------------------------
def test_route_includes_request_type(router):
    """The route decision includes a valid request_type field."""
    decision = router.route("create a presentation for the spl dashboard")
    assert decision.request_type in (
        "question",
        "action",
        "report",
        "development",
    )


# ------------------------------------------------------------------
# 12. route_multi returns at least the primary decision
# ------------------------------------------------------------------
def test_route_multi_always_has_primary(router):
    """route_multi always returns at least one RoutingDecision."""
    decisions = router.route_multi("hello")
    assert len(decisions) >= 1
    assert isinstance(decisions[0], RoutingDecision)


# ------------------------------------------------------------------
# 13. _score_agent returns zero for unrelated input
# ------------------------------------------------------------------
def test_score_agent_zero_for_unrelated(router):
    """An agent scores 0 when the request has no matching keywords."""
    caps = SmartRouter.AGENT_CAPABILITIES["secretary"]
    score = router._score_agent("astrophysics quantum theory", caps)
    assert score == 0.0


# ------------------------------------------------------------------
# 14. _score_agent awards more for patterns than keywords
# ------------------------------------------------------------------
def test_score_agent_pattern_bonus(router):
    """Pattern matches (2 pts) score higher than keyword matches (1 pt)."""
    caps = SmartRouter.AGENT_CAPABILITIES["secretary"]

    # "check my" is a pattern (2pts) AND "email" is a keyword (1pt)
    score_with_pattern = router._score_agent("check my email", caps)
    # "email" alone is just a keyword (1pt)
    score_keyword_only = router._score_agent("email", caps)

    assert score_with_pattern > score_keyword_only
