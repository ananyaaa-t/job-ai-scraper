"""
Scraper for companies hosted on Ashby (api.ashbyhq.com public job-board API).
Ashby is common among modern AI-native startups (Cursor, Perplexity, Cognition).
No auth required; returns clean structured JSON.
"""
from scrapers.base import RawPosting, Scraper, matches_role_keywords

ASHBY_API = "https://api.ashbyhq.com/posting-api/job-board/{board}"


class AshbyScraper(Scraper):
    def __init__(self, company: dict):
        super().__init__()
        self.company = company

    def fetch(self) -> list[RawPosting]:
        url = ASHBY_API.format(board=self.company["board_token"])
        try:
            data = self.get_json(url)
        except Exception:
            return []
        postings = []
        for job in data.get("jobs", []):
            title = job.get("title", "")
            if not matches_role_keywords(title):
                continue
            postings.append(
                RawPosting(
                    title=title,
                    company=self.company["name"],
                    url=job.get("jobUrl", job.get("applyUrl", "")),
                    source=f"ashby:{self.company['slug']}",
                    location=job.get("location", ""),
                    description=job.get("descriptionPlain", ""),
                    posted_date=job.get("publishedAt", ""),
                    raw=job,
                )
            )
        return postings
