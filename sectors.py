"""
sectors.py - Industry sectors the app can watch.

For each sector we keep:
  icon      - shown in the sidebar
  keywords  - regex fragments used to decide which sector an article belongs to
  queries   - Google News searches aimed at newly coined words in that sector
"""
import re

SECTORS = {
    "AI": {
        "icon": "🤖",
        "keywords": [r"\bai\b", r"artificial intell", r"machine learn", r"deep learn", r"neural",
                     r"\bllms?\b", r"chatbot", r"\bgpt", r"generative", r"openai", r"anthropic",
                     r"agentic", r"language model", r"copilot", r"gemini", r"diffusion model"],
        "queries": ['"coined the term" "artificial intelligence" when:14d',
                    'new AI buzzword OR jargon when:14d'],
    },
    "Science": {
        "icon": "🔬",
        "keywords": [r"scientist", r"researchers?\b", r"physics", r"chemistry", r"particle",
                     r"quantum", r"species", r"fossil", r"laborator", r"molecul", r"physicist"],
        "queries": ['"coined the term" scientists when:14d',
                    'researchers "dubbed" new discovery when:14d'],
    },
    "Medicine": {
        "icon": "💊",
        "keywords": [r"patient", r"clinical", r"disease", r"therap", r"vaccin", r"cancer",
                     r"hospital", r"\bdrugs?\b", r"surgery", r"diagnos", r"symptom", r"medical",
                     r"health", r"doctors?\b"],
        "queries": ['"coined the term" medicine OR health when:14d',
                    'doctors "dubbed" OR "new term" disease when:14d'],
    },
    "Biotech": {
        "icon": "🧬",
        "keywords": [r"biotech", r"genom", r"crispr", r"\bgene\b", r"\bgenes\b", r"protein",
                     r"cell therapy", r"mrna", r"synthetic biology", r"genetic"],
        "queries": ['biotech "new term" OR "dubbed" OR "coined" when:14d'],
    },
    "Finance": {
        "icon": "💰",
        "keywords": [r"\bbanks?\b", r"invest", r"\bstocks?\b", r"market", r"fintech", r"inflation",
                     r"interest rate", r"hedge fund", r"\bipo\b", r"payment", r"\betfs?\b",
                     r"econom", r"venture capital", r"trading"],
        "queries": ['"coined the term" finance OR economy OR fintech when:14d',
                    'new financial buzzword OR "dubbed" markets when:14d'],
    },
    "Crypto & Web3": {
        "icon": "₿",
        "keywords": [r"crypto", r"bitcoin", r"blockchain", r"ethereum", r"\btokens?\b", r"\bdefi\b",
                     r"\bnfts?\b", r"web3", r"stablecoin"],
        "queries": ['crypto "new term" OR "coined" OR "dubbed" when:14d'],
    },
    "Technology": {
        "icon": "💻",
        "keywords": [r"software", r"startup", r"\bapps?\b", r"\bchips?\b", r"semiconductor", r"cloud",
                     r"smartphone", r"internet", r"platform", r"developer", r"data cent"],
        "queries": ['"coined the term" technology when:14d',
                    'tech "new buzzword" OR "dubbed" when:14d'],
    },
    "Robotics": {
        "icon": "🦾",
        "keywords": [r"robot", r"humanoid", r"\bdrones?\b", r"autonomous", r"automation",
                     r"exoskeleton"],
        "queries": ['robotics "new term" OR "dubbed" OR "coined" when:14d'],
    },
    "Cybersecurity": {
        "icon": "🛡",
        "keywords": [r"cyber", r"hack", r"ransomware", r"malware", r"breach", r"vulnerab",
                     r"phishing", r"encryption"],
        "queries": ['cybersecurity "dubbed" OR "coined" OR "new term" when:14d'],
    },
    "Space": {
        "icon": "🚀",
        "keywords": [r"\bnasa\b", r"spacex", r"rocket", r"satellite", r"orbit", r"asteroid",
                     r"telescope", r"galax", r"exoplanet", r"astronaut", r"\bmars\b", r"\bmoon\b"],
        "queries": ['space astronomy "dubbed" OR "coined" OR "new term" when:14d'],
    },
    "Energy & Climate": {
        "icon": "🌱",
        "keywords": [r"climate", r"renewable", r"solar", r"batter", r"carbon", r"emission",
                     r"hydrogen", r"nuclear", r"fusion", r"wind power", r"energy"],
        "queries": ['climate OR energy "coined the term" OR "dubbed" when:14d'],
    },
}

# Sectors whose domain names tend to be worth more (small bonus in the score)
PREMIUM_SECTORS = {"AI", "Finance", "Medicine", "Biotech", "Crypto & Web3", "Cybersecurity"}

_PATTERNS = {name: re.compile("|".join(info["keywords"]), re.IGNORECASE)
             for name, info in SECTORS.items()}


def classify(text):
    """Return the best-matching sector name for a text, or None if nothing matches."""
    best, best_hits = None, 0
    for name, pattern in _PATTERNS.items():
        hits = len(pattern.findall(text))
        if hits > best_hits:
            best, best_hits = name, hits
    return best
