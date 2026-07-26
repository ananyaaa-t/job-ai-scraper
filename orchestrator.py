#!/usr/bin/env python3
"""
Daily entry point: scrape -> normalize -> dedup -> evaluate fit -> rank/filter
-> pre-fill top-match applications -> send digest email -> mark as emailed.

Run manually with `python orchestrator.py`, or on a daily cron schedule
(see README.md for the cron/launchd setup).
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv

load_dotenv()

from apply import ALL_ADAPTERS, get_adapter_for_url
from config.settings import (
    FIT_SCORE_PREFILL_THRESHOLD,
    FIT_SCORE_RECOMMEND_THRESHOLD,
    LOG_DIR,
)
from email_digest.digest import send_digest
from evaluator.fit_llm import evaluate_fit
from normalize import normalize_all
from scrapers.company_pages import get_priority0_scrapers, get_tier2_scrapers
from scrapers.linkedin import LinkedInScraper
from scrapers.wellfound import WellfoundScraper
from scrapers.yc_startups import YCStartupsScraper
from storage import db

LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "orchestrator.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("orchestrator")


def run_scrapers() -> list:
    all_raw = []
    scrapers = [*get_priority0_scrapers(), *get_tier2_scrapers(), YCStartupsScraper(), WellfoundScraper(), LinkedInScraper()]
    for scraper in scrapers:
        try:
            raw = scraper.fetch()
            logger.info("%s: found %d postings", scraper.__class__.__name__, len(raw))
            all_raw.extend(raw)
        except Exception as e:
            logger.error("%s failed: %s", scraper.__class__.__name__, e)
    return all_raw


def dedup_and_store(normalized_postings: list[dict]) -> list[dict]:
    new_ones = []
    for posting in normalized_postings:
        if db.upsert_posting(posting):
            new_ones.append(posting)
    logger.info("%d new postings out of %d scraped", len(new_ones), len(normalized_postings))
    return new_ones


def evaluate_new_postings(new_postings: list[dict]):
    for posting in new_postings:
        result = evaluate_fit(posting)
        db.save_evaluation(
            posting["id"],
            result["fit_score"],
            result["reasoning"],
            "\n".join(result.get("tailored_bullets", [])),
            result.get("cover_letter_opening", ""),
        )
        logger.info("Evaluated '%s @ %s' -> fit_score=%s", posting["title"], posting["company"], result["fit_score"])


def prefill_top_matches(rows: list) -> dict:
    """Attempt semi-auto form pre-fill for the highest-fit postings. Returns id -> status."""
    statuses = {}
    for row in rows:
        if row["fit_score"] < FIT_SCORE_PREFILL_THRESHOLD:
            continue
        adapter = get_adapter_for_url(row["url"], ALL_ADAPTERS)
        if not adapter:
            continue
        posting = dict(row)
        result = adapter.prefill(posting)
        statuses[row["id"]] = result.status
        db.mark_status(row["id"], result.status)
        logger.info("Prefill for '%s': %s (%s)", row["title"], result.status, result.detail)
    return statuses


def build_digest_rows(rows: list, prefill_statuses: dict) -> list[dict]:
    out = []
    for row in rows:
        d = dict(row)
        d["tailored_bullets"] = (d.get("tailored_bullets") or "").split("\n") if d.get("tailored_bullets") else []
        d["prefill_status"] = prefill_statuses.get(row["id"])
        out.append(d)
    # Rank by fit_score, with location_boost recomputed at digest render time isn't stored,
    # so fit_score already dominates; ties broken by company name for stability.
    out.sort(key=lambda j: (-j["fit_score"], j["company"]))
    return out


def main():
    logger.info("=== Starting daily job scraper run ===")
    raw_postings = run_scrapers()
    normalized = normalize_all(raw_postings)
    new_postings = dedup_and_store(normalized)
    if new_postings:
        evaluate_new_postings(new_postings)

    all_to_email = db.get_postings_to_email(FIT_SCORE_RECOMMEND_THRESHOLD)
    prefill_statuses = prefill_top_matches(all_to_email)

    priority0 = build_digest_rows([r for r in all_to_email if r["priority_tier"] == "priority0"], prefill_statuses)
    startups = build_digest_rows([r for r in all_to_email if r["priority_tier"] == "startup"], prefill_statuses)

    sent = send_digest(priority0, startups)
    if sent:
        db.mark_emailed([r["id"] for r in priority0 + startups])

    logger.info("=== Run complete: %d priority0, %d startup postings sent ===", len(priority0), len(startups))


if __name__ == "__main__":
    main()
