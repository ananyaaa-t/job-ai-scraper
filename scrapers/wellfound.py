"""
Scraper for Wellfound (formerly AngelList Talent).

Wellfound heavily relies on client-side rendering and increasingly blocks
plain HTTP scraping. This scraper attempts a plain-request fetch first; if
the page returns no matches (likely JS-rendered shell), it degrades
gracefully and returns an empty list rather than erroring the whole pipeline.
A future upgrade path is to render via Playwright (already a dependency for
apply/*.py) if reliability becomes an issue.
"""
from bs4 import BeautifulSoup

from config.settings import STARTUP_SOURCES
from scrapers.base import RawPosting, Scraper, matches_role_keywords


class WellfoundScraper(Scraper):
    rate_limit_seconds = 2.0

    def fetch(self) -> list[RawPosting]:
        if not STARTUP_SOURCES["wellfound"]["enabled"]:
            return []
        url = STARTUP_SOURCES["wellfound"]["url"]
        try:
            resp = self.get(url)
        except Exception:
            return []
        soup = BeautifulSoup(resp.text, "lxml")
        postings = []
        for a in soup.find_all("a", href=True):
            title = a.get_text(strip=True)
            if not title or not matches_role_keywords(title):
                continue
            href = a["href"]
            if href.startswith("/"):
                href = "https://wellfound.com" + href
            postings.append(
                RawPosting(
                    title=title,
                    company="(startup - see listing)",
                    url=href,
                    source="wellfound",
                    raw={},
                )
            )
        return postings
