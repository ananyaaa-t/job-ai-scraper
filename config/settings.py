"""
Central configuration for the job scraper: companies to track, role keywords,
location preferences, and the candidate profile used to ground LLM fit evaluation.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
DB_PATH = DATA_DIR / "jobs.db"
RESUME_PATH = DATA_DIR / "resume.txt"

# --- Priority 0 companies (always scraped, always shown in their own digest section) ---
PRIORITY_0_COMPANIES = [
    {"name": "Google", "slug": "google", "board_type": "custom", "careers_url": "https://www.google.com/about/careers/applications/jobs/results/"},
    {"name": "Apple", "slug": "apple", "board_type": "custom", "careers_url": "https://jobs.apple.com/en-us/search"},
    {"name": "Microsoft", "slug": "microsoft", "board_type": "custom", "careers_url": "https://jobs.careers.microsoft.com/global/en/search"},
    {"name": "Notion", "slug": "notion", "board_type": "greenhouse", "board_token": "notion"},
    {"name": "Stripe", "slug": "stripe", "board_type": "greenhouse", "board_token": "stripe"},
]

# --- Tier 2 companies (admired product-driven companies + notable AI-native startups) ---
# Scraped and shown in the "Startups"/secondary section, not Priority 0.
TIER_2_COMPANIES = [
    {"name": "Airbnb", "slug": "airbnb", "board_type": "greenhouse", "board_token": "airbnb"},
    {"name": "Figma", "slug": "figma", "board_type": "greenhouse", "board_token": "figma"},
    {"name": "Pinterest", "slug": "pinterest", "board_type": "greenhouse", "board_token": "pinterest"},
    {"name": "Vercel", "slug": "vercel", "board_type": "greenhouse", "board_token": "vercel"},
    {"name": "Slack", "slug": "slack", "board_type": "custom", "careers_url": "https://slack.com/careers"},
    {"name": "Cursor", "slug": "cursor", "board_type": "ashby", "board_token": "cursor"},
    {"name": "Perplexity", "slug": "perplexity", "board_type": "ashby", "board_token": "perplexity"},
    {"name": "Cognition", "slug": "cognition", "board_type": "ashby", "board_token": "cognition"},
]

# --- Role keywords used to filter postings from every source ---
ROLE_KEYWORDS = [
    "software engineer i", "software engineer, new grad", "new grad software engineer",
    "software engineer 1", "swe i", "swe 1", "early career software engineer",
    "forward deployed engineer", "software engineer", "full stack engineer",
    "product engineer",
]
SENIORITY_EXCLUDE_KEYWORDS = [
    "senior", "staff", "principal", "lead ", "manager", "director", "architect",
]

# --- Years-of-experience cap ---
# Postings that explicitly require more than this many years of experience are
# excluded before they ever reach the LLM (see evaluator/fit_llm.py). Set to
# None to disable this filter entirely.
MAX_YEARS_EXPERIENCE = 2

# --- Location preferences (used for ranking/boosting, never a hard filter) ---
LOCATION_BOOST = {
    "seattle": 15,
    "sf": 10, "san francisco": 10, "bay area": 8,
}
REMOTE_KEYWORDS = ["remote"]

# --- Startup sources ---
STARTUP_SOURCES = {
    "yc": {"enabled": True, "url": "https://www.workatastartup.com/jobs"},
    "wellfound": {"enabled": True, "url": "https://wellfound.com/jobs"},
    "linkedin": {"enabled": True, "best_effort": True},  # ToS-sensitive, see scrapers/linkedin.py
}

# --- Fit evaluation thresholds ---
FIT_SCORE_RECOMMEND_THRESHOLD = 65  # >= this score -> included in digest
FIT_SCORE_PREFILL_THRESHOLD = 80    # >= this score -> attempt semi-auto form pre-fill

# --- Candidate profile fed to the LLM for every fit evaluation ---
# Generic placeholder below is committed to the repo. To use your own real
# background, create config/candidate_profile_local.py (gitignored) defining
# CANDIDATE_PROFILE — it will automatically override the placeholder below.
CANDIDATE_PROFILE = """
Name: Your Name
Current role: Your current job title and company, and how long you've been there
Education: Degree, school, graduation date
Location: Where you're based and your location preferences (top choice, secondary
  choices, and whether you're open to remote/hybrid/onsite elsewhere).
Target roles: The specific job titles/levels you're targeting (e.g. "Software Engineer I",
  "Forward Deployed Engineer"). Note any levels you explicitly do NOT want (e.g. senior/staff).
Interests: The kind of work you want to do (e.g. full-stack, developer tools, AI products)
  versus what you want to move away from (e.g. pure infrastructure).
Career direction: Your longer-term career goals and the kind of company culture/product
  philosophy you're drawn to (list a few companies you admire, if helpful).
Key differentiator: What makes you stand out beyond baseline technical skills — e.g.
  leadership experience, notable projects, unique background.
"""
try:
    from config.candidate_profile_local import CANDIDATE_PROFILE  # noqa: F811 - optional personal override
except ImportError:
    pass

GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
DIGEST_RECIPIENT = os.environ.get("DIGEST_RECIPIENT", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
