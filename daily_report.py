import os
import psycopg2
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
    query = """
        SELECT COALESCE(SUM(amount), 0), COUNT(*)
        FROM deposits
        WHERE deposit_date = %s;
    """

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


def build_report(conn, target_date=None):
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


def main():
    from datetime import date

    conn = get_connection()
    try:
        report = build_report(conn, target_date=date(2020, 6, 15))
        print(report)
    finally:
        conn.close()


if __name__ == "__main__":
    main()