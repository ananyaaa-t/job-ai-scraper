"""
Workday application form pre-fill adapter.

Workday-hosted career sites (used by many large companies, e.g. some
Microsoft/enterprise postings) are heavily templated per-tenant with
shifting field ids, multi-step wizards, and mandatory account creation
before a form is even visible. Because of this, full field automation is
unreliable across tenants. This adapter therefore does the safe, high-value
part only: opens the posting, waits for load, and reports back so the
candidate applies manually — it declares itself "matched" but reports
'unsupported' for actual pre-fill rather than guessing at brittle selectors.
"""
import logging

from playwright.sync_api import sync_playwright

from apply.base_adapter import ATSAdapter, PrefillResult

logger = logging.getLogger(__name__)


class WorkdayAdapter(ATSAdapter):
    @staticmethod
    def matches(url: str) -> bool:
        return "myworkdayjobs.com" in url

    def prefill(self, posting: dict) -> PrefillResult:
        url = posting["url"]
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False)
                page = browser.new_page()
                page.goto(url, timeout=30000)
                # Workday requires account creation/login before the application
                # form fields are even present, and field ids vary per tenant —
                # too unreliable to auto-fill safely. Leave open for manual apply.
                return PrefillResult(
                    posting["id"], url, "unsupported",
                    "Workday postings vary too much per company to auto-fill reliably; "
                    "opened for manual application.",
                )
        except Exception as e:
            logger.warning("Workday open failed for %s: %s", url, e)
            return PrefillResult(posting["id"], url, "failed", str(e))
