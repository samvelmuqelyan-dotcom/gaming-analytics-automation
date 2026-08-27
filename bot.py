import os
import psycopg2
import ollama
from datetime import date, timedelta
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD")
}
MODEL_NAME = os.getenv("OLLAMA_MODEL", "llama3.2")


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def get_latest_date(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT MAX(DATE(timestamp)) FROM bets;")
        return cur.fetchone()[0]


def get_daily_metrics(conn, target_date):
    query = """
        SELECT
            COUNT(DISTINCT b.player_id) AS active_players,
            COALESCE(SUM(b.bet_amount), 0) AS total_bets,
            COALESCE(SUM(b.win_amount), 0) AS total_wins,
            COALESCE(SUM(b.bet_amount) - SUM(b.win_amount), 0) AS ggr
        FROM bets b
        WHERE DATE(b.timestamp) = %s;
    """
    with conn.cursor() as cur:
        cur.execute(query, (target_date,))
        row = cur.fetchone()

    active_players, total_bets, total_wins, ggr = row
    rtp = (float(total_wins) / float(total_bets) * 100) if total_bets else 0

    return {
        "active_players": active_players,
        "total_bets": float(total_bets),
        "total_wins": float(total_wins),
        "ggr": float(ggr),
        "rtp": rtp
    }


def get_deposits_for_date(conn, target_date):
    query = "SELECT COALESCE(SUM(amount), 0), COUNT(*) FROM deposits WHERE deposit_date = %s;"
    with conn.cursor() as cur:
        cur.execute(query, (target_date,))
        total, count = cur.fetchone()
    return float(total), count


def calculate_change(current, previous):
    if previous == 0:
        return None
    return (current - previous) / previous * 100


def format_change(change):
    if change is None:
        return ""
    sign = "+" if change >= 0 else ""
    return f" ({sign}{change:.1f}%)"


def build_daily_report(conn, target_date=None):
    latest_date = target_date if target_date else get_latest_date(conn)
    previous_date = latest_date - timedelta(days=1)

    today = get_daily_metrics(conn, latest_date)
    yesterday = get_daily_metrics(conn, previous_date)

    today_deposits, today_deposit_count = get_deposits_for_date(conn, latest_date)
    yesterday_deposits, _ = get_deposits_for_date(conn, previous_date)

    ggr_change = calculate_change(today["ggr"], yesterday["ggr"])
    rtp_change = calculate_change(today["rtp"], yesterday["rtp"])
    players_change = calculate_change(today["active_players"], yesterday["active_players"])
    deposits_change = calculate_change(today_deposits, yesterday_deposits)

    lines = [
        "🎰 Daily Casino Report",
        "─" * 28,
        f"Date: {latest_date}",
        "",
        f"Active players: {today['active_players']}{format_change(players_change)}",
        f"Deposits: ${today_deposits:,.2f} ({today_deposit_count} deposits){format_change(deposits_change)}",
        "",
        f"Total bets: ${today['total_bets']:,.2f}",
        f"Total wins: ${today['total_wins']:,.2f}",
        f"GGR: ${today['ggr']:,.2f}{format_change(ggr_change)}",
        f"RTP: {today['rtp']:.2f}%{format_change(rtp_change)}",
    ]

    return "\n".join(lines)


def get_top_games(conn, limit=5):
    query = """
        SELECT
            game,
            ROUND(SUM(bet_amount) - SUM(win_amount), 2) AS ggr,
            ROUND(SUM(win_amount) / SUM(bet_amount) * 100, 2) AS rtp
        FROM bets
        GROUP BY game
        ORDER BY ggr DESC
        LIMIT %s;
    """
    with conn.cursor() as cur:
        cur.execute(query, (limit,))
        return cur.fetchall()


def get_top_countries(conn, limit=5):
    query = """
        SELECT
            p.country,
            ROUND(SUM(b.bet_amount) - SUM(b.win_amount), 2) AS ggr,
            ROUND(SUM(b.win_amount) / SUM(b.bet_amount) * 100, 2) AS rtp
        FROM bets b
        JOIN players p ON b.player_id = p.player_id
        GROUP BY p.country
        ORDER BY ggr DESC
        LIMIT %s;
    """
    with conn.cursor() as cur:
        cur.execute(query, (limit,))
        return cur.fetchall()


def get_player_info(conn, player_id):
    query = """
        SELECT
            p.player_id,
            p.country,
            p.age_group,
            p.player_type,
            p.registration_date,
            COALESCE(SUM(DISTINCT d.amount), 0),
            (SELECT COUNT(*) FROM deposits WHERE player_id = p.player_id) AS deposit_count,
            (SELECT COALESCE(SUM(bet_amount), 0) FROM bets WHERE player_id = p.player_id) AS total_bets,
            (SELECT COALESCE(SUM(win_amount), 0) FROM bets WHERE player_id = p.player_id) AS total_wins
        FROM players p
        LEFT JOIN deposits d ON d.player_id = p.player_id
        WHERE p.player_id = %s
        GROUP BY p.player_id;
    """
    with conn.cursor() as cur:
        cur.execute(query, (player_id,))
        return cur.fetchone()


def get_top_games_for_date(conn, target_date, limit=3):
    query = """
        SELECT
            game,
            ROUND(SUM(bet_amount) - SUM(win_amount), 2) AS ggr,
            ROUND(SUM(win_amount) / SUM(bet_amount) * 100, 2) AS rtp
        FROM bets
        WHERE DATE(timestamp) = %s
        GROUP BY game
        ORDER BY ggr DESC
        LIMIT %s;
    """
    with conn.cursor() as cur:
        cur.execute(query, (target_date, limit))
        return cur.fetchall()


def get_top_countries_for_date(conn, target_date, limit=3):
    query = """
        SELECT
            p.country,
            ROUND(SUM(b.bet_amount) - SUM(b.win_amount), 2) AS ggr,
            ROUND(SUM(b.win_amount) / SUM(b.bet_amount) * 100, 2) AS rtp
        FROM bets b
        JOIN players p ON b.player_id = p.player_id
        WHERE DATE(b.timestamp) = %s
        GROUP BY p.country
        ORDER BY ggr DESC
        LIMIT %s;
    """
    with conn.cursor() as cur:
        cur.execute(query, (target_date, limit))
        return cur.fetchall()


def find_biggest_anomaly(top_games, top_countries):
    candidates = []

    for game, ggr, rtp in top_games:
        candidates.append(("game", game, float(ggr), float(rtp)))

    for country, ggr, rtp in top_countries:
        candidates.append(("country", country, float(ggr), float(rtp)))

    if not candidates:
        return None

    return max(candidates, key=lambda c: abs(c[3] - 100))


def generate_ai_insight(anomaly):
    if not anomaly:
        return "Not enough data to detect anomalies today."

    kind, name, ggr, rtp = anomaly
    label = "game" if kind == "game" else "country"

    prompt = f"""Rewrite the following fact as one clear, professional business sentence. Do not add any information, do not calculate anything, do not expand or explain abbreviations, use only these exact numbers and keep "RTP" and "GGR" exactly as written:

    Fact: RTP (a casino industry metric) for {label} "{name}" was {rtp:.2f}%, the largest deviation from the 100% baseline among today's metrics. GGR for this {label} was ${ggr:,.2f}.

    Respond with exactly one sentence in English. Do not spell out what RTP or GGR stand for."""

    response = ollama.generate(model=MODEL_NAME, prompt=prompt)
    return response["response"].strip()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎰 Casino Analytics Bot\n\n"
        "Доступные команды:\n"
        "/report — отчёт за последний день\n"
        "/top_games — топ-5 игр по GGR\n"
        "/top_countries — топ-5 стран по GGR\n"
        "/player <id> — карточка игрока\n"
        "/check_alerts — проверка аномалий за последний день\n"
        "/insight — AI-анализ главной аномалии дня"
    )


