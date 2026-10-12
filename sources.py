"""
sources.py - The websites (RSS feeds) the app reads.

Each feed: (display name, URL, [sectors it is useful for]).
Only feeds matching the sectors you ticked are visited. Dead feeds are skipped,
so you can add/remove lines freely. RSS is the polite, official way to read news sites.
"""
from urllib.parse import quote_plus

from sectors import SECTORS


def _gnews_search(query):
    return ("https://news.google.com/rss/search?q="
            f"{quote_plus(query)}&hl=en-US&gl=US&ceid=US:en")


def _gnews_topic(topic):
    return f"https://news.google.com/rss/headlines/section/topic/{topic}?hl=en-US&gl=US&ceid=US:en"


FEEDS = [
    # ---- Google News topics ----
    ("Google News", _gnews_topic("SCIENCE"), ["Science"]),
    ("Google News", _gnews_topic("TECHNOLOGY"), ["Technology", "AI"]),
    ("Google News", _gnews_topic("HEALTH"), ["Medicine"]),
    ("Google News", _gnews_topic("BUSINESS"), ["Finance"]),

    # ---- General news ----
    ("BBC Science", "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml", ["Science", "Space", "Energy & Climate"]),
    ("BBC Technology", "https://feeds.bbci.co.uk/news/technology/rss.xml", ["Technology", "AI", "Cybersecurity"]),
    ("BBC Health", "https://feeds.bbci.co.uk/news/health/rss.xml", ["Medicine"]),
    ("BBC Business", "https://feeds.bbci.co.uk/news/business/rss.xml", ["Finance"]),
    ("NY Times Science", "https://rss.nytimes.com/services/xml/rss/nyt/Science.xml", ["Science", "Space", "Biotech"]),
    ("NY Times Technology", "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml", ["Technology", "AI"]),
    ("NY Times Health", "https://rss.nytimes.com/services/xml/rss/nyt/Health.xml", ["Medicine", "Biotech"]),
    ("NY Times Business", "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml", ["Finance"]),
    ("The Guardian Science", "https://www.theguardian.com/science/rss", ["Science", "Space"]),
    ("The Guardian AI", "https://www.theguardian.com/technology/artificialintelligenceai/rss", ["AI"]),
    ("The Guardian Environment", "https://www.theguardian.com/environment/rss", ["Energy & Climate"]),
    ("The Guardian Business", "https://www.theguardian.com/uk/business/rss", ["Finance"]),
    ("CNBC", "https://www.cnbc.com/id/100003114/device/rss/rss.html", ["Finance", "Technology"]),

    # ---- AI / tech / robotics / security ----
    ("MIT Technology Review", "https://www.technologyreview.com/feed/", ["AI", "Technology", "Biotech", "Energy & Climate"]),
    ("Wired", "https://www.wired.com/feed/rss", ["Technology", "AI", "Cybersecurity"]),
    ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index", ["Technology", "Science", "Space"]),
    ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/", ["AI"]),
    ("TechCrunch", "https://techcrunch.com/feed/", ["Technology"]),
    ("VentureBeat AI", "https://venturebeat.com/category/ai/feed/", ["AI"]),
    ("The Verge AI", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", ["AI"]),
    ("arXiv cs.AI", "https://rss.arxiv.org/rss/cs.AI", ["AI"]),
    ("IEEE Spectrum", "https://spectrum.ieee.org/feeds/feed.rss", ["Robotics", "Technology"]),
    ("The Robot Report", "https://www.therobotreport.com/feed/", ["Robotics"]),
    ("Krebs on Security", "https://krebsonsecurity.com/feed/", ["Cybersecurity"]),
    ("BleepingComputer", "https://www.bleepingcomputer.com/feed/", ["Cybersecurity"]),

    # ---- Science / medicine / biotech ----
    ("Nature", "https://www.nature.com/nature.rss", ["Science", "Biotech", "Medicine"]),
    ("Science (AAAS)", "https://www.science.org/rss/news_current.xml", ["Science", "Biotech"]),
    ("ScienceDaily", "https://www.sciencedaily.com/rss/top/science.xml", ["Science"]),
    ("ScienceDaily Health", "https://www.sciencedaily.com/rss/top/health.xml", ["Medicine"]),
    ("Phys.org", "https://phys.org/rss-feed/", ["Science", "Space", "Energy & Climate"]),
    ("Medical Xpress", "https://medicalxpress.com/rss-feed/", ["Medicine", "Biotech"]),
    ("STAT News", "https://www.statnews.com/feed/", ["Medicine", "Biotech"]),
    ("Fierce Biotech", "https://www.fiercebiotech.com/rss/xml", ["Biotech", "Medicine"]),
    ("GEN", "https://www.genengnews.com/feed/", ["Biotech"]),

    # ---- Finance / crypto ----
    ("MarketWatch", "https://feeds.content.dowjones.io/public/rss/mw_topstories", ["Finance"]),
    ("Yahoo Finance", "https://finance.yahoo.com/news/rssindex", ["Finance"]),
    ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/", ["Crypto & Web3", "Finance"]),
    ("Cointelegraph", "https://cointelegraph.com/rss", ["Crypto & Web3"]),

    # ---- Space / energy ----
    ("NASA", "https://www.nasa.gov/rss/dyn/breaking_news.rss", ["Space", "Science"]),
    ("Space.com", "https://www.space.com/feeds/all", ["Space"]),
    ("Carbon Brief", "https://www.carbonbrief.org/feed/", ["Energy & Climate"]),
    ("CleanTechnica", "https://cleantechnica.com/feed/", ["Energy & Climate"]),
]


def build_feeds(selected_sectors):
    """
    Return [(name, url, default_sector)] for the chosen sectors:
    matching feeds + Google News searches written for each sector.
    """
    selected = [s for s in SECTORS if s in set(selected_sectors)]
    feeds, seen = [], set()
    for name, url, tags in FEEDS:
        mine = [t for t in tags if t in selected]
        if mine and url not in seen:
            seen.add(url)
            feeds.append((name, url, mine[0]))
    for sector in selected:
        for query in SECTORS[sector]["queries"]:
            url = _gnews_search(query)
            if url not in seen:
                seen.add(url)
                feeds.append(("Google News", url, sector))
    return feeds
