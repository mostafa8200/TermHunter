"""
storage.py - Saves everything locally so nothing is lost when the app closes.

SQLite database + settings in:  %APPDATA%\\TermHunter\\termhunter.db
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

DEFAULT_SETTINGS = {
    "interval_minutes": 30,
    "check_availability": True,
    "minimize_to_tray": True,
    "auto_start": False,
    "notify": True,
    "appearance": "Dark",                      # Dark / Light / System
    "sectors": ["AI", "Science", "Medicine", "Finance", "Technology"],
    "extensions": ["com", "ai", "io", "tech", "app", "dev", "co", "si"],
    "custom_extensions": [],
    "styles": ["get", "the", "try"],
    "style_ext_count": 2,
    "rare_words": True,
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS terms (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    key       TEXT UNIQUE NOT NULL,
    term      TEXT NOT NULL,
    domains   TEXT NOT NULL,
    source    TEXT NOT NULL,
    url       TEXT,
    found_at  TEXT NOT NULL,
    sector    TEXT DEFAULT '',
    score     INTEGER DEFAULT 0,
    fav       INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class Storage:
    def __init__(self, path=DB_PATH):
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.executescript(SCHEMA)
            # Upgrade databases created by older versions of the app
            have = {r["name"] for r in self._conn.execute("PRAGMA table_info(terms)")}
            for col, ddl in (("sector", "TEXT DEFAULT ''"), ("score", "INTEGER DEFAULT 0"),
                             ("fav", "INTEGER DEFAULT 0")):
                if col not in have:
                    self._conn.execute(f"ALTER TABLE terms ADD COLUMN {col} {ddl}")
            self._conn.commit()

    # ---------- settings ----------
    def get_setting(self, name):
        with self._lock:
            row = self._conn.execute("SELECT value FROM settings WHERE key=?", (name,)).fetchone()
        if row is None:
            return DEFAULT_SETTINGS[name]
        try:
            return json.loads(row["value"])
        except ValueError:
            return DEFAULT_SETTINGS[name]

    def set_setting(self, name, value):
        with self._lock:
            self._conn.execute("INSERT OR REPLACE INTO settings(key, value) VALUES (?, ?)",
                               (name, json.dumps(value)))
            self._conn.commit()

    # ---------- terms ----------
    @staticmethod
    def make_key(term):
        return " ".join(term.lower().split())

    def exists(self, term):
        with self._lock:
            return self._conn.execute("SELECT 1 FROM terms WHERE key=?",
                                      (self.make_key(term),)).fetchone() is not None

    def add_term(self, term, domains, source, url, sector="", score=0):
        """Insert a term. Returns the saved row (dict) or None if it was a duplicate."""
        found_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._lock:
            cur = self._conn.execute(
                "INSERT OR IGNORE INTO terms(key, term, domains, source, url, found_at, sector, score) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (self.make_key(term), term, json.dumps(domains), source, url, found_at, sector, score))
            self._conn.commit()
            if cur.rowcount == 0:
                return None
            row_id = cur.lastrowid
        return {"id": row_id, "term": term, "domains": domains, "source": source, "url": url,
                "found_at": found_at, "sector": sector, "score": score, "fav": 0}

    def all_terms(self):
        with self._lock:
            rows = self._conn.execute("SELECT * FROM terms ORDER BY id DESC").fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["domains"] = json.loads(d["domains"])
            d["sector"] = d.get("sector") or ""
            d["score"] = d.get("score") or 0
            d["fav"] = d.get("fav") or 0
            out.append(d)
        return out

    def update_domains(self, row_id, domains, score):
        with self._lock:
            self._conn.execute("UPDATE terms SET domains=?, score=? WHERE id=?",
                               (json.dumps(domains), score, row_id))
            self._conn.commit()

    def set_favorite(self, row_id, fav):
        with self._lock:
            self._conn.execute("UPDATE terms SET fav=? WHERE id=?", (1 if fav else 0, row_id))
            self._conn.commit()

    def delete_term(self, row_id):
        with self._lock:
            self._conn.execute("DELETE FROM terms WHERE id=?", (row_id,))
            self._conn.commit()

    def clear_terms(self):
        with self._lock:
            self._conn.execute("DELETE FROM terms")
            self._conn.commit()