async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_connection()
    try:
        text = build_daily_report(conn)
    finally:
        conn.close()

    await update.message.reply_text(text)


async def top_games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_connection()
    try:
        rows = get_top_games(conn)
    finally:
        conn.close()

    lines = ["🎮 Top 5 Games by GGR", "─" * 28]
    for i, (game, ggr, rtp) in enumerate(rows, start=1):
        lines.append(f"{i}. {game} — GGR: ${ggr:,.2f}, RTP: {rtp}%")

    await update.message.reply_text("\n".join(lines))


def check_high_rtp_games(conn, target_date, threshold=105.0):
    query = """
        SELECT
            game,
            ROUND(SUM(win_amount) / SUM(bet_amount) * 100, 2) AS rtp
        FROM bets
        WHERE DATE(timestamp) = %s
        GROUP BY game
        HAVING SUM(win_amount) / SUM(bet_amount) * 100 > %s;
    """
    with conn.cursor() as cur:
        cur.execute(query, (target_date, threshold))
        return cur.fetchall()


def get_country_ggr_for_date(conn, target_date):
    query = """
        SELECT
            p.country,
            SUM(b.bet_amount) - SUM(b.win_amount) AS ggr
        FROM bets b
        JOIN players p ON b.player_id = p.player_id
        WHERE DATE(b.timestamp) = %s
        GROUP BY p.country;
    """
    with conn.cursor() as cur:
        cur.execute(query, (target_date,))
        return dict(cur.fetchall())


