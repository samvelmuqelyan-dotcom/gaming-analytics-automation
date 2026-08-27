import csv
import random
from datetime import datetime, timedelta


GAMES = [
    {"name": "Land of Ra", "rtp": 0.95, "volatility": "medium", "weight": 18},
    {"name": "Sweet Bonanza", "rtp": 0.96, "volatility": "high", "weight": 20},
    {"name": "Gates of Olympus", "rtp": 0.965, "volatility": "high", "weight": 19},
    {"name": "Lucky Wheelioanire", "rtp": 0.94, "volatility": "medium", "weight": 17},
    {"name": "Bluster Blackjack", "rtp": 0.97, "volatility": "low", "weight": 25},
    {"name": "VIP Bluster Blackjack", "rtp": 0.975, "volatility": "low", "weight": 3},
    {"name": "Speed Baccarat", "rtp": 0.985, "volatility": "low", "weight": 18}
]

GAME_WEIGHTS = [game["weight"] for game in GAMES]

WIN_PROBABILITY = {
    "low": 0.45,
    "medium": 0.30,
    "high": 0.15
}

MIN_BET = 0.10
BET_AMOUNT_MU = 0.3
BET_AMOUNT_SIGMA = 0.5

SECONDS_PER_ROUND_RANGE = (8, 20)

WIN_GROWTH_THRESHOLD = 0.5
WITHDRAWAL_FRACTION_RANGE = (0.3, 0.7)
MIN_WIN_FOR_WITHDRAWAL = 10.0


def read_players(path="players.csv"):
    players = {}
    with open(path, newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            players[row["player_id"]] = row["player_type"]
    return players


def read_sessions_by_player(path="sessions.csv"):
    sessions_by_player = {}
    with open(path, newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            player_id = row["player_id"]
            start = datetime.strptime(row["session_start"], "%Y-%m-%d %H:%M:%S")
            end = datetime.strptime(row["session_end"], "%Y-%m-%d %H:%M:%S")
            sessions_by_player.setdefault(player_id, []).append((start, end))

    for player_id in sessions_by_player:
        sessions_by_player[player_id].sort(key=lambda s: s[0])

    return sessions_by_player


def read_deposits_by_player(path="deposits.csv"):
    deposits_by_player = {}
    with open(path, newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            player_id = row["player_id"]
            deposit_date = datetime.strptime(row["deposit_date"], "%Y-%m-%d").date()
            amount = float(row["amount"])
            deposits_by_player.setdefault(player_id, []).append((deposit_date, amount))

    for player_id in deposits_by_player:
        deposits_by_player[player_id].sort(key=lambda d: d[0])

    return deposits_by_player


def random_bet_amount():
    amount = random.lognormvariate(BET_AMOUNT_MU, BET_AMOUNT_SIGMA)
    return round(amount, 2)


def simulate_win(bet, game):
    win_probability = WIN_PROBABILITY[game["volatility"]]

    if random.random() < win_probability:
        mean_multiplier = game["rtp"] / win_probability
        multiplier = random.expovariate(1 / mean_multiplier)
        win = bet * multiplier
    else:
        win = 0.0

    return round(win, 2)


def generate_bets_and_withdrawals(players, sessions_by_player, deposits_by_player):
    with open("bets.csv", "w", newline="", encoding="utf-8") as bets_file, \
         open("withdrawals.csv", "w", newline="", encoding="utf-8") as withdrawals_file:

        bets_writer = csv.writer(bets_file)
        withdrawals_writer = csv.writer(withdrawals_file)

        bets_writer.writerow([
            "player_id",
            "timestamp",
            "game",
            "bet_amount",
            "win_amount",
            "balance_after"
        ])

        withdrawals_writer.writerow([
            "player_id",
            "timestamp",
            "amount",
            "balance_after"
        ])

        processed = 0

        for player_id, player_type in players.items():
            processed += 1
            if processed % 500 == 0:
                print(f"Processed {processed} players...")

            sessions = sessions_by_player.get(player_id, [])
            deposits = deposits_by_player.get(player_id, [])

            balance = 0.0
            deposit_index = 0

            for start, end in sessions:
                while deposit_index < len(deposits) and deposits[deposit_index][0] <= start.date():
                    balance += deposits[deposit_index][1]
                    deposit_index += 1

                duration_seconds = (end - start).total_seconds()
                seconds_per_round = random.uniform(*SECONDS_PER_ROUND_RANGE)
                max_rounds = int(duration_seconds // seconds_per_round)

                current_time = start

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

                    bets_writer.writerow([
                        player_id,
                        current_time,
                        game["name"],
                        bet,
                        win,
                        round(balance, 2)
                    ])

                    if balance_before_bet > 0 and win > balance_before_bet * WIN_GROWTH_THRESHOLD and win > MIN_WIN_FOR_WITHDRAWAL:
                        fraction = random.uniform(*WITHDRAWAL_FRACTION_RANGE)
                        withdrawal_amount = round(balance * fraction, 2)

                        balance -= withdrawal_amount

                        withdrawals_writer.writerow([
                            player_id,
                            current_time,
                            withdrawal_amount,
                            round(balance, 2)
                        ])

                    current_time += timedelta(seconds=seconds_per_round)


if __name__ == "__main__":
    players = read_players()
    sessions_by_player = read_sessions_by_player()
    deposits_by_player = read_deposits_by_player()
    generate_bets_and_withdrawals(players, sessions_by_player, deposits_by_player)