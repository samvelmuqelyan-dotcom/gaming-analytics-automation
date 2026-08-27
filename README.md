# Casino Analytics & Automation

A self-contained analytics system for a simulated online casino: synthetic data generation, a PostgreSQL database, a daily "live" simulation engine, scheduled automation, a Telegram bot for reporting, and an AI layer for anomaly explanations.

The project was built as a learning exercise to practice the full path from raw data generation to an automated, queryable analytics product — the kind of pipeline used in real iGaming Back Office / BI systems.

## What it does

- Generates a realistic synthetic dataset: players, daily activity, sessions, deposits, bets, and withdrawals, with weighted distributions for country, age group, player behavior type, and game popularity.
- Stores everything in a normalized PostgreSQL database with foreign keys and indexes.
- Simulates a new "day" of casino activity on demand (new registrations, returning players, balance-aware betting, deposits, withdrawals, churn) so the dataset keeps growing like a real system would.
- Runs that daily simulation automatically on a schedule via Windows Task Scheduler.
- Serves reports and analytics through a Telegram bot.
- Uses a local LLM (via Ollama) to turn the day's biggest metric anomaly into a plain-language business insight.

## Architecture

```
DATA GENERATOR
      |
      v
  PLAYERS ---- GAMES
      |
      v
   ACTIVITY
      |
      v
   SESSIONS
      |
      v
DEPOSITS / BETS / WINS
      |
      v
  WITHDRAWALS
      |
      v
  POSTGRESQL DATABASE
      |
      v
   SQL ANALYTICS
      |
      +--> TELEGRAM BOT (reports, top games/countries, player lookup, alerts)
      |
      +--> AI INSIGHTS (Ollama) --> plain-language anomaly explanation
      |
DAILY SIMULATION (simulate_next_day.py)
      |
      v
WINDOWS TASK SCHEDULER (runs it automatically every day)
```

## Tech stack

- **Python** — data generation, simulation logic, bot, automation scripts
- **PostgreSQL** — relational storage with foreign keys and indexes
- **psycopg2** — Python/PostgreSQL driver
- **python-telegram-bot** — Telegram Bot API integration
- **Ollama (llama3.2)** — local LLM for generating text insights, no external API or cost
- **Windows Task Scheduler** — daily automated execution
- **python-dotenv** — environment-based secrets management

## Project structure

```
generate_players.py       Generates the initial player base
generate_activity.py      Generates which days each player was active
generate_sessions.py      Turns active days into timestamped sessions
generate_deposits.py      Generates deposits tied to sessions
generate_bets.py          Generates bets, wins, and withdrawals with running balance
generate_data.py          Runs the full generation pipeline in order
schema.sql                PostgreSQL table definitions
load_data.py              Loads generated CSVs into PostgreSQL
simulate_next_day.py      Simulates one new day on top of existing data (registrations,
                           activity, betting, deposits, withdrawals, churn)
daily_report.py           Builds a day-over-day text report from the database
ai_insights.py            Finds the day's biggest anomaly and asks a local LLM to explain it
bot.py                    Telegram bot exposing reports, top lists, player lookup,
                           anomaly alerts, and AI insights as commands
```

## Setup

**1. Clone the repository**
```
git clone https://github.com/samvelmuqelyan-dotcom/gaming-analytics-automation.git
cd gaming-analytics-automation
```

**2. Install dependencies**
```
pip install psycopg2-binary python-telegram-bot python-dotenv ollama
```

**3. Set up PostgreSQL**

Create a database and apply the schema:
```
psql -U postgres -c "CREATE DATABASE casino_analytics;"
psql -U postgres -d casino_analytics -f schema.sql
```

**4. Set up Ollama (for AI insights)**

Install Ollama from [ollama.com](https://ollama.com), then pull the model:
```
ollama pull llama3.2
```

**5. Configure environment variables**

Copy `.env.example` to `.env` and fill in your own values:
```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=casino_analytics
DB_USER=postgres
DB_PASSWORD=your_password_here

BOT_TOKEN=your_telegram_bot_token_here

OLLAMA_MODEL=llama3.2
```

Get a bot token by messaging [@BotFather](https://t.me/BotFather) on Telegram and running `/newbot`.

**6. Generate the initial dataset and load it**
```
python generate_data.py
python load_data.py
```

**7. Run the bot**
```
python bot.py
```

**8. (Optional) Automate daily simulation**

Set up Windows Task Scheduler to run `simulate_next_day.py` once a day, or run it manually whenever you want to advance the simulation by one day:
```
python simulate_next_day.py
```

## Telegram bot commands

| Command | Description |
|---|---|
| `/report` | Daily report with day-over-day change (active players, deposits, GGR, RTP) |
| `/top_games` | Top 5 games by GGR |
| `/top_countries` | Top 5 countries by GGR |
| `/player <id>` | Player profile: country, type, deposits, bets, GGR contribution |
| `/check_alerts` | Flags anomalies: unusually high RTP, sharp GGR drops by country |
| `/insight` | AI-generated one-sentence explanation of today's biggest anomaly |

## Key design decisions

- **Weighted randomness everywhere** — countries, age groups, player behavior types, and game popularity all use weighted distributions instead of uniform randomness, so aggregate metrics resemble a real casino's traffic mix.
- **Balance-aware bet generation** — bets are generated sequentially per session against a running balance, so a player can never bet more than they have, and sessions end early if the balance runs out.
- **Large wins trigger withdrawals** — a win exceeding both a relative (vs. current balance) and absolute threshold triggers a partial withdrawal, avoiding the unrealistic case of a player cashing out to zero after every good session.
- **Sessions never cross midnight** — session end times are clipped to the calendar day, so daily aggregates (`DATE(timestamp)`) always match the `activity` table exactly.
- **player_state table** — tracks each player's current balance and last activity date, letting `simulate_next_day.py` continue the simulation incrementally instead of regenerating everything from scratch.
- **Savepoint-protected inserts** — each player's daily data is inserted inside a savepoint; if one player's insert fails, it rolls back cleanly without corrupting the rest of the day's data.
- **Local AI, not a paid API** — insights are generated with a local Ollama model to keep the project fully free to run, at the cost of some inconsistency in phrasing.

## Known limitations

- `player_type` (normal / losing / winning) currently affects play frequency and deposit frequency, but not bet outcomes — RTP is driven purely by each game's configured RTP and volatility.
- Deposit-to-player conversion is fixed at roughly 57%, a deliberate calibration choice rather than a benchmarked industry figure.
- The local LLM (llama3.2) occasionally misnames metric abbreviations or produces awkward phrasing; a larger or paid model would likely improve consistency.

## Data model

```
players (player_id, registration_date, country, age_group, player_type)
activity (player_id, activity_date)
sessions (player_id, session_start, session_end)
deposits (player_id, deposit_date, amount)
bets (player_id, timestamp, game, bet_amount, win_amount, balance_after)
withdrawals (player_id, timestamp, amount, balance_after)
player_state (player_id, current_balance, last_activity_date, is_churned)
```

All tables reference `players.player_id` as a foreign key, with indexes on `player_id` across the board to keep joins fast.