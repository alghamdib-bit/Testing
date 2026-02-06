-- 001_initial_schema.sql
-- Initial database schema for Business Team Multi-Agent System.
-- Migrates all JSON flat-file storage to normalized SQLite tables.

-- Enable WAL mode for better concurrent read performance.
PRAGMA journal_mode=WAL;

-- ============================================================
-- Projects
-- ============================================================
CREATE TABLE IF NOT EXISTS projects (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    owner           TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active', 'on_hold', 'completed', 'at_risk')),
    progress_percent INTEGER NOT NULL DEFAULT 0
                        CHECK (progress_percent BETWEEN 0 AND 100),
    start_date      TEXT NOT NULL,
    target_end_date TEXT NOT NULL,
    milestones      TEXT NOT NULL DEFAULT '[]',   -- JSON array
    notes_history   TEXT NOT NULL DEFAULT '[]',   -- JSON array
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

-- ============================================================
-- Tasks
-- ============================================================
CREATE TABLE IF NOT EXISTS tasks (
    id              TEXT PRIMARY KEY,
    project_id      TEXT NOT NULL,
    title           TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    assignee        TEXT NOT NULL,
    priority        TEXT NOT NULL DEFAULT 'medium'
                        CHECK (priority IN ('high', 'medium', 'low')),
    status          TEXT NOT NULL DEFAULT 'todo'
                        CHECK (status IN ('todo', 'in_progress', 'review', 'done', 'blocked')),
    progress_percent INTEGER NOT NULL DEFAULT 0
                        CHECK (progress_percent BETWEEN 0 AND 100),
    due_date        TEXT NOT NULL DEFAULT '',
    notes_history   TEXT NOT NULL DEFAULT '[]',   -- JSON array
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE INDEX IF NOT EXISTS idx_tasks_project_id ON tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status     ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_assignee   ON tasks(assignee);

-- ============================================================
-- Todos
-- ============================================================
CREATE TABLE IF NOT EXISTS todos (
    id              TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    priority        TEXT NOT NULL DEFAULT 'medium'
                        CHECK (priority IN ('high', 'medium', 'low')),
    status          TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'in_progress', 'completed', 'overdue')),
    due_date        TEXT NOT NULL DEFAULT '',
    assignee        TEXT NOT NULL DEFAULT '',
    category        TEXT NOT NULL DEFAULT 'general',
    notes           TEXT NOT NULL DEFAULT '',
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_todos_status   ON todos(status);
CREATE INDEX IF NOT EXISTS idx_todos_priority ON todos(priority);

-- ============================================================
-- Email Log
-- ============================================================
CREATE TABLE IF NOT EXISTS email_log (
    email_id        TEXT PRIMARY KEY,
    subject         TEXT NOT NULL,
    sender          TEXT NOT NULL,
    summary         TEXT NOT NULL DEFAULT '',
    priority        TEXT NOT NULL DEFAULT 'medium'
                        CHECK (priority IN ('high', 'medium', 'low')),
    action_required INTEGER NOT NULL DEFAULT 0,  -- boolean: 0/1
    action_items    TEXT NOT NULL DEFAULT '[]',   -- JSON array
    logged_at       TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_email_log_priority  ON email_log(priority);
CREATE INDEX IF NOT EXISTS idx_email_log_logged_at ON email_log(logged_at);

-- ============================================================
-- Calendar Events
-- ============================================================
CREATE TABLE IF NOT EXISTS calendar_events (
    id              TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    date            TEXT NOT NULL,
    start_time      TEXT NOT NULL,
    end_time        TEXT NOT NULL,
    location        TEXT NOT NULL DEFAULT '',
    attendees       TEXT NOT NULL DEFAULT '[]',   -- JSON array
    priority        TEXT NOT NULL DEFAULT 'medium'
                        CHECK (priority IN ('high', 'medium', 'low')),
    notes           TEXT NOT NULL DEFAULT '',
    created_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_calendar_events_date ON calendar_events(date);

-- ============================================================
-- Activity Log  (audit trail for all agent actions)
-- ============================================================
CREATE TABLE IF NOT EXISTS activity_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    agent           TEXT NOT NULL,
    activity_type   TEXT NOT NULL,
    details         TEXT NOT NULL DEFAULT '',
    created_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_activity_log_agent      ON activity_log(agent);
CREATE INDEX IF NOT EXISTS idx_activity_log_created_at ON activity_log(created_at);

-- ============================================================
-- Schema version tracking
-- ============================================================
CREATE TABLE IF NOT EXISTS schema_version (
    version     INTEGER PRIMARY KEY,
    applied_at  TEXT NOT NULL
);

INSERT OR IGNORE INTO schema_version (version, applied_at)
VALUES (1, datetime('now'));
