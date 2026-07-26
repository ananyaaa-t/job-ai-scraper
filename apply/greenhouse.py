"""
Greenhouse application form pre-fill adapter.

Greenhouse-hosted "Apply" pages use fairly consistent field names/ids
(first_name, last_name, email, phone) which makes them the most reliable
target for automated pre-fill. Resume upload is left for the human to attach
manually (file upload dialogs are OS-native and not worth automating for a
one-person tool), everything else supported is filled in.
"""
import logging

from playwright.sync_api import sync_playwright

from apply import applicant_profile as profile
from apply.base_adapter import ATSAdapter, PrefillResult

logger = logging.getLogger(__name__)


class GreenhouseAdapter(ATSAdapter):
    @staticmethod
    def matches(url: str) -> bool:
        return "greenhouse.io" in url or "boards.greenhouse.io" in url

    def prefill(self, posting: dict) -> PrefillResult:
        url = posting["url"]
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False)
                page = browser.new_page()
                page.goto(url, timeout=30000)

                self._fill_if_present(page, "input#first_name", profile.FIRST_NAME)
                self._fill_if_present(page, "input#last_name", profile.LAST_NAME)
                self._fill_if_present(page, "input#email", profile.EMAIL)
                self._fill_if_present(page, "input#phone", profile.PHONE)

                # Common "additional links" free-text fields, best-effort.
                for selector in ["input[name*='github' i]"]:
                    self._fill_if_present(page, selector, profile.GITHUB_URL)
                for selector in ["input[name*='linkedin' i]"]:
                    self._fill_if_present(page, selector, profile.LINKEDIN_URL)
                for selector in ["input[name*='portfolio' i]", "input[name*='website' i]"]:
                    self._fill_if_present(page, selector, profile.PORTFOLIO_URL)

                # Intentionally does NOT click submit. Browser stays open for review.
                return PrefillResult(posting["id"], url, "prefilled",
                                      "Form pre-filled; resume upload + review + submit are manual.")
        except Exception as e:
            logger.warning("Greenhouse prefill failed for %s: %s", url, e)
            return PrefillResult(posting["id"], url, "failed", str(e))

    @staticmethod
    def _fill_if_present(page, selector: str, value: str):
        try:
            locator = page.locator(selector).first
            if locator.count() > 0:
                locator.fill(value)
        except Exception:
            pass  # field not present / not fillable — skip silently, non-fatal
