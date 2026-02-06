"""
Tests for business_team.memory.AgentMemory.

Run with:
    python -m pytest business_team/tests/test_memory.py -v
"""

import json
import sys
from pathlib import Path

import pytest

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.fixture(autouse=True)
def _patch_data_dir(tmp_path, monkeypatch):
    """Redirect config.DATA_DIR to a temporary directory for every test."""
    import business_team.config as cfg

    monkeypatch.setattr(cfg, "DATA_DIR", tmp_path)


@pytest.fixture
def memory(tmp_path):
    """Create a fresh AgentMemory instance with a temp file."""
    from business_team.memory import AgentMemory

    return AgentMemory(memory_file=tmp_path / "test_memory.json")


# ------------------------------------------------------------------
# 1. remember and recall — basic store and retrieve
# ------------------------------------------------------------------
def test_remember_and_recall(memory):
    """Storing a fact with remember() and retrieving it with recall()."""
    memory.remember("boss_name", "Alice", category="important_contacts")
    results = memory.recall("boss")
    assert len(results) == 1
    assert results[0]["key"] == "boss_name"
    assert results[0]["value"] == "Alice"
    assert results[0]["category"] == "important_contacts"


# ------------------------------------------------------------------
# 2. remember updates existing key
# ------------------------------------------------------------------
def test_remember_updates_existing(memory):
    """Storing the same key twice updates the value in place."""
    memory.remember("theme", "dark", category="user_preferences")
    memory.remember("theme", "light", category="user_preferences")

    results = memory.recall("theme", category="user_preferences")
    assert len(results) == 1
    assert results[0]["value"] == "light"


# ------------------------------------------------------------------
# 3. recall by category
# ------------------------------------------------------------------
def test_recall_by_category(memory):
    """recall with a category filter only returns facts from that category."""
    memory.remember("daily_standup", "09:00", category="recurring_tasks")
    memory.remember("boss", "Charlie", category="important_contacts")

    results = memory.recall(category="recurring_tasks")
    assert len(results) == 1
    assert results[0]["key"] == "daily_standup"

    results = memory.recall(category="important_contacts")
    assert len(results) == 1
    assert results[0]["key"] == "boss"


# ------------------------------------------------------------------
# 4. recall by query keyword
# ------------------------------------------------------------------
def test_recall_by_query(memory):
    """recall with a query string matches against keys and values."""
    memory.remember("report_format", "PDF weekly", category="user_preferences")
    memory.remember("editor", "vim", category="user_preferences")

    results = memory.recall("weekly")
    assert len(results) == 1
    assert results[0]["key"] == "report_format"

    # Query matching the value
    results = memory.recall("vim")
    assert len(results) == 1
    assert results[0]["key"] == "editor"


# ------------------------------------------------------------------
# 5. add_interaction — short-term memory
# ------------------------------------------------------------------
def test_add_interaction(memory):
    """add_interaction appends to short_term list."""
    memory.add_interaction("secretary", "check emails", "Found 3 new emails")
    assert len(memory.short_term) == 1
    entry = memory.short_term[0]
    assert entry["agent"] == "secretary"
    assert entry["input"] == "check emails"
    assert entry["response"] == "Found 3 new emails"
    assert "timestamp" in entry


# ------------------------------------------------------------------
# 6. short-term limit is enforced
# ------------------------------------------------------------------
def test_short_term_limit(tmp_path):
    """Short-term memory does not exceed max_short_term."""
    from business_team.memory import AgentMemory

    mem = AgentMemory(
        memory_file=tmp_path / "test_memory.json", max_short_term=5
    )

    for i in range(10):
        mem.add_interaction("agent", f"input {i}", f"response {i}")

    assert len(mem.short_term) == 5
    # Should keep the most recent 5
    assert mem.short_term[0]["input"] == "input 5"
    assert mem.short_term[-1]["input"] == "input 9"


