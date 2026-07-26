"""
Applicant profile used to pre-fill application forms.

Generic placeholders below are committed to the repo. To use your own real
contact info, create `apply/applicant_profile_local.py` (gitignored, never
committed) defining any of the same variable names — they'll automatically
override the placeholders below. See README.md for the exact fields to set.
"""
FULL_NAME = "Your Full Name"
FIRST_NAME = "Your"
LAST_NAME = "Name"
EMAIL = "you@example.com"
PHONE = "555-555-5555"
LOCATION = "City, ST"
GITHUB_URL = "https://github.com/yourusername"
PORTFOLIO_URL = "https://yourportfolio.example.com"
LINKEDIN_URL = "https://linkedin.com/in/yourusername/"
RESUME_FILE = "data/resume.txt"  # swap for a PDF export path when available

try:
    from apply.applicant_profile_local import *  # noqa: F401,F403 - optional personal overrides
except ImportError:
    pass
