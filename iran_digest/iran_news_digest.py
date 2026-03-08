#!/usr/bin/env python3
"""
Iran News Digest
Fetches Iran-related news from English-language Iranian RSS feeds (categorised as
pro-regime or anti-regime), deduplicates cross-source stories, summarises via
Groq, and sends an HTML email via Resend.
"""

import os
import sys
import re
import time
import requests
import feedparser
from groq import Groq
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime


# ---------------------------------------------------------------------------
# News Sources
# ---------------------------------------------------------------------------

RSS_FEEDS = [
    # ── PRO-REGIME: State-controlled / IRGC-linked ─────────────────────────
    {
        "name": "IRNA",
        "url": "https://en.irna.ir/rss",
        "iran_only": False,
        "bias": "pro-regime",
        "description": "Islamic Republic News Agency (official state wire)",
    },
    {
        "name": "Press TV",
        "url": "https://www.presstv.ir/rss.xml",
        "iran_only": False,
        "bias": "pro-regime",
        "description": "IRIB-owned English-language state broadcaster",
    },
    {
        "name": "Tasnim News",
        "url": "https://www.tasnimnews.com/en/rss",
        "iran_only": False,
        "bias": "pro-regime",
        "description": "IRGC-linked news agency",
    },
    {
        "name": "Mehr News",
        "url": "https://en.mehrnews.com/rss",
        "iran_only": False,
        "bias": "pro-regime",
        "description": "Government-sponsored (Islamic Development Org.)",
    },
    {
        "name": "Tehran Times",
        "url": "https://www.tehrantimes.com/rss",
        "iran_only": False,
        "bias": "pro-regime",
        "description": "State-controlled English-language daily",
    },
    {
        "name": "Kayhan International",
        "url": "https://kayhan.ir/en/rss/allnews",
        "iran_only": False,
        "bias": "pro-regime",
        "description": "Hardline daily; publisher appointed by Supreme Leader",
    },
    {
        "name": "Iran Daily",
        "url": "https://irandaily.ir/News/Feed2",
        "iran_only": False,
        "bias": "pro-regime",
        "description": "Government-controlled English daily",
    },
    {
        "name": "ISNA",
        "url": "https://en.isna.ir/rss",
        "iran_only": False,
        "bias": "pro-regime",
        "description": "Iranian Students' News Agency (state-affiliated)",
    },
    # ── ANTI-REGIME: Opposition / Exile / Independent ───────────────────────
    {
        "name": "Iran International",
        "url": "https://www.iranintl.com/en/rss",
        "iran_only": False,
        "bias": "anti-regime",
        "description": "London-based opposition satellite channel",
    },
    {
        "name": "Radio Farda",
        "url": "https://www.radiofarda.com/api/zmpbjqimiv",
        "iran_only": False,
        "bias": "anti-regime",
        "description": "RFE/RL Persian Service (US-funded independent journalism)",
    },
    {
        "name": "IranWire",
        "url": "https://iranwire.com/en/feed/",
        "iran_only": False,
        "bias": "anti-regime",
        "description": "Investigative platform combining diaspora & citizen journalists",
    },
    {
        "name": "Zamaneh Media",
        "url": "https://en.radiozamaneh.com/feed",
        "iran_only": False,
        "bias": "anti-regime",
        "description": "Amsterdam-based independent exile media (human rights focus)",
    },
    {
        "name": "CHRI",
        "url": "https://iranhumanrights.org/feed/",
        "iran_only": False,
        "bias": "anti-regime",
        "description": "Center for Human Rights in Iran (independent NGO)",
    },
]

# Keywords used when iran_only=True to filter non-Iran-specific feeds
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
    combined = (title + " " + description).lower()
    return any(kw in combined for kw in IRAN_KEYWORDS)


def _parse_date(entry) -> datetime:
    for field in ("published", "updated"):
        raw = entry.get(field)
        if raw:
            try:
                return parsedate_to_datetime(raw)
            except Exception:
                pass
    return datetime.now(timezone.utc)


