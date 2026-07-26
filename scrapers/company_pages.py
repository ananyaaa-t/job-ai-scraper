"""
Scraper for Priority 0 companies (Google, Apple, Microsoft, Notion, Stripe)
and Tier 2 companies (other admired product companies + AI-native startups).

Notion, Stripe, Airbnb, Figma, Pinterest, and Vercel are queried via the
public Greenhouse job-board JSON API (no login/auth required, stable
schema). Cursor, Perplexity, and Cognition use Ashby (see scrapers/ashby.py).
Google/Apple/Microsoft/Slack don't expose a simple public JSON API, so
they're scraped from their public career-search pages; these are more
brittle and may need selector updates over time if the companies change
their site markup.
"""
import re

from bs4 import BeautifulSoup

from config.settings import PRIORITY_0_COMPANIES, TIER_2_COMPANIES
from scrapers.base import RawPosting, Scraper, matches_role_keywords

GREENHOUSE_API = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"

# Kept for backwards compatibility with modules that import this name directly.
_matches_role_keywords = matches_role_keywords


class GreenhouseScraper(Scraper):
    """Handles any company on this list whose board_type == 'greenhouse'."""

    def __init__(self, company: dict):
        super().__init__()
        self.company = company

    def fetch(self) -> list[RawPosting]:
        url = GREENHOUSE_API.format(token=self.company["board_token"])
        data = self.get_json(url)
        postings = []
        for job in data.get("jobs", []):
            title = job.get("title", "")
            if not matches_role_keywords(title):
                continue
            location = (job.get("location") or {}).get("name", "")
            postings.append(
                RawPosting(
                    title=title,
                    company=self.company["name"],
                    url=job.get("absolute_url", ""),
                    source=f"greenhouse:{self.company['slug']}",
                    location=location,
                    description=re.sub("<[^<]+?>", " ", job.get("content", "")),
                    posted_date=job.get("updated_at", ""),
                    raw=job,
                )
            )
        return postings


class GenericCareerPageScraper(Scraper):
    """
    Best-effort scraper for companies without a public JSON API
    (Google, Apple, Microsoft, Slack). Parses the rendered search page HTML.
    NOTE: these career sites are JS-heavy; for reliable results this may need
    to be upgraded to a Playwright-based render+scrape (same engine already
    used by apply/*.py) rather than a plain HTML GET. Marked as a known
    follow-up if results come back empty.
    """

    def __init__(self, company: dict):
        super().__init__()
        self.company = company

    def fetch(self) -> list[RawPosting]:
        try:
            resp = self.get(self.company["careers_url"])
        except Exception:
            return []
        soup = BeautifulSoup(resp.text, "lxml")
        postings = []
        # Heuristic: look for anchor tags whose text matches our role keywords.
        for a in soup.find_all("a"):
            title = a.get_text(strip=True)
            if not title or not matches_role_keywords(title):
                continue
            href = a.get("href", "")
            if href.startswith("/"):
                from urllib.parse import urljoin
                href = urljoin(self.company["careers_url"], href)
            postings.append(
                RawPosting(
                    title=title,
                    company=self.company["name"],
                    url=href,
                    source=f"careerpage:{self.company['slug']}",
                    raw={},
                )
            )
        return postings


def _build_scraper(company: dict) -> Scraper:
    if company["board_type"] == "greenhouse":
        return GreenhouseScraper(company)
    if company["board_type"] == "ashby":
        from scrapers.ashby import AshbyScraper  # local import: avoids circular import at module load
        return AshbyScraper(company)
    return GenericCareerPageScraper(company)


def get_priority0_scrapers() -> list[Scraper]:
    return [_build_scraper(company) for company in PRIORITY_0_COMPANIES]


def get_tier2_scrapers() -> list[Scraper]:
    return [_build_scraper(company) for company in TIER_2_COMPANIES]

