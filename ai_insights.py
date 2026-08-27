import os
import psycopg2
import ollama
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

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


def build_metrics_summary(conn, target_date):
    previous_date = target_date - timedelta(days=1)

    today = get_daily_metrics(conn, target_date)
    yesterday = get_daily_metrics(conn, previous_date)

    top_games = get_top_games_for_date(conn, target_date)
    top_countries = get_top_countries_for_date(conn, target_date)

    ggr_change = ((today["ggr"] - yesterday["ggr"]) / yesterday["ggr"] * 100) if yesterday["ggr"] else None
    rtp_change = today["rtp"] - yesterday["rtp"]

    lines = [
        f"Date: {target_date}",
        f"Active players: {today['active_players']} (yesterday: {yesterday['active_players']})",
        f"GGR: ${today['ggr']:,.2f} (yesterday: ${yesterday['ggr']:,.2f})",
        f"RTP: {today['rtp']:.2f}% (yesterday: {yesterday['rtp']:.2f}%, change: {rtp_change:+.2f}pp)",
    ]

    if ggr_change is not None:
        lines.append(f"GGR change vs yesterday: {ggr_change:+.1f}%")

    lines.append("\nTop games by GGR today:")
    for game, ggr, rtp in top_games:
        lines.append(f"  - {game}: GGR ${ggr:,.2f}, RTP {rtp}%")

    lines.append("\nTop countries by GGR today:")
    for country, ggr, rtp in top_countries:
        lines.append(f"  - {country}: GGR ${ggr:,.2f}, RTP {rtp}%")

    return "\n".join(lines)


def find_biggest_anomaly(top_games, top_countries):
    candidates = []

    for game, ggr, rtp in top_games:
        candidates.append(("game", game, float(ggr), float(rtp)))

    for country, ggr, rtp in top_countries:
        candidates.append(("country", country, float(ggr), float(rtp)))

    if not candidates:
        return None

    return max(candidates, key=lambda c: abs(c[3] - 100))


def generate_ai_insight(metrics_summary, anomaly):
    if not anomaly:
        return "Not enough data to detect anomalies today."

    kind, name, ggr, rtp = anomaly
    label = "game" if kind == "game" else "country"

    prompt = f"""Rewrite the following fact as one clear, professional business sentence. Do not add any information, do not calculate anything, use only these exact numbers:

Fact: RTP for {label} "{name}" was {rtp:.2f}%, the largest deviation from the 100% baseline among today's metrics. GGR for this {label} was ${ggr:,.2f}.

Respond with exactly one sentence in English."""

    response = ollama.generate(model=MODEL_NAME, prompt=prompt)
    return response["response"].strip()


def main():
    conn = get_connection()
    try:
        target_date = get_latest_date(conn)
        metrics_summary = build_metrics_summary(conn, target_date)

        print("=== Metrics Summary ===")
        print(metrics_summary)

        top_games = get_top_games_for_date(conn, target_date)
        top_countries = get_top_countries_for_date(conn, target_date)
        anomaly = find_biggest_anomaly(top_games, top_countries)

        print("\n=== AI Insight ===")
        insight = generate_ai_insight(metrics_summary, anomaly)
        print(insight)

    finally:
        conn.close()


if __name__ == "__main__":
    main()