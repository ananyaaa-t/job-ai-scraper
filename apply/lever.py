"""
Lever application form pre-fill adapter. Lever forms typically use
name="name", name="email", name="phone", name="org" (LinkedIn/GitHub/portfolio
usually go in a generic "urls[...]" field set). Same safety rule as
Greenhouse: fills fields, never submits.
"""
import logging

from playwright.sync_api import sync_playwright

from apply import applicant_profile as profile
from apply.base_adapter import ATSAdapter, PrefillResult

logger = logging.getLogger(__name__)


class LeverAdapter(ATSAdapter):
    @staticmethod
    def matches(url: str) -> bool:
        return "jobs.lever.co" in url

    def prefill(self, posting: dict) -> PrefillResult:
        url = posting["url"]
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False)
                page = browser.new_page()
                page.goto(url, timeout=30000)

                self._fill_if_present(page, "input[name='name']", profile.FULL_NAME)
                self._fill_if_present(page, "input[name='email']", profile.EMAIL)
                self._fill_if_present(page, "input[name='phone']", profile.PHONE)
                self._fill_if_present(page, "input[name='org']", "")
                for selector in ["input[name*='urls[LinkedIn]' i]", "input[name*='linkedin' i]"]:
                    self._fill_if_present(page, selector, profile.LINKEDIN_URL)
                for selector in ["input[name*='urls[GitHub]' i]", "input[name*='github' i]"]:
                    self._fill_if_present(page, selector, profile.GITHUB_URL)
                for selector in ["input[name*='urls[Portfolio]' i]", "input[name*='portfolio' i]"]:
                    self._fill_if_present(page, selector, profile.PORTFOLIO_URL)

                return PrefillResult(posting["id"], url, "prefilled",
                                      "Form pre-filled; resume upload + review + submit are manual.")
        except Exception as e:
            logger.warning("Lever prefill failed for %s: %s", url, e)
            return PrefillResult(posting["id"], url, "failed", str(e))

    @staticmethod
    def _fill_if_present(page, selector: str, value: str):
        try:
            locator = page.locator(selector).first
            if locator.count() > 0:
                locator.fill(value)
        except Exception:
            pass
