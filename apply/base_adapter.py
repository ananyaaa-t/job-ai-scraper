"""
Base interface for ATS (Applicant Tracking System) form pre-fill adapters.

CRITICAL SAFETY RULE: adapters may fill in form fields but must NEVER click
submit/apply. The browser is left open (headless=False) on the review step
so a human reviews everything and submits manually. This is enforced by
never calling a submit action anywhere in this module or its subclasses.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class PrefillResult:
    posting_id: str
    url: str
    status: str          # 'prefilled' | 'unsupported' | 'failed'
    detail: str = ""


class ATSAdapter(ABC):
    """One adapter per ATS platform (Greenhouse, Lever, Workday, ...)."""

    @staticmethod
    @abstractmethod
    def matches(url: str) -> bool:
        """Return True if this adapter knows how to handle the given posting URL."""
        ...

    @abstractmethod
    def prefill(self, posting: dict) -> PrefillResult:
        """
        Open the application form in a visible (non-headless) browser and fill
        in known fields from apply.applicant_profile. Must leave the browser
        open and NOT submit — the human reviews and submits manually.
        """
        ...


def get_adapter_for_url(url: str, adapters: list[ATSAdapter]) -> ATSAdapter | None:
    for adapter in adapters:
        if adapter.matches(url):
            return adapter
    return None
