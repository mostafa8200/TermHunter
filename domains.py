"""
domains.py - Turns a word into domain-name ideas and (optionally) checks
whether they look free.

"Looks free" = the name does not resolve in DNS. That is a quick hint only,
NOT proof it is available - always confirm at a registrar before buying.
"""
import re
import socket
from concurrent.futures import ThreadPoolExecutor


def slugify(term):
    """'Brain Rot' -> 'brainrot'  (letters and digits only)."""
    return re.sub(r"[^a-z0-9]", "", term.lower())


def suggest_domains(term, max_names=10):
    """Return a list of candidate domain names for the term."""
    s = slugify(term)
    if len(s) < 3 or len(s) > 40:
        return []
    patterns = [
        f"{s}.ai", f"{s}.com", f"get{s}.ai", f"{s}.io", f"the{s}.tech",
        f"{s}.app", f"get{s}.com", f"try{s}.com", f"{s}.dev", f"{s}.tech",
        f"{s}labs.ai", f"{s}hq.com",
    ]
    names = [p for p in patterns if len(p.split(".")[0]) <= 63]
    return names[:max_names]


def _is_registered(domain):
    """True if the domain resolves (so it is certainly in use)."""
    try:
        socket.gethostbyname(domain)
        return True
    except socket.gaierror:
        return False
    except Exception:
        return None  # unknown (network hiccup)


def check_availability(names):
    """
    Return [{"name": "x.ai", "free": True/False/None}, ...].
    free=True means 'did not resolve' (likely available).
    """
    if not names:
        return []
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(_is_registered, names))
    out = []
    for name, registered in zip(names, results):
        free = None if registered is None else (not registered)
        out.append({"name": name, "free": free})
    return out


def unchecked(names):
    """Wrap names without checking them."""
    return [{"name": n, "free": None} for n in names]
