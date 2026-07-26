"""
Deterministic pre-filter for years-of-experience requirements.

Job postings often state an explicit minimum years-of-experience requirement
(e.g. "3+ years", "5-7 years of experience", "minimum of 4 years"). Rather
than relying on the LLM to always catch and penalize this correctly, this
module extracts any such requirement with regex and applies a hard cutoff
before a posting is ever sent to Gemini for scoring. This is both more
reliable and saves API calls on postings that should never be recommended.
"""
import re

# A single alternation-based pattern, checked in priority order at each
# position in the text, so range phrases like "5-7 years" are consumed as one
# match (capturing the true lower bound) instead of also being re-matched by
# a more generic pattern later in the string (which would incorrectly grab
# the upper bound as if it were a separate, higher requirement).
_YEARS_PATTERN = re.compile(
    r"(?:(?P<range_dash>\d+)\s*[-–—]\s*\d+\+?\s*years?)"
    r"|(?:(?P<range_to>\d+)\s+to\s+\d+\+?\s*years?)"
    r"|(?:(?:minimum|at least)\s+(?:of\s+)?(?P<min_phrase>\d+)\+?\s*years?)"
    r"|(?:(?P<plus>\d+)\+\s*years?)"
    r"|(?:(?P<generic>\d+)\+?\s*years?\s+(?:of\s+)?(?:\w+\s+){0,3}experience)",
    re.IGNORECASE,
)


def extract_min_years_required(text: str) -> int | None:
    """Returns the highest minimum-years figure found in the text, or None if
    no years-of-experience requirement was detected. For range phrases (e.g.
    "3-5 years"), the lower bound is used as that phrase's requirement."""
    if not text:
        return None
    found = []
    for match in _YEARS_PATTERN.finditer(text):
        group_value = match.group("range_dash") or match.group("range_to") \
            or match.group("min_phrase") or match.group("plus") or match.group("generic")
        if group_value is not None:
            found.append(int(group_value))
    return max(found) if found else None


def exceeds_max_years(text: str, max_years: int | None) -> bool:
    """True if the text states an experience requirement strictly greater
    than max_years. If max_years is None, this filter is disabled."""
    if max_years is None:
        return False
    required = extract_min_years_required(text)
    return required is not None and required > max_years
