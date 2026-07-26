"""
Base interface all scrapers implement, plus shared HTTP helpers (retry/backoff,
polite rate limiting, consistent user-agent) so individual scrapers stay small.
"""
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import ROLE_KEYWORDS, SENIORITY_EXCLUDE_KEYWORDS

USER_AGENT = "Mozilla/5.0 (compatible; job-fit-research-bot/1.0; personal use)"


def matches_role_keywords(title: str) -> bool:
    """Shared title filter used by every scraper: role keyword match, seniority exclude."""
    t = title.lower()
    if any(kw in t for kw in SENIORITY_EXCLUDE_KEYWORDS):
        return False
    return any(kw in t for kw in ROLE_KEYWORDS)


@dataclass
class RawPosting:
    """Un-normalized posting as returned directly by a scraper."""
    title: str
    company: str
    url: str
    source: str
    location: str = ""
    description: str = ""
    posted_date: str = ""
    raw: dict = field(default_factory=dict)


class Scraper(ABC):
    """Every concrete scraper implements fetch() -> list[RawPosting]."""

    #: minimum seconds to sleep between HTTP requests to be a polite scraper
    rate_limit_seconds: float = 1.0

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    @abstractmethod
    def fetch(self) -> list[RawPosting]:
        ...

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get(self, url: str, **kwargs) -> requests.Response:
        resp = self.session.get(url, timeout=15, **kwargs)
        resp.raise_for_status()
        time.sleep(self.rate_limit_seconds)
        return resp

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_json(self, url: str, **kwargs) -> dict:
        resp = self.get(url, **kwargs)
        return resp.json()
