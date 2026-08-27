import csv
import random
from datetime import date, timedelta


START_DATE = date(2020, 1, 1)
END_DATE = date(2021, 1, 1)

ACTIVITY_PROFILES = {
    "normal": {"play_probability": 0.12, "lifetime_days": (30, 900)},
    "losing": {"play_probability": 0.06, "lifetime_days": (10, 300)},
    "winning": {"play_probability": 0.25, "lifetime_days": (180, 1800)}
}


def read_players(path="players.csv"):
    players = []

    with open(path, newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            row["registration_date"] = date.fromisoformat(row["registration_date"])
            players.append(row)

    return players


def generate_activity(players):
    with open("activity.csv", "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["player_id", "activity_date"])

        for player in players:
            profile = ACTIVITY_PROFILES[player["player_type"]]
            registration_date = player["registration_date"]

            if registration_date >= END_DATE:
                continue

            min_life, max_life = profile["lifetime_days"]
            lifetime = random.randint(min_life, max_life)

            last_active_day = registration_date + timedelta(days=lifetime)
            if last_active_day > END_DATE:
                last_active_day = END_DATE

            total_days = (last_active_day - registration_date).days
            if total_days <= 0:
                continue

            play_probability = profile["play_probability"]

            for offset in range(total_days + 1):
                current_day = registration_date + timedelta(days=offset)
                if random.random() < play_probability:
                    writer.writerow([player["player_id"], current_day])


if __name__ == "__main__":
    players = read_players()
    generate_activity(players)