import os
import sqlite3
from datetime import datetime


SCHEMA = """
CREATE TABLE IF NOT EXISTS decisions (
    job_id TEXT PRIMARY KEY,
    vote TEXT NOT NULL,
    note TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS job_states (
    job_id TEXT PRIMARY KEY,
    score REAL NOT NULL,
    recommendation TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def _db_path(config):
    db_cfg = config.get("db", {})
    env = db_cfg.get("env", "prod")
    if env == "dev":
        return db_cfg.get("dev_path", "db/applicant_dev.db")
    return db_cfg.get("path", "db/applicant.db")


def db_enabled(config):
    return bool(config.get("db", {}).get("enabled", False))


def init_db(config):
    path = _db_path(config)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.executescript(SCHEMA)


def load_votes(config):
    path = _db_path(config)
    if not os.path.exists(path):
        return {}
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT job_id, vote, note, updated_at FROM decisions").fetchall()
    votes = {}
    for row in rows:
        votes[row["job_id"]] = {
            "vote": row["vote"],
            "note": row["note"],
            "updated_at": row["updated_at"],
        }
    return votes


def upsert_vote(config, job_id, vote, note):
    path = _db_path(config)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    updated_at = datetime.utcnow().isoformat() + "Z"
    with sqlite3.connect(path) as conn:
        conn.executescript(SCHEMA)
        conn.execute(
            "INSERT INTO decisions (job_id, vote, note, updated_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(job_id) DO UPDATE SET vote=excluded.vote, note=excluded.note, updated_at=excluded.updated_at",
            (job_id, vote, note, updated_at),
        )
    return updated_at


def upsert_job_state(config, job_id, score, recommendation):
    path = _db_path(config)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    updated_at = datetime.utcnow().isoformat() + "Z"
    with sqlite3.connect(path) as conn:
        conn.executescript(SCHEMA)
        conn.execute(
            "INSERT INTO job_states (job_id, score, recommendation, updated_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(job_id) DO UPDATE SET score=excluded.score, recommendation=excluded.recommendation, updated_at=excluded.updated_at",
            (job_id, score, recommendation, updated_at),
        )
    return updated_at
