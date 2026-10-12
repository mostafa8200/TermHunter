"""
domains.py - Domain ideas, quick availability hints and a "premium score".

"Looks free" = the name does not resolve in DNS. That is only a hint, NOT proof
it can be registered - always confirm at a registrar before buying.
"""
import re
import socket
from concurrent.futures import ThreadPoolExecutor

from sectors import PREMIUM_SECTORS

# Every extension offered in Settings (without the dot). Order = priority.
ALL_EXTENSIONS = [
    "com", "ai", "io", "tech", "app", "dev", "co", "si", "net", "org", "xyz",
    "bio", "science", "health", "med", "life", "finance", "money", "capital",
    "fund", "bank", "ventures", "vc", "cloud", "data", "labs", "lab", "digital",
    "online", "site", "store", "me", "gg", "so", "sh", "tools", "systems",
    "network", "world", "global", "inc", "agency", "studio", "design",
    "energy", "solar", "space", "security", "crypto", "eco", "pro", "info", "one",
]
POPULAR_EXTENSIONS = ["com", "ai", "io", "tech", "app", "dev", "co", "si"]

# (key, pattern) - how a word is dressed up. "Exact word" is always included.
STYLE_DEFS = [
    ("get", "get{word}"), ("the", "the{word}"), ("try", "try{word}"),
    ("my", "my{word}"), ("use", "use{word}"), ("hq", "{word}hq"),
    ("labs", "{word}labs"), ("ai", "{word}ai"), ("app", "{word}app"),
]
DEFAULT_STYLES = ["get", "the", "try"]


def slugify(term):
    """'Brain Rot' -> 'brainrot'."""
    return re.sub(r"[^a-z0-9]", "", term.lower())


def selected_extensions(db):
    """The user's chosen extensions, in priority order."""
    custom = db.get_setting("custom_extensions")
    chosen = set(db.get_setting("extensions"))
    ordered = ALL_EXTENSIONS + [c for c in custom if c not in ALL_EXTENSIONS]
    return [e for e in ordered if e in chosen] or ["com"]


def suggest_domains(term, extensions, styles, style_ext_count=2, max_names=40):
    """
    Candidate names: exact word on every chosen extension, plus the chosen
    styles (get/the/try...) on the first few extensions.
    """
    s = slugify(term)
    if not 3 <= len(s) <= 40:
        return []
    names = [f"{s}.{e}" for e in extensions]
    for key, pattern in STYLE_DEFS:
        if key in styles:
            base = pattern.format(word=s)
            names += [f"{base}.{e}" for e in extensions[:max(1, style_ext_count)]]
    seen, out = set(), []
    for n in names:
        if n not in seen and len(n.split(".")[0]) <= 63:
            seen.add(n)
            out.append(n)
    return out[:max_names]


def _is_registered(domain):
    try:
        socket.gethostbyname(domain)
        return True
    except socket.gaierror:
        return False
    except Exception:
        return None


def check_availability(names):
    """[{'name','free'}]  free=True: did not resolve (likely free); None: unknown."""
    if not names:
        return []
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(_is_registered, names))
    return [{"name": n, "free": None if r is None else (not r)} for n, r in zip(names, results)]


def unchecked(names):
    return [{"name": n, "free": None} for n in names]


def score_term(term, sector, domains):
    """
    Premium score 0-100. Rewards: short, one-word, pronounceable, clean (no digits or
    hyphens), valuable sector, and a free .com/.ai/.io/.co.
    """
    s = slugify(term)
    n = max(1, len(s))
    length = max(0, 40 - max(0, n - 5) * 3)                      # up to 40
    words = len([w for w in re.split(r"[\s\-]+", term.strip()) if w])
    word_pts = {1: 15, 2: 8}.get(words, 0)                        # up to 15
    vowel_ratio = sum(c in "aeiouy" for c in s) / n
    pron = (15 if 0.25 <= vowel_ratio <= 0.6 else 0)
    pron += 5 if not re.search(r"[^aeiouy0-9]{4,}", s) else 0     # up to 20
    clean = 10 if not re.search(r"[\d\-]", term) else 0           # up to 10
    sector_pts = 5 if sector in PREMIUM_SECTORS else 2
    free_exact = {d["name"].split(".", 1)[1] for d in domains
                  if d.get("free") is True and d["name"].split(".", 1)[0] == s}
    avail = (6 if "com" in free_exact else 0) + (4 if free_exact & {"ai", "io", "co"} else 0)
    return int(min(100, length + word_pts + pron + clean + sector_pts + avail))
