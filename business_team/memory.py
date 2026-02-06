"""
Agent Memory -- Persistent context that survives conversation resets.

Short-term memory: recent interactions (in-memory, last N items).
Long-term memory: learned facts, preferences, patterns (persisted to JSON).

Usage:
    from business_team.memory import AgentMemory
    memory = AgentMemory()
    memory.remember("preferred_report_format", "pdf", category="user_preferences")
    results = memory.recall("report")
    summary = memory.get_context_summary()
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from business_team import config


class AgentMemory:
    """Persistent memory for business team agents.

    Provides two tiers of memory:
      - short_term: a bounded in-memory list of recent interactions
      - long_term: categorized key-value facts persisted to a JSON file
    """

    CATEGORIES = [
        "user_preferences",
        "recurring_tasks",
        "important_contacts",
        "project_context",
        "learned_patterns",
        "agent_feedback",
    ]

    def __init__(self, memory_file=None, max_short_term: int = 20):
        """Initialize agent memory.

        Args:
            memory_file: Path to the JSON file for long-term memory persistence.
                         Defaults to config.DATA_DIR / 'agent_memory.json'.
            max_short_term: Maximum number of short-term interaction entries
                           to keep in memory.
        """
        self.memory_file = (
            Path(memory_file)
            if memory_file
            else config.DATA_DIR / "agent_memory.json"
        )
        self.max_short_term = max_short_term
        self.short_term: list[dict] = []  # Recent interactions
        self.long_term: dict[str, list[dict]] = {}  # Categorized persistent facts
        self.load()

    def remember(
        self, key: str, value: Any, category: str = "learned_patterns"
    ):
        """Store a fact in long-term memory.

        If a fact with the same key already exists in the given category,
        its value and timestamp are updated in place. Otherwise a new
        entry is appended.

        Args:
            key: A short identifier for the fact.
            value: The value to store (must be JSON-serialisable).
            category: One of CATEGORIES. Falls back to 'learned_patterns'.
        """
        if category not in self.CATEGORIES:
            category = "learned_patterns"
        if category not in self.long_term:
            self.long_term[category] = []

        entry = {
            "key": key,
            "value": value,
            "remembered_at": datetime.now().isoformat(),
            "access_count": 0,
        }

        # Update if key already exists
        existing = [
            e for e in self.long_term[category] if e["key"] == key
        ]
        if existing:
            existing[0]["value"] = value
            existing[0]["remembered_at"] = datetime.now().isoformat()
        else:
            self.long_term[category].append(entry)
        self.save()

    def recall(
        self, query: str = "", category: str = None
    ) -> list[dict]:
        """Recall facts from long-term memory.

        Optionally filter by category or keyword. Matching is
        case-insensitive against both key and value fields.

        Args:
            query: A search string to match against keys and values.
            category: If provided, restrict search to this category.

        Returns:
            A list of matching memory entries, each augmented with a
            'category' field.
        """
        results = []
        categories = [category] if category else self.CATEGORIES
        for cat in categories:
            for entry in self.long_term.get(cat, []):
                if (
                    not query
                    or query.lower()
                    in str(entry.get("key", "")).lower()
                    or query.lower()
                    in str(entry.get("value", "")).lower()
                ):
                    entry["access_count"] = (
                        entry.get("access_count", 0) + 1
                    )
                    results.append({**entry, "category": cat})
        return results

    def add_interaction(
        self,
        agent_name: str,
        user_input: str,
        response_summary: str,
    ):
        """Add an interaction record to short-term memory.

        Older entries are evicted once max_short_term is exceeded.

        Args:
            agent_name: The name of the agent that handled the interaction.
            user_input: The user's original input (truncated to 200 chars).
            response_summary: A brief summary of the response (truncated
                              to 200 chars).
        """
        self.short_term.append(
            {
                "agent": agent_name,
                "input": user_input[:200],
                "response": response_summary[:200],
                "timestamp": datetime.now().isoformat(),
            }
        )
        if len(self.short_term) > self.max_short_term:
            self.short_term = self.short_term[-self.max_short_term :]

    def get_context_summary(self, max_items: int = 10) -> str:
        """Generate a context summary string for injecting into agent prompts.

        Args:
            max_items: Maximum number of entries per category to include.

        Returns:
            A human-readable string summarising recent interactions and
            stored long-term facts, or a fallback message if empty.
        """
        parts = []

        # Recent interactions
        if self.short_term:
            parts.append("RECENT CONTEXT:")
            for item in self.short_term[-5:]:
                parts.append(
                    f"  [{item['agent']}] {item['input'][:80]}"
                )

        # Key facts by category
        for cat in self.CATEGORIES:
            items = self.long_term.get(cat, [])
            if items:
                parts.append(
                    f"\n{cat.upper().replace('_', ' ')}:"
                )
                for item in items[-max_items:]:
                    parts.append(
                        f"  - {item['key']}: "
                        f"{str(item['value'])[:100]}"
                    )

        return (
            "\n".join(parts) if parts else "No prior context available."
        )

    def forget(self, key: str, category: str = None) -> bool:
        """Remove a fact from long-term memory.

        Args:
            key: The key of the fact to remove.
            category: If provided, only search in this category.
                      Otherwise search all categories.

        Returns:
            True if a fact was removed, False otherwise.
        """
        categories = [category] if category else self.CATEGORIES
        for cat in categories:
            before = len(self.long_term.get(cat, []))
            self.long_term[cat] = [
                e
                for e in self.long_term.get(cat, [])
                if e["key"] != key
            ]
            if len(self.long_term.get(cat, [])) < before:
                self.save()
                return True
        return False

    def save(self):
        """Persist long-term memory to disk."""
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "long_term": self.long_term,
            "saved_at": datetime.now().isoformat(),
        }
        self.memory_file.write_text(json.dumps(data, indent=2))

    def load(self):
        """Load long-term memory from disk.

        If the file does not exist or is corrupt, starts with empty memory.
        """
        if self.memory_file.exists():
            try:
                data = json.loads(self.memory_file.read_text())
                self.long_term = data.get("long_term", {})
            except (json.JSONDecodeError, KeyError):
                self.long_term = {}
        else:
            self.long_term = {}

    def get_stats(self) -> dict:
        """Return memory statistics.

        Returns:
            A dict with counts for short-term and long-term memory,
            per-category breakdowns, and the memory file path.
        """
        total_facts = sum(len(v) for v in self.long_term.values())
        return {
            "short_term_count": len(self.short_term),
            "long_term_count": total_facts,
            "categories": {
                cat: len(self.long_term.get(cat, []))
                for cat in self.CATEGORIES
            },
            "memory_file": str(self.memory_file),
        }
