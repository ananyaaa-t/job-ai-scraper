# Job AI Scraper

A script that scrapes job postings from a set of companies I care about
(Google, Apple, Microsoft, Notion, Stripe, plus a "tier 2" list of Airbnb,
Figma, Pinterest, Vercel, Slack, Cursor, Perplexity, Cognition) as well as
general startup boards (YC, Wellfound, LinkedIn), runs each posting through
Gemini to score how well it fits my resume/background, and emails me a
digest every morning. For the strongest matches it'll also pre-fill the
application form in a browser window so I just have to review and hit
submit myself.

It doesn't submit anything on its own — that part's always manual.

## Setup

```bash
cd ~/job-ai-scraper
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

Copy `.env.example` to `.env` and fill in:
- `GEMINI_API_KEY` — free tier key, get one at https://aistudio.google.com/apikey
- `GMAIL_ADDRESS` / `GMAIL_APP_PASSWORD` — the Gmail account sending the digest.
  Use an [App Password](https://myaccount.google.com/apppasswords), not your real password.
- `DIGEST_RECIPIENT` — where the digest gets sent

## Your resume / info

None of this stuff is checked into the repo — I kept my actual resume and
contact info in a few gitignored files instead:

- `data/resume.txt` — your resume as plain text (there's a `resume.example.txt` for format reference)
- `config/candidate_profile_local.py` — set `CANDIDATE_PROFILE = "..."` with your background, target roles, location prefs, whatever you want the LLM to know when judging fit
- `apply/applicant_profile_local.py` — name/email/phone/links used to pre-fill application forms

If those files aren't there it just falls back to placeholder values, so
the repo is safe to clone/fork without pulling in anyone's personal info.

## Running it

```bash
source .venv/bin/activate
python orchestrator.py
```

Logs go to `logs/orchestrator.log`, and the dedup DB is a plain SQLite file
at `data/jobs.db` so you never get emailed about the same posting twice.

To run it every morning, I set it up as a launchd job (cron on Mac has
issues launching a real browser window for the Playwright part):

```xml
<!-- ~/Library/LaunchAgents/com.ananya.jobscraper.plist -->
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

```
launchctl load ~/Library/LaunchAgents/com.ananya.jobscraper.plist
```

A regular crontab line works too, as long as you're okay with the
application pre-fill step not popping up a window (cron has no GUI):

```
0 7 * * * cd /Users/ananyathapar/job-ai-scraper && .venv/bin/python orchestrator.py >> logs/cron.log 2>&1
```

## How it's put together

```
config/settings.py     -> companies, role keywords, thresholds
scrapers/               -> one file per source (Greenhouse, Ashby, YC, Wellfound, LinkedIn, plain HTML)
normalize.py            -> turns whatever a scraper returns into one common shape
storage/db.py           -> SQLite, just for dedup + status tracking
evaluator/fit_llm.py    -> sends each posting + resume to Gemini, gets back a score + tailored bullets
apply/                  -> Playwright adapters that pre-fill Greenhouse/Lever forms
email_digest/digest.py  -> builds the HTML email and sends it through Gmail
orchestrator.py         -> the script that ties it all together, run daily
```

## Where jobs come from

- Google, Apple, Microsoft — scraped straight off their careers pages (no public API, so this is the most fragile part and might need fixing if a site redesign breaks it)
- Notion, Stripe, Airbnb, Figma, Pinterest, Vercel — Greenhouse's public API
- Slack — careers page scrape, same as Google/Apple/Microsoft
- Cursor, Perplexity, Cognition — these all run on Ashby, which also has a public API
- YC/Work at a Startup, Wellfound, LinkedIn — broader startup search, not tied to a specific company list

Adding a new company is usually a one-line addition to `PRIORITY_0_COMPANIES`
or `TIER_2_COMPANIES` in `config/settings.py` if they're on Greenhouse or
Ashby. Anything else needs a `careers_url` and falls back to generic HTML
scraping, which is less reliable.

## Stuff that's not perfect

- LinkedIn scraping can just stop working at any time — it's unauthenticated and LinkedIn doesn't want you doing this, so I treat it as a bonus, not something to depend on.
- The Google/Apple/Microsoft/Slack scrapers are HTML heuristics against pages that aren't meant to be scraped, so they'll need occasional fixes.
- Workday-hosted postings just get opened in a browser tab for you to fill out by hand — every company's Workday form is different enough that auto-filling it reliably wasn't worth the risk of it going wrong silently.
- You still have to manually attach your resume file in any pre-filled form — file upload dialogs are OS-level and not something I bothered automating for a personal tool.
