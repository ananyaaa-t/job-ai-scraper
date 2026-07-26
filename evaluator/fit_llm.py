"""
LLM-based fit evaluation using the Google Gemini API (free tier).

For each new job posting, asks Gemini to:
  1. Score fit 0-100 against the candidate profile + resume.
  2. Explain the reasoning in 2-3 sentences.
  3. Suggest 2-4 tailored resume bullet rewrites specific to this posting.
  4. Draft a short (3-4 sentence) cover-letter opening paragraph.

Returns a structured dict; falls back to a neutral/skip result if the API
call fails or the response can't be parsed, so one bad call never crashes
the whole daily run.
"""
import json
import logging

from google import genai
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import CANDIDATE_PROFILE, GEMINI_API_KEY, RESUME_PATH

logger = logging.getLogger(__name__)

MODEL_NAME = "gemini-flash-lite-latest"  # alias that auto-tracks the current fast/free-tier model

PROMPT_TEMPLATE = """\
You are an expert technical recruiter evaluating a job posting for a candidate.

## Candidate profile
{profile}

## Candidate resume
{resume}

## Job posting
Title: {title}
Company: {company}
Location: {location}
Description:
{description}

## Task
Evaluate how strong a fit this posting is for the candidate. Respond with ONLY a
JSON object (no markdown fences, no extra text) with exactly these keys:
{{
  "fit_score": <integer 0-100>,
  "reasoning": "<2-3 sentence explanation of the score, referencing specific resume/profile details>",
  "tailored_bullets": ["<rewritten resume bullet 1 tailored to this posting>", "<bullet 2>", "<bullet 3>"],
  "cover_letter_opening": "<3-4 sentence cover letter opening paragraph tailored to this posting>"
}}
"""

_client = None


def _get_client():
    global _client
    if _client is None:
        if not GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not set in the environment/.env file")
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def _load_resume() -> str:
    if RESUME_PATH.exists():
        return RESUME_PATH.read_text()
    return "(resume not found)"


def _fallback_result(reason: str) -> dict:
    return {
        "fit_score": 0,
        "reasoning": f"Evaluation skipped: {reason}",
        "tailored_bullets": [],
        "cover_letter_opening": "",
    }


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=15))
def _call_gemini(prompt: str) -> str:
    client = _get_client()
    response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
    return response.text


def evaluate_fit(posting: dict) -> dict:
    """
    posting: normalized dict with keys title, company, location, description.
    Returns dict: fit_score, reasoning, tailored_bullets (list[str]), cover_letter_opening.
    """
    prompt = PROMPT_TEMPLATE.format(
        profile=CANDIDATE_PROFILE,
        resume=_load_resume(),
        title=posting.get("title", ""),
        company=posting.get("company", ""),
        location=posting.get("location", ""),
        description=(posting.get("description") or "")[:6000],  # keep prompt reasonably sized
    )
    try:
        raw_text = _call_gemini(prompt)
    except Exception as e:
        logger.warning("Gemini call failed for %s @ %s: %s", posting.get("title"), posting.get("company"), e)
        return _fallback_result(str(e))

    cleaned = raw_text.strip().strip("`")
    if cleaned.lower().startswith("json"):
        cleaned = cleaned[4:].strip()
    try:
        parsed = json.loads(cleaned)
        return {
            "fit_score": int(parsed.get("fit_score", 0)),
            "reasoning": parsed.get("reasoning", ""),
            "tailored_bullets": parsed.get("tailored_bullets", []),
            "cover_letter_opening": parsed.get("cover_letter_opening", ""),
        }
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        logger.warning("Could not parse Gemini response for %s: %s\nRaw: %s", posting.get("title"), e, raw_text)
        return _fallback_result("could not parse model response")