def fetch_articles() -> list[dict]:
    """Fetch and URL-deduplicate articles from all RSS feeds, retaining bias label."""
    articles: list[dict] = []
    seen_urls: set[str] = set()

    for feed_info in RSS_FEEDS:
        name = feed_info["name"]
        url = feed_info["url"]
        iran_only = feed_info["iran_only"]
        bias = feed_info["bias"]

        try:
            feed = feedparser.parse(url, request_headers={"User-Agent": "IranNewsDigest/1.0"})
            count = 0
            for entry in feed.entries[:20]:
                title = entry.get("title", "").strip()
                description = entry.get("summary", entry.get("description", "")).strip()
                description = re.sub(r"<[^>]+>", "", description)[:250]
                link = entry.get("link", "").strip()

                if not title or not link:
                    continue
                if link in seen_urls:
                    continue
                if iran_only and not _is_iran_related(title, description):
                    continue

                seen_urls.add(link)
                articles.append({
                    "source": name,
                    "bias": bias,
                    "title": title,
                    "description": description,
                    "url": link,
                    "published": _parse_date(entry),
                })
                count += 1

            print(f"  [{bias:12s}] {name}: {count} articles")
        except Exception as exc:
            print(f"  [ERROR] {name}: {exc}", file=sys.stderr)

    articles.sort(key=lambda a: a["published"], reverse=True)
    pro_count = sum(1 for a in articles if a["bias"] == "pro-regime")
    anti_count = sum(1 for a in articles if a["bias"] == "anti-regime")
    print(f"\nTotal unique articles: {len(articles)} "
          f"(pro-regime: {pro_count}, anti-regime: {anti_count})")
    return articles


# ---------------------------------------------------------------------------
# AI Summarization (Groq)
# ---------------------------------------------------------------------------

GROQ_MODEL = "llama-3.3-70b-versatile"

GEMINI_PROMPT = """You are a senior analyst specializing in Iranian affairs.

Below are recent news articles from two sets of sources:
  [PRO-REGIME] — Iranian state media and IRGC-linked outlets
  [ANTI-REGIME] — Opposition, exile, and independent media

Your task: produce a **Top 10 Iran News Digest** that surfaces the most important stories.

## Rules
1. **Deduplicate**: If multiple sources (from the same or different camps) report the same event,
   merge them into ONE story item. List ALL source names that covered it under "Sources:".
2. **Dual perspectives**: If both camps covered the same event, briefly note how each side
   framed it (1 sentence each) under "Pro-regime angle:" and "Anti-regime angle:".
   If only one camp covered a story, omit the other angle line entirely.
3. **Rank** from most to least significant (domestic politics, nuclear/JCPOA, geopolitics,
   economy & sanctions, military/IRGC, protests/human rights, regional proxies, diplomacy).
4. **Significance tag**: 🔴 High | 🟡 Medium (one per story, on the headline line).
5. Keep each summary to 3-4 sentences max.
6. Respond ONLY with the numbered list (1-10). No preamble or closing remarks.

## Required output format (repeat exactly for each story):

N. 🔴 [HEADLINE]
Summary: [3-4 sentences on what happened, key actors, why it matters]
Pro-regime angle: [How pro-regime sources framed it — omit line if not covered by them]
Anti-regime angle: [How anti-regime sources framed it — omit line if not covered by them]
Sources: [Comma-separated list of all outlet names that reported this]

---

## ARTICLES

{articles}"""


