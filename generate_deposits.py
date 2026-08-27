import csv
import random
from datetime import date, datetime, timedelta


START_DATE = date(2020, 1, 1)
END_DATE = date(2021, 1, 1)


DEPOSIT_PROBABILITY_PER_SESSION = {
    "losing": 0.09,
    "normal": 0.04,
    "winning": 0.013
}

DEPOSIT_AMOUNT_MU = 3.5
DEPOSIT_AMOUNT_SIGMA = 0.8

OFF_DAY_DEPOSIT_PROBABILITY = 0.03


def read_players(path="players.csv"):
    players = []

    with open(path, newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            row["registration_date"] = date.fromisoformat(row["registration_date"])
            players.append(row)

    return players


def read_sessions_by_player(path="sessions.csv"):
    sessions_by_player = {}

    with open(path, newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            player_id = row["player_id"]
            session_start = datetime.strptime(row["session_start"], "%Y-%m-%d %H:%M:%S")
            sessions_by_player.setdefault(player_id, []).append(session_start)

    for player_id in sessions_by_player:
        sessions_by_player[player_id].sort()

    return sessions_by_player


def random_deposit_amount():
    amount = random.lognormvariate(DEPOSIT_AMOUNT_MU, DEPOSIT_AMOUNT_SIGMA)
    return round(amount, 2)


def generate_deposits(players, sessions_by_player):
    with open("deposits.csv", "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        writer.writerow([
            "player_id",
            "deposit_date",
            "amount"
        ])

        for player in players:
            player_id = player["player_id"]
            player_type = player["player_type"]
            registration_date = player["registration_date"]

            probability = DEPOSIT_PROBABILITY_PER_SESSION[player_type]
            sessions = sessions_by_player.get(player_id, [])

            for session_start in sessions:
                if random.random() < probability:
                    amount = random_deposit_amount()

                    writer.writerow([
                        player_id,
                        session_start.date(),
                        amount
                    ])

            if random.random() < OFF_DAY_DEPOSIT_PROBABILITY:
                days_range = (END_DATE - registration_date).days
                if days_range > 0:
                    random_offset = random.randint(0, days_range)
                    off_date = registration_date + timedelta(days=random_offset)

                    amount = random_deposit_amount()

                    writer.writerow([
                        player_id,
                        off_date,
                        amount
                    ])


if __name__ == "__main__":
    players = read_players()
    sessions_by_player = read_sessions_by_player()
    generate_deposits(players, sessions_by_player)