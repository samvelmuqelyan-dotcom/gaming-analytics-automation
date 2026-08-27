import os
import csv
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD")
}

BATCH_SIZE = 5000


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def load_players(conn, path="players.csv"):
    with open(path, newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        rows = [
            (row["player_id"], row["registration_date"], row["country"], row["age_group"], row["player_type"])
            for row in reader
        ]

    with conn.cursor() as cur:
        execute_values(
            cur,
            "INSERT INTO players (player_id, registration_date, country, age_group, player_type) VALUES %s",
            rows,
            page_size=BATCH_SIZE
        )

    conn.commit()
    print(f"Loaded {len(rows)} players")


def load_activity(conn, path="activity.csv"):
    with open(path, newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        rows = [(row["player_id"], row["activity_date"]) for row in reader]

    with conn.cursor() as cur:
        execute_values(
            cur,
            "INSERT INTO activity (player_id, activity_date) VALUES %s",
            rows,
            page_size=BATCH_SIZE
        )

    conn.commit()
    print(f"Loaded {len(rows)} activity records")


def load_sessions(conn, path="sessions.csv"):
    with open(path, newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        rows = [(row["player_id"], row["session_start"], row["session_end"]) for row in reader]

    with conn.cursor() as cur:
        execute_values(
            cur,
            "INSERT INTO sessions (player_id, session_start, session_end) VALUES %s",
            rows,
            page_size=BATCH_SIZE
        )

    conn.commit()
    print(f"Loaded {len(rows)} sessions")


def load_deposits(conn, path="deposits.csv"):
    with open(path, newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        rows = [(row["player_id"], row["deposit_date"], row["amount"]) for row in reader]

    with conn.cursor() as cur:
        execute_values(
            cur,
            "INSERT INTO deposits (player_id, deposit_date, amount) VALUES %s",
            rows,
            page_size=BATCH_SIZE
        )

    conn.commit()
    print(f"Loaded {len(rows)} deposits")


def load_bets(conn, path="bets.csv"):
    with open(path, newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        rows = [
            (row["player_id"], row["timestamp"], row["game"], row["bet_amount"], row["win_amount"], row["balance_after"])
            for row in reader
        ]

    with conn.cursor() as cur:
        execute_values(
            cur,
            "INSERT INTO bets (player_id, timestamp, game, bet_amount, win_amount, balance_after) VALUES %s",
            rows,
            page_size=BATCH_SIZE
        )

    conn.commit()
    print(f"Loaded {len(rows)} bets")


def load_withdrawals(conn, path="withdrawals.csv"):
    with open(path, newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        rows = [(row["player_id"], row["timestamp"], row["amount"], row["balance_after"]) for row in reader]

    with conn.cursor() as cur:
        execute_values(
            cur,
            "INSERT INTO withdrawals (player_id, timestamp, amount, balance_after) VALUES %s",
            rows,
            page_size=BATCH_SIZE
        )

    conn.commit()
    print(f"Loaded {len(rows)} withdrawals")


def main():
    conn = get_connection()

    try:
        load_players(conn)
        load_activity(conn)
        load_sessions(conn)
        load_deposits(conn)
        load_bets(conn)
        load_withdrawals(conn)
        print("All data loaded successfully.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()