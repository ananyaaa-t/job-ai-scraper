# Job AI Scraper

Daily job-search assistant: scrapes Priority 0 companies (Google, Apple,
Microsoft, Notion, Stripe), Tier 2 companies (Airbnb, Figma, Pinterest,
Vercel, Slack, Cursor, Perplexity, Cognition), and general startup sources
(YC/Work at a Startup, Wellfound, LinkedIn best-effort), scores fit against
your resume with Gemini, semi-automates application form pre-fill, and
emails you a daily digest via Gmail.

**Safety guarantee:** application forms are pre-filled only — the tool never
clicks submit. You always review and submit manually.

**Privacy by design:** all personal data (resume, contact info, career
profile) lives in gitignored local files, never committed. The repo only
ever contains generic placeholder templates — see step 3 below.

## 1. Setup

```bash
cd ~/job-ai-scraper
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

## 2. Configure secrets

```bash
cp .env.example .env
```

Then edit `.env`:
- `GEMINI_API_KEY` — free tier key from https://aistudio.google.com/apikey
- `GMAIL_ADDRESS` — the Gmail account that will send the digest
- `GMAIL_APP_PASSWORD` — a 16-character [App Password](https://myaccount.google.com/apppasswords)
  (requires 2FA enabled on the Google account; do NOT use your normal password)
- `DIGEST_RECIPIENT` — the email address that should receive the daily digest

`.env` is gitignored and never committed.

## 3. Add your personal data (gitignored, never committed)

Three pieces of personal data are excluded from git via generic-default +
local-override files. To use your own:

| What | Generic template (committed) | Your real data (gitignored, create it) |
|---|---|---|
| Resume text fed to the LLM | `data/resume.example.txt` | `data/resume.txt` |
| Career profile/preferences fed to the LLM | built into `config/settings.py` | `config/candidate_profile_local.py` (define `CANDIDATE_PROFILE = "..."`) |
| Application form contact info | built into `apply/applicant_profile.py` | `apply/applicant_profile_local.py` (define `FULL_NAME`, `EMAIL`, `PHONE`, etc.) |

If the `_local`/real files don't exist, the app runs fine with the generic
placeholders (useful for anyone forking this as a reusable tool).

## 4. Run manually

```bash
source .venv/bin/activate
python orchestrator.py
```

Logs are written to `logs/orchestrator.log` and also printed to stdout.
The SQLite dedup DB lives at `data/jobs.db` (gitignored).

## 5. Schedule it daily (macOS)

macOS's cron is often blocked by System Integrity Protection for launching
GUI browser processes (needed for Playwright pre-fill), so `launchd` is more
reliable than crontab on Mac. Example `launchd` plist:

`~/Library/LaunchAgents/com.ananya.jobscraper.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.ananya.jobscraper</string>
  <key>ProgramArguments</key>
  <array>
    <string>/Users/ananyathapar/job-ai-scraper/.venv/bin/python</string>
    <string>/Users/ananyathapar/job-ai-scraper/orchestrator.py</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key><integer>7</integer>
    <key>Minute</key><integer>0</integer>
  </dict>
  <key>WorkingDirectory</key><string>/Users/ananyathapar/job-ai-scraper</string>
  <key>StandardOutPath</key><string>/Users/ananyathapar/job-ai-scraper/logs/launchd.out.log</string>
  <key>StandardErrorPath</key><string>/Users/ananyathapar/job-ai-scraper/logs/launchd.err.log</string>
</dict>
</plist>
```
Load it with: `launchctl load ~/Library/LaunchAgents/com.ananya.jobscraper.plist`

Alternatively, a plain crontab entry works fine if you disable/adjust the
Playwright pre-fill step (or run headless) since cron sessions have no GUI:
```
0 7 * * * cd /Users/ananyathapar/job-ai-scraper && .venv/bin/python orchestrator.py >> logs/cron.log 2>&1
```

## Architecture

```
job-ai-scraper/
├── config/settings.py     # companies, role keywords, thresholds, candidate profile
├── scrapers/               # one module per source, all implement Scraper.fetch()
│   ├── base.py             # shared HTTP helpers + role/seniority keyword filter
│   ├── company_pages.py    # Greenhouse API + generic HTML scraping for named companies
│   ├── ashby.py            # Ashby public API (Cursor, Perplexity, Cognition, ...)
│   ├── yc_startups.py, wellfound.py, linkedin.py
├── normalize.py            # raw postings -> common schema + location boost
├── storage/db.py           # SQLite dedup + status tracking
├── evaluator/fit_llm.py    # Gemini fit scoring + tailored bullets + cover letter draft
├── apply/                  # Greenhouse/Lever/Workday form pre-fill (never submits)
├── email_digest/digest.py  # HTML digest builder + Gmail SMTP sender
└── orchestrator.py         # daily pipeline entry point
```

## Company sources

| Tier | Companies | Board type |
|---|---|---|
| Priority 0 | Google, Apple, Microsoft | Custom HTML scrape |
| Priority 0 | Notion, Stripe | Greenhouse API |
| Tier 2 | Airbnb, Figma, Pinterest, Vercel | Greenhouse API |
| Tier 2 | Slack | Custom HTML scrape |
| Tier 2 | Cursor, Perplexity, Cognition | Ashby API |
| Startups (general) | YC/Work at a Startup, Wellfound, LinkedIn (best-effort) | scraped broadly by role keyword |

Add more companies by adding an entry to `PRIORITY_0_COMPANIES` or
`TIER_2_COMPANIES` in `config/settings.py` — Greenhouse and Ashby entries
just need a `board_token`; anything else falls back to the generic HTML
scraper via a `careers_url`.

## Known limitations (by design, see plan)
- **LinkedIn** scraping is best-effort/ToS-sensitive and may break or return
  nothing at any time — treat it as a bonus source, not a dependency.
- **Google/Apple/Microsoft/Slack** career pages are scraped via HTML
  heuristics (no public JSON API); may need selector updates if results come
  back empty.
- **Workday** postings are opened for manual application but not auto-filled
  — field structure varies too much per company tenant to do safely.
- Resume **file upload** in application forms is always manual (OS-native
  file dialogs aren't automated).
