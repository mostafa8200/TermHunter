"""
sources.py - The list of websites (RSS feeds) the app checks.

Each entry is (display name, feed URL). Feeds that fail or disappear are
simply skipped, so you can safely add or remove lines here.
RSS feeds are the polite, officially-supported way to read news sites.
"""
from urllib.parse import quote_plus


def _gnews_search(query):
    """Google News RSS search feed for a query."""
    return ("https://news.google.com/rss/search?q="
            f"{quote_plus(query)}&hl=en-US&gl=US&ceid=US:en")


FEEDS = [
    # ---- Google News: searches aimed at newly coined words ----
    ("Google News", _gnews_search('"coined the term" AI OR science when:7d')),
    ("Google News", _gnews_search('new buzzword "artificial intelligence" when:7d')),
    ("Google News", _gnews_search('scientists "dubbed" new discovery when:7d')),
    ("Google News", _gnews_search('neologism OR "new word" technology when:14d')),
    ("Google News", "https://news.google.com/rss/headlines/section/topic/SCIENCE?hl=en-US&gl=US&ceid=US:en"),
    ("Google News", "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=en-US&gl=US&ceid=US:en"),

    # ---- Major news: science & tech sections ----
    ("BBC Science", "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml"),
    ("BBC Technology", "https://feeds.bbci.co.uk/news/technology/rss.xml"),
    ("NY Times Science", "https://rss.nytimes.com/services/xml/rss/nyt/Science.xml"),
    ("NY Times Technology", "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml"),
    ("The Guardian Science", "https://www.theguardian.com/science/rss"),
    ("The Guardian AI", "https://www.theguardian.com/technology/artificialintelligenceai/rss"),

    # ---- AI / tech publications ----
    ("MIT Technology Review", "https://www.technologyreview.com/feed/"),
    ("Wired", "https://www.wired.com/feed/rss"),
    ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
    ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("VentureBeat AI", "https://venturebeat.com/category/ai/feed/"),
    ("The Verge AI", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"),

    # ---- Science sources ----
    ("Nature", "https://www.nature.com/nature.rss"),
    ("Science (AAAS)", "https://www.science.org/rss/news_current.xml"),
    ("ScienceDaily", "https://www.sciencedaily.com/rss/top/science.xml"),
    ("Phys.org", "https://phys.org/rss-feed/"),
    ("arXiv cs.AI", "https://rss.arxiv.org/rss/cs.AI"),
]
