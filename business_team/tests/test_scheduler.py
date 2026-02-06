"""
Tests for business_team.scheduler.Scheduler.

Run with:
    python -m pytest business_team/tests/test_scheduler.py -v
"""

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.fixture(autouse=True)
def _patch_data_dir(tmp_path, monkeypatch):
    """Redirect config.DATA_DIR to a temporary directory for every test."""
    import business_team.config as cfg

    monkeypatch.setattr(cfg, "DATA_DIR", tmp_path)


# ------------------------------------------------------------------
# 1. Scheduler initializes without agents
# ------------------------------------------------------------------
def test_scheduler_initializes():
    """Scheduler can be created with no manager or poller."""
    from business_team.scheduler import Scheduler

    s = Scheduler()
    assert s.manager is None
    assert s.poller is None
    assert s._running is False
    assert s._thread is None


# ------------------------------------------------------------------
# 2. Scheduled jobs are set up
# ------------------------------------------------------------------
def test_scheduler_setup_jobs():
    """After init, the internal schedule should have 4 jobs configured."""
    from business_team.scheduler import Scheduler

    s = Scheduler()
    jobs = s._schedule.get_jobs()
    assert len(jobs) == 4, f"Expected 4 jobs, got {len(jobs)}"


# ------------------------------------------------------------------
# 3. get_upcoming_jobs returns structured data
# ------------------------------------------------------------------
def test_scheduler_get_upcoming_jobs():
    """get_upcoming_jobs returns a non-empty list of dicts with expected keys."""
    from business_team.scheduler import Scheduler

    s = Scheduler()
    upcoming = s.get_upcoming_jobs()
    assert isinstance(upcoming, list)
    assert len(upcoming) == 4
    for job in upcoming:
        assert "job_name" in job
        assert "next_run" in job


# ------------------------------------------------------------------
# 4. run_now triggers daily_brief via manager
# ------------------------------------------------------------------
def test_scheduler_run_now_daily_brief(tmp_path):
    """run_now('daily_brief') calls manager.generate_daily_brief()."""
    from business_team.scheduler import Scheduler

    mock_mgr = MagicMock()
    mock_mgr.generate_daily_brief.return_value = "Brief content here"

    s = Scheduler(manager=mock_mgr)
    result = s.run_now("daily_brief")
    assert result == "Executed daily_brief"
    mock_mgr.generate_daily_brief.assert_called_once()


# ------------------------------------------------------------------
# 5. run_now triggers email_poll via poller
# ------------------------------------------------------------------
def test_scheduler_run_now_email_poll(tmp_path):
    """run_now('email_poll') calls poller.poll_once()."""
    from business_team.scheduler import Scheduler

    mock_poller = MagicMock()
    mock_poller.poll_once.return_value = {"summary": "No new emails"}

    s = Scheduler(poller=mock_poller)
    result = s.run_now("email_poll")
    assert result == "Executed email_poll"
    mock_poller.poll_once.assert_called_once()


# ------------------------------------------------------------------
# 6. run_now with unknown job name
# ------------------------------------------------------------------
def test_scheduler_run_now_unknown():
    """run_now with an invalid job name returns an error message."""
    from business_team.scheduler import Scheduler

    s = Scheduler()
    result = s.run_now("nonexistent_job")
    assert "Unknown job" in result
    assert "nonexistent_job" in result


# ------------------------------------------------------------------
# 7. stop sets _running to False
# ------------------------------------------------------------------
def test_scheduler_stop(capsys):
    """stop() sets _running to False and prints a message."""
    from business_team.scheduler import Scheduler

    s = Scheduler()
    s._running = True
    s.stop()
    assert s._running is False
    captured = capsys.readouterr()
    assert "Scheduler stopped" in captured.out


# ------------------------------------------------------------------
# 8. _log_execution creates log entries
# ------------------------------------------------------------------
def test_scheduler_log_execution(tmp_path):
    """_log_execution writes structured entries to the log file."""
    from business_team.scheduler import Scheduler

    s = Scheduler()
    # Log file path is based on patched DATA_DIR
    s._log_execution("daily_brief", "success", "Generated brief")
    s._log_execution("email_poll", "error", "Connection refused")

    assert s.log_file.exists()
    entries = json.loads(s.log_file.read_text())
    assert len(entries) == 2
    assert entries[0]["job_name"] == "daily_brief"
    assert entries[0]["status"] == "success"
    assert entries[0]["details"] == "Generated brief"
    assert entries[1]["job_name"] == "email_poll"
    assert entries[1]["status"] == "error"
    assert "timestamp" in entries[0]


# ------------------------------------------------------------------
# 9. get_log returns recent entries
# ------------------------------------------------------------------
def test_scheduler_get_log(tmp_path):
    """get_log returns the most recent entries up to the limit."""
    from business_team.scheduler import Scheduler

    s = Scheduler()
    # Write 5 entries
    for i in range(5):
        s._log_execution(f"job_{i}", "success", f"Detail {i}")

    log = s.get_log(limit=3)
    assert len(log) == 3
    # Most recent 3 should be jobs 2, 3, 4
    assert log[0]["job_name"] == "job_2"
    assert log[2]["job_name"] == "job_4"


# ------------------------------------------------------------------
# 10. get_log on empty/missing file returns empty list
# ------------------------------------------------------------------
def test_scheduler_get_log_empty():
    """get_log returns an empty list when no log file exists."""
    from business_team.scheduler import Scheduler

    s = Scheduler()
    log = s.get_log()
    assert log == []


# ------------------------------------------------------------------
# 11. _run_daily_brief handles exceptions gracefully
# ------------------------------------------------------------------
def test_scheduler_daily_brief_error(tmp_path):
    """If manager.generate_daily_brief raises, it is logged as error."""
    from business_team.scheduler import Scheduler

    mock_mgr = MagicMock()
    mock_mgr.generate_daily_brief.side_effect = RuntimeError("API down")

    s = Scheduler(manager=mock_mgr)
    s._run_daily_brief()

    entries = json.loads(s.log_file.read_text())
    assert len(entries) == 1
    assert entries[0]["status"] == "error"
    assert "API down" in entries[0]["details"]


# ------------------------------------------------------------------
# 12. start_background and stop lifecycle
# ------------------------------------------------------------------
def test_scheduler_background_lifecycle():
    """start_background starts a daemon thread; stop joins it."""
    from business_team.scheduler import Scheduler

    s = Scheduler()
    s.start_background()
    assert s._running is True
    assert s._thread is not None
    assert s._thread.is_alive()

    s.stop()
    assert s._running is False
    # Thread should terminate within the join timeout
    assert not s._thread.is_alive()
