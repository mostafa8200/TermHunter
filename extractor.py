"""
extractor.py - Finds "new words" inside a news headline + summary.

Two methods are used:

1. CUE PHRASES (most reliable): text like  coined the term "brain rot",
   scientists dubbed the effect "X", the so-called 'Y' ...
2. RARE WORDS: words that are missing from (or extremely rare in) a large
   English frequency list ("wordfreq"). New inventions such as 'vibecoding'
   are not in that list yet, so they stand out. Names of people/companies are
   filtered out where possible (they are normally capitalised mid-sentence).

No method is perfect - expect some noise. That's normal for this kind of tool.
"""
import html
import re

from wordfreq import zipf_frequency

# Zipf scale: 0 = unknown word, ~3 = uncommon, 7 = "the".
RARE_MAX = 1.5            # words rarer than this count as "new-looking"
COMMON_SINGLE_WORD = 3.8  # a single quoted word above this is just normal English
MAX_PER_ENTRY = 4         # cap on rare words taken from one article

TAG_RE = re.compile(r"<[^>]+>")
WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9\-]{4,24}")
OPEN_Q = r"(?:[\u201c\"\u2018]|')"
CLOSE_Q = r"(?:[\u201d\"\u2019]|'(?!\w))"
CUE_RE = re.compile(
    r"(?:coined(?:\s+the\s+(?:term|word|phrase))?|dubbed|dubs|nicknamed|termed|"
    r"christened|new\s+(?:term|word|phrase|buzzword)|the\s+(?:term|word|buzzword)|"
    r"so-called|known\s+as|called)\s*[:,]?\s*"
    + OPEN_Q + r"([^\u201c\u201d\u2018\u2019\"'\n]{3,32}?)" + CLOSE_Q,
    re.IGNORECASE,
)
UNQUOTED_RE = re.compile(
    r"coined\s+the\s+(?:term|word|phrase)\s+([A-Za-z][A-Za-z0-9\-]{3,24})", re.I)

# Science / AI flavoured fragments - lets us keep Capitalised Title-Case terms
HINT_RE = re.compile(
    r"(neuro|quantum|bio|nano|cyber|crypto|gpt|llm|agentic|robo|astro|geno|"
    r"proteo|synth|deep|vibe|slop|omics?$|ification$|^ai|ai$)", re.I)

LEADING_JUNK = re.compile(r"^(the|a|an)\s+", re.I)


def clean_text(raw):
    """Strip HTML tags/entities."""
    return " ".join(html.unescape(TAG_RE.sub(" ", raw or "")).split())


def _from_cues(text):
    found = []
    for m in CUE_RE.finditer(text):
        found.append(m.group(1))
    for m in UNQUOTED_RE.finditer(text):
        found.append(m.group(1))
    out = []
    for t in found:
        t = LEADING_JUNK.sub("", t.strip(" .,:;-"))
        words = t.split()
        if not 1 <= len(words) <= 3 or not re.search(r"[A-Za-z]", t):
            continue
        # A single ordinary dictionary word is not a "new term"
        if len(words) == 1 and zipf_frequency(t.lower(), "en") >= COMMON_SINGLE_WORD:
            continue
        out.append((t, "coined/cued phrase"))
    return out


def _is_sentence_start(text, pos):
    return pos == 0 or text[max(0, pos - 2):pos] in (". ", "! ", "? ", ": ")


def _rare_words(text):
    occurrences = {}
    for m in WORD_RE.finditer(text):
        tok = m.group(0).strip("-")
        if len(tok) < 5:
            continue
        occurrences.setdefault(tok.lower(), []).append((tok, m.start()))

    out = []
    for low, occ in occurrences.items():
        if zipf_frequency(low, "en") > RARE_MAX:
            continue
        if re.search(r"(.)\1\1", low):          # 'aaaa' style junk
            continue
        forms = [t for t, _ in occ]
        has_lower = any(t == t.lower() for t in forms)
        camel = any(re.search(r"[a-z][A-Z]", t) for t in forms)
        all_caps = all(t.isupper() for t in forms)
        hinted = bool(HINT_RE.search(low))
        mid_sentence_cap = any(t[0].isupper() and not _is_sentence_start(text, p)
                               for t, p in occ)
        if all_caps and not hinted:
            continue                              # company / acronym
        # Plain capitalised words are usually names -> keep only if hinted
        if not (has_lower or camel or hinted) and mid_sentence_cap:
            continue
        display = next((t for t in forms if t == t.lower()), forms[0])
        out.append((display, "rare word"))
    return out[:MAX_PER_ENTRY]


def extract_terms(title, summary="", use_rare=True):
    """Return a de-duplicated list of (term, reason) found in an article."""
    text = clean_text(f"{title}. {summary}")[:2500]
    results, seen = [], set()
    for term, why in _from_cues(text) + (_rare_words(text) if use_rare else []):
        k = term.lower()
        if k not in seen:
            seen.add(k)
            results.append((term, why))
    return results