def summarize_with_groq(articles: list[dict]) -> str:
    """Call Groq with the dual-perspective prompt."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable is not set")

    client = Groq(api_key=api_key)

    # Build article text — cap at 30 articles, label each with bias
    article_lines = []
    for i, a in enumerate(articles[:30], 1):
        pub = a["published"].strftime("%b %d, %H:%M UTC")
        bias_tag = "[PRO-REGIME]" if a["bias"] == "pro-regime" else "[ANTI-REGIME]"
        article_lines.append(
            f"{i}. {bias_tag} {a['source']} ({pub})\n"
            f"   TITLE: {a['title']}\n"
            f"   DESC:  {a['description']}"
        )

    articles_text = "\n\n".join(article_lines)
    prompt = GEMINI_PROMPT.format(articles=articles_text)

    last_exc: Exception = RuntimeError("No models attempted")
    for attempt in range(3):
        try:
            print(f"  Calling {GROQ_MODEL} (attempt {attempt + 1})...")
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=2048,
            )
            return response.choices[0].message.content.strip()
        except Exception as exc:
            last_exc = exc
            reason = str(exc).split("\n")[0][:120]
            if attempt < 2:
                wait = 2 ** (attempt + 1)
                print(f"  Error, retrying in {wait}s: {reason}")
                time.sleep(wait)
            else:
                print(f"  Failed: {reason}")

    raise last_exc


# ---------------------------------------------------------------------------
# Email rendering
# ---------------------------------------------------------------------------

def _parse_digest(digest: str) -> list[dict]:
    """
    Parse Gemini output into a list of story dicts:
      headline, significance, summary, pro_angle, anti_angle, sources
    """
    stories = []
    blocks = re.split(r"\n(?=\d{1,2}[\.\)])", digest.strip())

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        story: dict = {
            "headline": "",
            "significance": "medium",
            "summary": "",
            "pro_angle": "",
            "anti_angle": "",
            "sources": [],
        }

        lines = block.split("\n")

        # First line: "N. 🔴 HEADLINE"
        first = lines[0].strip()
        if "🔴" in first:
            story["significance"] = "high"
            first = first.replace("🔴", "").strip()
        elif "🟡" in first:
            story["significance"] = "medium"
            first = first.replace("🟡", "").strip()
        first = re.sub(r"^\d{1,2}[\.\)]\s*", "", first).strip()
        story["headline"] = first

        for line in lines[1:]:
            line = line.strip()
            low = line.lower()
            if low.startswith("summary:"):
                story["summary"] = line[len("summary:"):].strip()
            elif low.startswith("pro-regime angle:"):
                story["pro_angle"] = line[len("pro-regime angle:"):].strip()
            elif low.startswith("anti-regime angle:"):
                story["anti_angle"] = line[len("anti-regime angle:"):].strip()
            elif low.startswith("sources:"):
                raw = line[len("sources:"):].strip()
                story["sources"] = [s.strip() for s in raw.split(",") if s.strip()]
            elif story["summary"] and not re.match(
                r"^(pro-regime|anti-regime|sources)", low
            ):
                story["summary"] += " " + line

        if story["headline"]:
            stories.append(story)

    return stories


def _story_to_html(story: dict) -> str:
    sig = story["significance"]
    if sig == "high":
        border = "#c0392b"
        badge = ('<span style="background:#c0392b;color:#fff;padding:2px 9px;'
                 'border-radius:12px;font-size:11px;font-weight:bold;'
                 'letter-spacing:.5px;">HIGH</span>')
    else:
        border = "#e67e22"
        badge = ('<span style="background:#e67e22;color:#fff;padding:2px 9px;'
                 'border-radius:12px;font-size:11px;font-weight:bold;'
                 'letter-spacing:.5px;">MEDIUM</span>')

    pro = (f'<p style="margin:8px 0 0;font-size:13px;color:#555;line-height:1.55;">'
           f'<strong style="color:#8b0000;">🔵 Pro-regime:</strong> {story["pro_angle"]}</p>'
           if story["pro_angle"] else "")

    anti = (f'<p style="margin:6px 0 0;font-size:13px;color:#555;line-height:1.55;">'
            f'<strong style="color:#1a5276;">🟢 Anti-regime:</strong> {story["anti_angle"]}</p>'
            if story["anti_angle"] else "")

    sources_txt = ""
    if story["sources"]:
        src_list = ", ".join(f"<em>{s}</em>" for s in story["sources"])
        sources_txt = (f'<p style="margin:8px 0 0;font-size:11px;color:#888;">'
                       f'Sources: {src_list}</p>')

    dual_bar = ""
    if story["pro_angle"] and story["anti_angle"]:
        dual_bar = ('<p style="margin:8px 0 0;font-size:11px;color:#6c3483;font-weight:bold;">'
                    '⚡ Covered by both sides</p>')

    return f"""<div style="border-left:4px solid {border};padding:14px 18px;
                           margin-bottom:18px;background:#fafafa;border-radius:0 6px 6px 0;">
  <p style="margin:0 0 6px;font-size:16px;font-weight:700;color:#1a1a2e;">
    {story['headline']} &nbsp;{badge}
  </p>
  <p style="margin:0;font-size:14px;color:#444;line-height:1.6;">{story['summary']}</p>
  {dual_bar}
  {pro}
  {anti}
  {sources_txt}