# ------------------------------------------------------------------
# 7. save and load — persistence to disk
# ------------------------------------------------------------------
def test_save_and_load(tmp_path):
    """Long-term memory survives save/load cycle."""
    from business_team.memory import AgentMemory

    mem_file = tmp_path / "persist_test.json"

    mem1 = AgentMemory(memory_file=mem_file)
    mem1.remember("color", "blue", category="user_preferences")
    mem1.remember("standup", "daily at 9am", category="recurring_tasks")

    # Create a new instance from the same file
    mem2 = AgentMemory(memory_file=mem_file)
    results = mem2.recall("color")
    assert len(results) == 1
    assert results[0]["value"] == "blue"

    results = mem2.recall("standup")
    assert len(results) == 1
    assert results[0]["value"] == "daily at 9am"


# ------------------------------------------------------------------
# 8. get_context_summary — generates summary string
# ------------------------------------------------------------------
def test_get_context_summary(memory):
    """get_context_summary produces a formatted string with stored data."""
    memory.add_interaction("secretary", "read my emails", "5 new emails")
    memory.remember("preferred_channel", "email", category="user_preferences")

    summary = memory.get_context_summary()
    assert "RECENT CONTEXT:" in summary
    assert "secretary" in summary
    assert "USER PREFERENCES:" in summary
    assert "preferred_channel" in summary
    assert "email" in summary


# ------------------------------------------------------------------
# 9. get_context_summary — empty memory
# ------------------------------------------------------------------
def test_get_context_summary_empty(memory):
    """get_context_summary returns fallback text when memory is empty."""
    summary = memory.get_context_summary()
    assert summary == "No prior context available."


# ------------------------------------------------------------------
# 10. forget — removes a fact
# ------------------------------------------------------------------
def test_forget(memory):
    """forget() removes a fact by key and returns True."""
    memory.remember("temp_fact", "remove me", category="learned_patterns")

    removed = memory.forget("temp_fact")
    assert removed is True

    results = memory.recall("temp_fact")
    assert len(results) == 0


# ------------------------------------------------------------------
# 11. forget — returns False when key not found
# ------------------------------------------------------------------
def test_forget_not_found(memory):
    """forget() returns False when the key does not exist."""
    removed = memory.forget("nonexistent_key")
    assert removed is False


# ------------------------------------------------------------------
# 12. get_stats — returns memory statistics
# ------------------------------------------------------------------
def test_get_stats(memory):
    """get_stats returns counts and category breakdown."""
    memory.remember("fact1", "val1", category="user_preferences")
    memory.remember("fact2", "val2", category="user_preferences")
    memory.remember("fact3", "val3", category="project_context")
    memory.add_interaction("agent", "hi", "hello")

    stats = memory.get_stats()
    assert stats["short_term_count"] == 1
    assert stats["long_term_count"] == 3
    assert stats["categories"]["user_preferences"] == 2
    assert stats["categories"]["project_context"] == 1
    assert stats["categories"]["learned_patterns"] == 0
    assert "memory_file" in stats


# ------------------------------------------------------------------
# 13. invalid category falls back to learned_patterns
# ------------------------------------------------------------------
def test_invalid_category_fallback(memory):
    """Passing an invalid category falls back to learned_patterns."""
    memory.remember("misc", "data", category="nonexistent_category")
    results = memory.recall("misc", category="learned_patterns")
    assert len(results) == 1
    assert results[0]["value"] == "data"


# ------------------------------------------------------------------
# 14. load handles corrupt JSON gracefully
# ------------------------------------------------------------------
def test_load_corrupt_json(tmp_path):
    """If the memory file contains invalid JSON, load starts with empty memory."""
    from business_team.memory import AgentMemory

    mem_file = tmp_path / "corrupt.json"
    mem_file.write_text("{not valid json!!!")

    mem = AgentMemory(memory_file=mem_file)
    assert mem.long_term == {}
