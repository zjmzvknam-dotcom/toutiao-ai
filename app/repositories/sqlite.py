from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from app.models.domain import Article, TaskEvent, Topic


class SQLiteRepository:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS topics (id TEXT PRIMARY KEY, title TEXT NOT NULL, payload TEXT NOT NULL, updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS articles (id TEXT PRIMARY KEY, title TEXT NOT NULL, topic TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS usage_events (id INTEGER PRIMARY KEY AUTOINCREMENT, provider TEXT, model TEXT, workflow TEXT, tokens INTEGER, estimated_cost REAL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS task_events (id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL, step TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL);
            """)
            columns = {row["name"] for row in db.execute("PRAGMA table_info(usage_events)").fetchall()}
            if "task_id" not in columns:
                db.execute("ALTER TABLE usage_events ADD COLUMN task_id TEXT")

    def save_topic(self, topic: Topic) -> None:
        with self._connect() as db:
            db.execute("INSERT OR REPLACE INTO topics VALUES (?, ?, ?, ?)", (topic.id, topic.title, topic.model_dump_json(), topic.updated_at.isoformat()))

    def list_topics(self, limit: int = 50) -> list[Topic]:
        with self._connect() as db:
            rows = db.execute("SELECT payload FROM topics ORDER BY updated_at DESC LIMIT ?", (limit,)).fetchall()
        return [Topic.model_validate_json(row["payload"]) for row in rows]

    def save_article(self, article: Article) -> None:
        with self._connect() as db:
            db.execute("INSERT OR REPLACE INTO articles VALUES (?, ?, ?, ?, ?)", (article.id, article.title, article.topic, article.model_dump_json(), article.created_at.isoformat()))

    def list_articles(self, query: str = "", limit: int = 50) -> list[Article]:
        with self._connect() as db:
            rows = db.execute("SELECT payload FROM articles WHERE title LIKE ? OR topic LIKE ? ORDER BY created_at DESC LIMIT ?", (f"%{query}%", f"%{query}%", limit)).fetchall()
        return [Article.model_validate_json(row["payload"]) for row in rows]

    def record_usage(self, provider: str, model: str, workflow: str, tokens: int = 0, estimated_cost: float = 0, task_id: str | None = None) -> None:
        with self._connect() as db:
            db.execute("INSERT INTO usage_events (provider, model, workflow, tokens, estimated_cost, task_id) VALUES (?, ?, ?, ?, ?, ?)", (provider, model, workflow, tokens, estimated_cost, task_id))

    def usage_summary(self) -> list[dict[str, object]]:
        with self._connect() as db:
            rows = db.execute("SELECT workflow, COUNT(*) requests, SUM(tokens) tokens, ROUND(SUM(estimated_cost), 6) cost FROM usage_events GROUP BY workflow ORDER BY cost DESC").fetchall()
        return [dict(row) for row in rows]

    def usage_totals(self, period: str) -> dict[str, float | int]:
        modifiers = {"today": "-0 days", "week": "-7 days", "month": "-30 days", "all": "-100 years"}
        if period not in modifiers:
            raise ValueError("unsupported usage period")
        with self._connect() as db:
            row = db.execute("SELECT COUNT(*) requests, COALESCE(SUM(tokens), 0) tokens, COALESCE(SUM(estimated_cost), 0) cost FROM usage_events WHERE created_at >= datetime('now', ?)", (modifiers[period],)).fetchone()
        return {"requests": int(row["requests"]), "tokens": int(row["tokens"]), "cost": float(row["cost"])}

    def task_usage_totals(self, task_id: str) -> dict[str, float | int]:
        with self._connect() as db:
            row = db.execute("SELECT COUNT(*) requests, COALESCE(SUM(tokens), 0) tokens, COALESCE(SUM(estimated_cost), 0) cost FROM usage_events WHERE task_id = ?", (task_id,)).fetchone()
        return {"requests": int(row["requests"]), "tokens": int(row["tokens"]), "cost": float(row["cost"])}

    def record_task_event(self, event: TaskEvent) -> None:
        with self._connect() as db:
            db.execute("INSERT INTO task_events (task_id, step, status, created_at) VALUES (?, ?, ?, ?)", (event.task_id, event.step, event.status, event.created_at.isoformat()))

    def list_task_events(self, task_id: str) -> list[TaskEvent]:
        with self._connect() as db:
            rows = db.execute("SELECT task_id, step, status, created_at FROM task_events WHERE task_id = ? ORDER BY id", (task_id,)).fetchall()
        return [TaskEvent(task_id=row["task_id"], step=row["step"], status=row["status"], created_at=row["created_at"]) for row in rows]
