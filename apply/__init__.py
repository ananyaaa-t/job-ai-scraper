"""Registry of all available ATS adapters for application pre-fill."""
from apply.base_adapter import ATSAdapter, get_adapter_for_url
from apply.greenhouse import GreenhouseAdapter
from apply.lever import LeverAdapter
from apply.workday import WorkdayAdapter

ALL_ADAPTERS: list[ATSAdapter] = [GreenhouseAdapter(), LeverAdapter(), WorkdayAdapter()]

__all__ = ["ALL_ADAPTERS", "get_adapter_for_url"]
