"""
storage.py - Saves everything locally so nothing is lost when the app closes.

Uses SQLite (built into Python). Data lives in:
    %APPDATA%\\TermHunter\\termhunter.db
"""
import json
import os
import sqlite3
import threading
from datetime import datetime
from pathlib import Path

APP_NAME = "TermHunter"
DATA_DIR = Path(os.getenv("APPDATA") or Path.home()) / APP_NAME
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "termhunter.db"

# Settings the user can change (stored in the same database)
DEFAULT_SETTINGS = {
    "interval_minutes": 30,        # how often to search (20-60)
    "check_availability": True,    # quick DNS check to mark domains "likely free"
    "minimize_to_tray": True,      # closing the window hides it to the tray
    "auto_start": False,           # begin monitoring when the app opens
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS terms (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    key       TEXT UNIQUE NOT NULL,   -- lowercase term, used to avoid duplicates
    term      TEXT NOT NULL,
    domains   TEXT NOT NULL,          -- JSON list: [{"name": "x.ai", "free": true}, ...]
    source    TEXT NOT NULL,
    url       TEXT,
    found_at  TEXT NOT NULL           -- local time "YYYY-MM-DD HH:MM:SS"
);
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class Storage:
    def __init__(self, path=DB_PATH):
        # The monitor thread and the GUI both use this object, so we lock.
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.executescript(SCHEMA)
            self._conn.commit()

    # ---------- settings ----------
    def get_setting(self, name):
        with self._lock:
            row = self._conn.execute(
                "SELECT value FROM settings WHERE key=?", (name,)).fetchone()
        if row is None:
            return DEFAULT_SETTINGS[name]
        try:
            return json.loads(row["value"])
        except ValueError:
            return DEFAULT_SETTINGS[name]

    def set_setting(self, name, value):
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO settings(key, value) VALUES (?, ?)",
                (name, json.dumps(value)))
            self._conn.commit()

    # ---------- terms ----------
    @staticmethod
    def make_key(term):
        return " ".join(term.lower().split())

    def exists(self, term):
        with self._lock:
            return self._conn.execute(
                "SELECT 1 FROM terms WHERE key=?",
                (self.make_key(term),)).fetchone() is not None

    def add_term(self, term, domains, source, url):
        """Insert a term. Returns the saved row (dict) or None if it was a duplicate."""
        found_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._lock:
            cur = self._conn.execute(
                "INSERT OR IGNORE INTO terms(key, term, domains, source, url, found_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (self.make_key(term), term, json.dumps(domains), source, url, found_at))
            self._conn.commit()
            if cur.rowcount == 0:
                return None
            row_id = cur.lastrowid
        return {"id": row_id, "term": term, "domains": domains,
                "source": source, "url": url, "found_at": found_at}

    def all_terms(self):
        """All saved terms, newest first."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM terms ORDER BY id DESC").fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["domains"] = json.loads(d["domains"])
            out.append(d)
        return out

    def clear_terms(self):
        with self._lock:
            self._conn.execute("DELETE FROM terms")
            self._conn.commit()
