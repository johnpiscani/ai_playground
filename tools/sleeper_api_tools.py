from langchain.tools import tool
import json
from typing import Union, Optional
from sleeper_client import SleeperClient

# Create a shared SleeperClient instance
sleeper_client = SleeperClient()
def get_player_name_to_id() -> dict:
    """
    Build a dictionary mapping canonical player names to player IDs.
    This function calls the Sleeper API endpoint 'players/nfl', which returns
    a dictionary of all players, then iterates over it to build the mapping.
    """
    # Call the players endpoint directly.
    players = sleeper_client._get_json('players/nfl')
    # Build mapping: {player_full_name: player_id}
    name_to_id = {}
    for player_id, details in players.items():
        # Use the 'full_name' field if available.
        if 'full_name' in details:
            name_to_id[details['full_name']] = player_id
    return name_to_id


@tool
def fetch_league_info(league_id: str) -> str:
    """
    Fetch league information including standings, current week, and playoff teams.
    Input: league_id (string)
    Returns: JSON string of league info.
    """
    info = sleeper_client.get_league_info(league_id)
    return json.dumps(info)

@tool
def retrieve_rosters(league_id: str) -> str:
    """
    Retrieve all team rosters for a given league.
    Input: league_id (string)
    Returns: JSON string of rosters.
    """
    rosters = sleeper_client.get_league_rosters(league_id)
    return json.dumps(rosters)

@tool
def fetch_player_statistics(player_id: Union[str, int], season: Optional[int] = None, group_by_week: bool = False) -> str:
    """
    Fetch player statistics such as weekly points, matchups, and injury status.
    Input: player_id (string or int), optional season, group_by_week flag.
    Returns: JSON string of player statistics.
    """
    stats = sleeper_client.get_player_statistics(player_id, season, group_by_week)
    return json.dumps(stats)

@tool
def fetch_player_news(player_id: Union[str, int], limit: int = 3) -> str:
    """
    Fetch the latest news for a given player.
    Input: player_id (string or int), limit (int, default=3)
    Returns: JSON string of news articles.
    """
    news = sleeper_client.get_player_news(player_id, limit)
    return json.dumps(news)

@tool
def evaluate_trade(league_id: str, player_id: Union[str, int]) -> str:
    """
    Evaluate a player as a candidate for a trade or waiver wire pick.
    Input: league_id (string) and player_id (string or int)
    Returns: JSON string containing evaluation score and related data.
    """
    evaluation = sleeper_client.evaluate_trade_candidate(league_id, player_id)
    return json.dumps(evaluation)

@tool
def evaluate_waiver_wire(position: str, league_id: str) -> str:
    """
    Evaluate and rank the best available waiver wire picks for a given position.
    Input: position (string), league_id (string)
    Returns: JSON string of top recommendations.
    """
    recommendations = sleeper_client.evaluate_waiver_wire(league_id, position)
    return json.dumps(recommendations)
