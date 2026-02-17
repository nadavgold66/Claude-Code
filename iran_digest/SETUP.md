# Iran News Digest — Setup Guide

Twice-daily email digest of the top 10 Iran news stories, powered by
Google Gemini AI and delivered via Resend. Runs automatically on GitHub Actions — **$0/month**.

---

## How It Works

```
GitHub Actions (cron)
       │
       ▼
  Fetch RSS feeds (12 sources)
  Filter Iran-related articles
       │
       ▼
  Google Gemini 1.5 Flash
  → Top 10 ranked & summarized
       │
       ▼
  Resend API → HTML email to you
```

**Schedule:** 07:00 UTC (morning) and 16:00 UTC (evening) every day.

---

## Step 1 — Get a Gemini API Key (Free)

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Click **"Create API Key"**
3. Copy the key — you will add it as a GitHub secret

**Free tier limits:** 1,500 requests/day, 1M tokens/min — more than enough.

---

## Step 2 — Get a Resend API Key (Free)

1. Sign up at [resend.com](https://resend.com)
2. Go to **API Keys** → **Create API Key**
3. Copy the key

### Sender email options

| Situation | From address | Setup needed |
|---|---|---|
| **Testing** (send only to your own email) | `onboarding@resend.dev` | None — works immediately |
| **Production** (send to anyone) | `digest@yourdomain.com` | Add DNS records to verify your domain |

For testing, leave `SENDER_EMAIL` unset — the script defaults to `onboarding@resend.dev`
which Resend allows for sending to your own verified email only.

To verify a domain: Resend dashboard → **Domains** → **Add Domain** → follow DNS instructions.

---

## Step 3 — Add GitHub Secrets

In your GitHub repository:
**Settings → Secrets and variables → Actions → New repository secret**

| Secret name | Value |
|---|---|
| `GEMINI_API_KEY` | Your Gemini API key |
| `RESEND_API_KEY` | Your Resend API key |
| `RECIPIENT_EMAIL` | Your email address |
| `SENDER_EMAIL` *(optional)* | Verified sender, e.g. `digest@yourdomain.com` |

---

## Step 4 — Push and Enable

1. Push this repository to GitHub
2. Go to **Actions** tab → **Iran News Digest**
3. Click **"Run workflow"** to test it manually before waiting for the cron

---

## Running Locally

```bash
cd iran_digest
pip install -r requirements.txt

# Set environment variables
export GEMINI_API_KEY="your-key-here"
export RESEND_API_KEY="your-key-here"
export RECIPIENT_EMAIL="you@example.com"

python iran_news_digest.py
```

---

## News Sources

| Source | Type |
|---|---|
| Google News – Iran (×3 queries) | Aggregated |
| Reuters – World News | Wire service |
| Al Jazeera | Regional |
| BBC World | International |
| Iran International | Diaspora/opposition |
| Radio Farda (RFE/RL) | US-funded |
| IRNA English | Official Iranian govt |
| Tehran Times | Pro-government Iranian |
| Mehr News Agency | Iranian state-affiliated |
| Press TV | Iranian state TV |

---

## Adjusting the Schedule

Edit `.github/workflows/iran-news-digest.yml` and change the cron expressions:

```yaml
# Example: 6 AM and 8 PM UTC
- cron: '0 6 * * *'
- cron: '0 20 * * *'
```

Use [crontab.guru](https://crontab.guru) to build cron expressions.
