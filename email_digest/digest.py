"""
Builds and sends the daily HTML digest email via Gmail SMTP (App Password),
split into "Priority 0" and "Startups" sections, ranked by fit score with a
Seattle/SF location boost applied.
"""
import logging
import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from jinja2 import Template

from config.settings import DIGEST_RECIPIENT, GMAIL_ADDRESS, GMAIL_APP_PASSWORD

logger = logging.getLogger(__name__)

TEMPLATE = Template("""
<html>
<body style="font-family: -apple-system, Helvetica, Arial, sans-serif; color:#1a1a1a; max-width:700px; margin:auto;">
  <h2 style="margin-bottom:0;">Job Digest — {{ today }}</h2>
  <p style="color:#666; margin-top:4px;">{{ total }} new recommended postings today.</p>

  {% for section_name, jobs in sections %}
    {% if jobs %}
      <h3 style="border-bottom:2px solid #eee; padding-bottom:4px;">{{ section_name }} ({{ jobs|length }})</h3>
      {% for job in jobs %}
        <div style="margin-bottom:18px; padding:12px; border:1px solid #eee; border-radius:8px;">
          <div style="font-size:16px; font-weight:600;">
            <a href="{{ job.url }}" style="color:#0a58ca; text-decoration:none;">{{ job.title }}</a>
          </div>
          <div style="color:#444;">{{ job.company }} — {{ job.location or "location n/a" }}</div>
          <div style="margin-top:6px;">
            <b>Fit score:</b> {{ job.fit_score }}/100
            {% if job.prefill_status %} · <b>Application:</b> {{ job.prefill_status }}{% endif %}
          </div>
          <div style="margin-top:6px; color:#333;">{{ job.fit_reasoning }}</div>
          {% if job.tailored_bullets %}
            <div style="margin-top:8px;"><b>Suggested tailored bullets:</b>
              <ul>{% for b in job.tailored_bullets %}<li>{{ b }}</li>{% endfor %}</ul>
            </div>
          {% endif %}
        </div>
      {% endfor %}
    {% endif %}
  {% endfor %}
  <p style="color:#999; font-size:12px;">Sent automatically by your local job-scraper. Application forms are
  pre-filled only, never auto-submitted — always review before applying.</p>
</body>
</html>
""")


def build_digest_html(priority0_jobs: list[dict], startup_jobs: list[dict]) -> str:
    return TEMPLATE.render(
        today=date.today().strftime("%B %d, %Y"),
        total=len(priority0_jobs) + len(startup_jobs),
        sections=[("Priority 0 Companies", priority0_jobs), ("Startups", startup_jobs)],
    )


def send_digest(priority0_jobs: list[dict], startup_jobs: list[dict]) -> bool:
    if not priority0_jobs and not startup_jobs:
        logger.info("No jobs to send today; skipping email.")
        return False
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        raise RuntimeError("GMAIL_ADDRESS / GMAIL_APP_PASSWORD not set in environment/.env")

    html = build_digest_html(priority0_jobs, startup_jobs)
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Job Digest — {date.today().strftime('%b %d')} " \
                      f"({len(priority0_jobs) + len(startup_jobs)} matches)"
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = DIGEST_RECIPIENT
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, [DIGEST_RECIPIENT], msg.as_string())
    logger.info("Digest email sent to %s", DIGEST_RECIPIENT)
    return True
