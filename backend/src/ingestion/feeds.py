from dataclasses import dataclass


@dataclass
class Feed:
    name: str   # used as the `source` column in SQLite
    url: str


# Chosen for reliability: all are major outlets with stable RSS feeds.
# Hacker News RSS gives front-page links, not full text — handled in fetcher.
FEEDS: list[Feed] = [
    Feed("Ars Technica",        "https://feeds.arstechnica.com/arstechnica/index"),
    Feed("TechCrunch",          "https://techcrunch.com/feed/"),
    Feed("The Verge",           "https://www.theverge.com/rss/index.xml"),
    Feed("Hacker News",         "https://news.ycombinator.com/rss"),
    Feed("MIT Technology Review", "https://www.technologyreview.com/feed/"),
    Feed("Wired",               "https://www.wired.com/feed/rss"),
]
