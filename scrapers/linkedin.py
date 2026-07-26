"""
Best-effort LinkedIn Jobs scraper.

IMPORTANT — read before enabling:
LinkedIn's Terms of Service prohibit automated scraping of the site, and
most job content is only visible to logged-in users. This scraper only ever
touches LinkedIn's public, unauthenticated job-search results page (no
login, no session cookies) and applies conservative rate limiting, but it
can still break at any time or be blocked. Treat this source as optional and
best-effort:
  - It is disabled by default risk-tolerance should be reassessed by the user
    before relying on it (see STARTUP_SOURCES['linkedin']['best_effort']).
  - If LinkedIn blocks/rate-limits the request, this scraper fails soft
    (returns an empty list) rather than crashing the pipeline.
  - Consider this a lower-reliability, supplementary source vs. YC/Wellfound/
    company career pages, which are scraped from public JSON APIs or plain
    static pages.
"""
from bs4 import BeautifulSoup

from config.settings import STARTUP_SOURCES
from scrapers.base import RawPosting, Scraper, matches_role_keywords

SEARCH_URL = (
    "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    "?keywords=software%20engineer&location=United%20States&f_TPR=r86400"
)


class LinkedInScraper(Scraper):
    rate_limit_seconds = 3.0

    def fetch(self) -> list[RawPosting]:
        cfg = STARTUP_SOURCES.get("linkedin", {})
        if not cfg.get("enabled") or not cfg.get("best_effort"):
            return []
        try:
            resp = self.get(SEARCH_URL)
        except Exception:
            # Fail soft: LinkedIn blocking/rate-limiting should never crash the run.
            return []
        soup = BeautifulSoup(resp.text, "lxml")
        postings = []
        for card in soup.select("li"):
            title_el = card.select_one(".base-search-card__title")
            company_el = card.select_one(".base-search-card__subtitle")
            link_el = card.select_one("a.base-card__full-link")
            location_el = card.select_one(".job-search-card__location")
            if not (title_el and link_el):
                continue
            title = title_el.get_text(strip=True)
            if not matches_role_keywords(title):
                continue
            postings.append(
                RawPosting(
                    title=title,
                    company=company_el.get_text(strip=True) if company_el else "(unknown)",
                    url=link_el["href"].split("?")[0],
                    source="linkedin",
                    location=location_el.get_text(strip=True) if location_el else "",
                    raw={},
                )
            )
        return postings
