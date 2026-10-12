"""
monitor.py - Background worker that periodically checks the news feeds.

Being polite (so websites don't block us):
  * one request at a time, with a random 1-2.5 s pause between sites
  * a clear User-Agent, short timeouts, no retries in a tight loop
  * remembers ETag / Last-Modified, so unchanged feeds cost almost nothing
  * if a site answers "429 / 403" it is left alone for an hour
  * the interval gets +/-10% random jitter
"""
import logging
import queue
import random
import threading
import time

import feedparser
import requests

from domains import check_availability, suggest_domains, unchecked
from extractor import clean_text, extract_terms
from sources import FEEDS

log = logging.getLogger("termhunter")

USER_AGENT = ("Mozilla/5.0 (compatible; TermHunter/1.0; personal research tool; "
              "reads public RSS feeds)")
MAX_NEW_PER_CYCLE = 60       # safety cap so one bad cycle can't flood the table
COOLDOWN_SECONDS = 3600      # pause for a feed that blocks/limits us


class Monitor:
    """Talks to the GUI only through `events` (a thread-safe queue)."""

    def __init__(self, db, events: queue.Queue):
        self.db = db
        self.events = events
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._thread = None
        self._cycle_lock = threading.Lock()
        self._http = requests.Session()
        self._http.headers["User-Agent"] = USER_AGENT
        self._cache = {}       # url -> {"etag":..., "modified":...}
        self._cooldown = {}    # url -> time when we may try again

    # ---------- public controls ----------
    @property
    def running(self):
        return self._thread is not None and self._thread.is_alive() and not self._stop.is_set()

    def start(self):
        if self.running:
            return
        self._stop.clear()
        self._wake.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        self._emit("state", True)

    def stop(self):
        self._stop.set()
        self._wake.set()       # wake the sleeping loop so it exits now
        self._emit("state", False)
        self._emit("next", None)
        self._emit("status", "Stopped")

    def search_now(self):
        """Run a check immediately (works whether started or not)."""
        if self.running:
            self._wake.set()
        else:
            self._stop.clear()
            threading.Thread(target=self._cycle, daemon=True).start()

    # ---------- internals ----------
    def _emit(self, kind, payload=None):
        self.events.put((kind, payload))

    def _loop(self):
        while not self._stop.is_set():
            self._cycle()
            if self._stop.is_set():
                break
            minutes = min(60, max(20, int(self.db.get_setting("interval_minutes"))))
            seconds = minutes * 60 * random.uniform(0.9, 1.1)
            self._emit("next", time.time() + seconds)
            self._emit("status", "Running - waiting for the next check")
            self._wake.clear()
            self._wake.wait(timeout=seconds)   # returns early on stop / "search now"
            self._wake.clear()

    def _fetch(self, name, url):
        """Download one feed. Returns a list of entries (may be empty)."""
        if self._cooldown.get(url, 0) > time.time():
            return []
        headers = {}
        cached = self._cache.get(url, {})
        if cached.get("etag"):
            headers["If-None-Match"] = cached["etag"]
        if cached.get("modified"):
            headers["If-Modified-Since"] = cached["modified"]
        try:
            resp = self._http.get(url, headers=headers, timeout=(5, 20))
        except requests.RequestException as exc:
            log.warning("Could not reach %s: %s", name, exc)
            return []
        if resp.status_code == 304:
            return []
        if resp.status_code in (403, 429, 503):
            log.warning("%s asked us to slow down (HTTP %s)", name, resp.status_code)
            self._cooldown[url] = time.time() + COOLDOWN_SECONDS
            return []
        if resp.status_code != 200:
            log.warning("%s returned HTTP %s", name, resp.status_code)
            return []
        self._cache[url] = {"etag": resp.headers.get("ETag"),
                            "modified": resp.headers.get("Last-Modified")}
        return feedparser.parse(resp.content).entries

    def _cycle(self):
        if not self._cycle_lock.acquire(blocking=False):
            return                      # a check is already in progress
        try:
            self._emit("status", "Checking sources...")
            check_free = bool(self.db.get_setting("check_availability"))
            feeds = list(FEEDS)
            random.shuffle(feeds)
            new_total, seen_this_run = 0, set()

            for i, (name, url) in enumerate(feeds, 1):
                if self._stop.is_set():
                    break
                self._emit("status", f"Checking {name} ({i}/{len(feeds)})...")
                for entry in self._fetch(name, url):
                    if new_total >= MAX_NEW_PER_CYCLE:
                        break
                    title = clean_text(entry.get("title", ""))
                    # Google News titles end with " - Publisher"; drop that part
                    publisher = (entry.get("source") or {}).get("title")
                    if publisher and title.endswith(" - " + publisher):
                        title = title[: -len(publisher) - 3]
                    summary = entry.get("summary", "") if name != "Google News" else ""
                    source = f"{name} - {publisher}" if (name == "Google News" and publisher) else name

                    for term, _why in extract_terms(title, summary):
                        key = self.db.make_key(term)
                        if key in seen_this_run or self.db.exists(term):
                            continue
                        seen_this_run.add(key)
                        names = suggest_domains(term)
                        if not names:
                            continue
                        domains = check_availability(names) if check_free else unchecked(names)
                        row = self.db.add_term(term, domains, source, entry.get("link", ""))
                        if row:
                            new_total += 1
                            self._emit("new", row)
                # polite pause between websites
                self._stop.wait(random.uniform(1.0, 2.5))

            self._emit("done", new_total)
            if self._stop.is_set():
                self._emit("status", "Stopped")
            else:
                self._emit("status", f"Check finished - {new_total} new term(s)")
        except Exception:
            log.exception("Unexpected error during check")
            self._emit("status", "A check failed - will try again later")
        finally:
            self._cycle_lock.release()
