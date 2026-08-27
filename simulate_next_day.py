import random
import psycopg2
from datetime import date, datetime, timedelta
import os
import sys
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD")
}
LOCK_FILE = "simulation.lock"


COUNTRIES = ["Armenia", "Georgia", "Kazakhstan", "Ukraine", "Germany", "France"]
COUNTRY_WEIGHTS = [40, 25, 15, 10, 6, 4]

AGE_GROUPS = ["18-24", "25-34", "35-44", "45-54", "55+"]
AGE_WEIGHTS = [15, 35, 25, 15, 10]

PLAYER_TYPES = ["normal", "losing", "winning"]
PLAYER_TYPE_WEIGHTS = [90, 8, 2]

NEW_PLAYERS_MEAN = 5
NEW_PLAYERS_STD = 4
NEW_PLAYERS_MAX = 30


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def get_new_date(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT MAX(activity_date) FROM activity;")
        last_date = cur.fetchone()[0]
    return last_date + timedelta(days=1)


def get_max_player_id(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT MAX(player_id) FROM players;")
        return cur.fetchone()[0]


def random_new_players_count():
    count = int(round(random.gauss(NEW_PLAYERS_MEAN, NEW_PLAYERS_STD)))
    count = max(0, count)
    count = min(NEW_PLAYERS_MAX, count)
    return count


def register_new_players(conn, new_date, max_player_id):
    count = random_new_players_count()

    if count == 0:
        return []

    new_players = []

    with conn.cursor() as cur:
        for i in range(count):
            player_id = max_player_id + 1 + i

            country = random.choices(COUNTRIES, weights=COUNTRY_WEIGHTS)[0]
            age_group = random.choices(AGE_GROUPS, weights=AGE_WEIGHTS)[0]
            player_type = random.choices(PLAYER_TYPES, weights=PLAYER_TYPE_WEIGHTS)[0]

            cur.execute(
                "INSERT INTO players (player_id, registration_date, country, age_group, player_type) VALUES (%s, %s, %s, %s, %s);",
                (player_id, new_date, country, age_group, player_type)
            )

            cur.execute(
                "INSERT INTO player_state (player_id, current_balance, last_activity_date, is_churned) VALUES (%s, %s, %s, %s);",
                (player_id, 0, None, False)
            )

            new_players.append(player_id)

    conn.commit()
    return new_players


ACTIVITY_PROFILES = {
    "normal": {"play_probability": 0.12},
    "losing": {"play_probability": 0.06},
    "winning": {"play_probability": 0.25}
}

DORMANT_THRESHOLD_DAYS = 90
CHURN_THRESHOLD_DAYS = 365
DORMANT_PROBABILITY_MULTIPLIER = 0.1


def get_active_players(conn):
    query = """
        SELECT
            p.player_id,
            p.player_type,
            ps.current_balance,
            ps.last_activity_date
        FROM players p
        JOIN player_state ps ON ps.player_id = p.player_id
        WHERE ps.is_churned = FALSE;
    """
    with conn.cursor() as cur:
        cur.execute(query)
        return cur.fetchall()


def decide_if_plays_today(player_type, last_activity_date, new_date):
    base_probability = ACTIVITY_PROFILES[player_type]["play_probability"]

    if last_activity_date is None:
        days_since_active = 0
    else:
        days_since_active = (new_date - last_activity_date).days

    if days_since_active >= CHURN_THRESHOLD_DAYS:
        return False, True

    if days_since_active >= DORMANT_THRESHOLD_DAYS:
        probability = base_probability * DORMANT_PROBABILITY_MULTIPLIER
    else:
        probability = base_probability

    plays_today = random.random() < probability
    return plays_today, False


GAMES = [
    {"name": "Land of Ra", "rtp": 0.95, "volatility": "medium", "weight": 19},
    {"name": "Sweet Bonanza", "rtp": 0.96, "volatility": "high", "weight": 20},
    {"name": "Gates of Olympus", "rtp": 0.965, "volatility": "high", "weight": 20},
    {"name": "Lucky Wheelioanire", "rtp": 0.94, "volatility": "medium", "weight": 18},
    {"name": "Bluster Blackjack", "rtp": 0.97, "volatility": "low", "weight": 25},
    {"name": "VIP Bluster Blackjack", "rtp": 0.975, "volatility": "low", "weight": 3},
    {"name": "Speed Baccarat", "rtp": 0.985, "volatility": "low", "weight": 19}
]
GAME_WEIGHTS = [g["weight"] for g in GAMES]

WIN_PROBABILITY = {"low": 0.45, "medium": 0.30, "high": 0.15}

MIN_BET = 0.10
BET_AMOUNT_MU = 0.3
BET_AMOUNT_SIGMA = 0.5

HOUR_WEIGHTS = [
    1, 1, 1, 1, 1, 1,
    1, 2, 3, 4, 5, 6,
    7, 8, 8, 7, 7, 8,
    10, 12, 14, 13, 10, 5
]
HOURS = list(range(24))

SESSIONS_PER_DAY = [1, 2, 3]
SESSIONS_PER_DAY_WEIGHTS = [75, 20, 5]

SESSION_DURATION_MINUTES = (5, 120)
GAP_BETWEEN_SESSIONS_MINUTES = (15, 240)
SECONDS_PER_ROUND_RANGE = (8, 20)

DEPOSIT_PROBABILITY_PER_SESSION = {"losing": 0.045, "normal": 0.02, "winning": 0.007}
DEPOSIT_AMOUNT_MU = 3.5
DEPOSIT_AMOUNT_SIGMA = 0.8

WIN_GROWTH_THRESHOLD = 0.5
WITHDRAWAL_FRACTION_RANGE = (0.3, 0.7)
MIN_WIN_FOR_WITHDRAWAL = 10.0


def random_start_time(activity_date):
    hour = random.choices(HOURS, weights=HOUR_WEIGHTS)[0]
    minute = random.randint(0, 59)
    return datetime.combine(activity_date, datetime.min.time()).replace(hour=hour, minute=minute)


def random_deposit_amount():
    return round(random.lognormvariate(DEPOSIT_AMOUNT_MU, DEPOSIT_AMOUNT_SIGMA), 2)


def random_bet_amount():
    return round(random.lognormvariate(BET_AMOUNT_MU, BET_AMOUNT_SIGMA), 2)


def simulate_win(bet, game):
    win_probability = WIN_PROBABILITY[game["volatility"]]

    if random.random() < win_probability:
        mean_multiplier = game["rtp"] / win_probability
        multiplier = random.expovariate(1 / mean_multiplier)
        win = bet * multiplier
    else:
        win = 0.0

    return round(win, 2)


def simulate_player_day(player_id, player_type, balance, new_date):
    activity_rows = [(player_id, new_date)]
    session_rows = []
    deposit_rows = []
    bet_rows = []
    withdrawal_rows = []

    number_of_sessions = random.choices(SESSIONS_PER_DAY, weights=SESSIONS_PER_DAY_WEIGHTS)[0]
    current_start = random_start_time(new_date)

    deposit_probability = DEPOSIT_PROBABILITY_PER_SESSION[player_type]

    for i in range(number_of_sessions):
        if i > 0:
            gap = random.randint(*GAP_BETWEEN_SESSIONS_MINUTES)
            current_start = current_start + timedelta(minutes=gap)

            if current_start.date() > new_date:
                break

        if random.random() < deposit_probability:
            deposit_amount = random_deposit_amount()
            balance += deposit_amount
            deposit_rows.append((player_id, new_date, deposit_amount))

        duration = random.randint(*SESSION_DURATION_MINUTES)
        session_end = current_start + timedelta(minutes=duration)

        end_of_day = datetime.combine(new_date, datetime.min.time()) + timedelta(days=1) - timedelta(seconds=1)
        if session_end > end_of_day:
            session_end = end_of_day

        session_rows.append((player_id, current_start, session_end))

        seconds_per_round = random.uniform(*SECONDS_PER_ROUND_RANGE)
        max_rounds = int((session_end - current_start).total_seconds() // seconds_per_round)

        bet_time = current_start

        for _ in range(max_rounds):
            if balance < MIN_BET:
                break

            game = random.choices(GAMES, weights=GAME_WEIGHTS)[0]

            bet = random_bet_amount()
            bet = min(bet, balance)

            balance_before_bet = balance
            balance -= bet

            win = simulate_win(bet, game)
            balance += win

            bet_rows.append((player_id, bet_time, game["name"], bet, win, round(balance, 2)))

            if balance_before_bet > 0 and win > balance_before_bet * WIN_GROWTH_THRESHOLD and win > MIN_WIN_FOR_WITHDRAWAL:
                fraction = random.uniform(*WITHDRAWAL_FRACTION_RANGE)
                withdrawal_amount = round(balance * fraction, 2)
                balance -= withdrawal_amount
                withdrawal_rows.append((player_id, bet_time, withdrawal_amount, round(balance, 2)))

            bet_time += timedelta(seconds=seconds_per_round)

        current_start = session_end

    return {
        "activity": activity_rows,
        "sessions": session_rows,
        "deposits": deposit_rows,
        "bets": bet_rows,
        "withdrawals": withdrawal_rows,
        "final_balance": round(balance, 2)
    }


def insert_simulation_results(conn, player_id, result):
    with conn.cursor() as cur:
        cur.execute("SAVEPOINT player_insert;")

        try:
            for row in result["activity"]:
                cur.execute("INSERT INTO activity (player_id, activity_date) VALUES (%s, %s);", row)

            for row in result["sessions"]:
                cur.execute("INSERT INTO sessions (player_id, session_start, session_end) VALUES (%s, %s, %s);", row)

            for row in result["deposits"]:
                cur.execute("INSERT INTO deposits (player_id, deposit_date, amount) VALUES (%s, %s, %s);", row)

            for row in result["bets"]:
                cur.execute(
                    "INSERT INTO bets (player_id, timestamp, game, bet_amount, win_amount, balance_after) VALUES (%s, %s, %s, %s, %s, %s);",
                    row
                )

            for row in result["withdrawals"]:
                cur.execute(
                    "INSERT INTO withdrawals (player_id, timestamp, amount, balance_after) VALUES (%s, %s, %s, %s);",
                    row
                )

            cur.execute(
                "UPDATE player_state SET current_balance = %s, last_activity_date = %s WHERE player_id = %s;",
                (result["final_balance"], result["activity"][0][1], player_id)
            )

            cur.execute("RELEASE SAVEPOINT player_insert;")
            return True

        except Exception as e:
            cur.execute("ROLLBACK TO SAVEPOINT player_insert;")
            print(f"ERROR inserting data for player {player_id}: {e}")
            return False


def mark_players_churned(conn, player_ids):
    if not player_ids:
        return

    with conn.cursor() as cur:
        cur.execute(
            "UPDATE player_state SET is_churned = TRUE WHERE player_id = ANY(%s);",
            (player_ids,)
        )


def main():
    if os.path.exists(LOCK_FILE):
        print("ERROR: Another simulation run appears to be in progress (or crashed without cleanup).")
        print(f"If you're sure no other run is active, delete '{LOCK_FILE}' manually and try again.")
        sys.exit(1)

    with open(LOCK_FILE, "w") as f:
        f.write("running")

    conn = get_connection()

    try:
        new_date = get_new_date(conn)
        max_player_id = get_max_player_id(conn)

        print(f"Simulating day: {new_date}")

        new_players = register_new_players(conn, new_date, max_player_id)
        print(f"Registered {len(new_players)} new players: {new_players}")

        active_players = get_active_players(conn)
        print(f"Checking {len(active_players)} active players...")

        newly_churned = []
        players_simulated = 0

        for player_id, player_type, current_balance, last_activity_date in active_players:
            plays_today, became_churned = decide_if_plays_today(player_type, last_activity_date, new_date)

            if became_churned:
                newly_churned.append(player_id)
                continue

            if not plays_today:
                continue

            result = simulate_player_day(player_id, player_type, float(current_balance), new_date)
            success = insert_simulation_results(conn, player_id, result)
            if success:
                players_simulated += 1

        mark_players_churned(conn, newly_churned)

        conn.commit()

        print(f"Players simulated today: {players_simulated}")
        print(f"Newly churned players: {len(newly_churned)}")
        print("Done.")

    finally:
        conn.close()
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)


if __name__ == "__main__":
    main()