import csv
import random
from datetime import datetime, timedelta


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


def read_activity(path="activity.csv"):
    rows = []
    with open(path, newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            rows.append(row)
    return rows


def random_start_time(activity_date):
    hour = random.choices(HOURS, weights=HOUR_WEIGHTS)[0]
    minute = random.randint(0, 59)
    activity_date = datetime.strptime(activity_date, "%Y-%m-%d")
    return activity_date.replace(hour=hour, minute=minute)


def generate_sessions(activity_rows):
    with open("sessions.csv", "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["player_id", "session_start", "session_end"])

        for row in activity_rows:
            player_id = row["player_id"]
            activity_date = row["activity_date"]

            number_of_sessions = random.choices(
                SESSIONS_PER_DAY, weights=SESSIONS_PER_DAY_WEIGHTS
            )[0]

            current_start = random_start_time(activity_date)

            for i in range(number_of_sessions):
                if i > 0:
                    gap = random.randint(*GAP_BETWEEN_SESSIONS_MINUTES)
                    current_start = current_start + timedelta(minutes=gap)

                duration = random.randint(*SESSION_DURATION_MINUTES)
                current_end = current_start + timedelta(minutes=duration)

                writer.writerow([player_id, current_start, current_end])
                current_start = current_end


if __name__ == "__main__":
    activity_rows = read_activity()
    generate_sessions(activity_rows)