def check_ggr_drops(conn, target_date, drop_threshold=20.0):
    previous_date = target_date - timedelta(days=1)

    today_ggr = get_country_ggr_for_date(conn, target_date)
    yesterday_ggr = get_country_ggr_for_date(conn, previous_date)

    drops = []

    for country, yesterday_value in yesterday_ggr.items():
        if yesterday_value is None or yesterday_value <= 0:
            continue

        yesterday_value = float(yesterday_value)
        today_value = float(today_ggr.get(country, 0) or 0)

        sign_changed = (yesterday_value > 0) and (today_value < 0)

        if sign_changed:
            drops.append((country, None, today_value, yesterday_value))
            continue

        change = (today_value - yesterday_value) / yesterday_value * 100

        if change <= -drop_threshold:
            drops.append((country, change, today_value, yesterday_value))

    return drops


async def check_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_connection()
    try:
        target_date = get_latest_date(conn)

        high_rtp_games = check_high_rtp_games(conn, target_date)
        ggr_drops = check_ggr_drops(conn, target_date)
    finally:
        conn.close()

    lines = [f"🔍 Alert Check — {target_date}", "─" * 28]

    if not high_rtp_games and not ggr_drops:
        lines.append("✅ No anomalies detected.")
    else:
        if high_rtp_games:
            lines.append("⚠️ High RTP games (possible big win day):")
            for game, rtp in high_rtp_games:
                lines.append(f"  • {game}: RTP {rtp}%")
            lines.append("")

        if ggr_drops:
            lines.append("⚠️ GGR drops by country:")
            for country, change, today_value, yesterday_value in ggr_drops:
                if change is None:
                    lines.append(f"  • {country}: turned negative (${yesterday_value:,.2f} → ${today_value:,.2f})")
                else:
                    lines.append(f"  • {country}: {change:.1f}% (${yesterday_value:,.2f} → ${today_value:,.2f})")

    await update.message.reply_text("\n".join(lines))


async def top_countries(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_connection()
    try:
        rows = get_top_countries(conn)
    finally:
        conn.close()

    lines = ["🌍 Top 5 Countries by GGR", "─" * 28]
    for i, (country, ggr, rtp) in enumerate(rows, start=1):
        lines.append(f"{i}. {country} — GGR: ${ggr:,.2f}, RTP: {rtp}%")

    await update.message.reply_text("\n".join(lines))


async def player(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Использование: /player <id>\nНапример: /player 1")
        return

    try:
        player_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("player_id должен быть числом.")
        return

    conn = get_connection()
    try:
        row = get_player_info(conn, player_id)
    finally:
        conn.close()

    if row is None:
        await update.message.reply_text(f"Игрок {player_id} не найден.")
        return

    (pid, country, age_group, player_type, reg_date,
     _unused, deposit_count, total_bets, total_wins) = row

    ggr = total_bets - total_wins

    lines = [
        f"👤 Player {pid}",
        "─" * 28,
        f"Country: {country}",
        f"Age group: {age_group}",
        f"Type: {player_type}",
        f"Registered: {reg_date}",
        "",
        f"Deposits made: {deposit_count}",
        f"Total bets: ${total_bets:,.2f}",
        f"Total wins: ${total_wins:,.2f}",
        f"GGR contribution: ${ggr:,.2f}",
    ]

    await update.message.reply_text("\n".join(lines))


async def insight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Analyzing today's data, please wait...")

    conn = get_connection()
    try:
        target_date = get_latest_date(conn)
        top_games = get_top_games_for_date(conn, target_date)
        top_countries = get_top_countries_for_date(conn, target_date)
        anomaly = find_biggest_anomaly(top_games, top_countries)
    finally:
        conn.close()

    ai_text = generate_ai_insight(anomaly)

    lines = [
        f"🤖 AI Insight — {target_date}",
        "─" * 28,
        ai_text
    ]

    await update.message.reply_text("\n".join(lines))


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("report", report))
    app.add_handler(CommandHandler("top_games", top_games))
    app.add_handler(CommandHandler("top_countries", top_countries))
    app.add_handler(CommandHandler("player", player))
    app.add_handler(CommandHandler("check_alerts", check_alerts))
    app.add_handler(CommandHandler("insight", insight))
    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()