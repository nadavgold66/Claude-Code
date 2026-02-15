# Israeli News – Telegram Notification Bot

A Python Telegram bot that sends news notifications from the Israeli News Aggregator.

## Setup

1. **Create a Telegram bot** via [@BotFather](https://t.me/BotFather) and copy the token.

2. **Install dependencies:**

   ```bash
   cd telegram-bot
   pip install -r requirements.txt
   ```

3. **Set environment variables:**

   ```bash
   export TELEGRAM_BOT_TOKEN="your-token-here"
   export NEWS_API_URL="http://localhost:3000"   # aggregator URL
   ```

4. **Start the news aggregator** (from the project root):

   ```bash
   npm run dev
   ```

5. **Run the bot:**

   ```bash
   python bot.py
   ```

## Commands

| Command                | Description                              |
| ---------------------- | ---------------------------------------- |
| `/start`               | Welcome message and usage info           |
| `/news`                | Fetch latest headlines                   |
| `/news <source>`       | Headlines filtered by source name        |
| `/sources`             | List all available news sources          |
| `/subscribe`           | Subscribe to periodic news notifications |
| `/subscribe <source>`  | Subscribe filtered to a specific source  |
| `/unsubscribe`         | Stop receiving notifications             |
| `/help`                | Show help text                           |

## Configuration

All settings are controlled via environment variables:

| Variable                 | Default                  | Description                     |
| ------------------------ | ------------------------ | ------------------------------- |
| `TELEGRAM_BOT_TOKEN`    | *(required)*             | Bot token from BotFather        |
| `NEWS_API_URL`          | `http://localhost:3000`  | News aggregator API base URL    |
| `POLL_INTERVAL_SECONDS` | `300`                    | Notification check interval (s) |
| `MAX_ARTICLES_PER_MESSAGE` | `10`                  | Max articles per notification   |
| `SUBSCRIBERS_FILE`      | `subscribers.json`       | Path to subscriber data file    |
