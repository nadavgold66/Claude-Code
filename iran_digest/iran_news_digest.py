#!/usr/bin/env python3
"""
Iran News Digest
Fetches Iran-related news from multiple RSS feeds, summarizes the top 10
most important stories using Google Gemini, and sends an HTML email via Resend.
"""

import os
import sys
import json
import re
import time
import requests
import feedparser
import google.generativeai as genai
from datetime import datetime, timezone
from typing import Optional
from email.utils import parsedate_to_datetime


# ---------------------------------------------------------------------------
# News Sources
# ---------------------------------------------------------------------------

RSS_FEEDS = [
    # International wire / broad coverage (filtered for Iran keywords)
    {
        "name": "Google News – Iran",
        "url": "https://news.google.com/rss/search?q=Iran&hl=en-US&gl=US&ceid=US:en",
        "iran_only": False,   # already filtered by Google
    },
    {
        "name": "Google News – Iran Politics",
        "url": "https://news.google.com/rss/search?q=Iran+politics+geopolitics&hl=en-US&gl=US&ceid=US:en",
        "iran_only": False,
    },
    {
        "name": "Google News – Iran Nuclear",
        "url": "https://news.google.com/rss/search?q=Iran+nuclear+sanctions&hl=en-US&gl=US&ceid=US:en",
        "iran_only": False,
    },
    {
        "name": "Reuters – World News",
        "url": "https://feeds.reuters.com/reuters/worldNews",
        "iran_only": True,   # filter for Iran keywords
    },
    {
        "name": "Al Jazeera – All",
        "url": "https://www.aljazeera.com/xml/rss/all.xml",
        "iran_only": True,
    },
    {
        "name": "BBC – World",
        "url": "https://feeds.bbci.co.uk/news/world/rss.xml",
        "iran_only": True,
    },
    # Iran-focused / regional outlets
    {
        "name": "Iran International",
        "url": "https://www.iranintl.com/en/rss",
        "iran_only": False,
    },
    {
        "name": "Radio Farda (RFE/RL)",
        "url": "https://www.radiofarda.com/api/zmpbjqimiv",
        "iran_only": False,
    },
    {
        "name": "IRNA – English",
        "url": "https://en.irna.ir/rss",
        "iran_only": False,
    },
    {
        "name": "Tehran Times",
        "url": "https://www.tehrantimes.com/rss",
        "iran_only": False,
    },
    {
        "name": "Mehr News Agency",
        "url": "https://en.mehrnews.com/rss",
        "iran_only": False,
    },
    {
        "name": "Press TV",
        "url": "https://www.presstv.ir/rss",
        "iran_only": False,
    },
]

# Keywords used to filter non-Iran-specific feeds
IRAN_KEYWORDS = {
    "iran", "iranian", "tehran", "khamenei", "khomeini", "raisi", "pezeshkian",
    "irgc", "islamic republic", "rouhani", "zarif", "araghchi",
    "nuclear deal", "jcpoa", "natanz", "fordow", "bushehr",
    "strait of hormuz", "persian gulf", "hezbollah", "hamas", "axis of resistance",
    "revolutionary guard", "basij", "rial", "sanctions on iran",
}


# ---------------------------------------------------------------------------
# Article fetching
# ---------------------------------------------------------------------------

def _is_iran_related(title: str, description: str) -> bool:
    """Return True if the text appears to be about Iran."""
    combined = (title + " " + description).lower()
    return any(kw in combined for kw in IRAN_KEYWORDS)


def _parse_date(entry) -> datetime:
    """Extract a timezone-aware datetime from a feedparser entry."""
    for field in ("published", "updated"):
        raw = entry.get(field)
        if raw:
            try:
                return parsedate_to_datetime(raw)
            except Exception:
                pass
    return datetime.now(timezone.utc)


def fetch_articles() -> list[dict]:
    """Fetch and deduplicate Iran-related articles from all RSS feeds."""
    articles: list[dict] = []
    seen_urls: set[str] = set()

    for feed_info in RSS_FEEDS:
        name = feed_info["name"]
        url = feed_info["url"]
        iran_only = feed_info["iran_only"]

        try:
            feed = feedparser.parse(url, request_headers={"User-Agent": "IranNewsDigest/1.0"})
            count = 0
            for entry in feed.entries[:20]:
                title = entry.get("title", "").strip()
                description = (
                    entry.get("summary", entry.get("description", "")).strip()
                )
                # Strip HTML tags from description
                description = re.sub(r"<[^>]+>", "", description)[:200]
                link = entry.get("link", "").strip()

                if not title or not link:
                    continue
                if link in seen_urls:
                    continue
                if iran_only and not _is_iran_related(title, description):
                    continue

                seen_urls.add(link)
                articles.append(
                    {
                        "source": name,
                        "title": title,
                        "description": description,
                        "url": link,
                        "published": _parse_date(entry),
                    }
                )
                count += 1

            print(f"  [{name}] {count} articles")
        except Exception as exc:
            print(f"  [{name}] ERROR: {exc}", file=sys.stderr)

    # Sort newest first
    articles.sort(key=lambda a: a["published"], reverse=True)
    print(f"\nTotal unique Iran-related articles: {len(articles)}")
    return articles