</div>"""


def _build_source_table() -> str:
    pro_sources = [f for f in RSS_FEEDS if f["bias"] == "pro-regime"]
    anti_sources = [f for f in RSS_FEEDS if f["bias"] == "anti-regime"]

    def rows(sources):
        return "".join(
            f'<tr><td style="padding:3px 8px 3px 0;font-size:12px;color:#444;'
            f'font-weight:bold;white-space:nowrap;">{s["name"]}</td>'
            f'<td style="padding:3px 0;font-size:12px;color:#666;">{s["description"]}</td></tr>'
            for s in sources
        )

    return f"""<table width="100%" cellpadding="0" cellspacing="0">
  <tr>
    <td width="48%" valign="top">
      <p style="margin:0 0 8px;font-size:12px;font-weight:bold;color:#8b0000;
                text-transform:uppercase;letter-spacing:.5px;">🔵 Pro-Regime</p>
      <table cellpadding="0" cellspacing="0">{rows(pro_sources)}</table>
    </td>
    <td width="4%"></td>
    <td width="48%" valign="top">
      <p style="margin:0 0 8px;font-size:12px;font-weight:bold;color:#1a5276;
                text-transform:uppercase;letter-spacing:.5px;">🟢 Anti-Regime</p>
      <table cellpadding="0" cellspacing="0">{rows(anti_sources)}</table>
    </td>
  </tr>
</table>"""


def build_html_email(digest: str, run_time: datetime) -> str:
    time_str = run_time.strftime("%A, %B %d, %Y — %H:%M UTC")
    slot = "Morning" if run_time.hour < 14 else "Evening"

    stories = _parse_digest(digest)
    stories_html = "\n".join(_story_to_html(s) for s in stories) if stories else (
        f'<pre style="font-size:13px;color:#444;">{digest}</pre>'
    )

    sources_table = _build_source_table()

    dual_count = sum(1 for s in stories if s["pro_angle"] and s["anti_angle"])
    stats = (f"{len(stories)} stories"
             + (f" &nbsp;·&nbsp; {dual_count} cross-perspective" if dual_count else ""))

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
            {stats} &nbsp;·&nbsp; Deduped &amp; cross-referenced from pro- and anti-regime sources
          </p>
        </td></tr>

        <!-- Legend -->
        <tr><td style="background:#f8f4ee;padding:12px 40px;border-bottom:1px solid #e8e0d0;">
          <p style="margin:0;font-size:12px;color:#666;text-align:center;">
            <strong style="color:#8b0000;">🔵 Pro-regime angle</strong>
            &nbsp;|&nbsp;
            <strong style="color:#1a5276;">🟢 Anti-regime angle</strong>
            &nbsp;|&nbsp;
            <strong style="color:#6c3483;">⚡ Both sides reported this story</strong>
          </p>
        </td></tr>

        <!-- Stories -->
        <tr><td style="background:#ffffff;padding:32px 40px;">
          {stories_html}
        </td></tr>

        <!-- Sources monitored -->
        <tr><td style="background:#f8f8f5;padding:24px 40px;border-top:1px solid #e8e8e0;">
          <h3 style="margin:0 0 14px;color:#1a1a2e;font-size:13px;text-transform:uppercase;
                     letter-spacing:1px;">Sources Monitored</h3>
          {sources_table}
        </td></tr>

        <!-- Footer -->
        <tr><td style="background:#1a1a2e;padding:20px 40px;border-radius:0 0 10px 10px;
                        text-align:center;">
          <p style="margin:0;color:#7a8898;font-size:11px;">
            Automated digest &nbsp;·&nbsp; Powered by Groq &nbsp;·&nbsp;
            Delivered via Resend
          </p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Email sending (Resend)
# ---------------------------------------------------------------------------

def send_email(html: str, run_time: datetime) -> None:
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
        raise RuntimeError(f"Resend API error {response.status_code}: {response.text}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    run_time = datetime.now(timezone.utc)
    print(f"=== Iran News Digest — {run_time.strftime('%Y-%m-%d %H:%M UTC')} ===\n")

    print("Step 1/3 — Fetching articles from RSS feeds...")
    articles = fetch_articles()

    if len(articles) < 5:
        print(f"Only {len(articles)} articles found (need >= 5). Aborting.", file=sys.stderr)
        sys.exit(1)

    print("\nStep 2/3 — Generating AI digest with Groq...")
    digest = summarize_with_groq(articles)
    print("\n--- Digest preview (first 600 chars) ---")
    print(digest[:600])
    print("...\n")

    print("Step 3/3 — Sending email via Resend...")
    html = build_html_email(digest, run_time)
    send_email(html, run_time)

    print("\n=== Done ===")


if __name__ == "__main__":
    main()
