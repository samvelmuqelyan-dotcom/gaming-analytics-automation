from generate_players import generate_players
from generate_activity import read_players, generate_activity
from generate_sessions import read_activity, generate_sessions
from generate_deposits import read_players as read_players_deposits, read_sessions_by_player, generate_deposits
from generate_bets import read_players as read_players_bets, read_sessions_by_player as read_sessions_bets, read_deposits_by_player, generate_bets_and_withdrawals

def main():
    print("Generating players...")
    generate_players()

    print("Generating activity...")
    players = read_players()
    generate_activity(players)

    print("Generating sessions...")
    activity_rows = read_activity()
    generate_sessions(activity_rows)

    print("Generating deposits...")
    players_for_deposits = read_players_deposits()
    sessions_by_player = read_sessions_by_player()
    generate_deposits(players_for_deposits, sessions_by_player)

    print("Generating bets and withdrawals...")
    players_for_bets = read_players_bets()
    sessions_for_bets = read_sessions_bets()
    deposits_for_bets = read_deposits_by_player()
    generate_bets_and_withdrawals(players_for_bets, sessions_for_bets, deposits_for_bets)

    print("Done.")


if __name__ == "__main__":
    main()