# ---------------------------------------------------------------------------
# AI Summarization (Google Gemini)
# ---------------------------------------------------------------------------

GEMINI_PROMPT = """You are a senior analyst specializing in Iranian affairs.

Below is a batch of recent news articles about Iran gathered from multiple international
and Iranian media outlets. Your job is to produce a **Top 10 Iran News Digest**.

**Focus areas:** domestic politics, geopolitics, nuclear program/JCPOA,
economy & sanctions, military/IRGC, protests/human rights, regional proxy activity,
and international diplomacy.

**For each item provide:**
1. A clear, punchy headline (one line)
2. A 3-4 sentence explanation: what happened, key actors involved, and why it matters
3. A significance tag: 🔴 High | 🟡 Medium

Rank them from most to least significant. Use clear, neutral language.
Do NOT repeat the same event twice. Consolidate duplicate stories.

---

ARTICLES:
{articles}

---

Respond ONLY with the numbered digest (1 through 10). No preamble, no closing remarks."""


def summarize_with_gemini(articles: list[dict]) -> str:
    """Use Gemini to summarize the top 10 stories.

    Tries multiple models in order (each has its own independent quota).
    On 404 or daily-quota exhaustion moves immediately to the next model.
    On per-minute 429 retries with exponential backoff.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set")

    genai.configure(api_key=api_key)

    # Build article text (cap at 20 articles to stay within free-tier token limits)
    article_lines = []
    for i, a in enumerate(articles[:20], 1):
        pub = a["published"].strftime("%b %d, %H:%M UTC")
        article_lines.append(
            f"{i}. [{a['source']}] ({pub})\n   TITLE: {a['title']}\n   DESC: {a['description']}"
        )

    articles_text = "\n\n".join(article_lines)
    prompt = GEMINI_PROMPT.format(articles=articles_text)

    generation_config = genai.GenerationConfig(
        temperature=0.3,
        max_output_tokens=2048,
    )

    # Each model has its own independent per-minute AND daily free-tier quota.
    # On any 429 (per-minute or per-day), immediately try the next model —
    # cycling is faster than waiting for the same model's quota to reset.
    models_to_try = [
        "gemini-2.0-flash-lite",   # lightest 2.0 model — own daily quota
        "gemini-1.5-flash-8b",     # small 1.5 model — own daily quota
        "gemini-2.0-flash",        # main 2.0 model — may be exhausted
    ]
    last_exc: Exception = RuntimeError("No models attempted")

    for model_name in models_to_try:
        model = genai.GenerativeModel(model_name)
        for attempt in range(3):  # up to 3 attempts per model (for transient non-quota errors)
            try:
                print(f"  Calling {model_name} (attempt {attempt + 1})...")
                response = model.generate_content(prompt, generation_config=generation_config)
                return response.text.strip()
            except Exception as exc:
                last_exc = exc
                err_str = str(exc)
                reason = str(exc).split("\n")[0][:120]
                if "429" in err_str:
                    # Any quota error (per-minute or per-day): immediately try next model.
                    # Each model has its own separate quota, so skipping is always better
                    # than waiting — the next model's quota is unaffected.
                    quota_type = "daily" if "PerDay" in err_str else "per-minute"
                    print(f"  {model_name} {quota_type} quota exceeded — trying next model")
                    break
                elif attempt < 2:
                    # Transient non-quota error (network blip, 503, etc.) — retry with backoff
                    wait = 2 ** (attempt + 1)  # 2, 4 seconds
                    print(f"  {model_name} error, retrying in {wait}s: {reason}")
                    time.sleep(wait)
                else:
                    print(f"  {model_name} unavailable: {reason}")
                    break

    raise last_exc


# ---------------------------------------------------------------------------
# Email (Resend)
# ---------------------------------------------------------------------------

def _digest_to_html(digest: str) -> str:
    """Convert the plain-text numbered digest to styled HTML blocks."""
    blocks = []
    # Split on numbered items like "1." or "1 " at start of line
    items = re.split(r"\n(?=\d{1,2}[\.\)])", digest.strip())

    for item in items:
        item = item.strip()
        if not item:
            continue

        # Detect significance tag
        if "🔴" in item:
            border = "#c0392b"
            badge = '<span style="background:#c0392b;color:white;padding:2px 8px;border-radius:12px;font-size:12px;font-weight:bold;">HIGH</span>'
        elif "🟡" in item:
            border = "#f39c12"
            badge = '<span style="background:#f39c12;color:white;padding:2px 8px;border-radius:12px;font-size:12px;font-weight:bold;">MEDIUM</span>'
        else:
            border = "#7f8c8d"
            badge = ""

        # Bold first line (headline), rest is body
        lines = item.split("\n", 2)
        headline = lines[0].strip()
        body = lines[1].strip() if len(lines) > 1 else ""
        if len(lines) > 2:
            body += " " + lines[2].strip()

        # Clean emoji from headline for the title
        body = body.replace("🔴 High", "").replace("🟡 Medium", "").strip()
        body = re.sub(r"Significance:\s*", "", body).strip()

        blocks.append(
            f"""<div style="border-left:4px solid {border};padding:14px 18px;
                           margin-bottom:18px;background:#fafafa;border-radius:0 6px 6px 0;">
              <p style="margin:0 0 6px;font-size:16px;font-weight:700;color:#1a1a2e;">{headline} {badge}</p>
              <p style="margin:0;font-size:14px;color:#444;line-height:1.6;">{body}</p>
            </div>"""
        )

    return "\n".join(blocks)


def build_html_email(digest: str, articles: list[dict], run_time: datetime) -> str:
    """Assemble the full HTML email."""
    time_str = run_time.strftime("%A, %B %d, %Y — %H:%M UTC")
    slot = "Morning" if run_time.hour < 14 else "Evening"
    digest_html = _digest_to_html(digest)

    # Source list (first 20 unique sources with their article titles as links)
    seen_sources: set[str] = set()
    source_links = []
    for a in articles[:30]:
        if a["source"] not in seen_sources:
            seen_sources.add(a["source"])
            source_links.append(
                f'<li style="margin-bottom:4px;"><strong>{a["source"]}</strong></li>'
            )

    sources_html = "\n".join(source_links)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Iran News Digest</title>
</head>
<body style="margin:0;padding:0;background:#f0f0eb;font-family:'Georgia',serif;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center" style="padding:30px 10px;">
      <table width="680" cellpadding="0" cellspacing="0" style="max-width:680px;width:100%;">

        <!-- Header -->
        <tr><td style="background:linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%);
                        padding:36px 40px;border-radius:10px 10px 0 0;text-align:center;">
          <h1 style="margin:0;color:#e8d5a3;font-size:26px;letter-spacing:1px;">
            🇮🇷 Iran News Digest
          </h1>
          <p style="margin:8px 0 0;color:#a0a8b8;font-size:13px;">
            {slot} Edition &nbsp;·&nbsp; {time_str}
          </p>
          <p style="margin:6px 0 0;color:#7a8898;font-size:12px;">
            AI-powered summary of the top 10 Iran stories
          </p>
        </td></tr>

        <!-- Body -->
        <tr><td style="background:#ffffff;padding:32px 40px;">
          {digest_html}
        </td></tr>

        <!-- Sources -->
        <tr><td style="background:#f8f8f5;padding:24px 40px;border-top:1px solid #e8e8e0;">
          <h3 style="margin:0 0 12px;color:#1a1a2e;font-size:14px;text-transform:uppercase;
                     letter-spacing:1px;">Sources Monitored</h3>
          <ul style="margin:0;padding-left:18px;color:#666;font-size:13px;columns:2;
                     column-gap:20px;list-style:disc;">
            {sources_html}
          </ul>
        </td></tr>

        <!-- Footer -->
        <tr><td style="background:#1a1a2e;padding:20px 40px;border-radius:0 0 10px 10px;
                        text-align:center;">
          <p style="margin:0;color:#7a8898;font-size:11px;">
            Automated digest · Powered by Google Gemini 1.5 Flash · Delivered via Resend
          </p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


def send_email(html: str, run_time: datetime) -> None:
    """Send the HTML email via Resend API."""
    api_key = os.environ.get("RESEND_API_KEY")
    recipient = os.environ.get("RECIPIENT_EMAIL")
    sender = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")

    if not api_key:
        raise ValueError("RESEND_API_KEY environment variable is not set")
    if not recipient:
        raise ValueError("RECIPIENT_EMAIL environment variable is not set")

    slot = "Morning" if run_time.hour < 14 else "Evening"
    date_str = run_time.strftime("%b %d, %Y")
    subject = f"🇮🇷 Iran {slot} Digest — {date_str}"

    response = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "from": sender,
            "to": [recipient],
            "subject": subject,
            "html": html,
        },
        timeout=30,
    )

    if response.status_code in (200, 201):
        data = response.json()
        print(f"Email sent successfully. ID: {data.get('id', 'unknown')}")
    else:
        raise RuntimeError(
            f"Resend API error {response.status_code}: {response.text}"
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    run_time = datetime.now(timezone.utc)
    print(f"=== Iran News Digest — {run_time.strftime('%Y-%m-%d %H:%M UTC')} ===\n")

    # 1. Fetch articles
    print("Step 1/3 — Fetching articles from RSS feeds...")
    articles = fetch_articles()

    if len(articles) < 5:
        print(
            f"Only {len(articles)} articles found (need at least 5). Aborting.",
            file=sys.stderr,
        )
        sys.exit(1)

    # 2. Summarize
    print("\nStep 2/3 — Generating AI digest with Gemini...")
    digest = summarize_with_gemini(articles)
    print("\n--- Digest preview (first 500 chars) ---")
    print(digest[:500])
    print("...")

    # 3. Send email
    print("\nStep 3/3 — Sending email via Resend...")
    html = build_html_email(digest, articles, run_time)
    send_email(html, run_time)

    print("\n=== Done ===")


if __name__ == "__main__":
    main()
