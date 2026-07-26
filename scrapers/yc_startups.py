"""
Scraper for Y Combinator's "Work at a Startup" job board.

Work at a Startup requires an authenticated session to browse the full board
in a browser, but exposes a public jobs search that returns enough data for
title/company/location/url without login for many listings. Where content is
gated, this scraper still records the listing card metadata (title, company,
url) so it can be surfaced in the digest for manual follow-up even if the
full description isn't scraped.
"""
from config.settings import STARTUP_SOURCES
from scrapers.base import RawPosting, Scraper, matches_role_keywords


class YCStartupsScraper(Scraper):
    rate_limit_seconds = 2.0

    def fetch(self) -> list[RawPosting]:
        if not STARTUP_SOURCES["yc"]["enabled"]:
            return []
        url = STARTUP_SOURCES["yc"]["url"]
        try:
            resp = self.get(url)
        except Exception:
            return []
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "lxml")
        postings = []
        for a in soup.find_all("a", href=True):
            title = a.get_text(strip=True)
            if not title or not matches_role_keywords(title):
                continue
            href = a["href"]
            if href.startswith("/"):
                href = "https://www.workatastartup.com" + href
            postings.append(
                RawPosting(
                    title=title,
                    company="(startup - see listing)",
                    url=href,
                    source="yc",
                    raw={},
                )
            )
        return postings
