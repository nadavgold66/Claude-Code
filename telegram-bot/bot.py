#!/usr/bin/env python3
"""Israeli News Aggregator – Telegram Notification Bot.

Commands
--------
/start          – Welcome message and usage info.
/news [source]  – Fetch the latest headlines (optionally filtered by source).
/sources        – List available news sources.
/subscribe      – Subscribe to periodic news notifications.
/unsubscribe    – Unsubscribe from notifications.
/help           – Show help text.
"""

import html
import logging
import sys

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

import config
import news_client
import store

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Helpers ──────────────────────────────────────────────────────────────────

# Track article URLs already sent per chat so we don't repeat them.
_sent_urls: dict[int, set[str]] = {}


def _format_article(article: dict) -> str:
    title = html.escape(article.get("title", "No title"))
    source = html.escape(article.get("source", "Unknown"))
    category = article.get("category") or ""
    url = article.get("url", "")
    tag = f" [{html.escape(category)}]" if category else ""
    return f"• <b>{title}</b>\n  <i>{source}{tag}</i>\n  {url}"


def _format_articles(articles: list[dict], limit: int) -> str:
    if not articles:
        return "No articles found."
    lines = [_format_article(a) for a in articles[:limit]]
    return "\n\n".join(lines)


# ── Command handlers ────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "Welcome to the <b>Israeli News Bot</b>!\n\n"
        "I aggregate headlines from major Israeli news sources and can "
        "send you periodic updates.\n\n"
        "<b>Commands:</b>\n"
        "/news – Latest headlines\n"
        "/news <i>source</i> – Headlines from a specific source\n"
        "/sources – List available sources\n"
        "/subscribe – Get periodic news notifications\n"
        "/unsubscribe – Stop notifications\n"
        "/help – Show this message"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await cmd_start(update, context)


async def cmd_news(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    source_filter = " ".join(context.args) if context.args else None
    try:
        data = await news_client.fetch_news(source=source_filter)
    except Exception as exc:
        logger.error("Failed to fetch news: %s", exc)
        await update.message.reply_text(
            "Could not reach the news service. Is the aggregator running?"
        )
        return

    articles = data.get("articles", [])
    header = f"Latest news from <b>{html.escape(source_filter)}</b>:" if source_filter else "Latest headlines:"
    body = _format_articles(articles, config.MAX_ARTICLES_PER_MESSAGE)
    await update.message.reply_text(
        f"{header}\n\n{body}", parse_mode="HTML", disable_web_page_preview=True
    )


async def cmd_sources(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        sources = await news_client.fetch_sources()
    except Exception as exc:
        logger.error("Failed to fetch sources: %s", exc)
        await update.message.reply_text("Could not reach the news service.")
        return

    lines = [
        f"• <b>{html.escape(s['name'])}</b> ({html.escape(s.get('nameHe', ''))}) – {s.get('feedCount', '?')} feeds"
        for s in sources
    ]
    await update.message.reply_text(
        "<b>Available sources:</b>\n\n" + "\n".join(lines),
        parse_mode="HTML",
    )


async def cmd_subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    source_filter = " ".join(context.args) if context.args else None
    is_new = store.add_subscriber(chat_id, source_filter)
    if is_new:
        msg = "Subscribed! You'll receive news updates every "
        msg += f"{config.POLL_INTERVAL_SECONDS // 60} minutes."
        if source_filter:
            msg += f"\nFiltered to source: <b>{html.escape(source_filter)}</b>"
    else:
        msg = "Subscription updated."
        if source_filter:
            msg += f"\nNow filtering to: <b>{html.escape(source_filter)}</b>"
        else:
            msg += " Receiving all sources."
    await update.message.reply_text(msg, parse_mode="HTML")


async def cmd_unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    removed = store.remove_subscriber(chat_id)
    if removed:
        _sent_urls.pop(chat_id, None)
        await update.message.reply_text("Unsubscribed. You won't receive further updates.")
    else:
        await update.message.reply_text("You weren't subscribed.")


# ── Scheduled notification job ──────────────────────────────────────────────

async def _notify_subscribers(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Periodic job: fetch fresh news and send new articles to subscribers."""
    subscribers = store.get_all_subscribers()
    if not subscribers:
        return

    try:
        all_data = await news_client.fetch_news()
    except Exception as exc:
        logger.error("Scheduled fetch failed: %s", exc)
        return

    all_articles = all_data.get("articles", [])

    for chat_id, prefs in subscribers.items():
        source_filter = prefs.get("source_filter")
        articles = all_articles
        if source_filter:
            articles = [
                a for a in articles
                if a.get("source", "").lower() == source_filter.lower()
            ]

        # Only send articles not yet sent to this chat
        seen = _sent_urls.setdefault(chat_id, set())
        new_articles = [a for a in articles if a.get("url") not in seen]

        if not new_articles:
            continue

        # Cap to avoid flooding
        to_send = new_articles[: config.MAX_ARTICLES_PER_MESSAGE]
        body = _format_articles(to_send, config.MAX_ARTICLES_PER_MESSAGE)
        count = len(to_send)
        text = f"<b>{count} new headline{'s' if count != 1 else ''}:</b>\n\n{body}"

        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
            for a in to_send:
                seen.add(a.get("url"))
        except Exception as exc:
            logger.warning("Could not send to %s: %s", chat_id, exc)

    # Prevent unbounded memory growth – keep only the most recent 500 URLs per chat
    for chat_id, seen in _sent_urls.items():
        if len(seen) > 500:
            _sent_urls[chat_id] = set(list(seen)[-500:])


# ── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    if not config.BOT_TOKEN:
        print("Error: Set TELEGRAM_BOT_TOKEN environment variable.")
        sys.exit(1)

    app = Application.builder().token(config.BOT_TOKEN).build()

    # Register command handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("news", cmd_news))
    app.add_handler(CommandHandler("sources", cmd_sources))
    app.add_handler(CommandHandler("subscribe", cmd_subscribe))
    app.add_handler(CommandHandler("unsubscribe", cmd_unsubscribe))

    # Schedule the notification job
    app.job_queue.run_repeating(
        _notify_subscribers,
        interval=config.POLL_INTERVAL_SECONDS,
        first=10,  # first run 10 s after startup
    )

    logger.info(
        "Bot starting – polling every %d s",
        config.POLL_INTERVAL_SECONDS,
    )
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    import asyncio
    # Python 3.14+ removed auto-creation of event loops;
    # ensure one exists before python-telegram-bot tries to use it.
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    main()
