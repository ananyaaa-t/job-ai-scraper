"""
Normalizes RawPosting objects (from any scraper) into a common dict schema
stored in SQLite, and computes a stable dedup id + location boost score.
"""
import hashlib

from config.settings import LOCATION_BOOST, PRIORITY_0_COMPANIES, REMOTE_KEYWORDS
from scrapers.base import RawPosting

PRIORITY_0_NAMES = {c["name"].lower() for c in PRIORITY_0_COMPANIES}


def _make_id(source: str, company: str, title: str, url: str) -> str:
    key = f"{source}|{company}|{title}|{url}".lower().strip()
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]


def location_boost(location: str) -> int:
    """Higher score = closer to preference (Seattle > SF/Bay Area > remote > other)."""
    loc = (location or "").lower()
    for keyword, boost in LOCATION_BOOST.items():
        if keyword in loc:
            return boost
    if any(kw in loc for kw in REMOTE_KEYWORDS):
        return 5
    return 0


def normalize(raw: RawPosting) -> dict:
    priority_tier = "priority0" if raw.company.lower() in PRIORITY_0_NAMES else "startup"
    return {
        "id": _make_id(raw.source, raw.company, raw.title, raw.url),
        "title": raw.title,
        "company": raw.company,
        "location": raw.location,
        "url": raw.url,
        "description": raw.description,
        "source": raw.source,
        "priority_tier": priority_tier,
        "posted_date": raw.posted_date,
        "location_boost": location_boost(raw.location),
    }


def normalize_all(raw_postings: list[RawPosting]) -> list[dict]:
    return [normalize(r) for r in raw_postings]
