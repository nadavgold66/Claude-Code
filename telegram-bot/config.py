import os

# Telegram bot token from @BotFather
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

# URL of the news aggregator API
NEWS_API_URL = os.environ.get("NEWS_API_URL", "http://localhost:3000")

# How often to check for new articles (in seconds)
POLL_INTERVAL_SECONDS = int(os.environ.get("POLL_INTERVAL_SECONDS", "300"))

# Maximum number of articles to show per /news command
MAX_ARTICLES_PER_MESSAGE = int(os.environ.get("MAX_ARTICLES_PER_MESSAGE", "10"))

# Path to store subscriber data
SUBSCRIBERS_FILE = os.environ.get("SUBSCRIBERS_FILE", "subscribers.json")
