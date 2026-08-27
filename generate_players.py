import random
import csv
from datetime import date, timedelta


COUNTRIES = [
    "Armenia", "Georgia", "Kazakhstan",
    "Ukraine", "Germany", "France"
]
COUNTRY_WEIGHTS = [40, 25, 15, 10, 6, 4]

AGE_GROUPS = ["18-24", "25-34", "35-44", "45-54", "55+"]
AGE_WEIGHTS = [15, 35, 25, 15, 10]

PLAYER_TYPES = ["normal", "losing", "winning"]
PLAYER_TYPE_WEIGHTS = [90, 8, 2]

START_DATE = date(2020, 1, 1)
END_DATE = date(2021, 1, 1)
DAYS = (END_DATE - START_DATE).days

NUMBER_OF_PLAYERS = 5000


def choose_player_type():
    return random.choices(PLAYER_TYPES, weights=PLAYER_TYPE_WEIGHTS)[0]


def generate_players():
    with open("players.csv", "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        writer.writerow([
            "player_id", "registration_date",
            "country", "age_group", "player_type"
        ])

        for player_id in range(1, NUMBER_OF_PLAYERS + 1):
            country = random.choices(COUNTRIES, weights=COUNTRY_WEIGHTS)[0]
            age_group = random.choices(AGE_GROUPS, weights=AGE_WEIGHTS)[0]
            player_type = choose_player_type()
            registration_date = START_DATE + timedelta(days=random.randint(0, DAYS))

            writer.writerow([
                player_id, registration_date,
                country, age_group, player_type
            ])


if __name__ == "__main__":
    generate_players()