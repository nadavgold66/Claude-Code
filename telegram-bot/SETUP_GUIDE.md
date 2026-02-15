# How to Run the Israeli News Telegram Bot – Step by Step

This guide assumes you're starting from zero. Follow each step in order.

---

## Step 1: Install Node.js

The news aggregator (which the bot reads from) runs on Node.js.

- Go to https://nodejs.org
- Download the **LTS** version
- Run the installer, click "Next" through everything
- To verify it worked, open a terminal and type:
  ```
  node --version
  ```
  You should see a version number like `v20.x.x`

---

## Step 2: Install Python

The Telegram bot itself runs on Python.

- Go to https://www.python.org/downloads
- Download **Python 3.10+**
- Run the installer — **check the box that says "Add Python to PATH"** before clicking Install
- To verify it worked, open a terminal and type:
  ```
  python --version
  ```
  You should see `Python 3.10.x` or higher

---

## Step 3: Clone this repository

Open a terminal and run:

```bash
git clone https://github.com/nadavgold66/Claude-Code.git
cd Claude-Code
```

---

## Step 4: Install the news aggregator dependencies

Still in the `Claude-Code` folder, run:

```bash
npm install
```

Wait for it to finish. You'll see a `node_modules` folder appear.

---

## Step 5: Start the news aggregator

```bash
npm run dev
```

You should see output like:

```
Israeli News Aggregator running at http://localhost:3000
```

**Leave this terminal window open and running.** The bot needs it.

---

## Step 6: Create a Telegram bot via BotFather

1. Open Telegram on your phone or desktop
2. Search for **@BotFather** and open a chat with it
3. Send the message: `/newbot`
4. BotFather will ask you for a **name** — type any name (e.g. `Israeli News Bot`)
5. BotFather will ask for a **username** — type a unique username ending in `bot` (e.g. `my_il_news_bot`)
6. BotFather will reply with a message containing your **token** — it looks like this:
   ```
   7123456789:AAF1k9x8bQ3r... (long string)
   ```
7. **Copy this token.** You'll need it in the next step.

---

## Step 7: Install the bot's Python dependencies

Open a **new terminal window** (keep the aggregator running in the first one).

Navigate to the bot folder. If you just opened a fresh terminal, you'll need the full path from wherever the repository was cloned:

```bash
cd Claude-Code/telegram-bot
```

If you're already inside the `Claude-Code` folder, just run:

```bash
cd telegram-bot
```

Then install the dependencies:

```bash
pip3 install -r requirements.txt
```

> **Note:** If `pip3` is not found, try `pip` instead. If neither works, reinstall Python and make sure "Add Python to PATH" is checked (see Step 2).

Wait for the installation to finish.

---

## Step 8: Set your bot token

In the same terminal, set the environment variable:

**On Mac/Linux:**
```bash
export TELEGRAM_BOT_TOKEN="paste-your-token-here"
```

**On Windows (Command Prompt):**
```cmd
set TELEGRAM_BOT_TOKEN=paste-your-token-here
```

**On Windows (PowerShell):**
```powershell
$env:TELEGRAM_BOT_TOKEN="paste-your-token-here"
```

Replace `paste-your-token-here` with the actual token from BotFather.

---

## Step 9: Run the bot

In the same terminal:

```bash
python3 bot.py
```

> **Note:** If `python3` doesn't work, try `python bot.py` instead.

You should see:

```
Bot starting – polling every 300 s
```

The bot is now live.

---

## Step 10: Talk to your bot

1. Open Telegram
2. Search for the **username** you chose in Step 6 (e.g. `@my_il_news_bot`)
3. Press **Start** or send `/start`
4. Try these commands:
   - `/news` — see the latest headlines
   - `/sources` — see all available news sources
   - `/news Ynet` — see headlines from Ynet only
   - `/subscribe` — get automatic updates every 5 minutes
   - `/unsubscribe` — stop automatic updates

---

## Quick Start (single terminal)

After completing Steps 1–4 and 6–8, you can run everything with **one command** instead of managing two terminals:

```bash
cd Claude-Code
export TELEGRAM_BOT_TOKEN="paste-your-token-here"
./start.sh
```

This starts both the aggregator and the bot together. Press **Ctrl+C** to stop everything.

---

## Summary: What should be running (manual method)

If you prefer running things separately, you need **two terminal windows** at the same time:

| Terminal | What's running | Command |
|----------|---------------|---------|
| Terminal 1 | News aggregator | `npm run dev` |
| Terminal 2 | Telegram bot | `python3 bot.py` |

If you close either one, the bot won't work properly.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `Error: Set TELEGRAM_BOT_TOKEN environment variable` | You forgot Step 8. Set the token and try again. |
| `Could not reach the news service` | The aggregator isn't running. Go back to Step 5. |
| Bot doesn't respond in Telegram | Make sure `python bot.py` is running and you're messaging the right bot username. |
| `pip: command not found` | Try `pip3` instead of `pip`, or reinstall Python with "Add to PATH" checked. |
| `npm: command not found` | Node.js isn't installed or not in PATH. Redo Step 1. |
