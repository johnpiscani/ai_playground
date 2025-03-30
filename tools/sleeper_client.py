# sleeper_client.py
import requests_cache
from urllib.parse import urljoin
from typing import Union, Optional, List, Dict
from pathlib import Path

class SleeperClient:
    def __init__(self, cache_path: str = '../.cache'):
        self.cache_path = cache_path
        self.session = requests_cache.CachedSession(
            Path(cache_path) / 'api_cache', 
            backend='sqlite',
            expire_after=60 * 60 * 24,  # cache expires in 24 hours
        )

        # Base API URLs
        self.base_url = 'https://api.sleeper.app/v1/'
        self.stats_url = 'https://api.sleeper.com/'
        self.cdn_base_url = 'https://sleepercdn.com/'
        self.graphql_url = 'https://sleeper.com/graphql'

        # Get NFL state info (season, current week, etc.)
        self.nfl_state = self.get_nfl_state()

    def _get_json(self, path: str, base_url: Optional[str] = None) -> dict:
        url = urljoin(base_url or self.base_url, path)
        return self.session.get(url).json()

    def _graphql(self, operation_name: str, query: str, variables: Optional[dict] = None) -> dict:
        return self.session.post(self.graphql_url, data={
            "operationName": operation_name,
            "variables": variables or {},
            "query": query,
        }).json()

    def get_nfl_state(self) -> dict:
        return self._get_json('state/nfl')

    def get_league_info(self, league_id: str) -> Dict:
        league_data = self._get_json(f'league/{league_id}')
        standings = self.get_league_standings(league_id)
        playoff_teams = league_data.get('playoff_teams', [])
        return {
            "league_data": league_data,
            "standings": standings,
            "playoff_teams": playoff_teams,
            "current_week": self.nfl_state.get('display_week')
        }

    def get_league_standings(self, league_id: str) -> List[Dict]:
        query = f"""query get_league_standings {{
            metadata(type: "league_history", key: "{league_id}") {{
                data {{
                    standings {{
                        team_id
                        wins
                        fpts
                    }}
                }}
            }}
        }}"""
        response = self._graphql(operation_name='get_league_standings', query=query)
        standings = response['data']['metadata']['data'].get('standings', [])
        sorted_standings = sorted(standings, key=lambda x: (x['wins'], x.get('fpts', 0)), reverse=True)
        return sorted_standings

    def get_league_rosters(self, league_id: str) -> Dict:
        return self._get_json(f'league/{league_id}/rosters')

    def get_player_statistics(self, player_id: Union[str, int], season: Optional[int] = None, group_by_week: bool = False) -> Dict:
        stats = self._get_json(
            f'stats/nfl/player/{player_id}?season_type=regular&season={season or self.nfl_state["season"]}{"&grouping=week" if group_by_week else ""}',
            base_url=self.stats_url
        )
        return stats.get('stats', {})

    def get_player_news(self, player_id: Union[str, int], limit: int = 3) -> List[Dict]:
        query = f"""query get_player_news {{
            news: get_player_news(sport: "nfl", player_id: "{player_id}", limit: {limit}) {{
                metadata {{
                    title
                    description
                    analysis
                    url
                }}
                published
                source
            }}
        }}"""
        response = self._graphql(operation_name='get_player_news', query=query)
        return response['data']['news']

    def evaluate_trade_candidate(self, league_id: str, player_id: Union[str, int]) -> Dict:
        stats = self.get_player_statistics(player_id)
        news = self.get_player_news(player_id)
        fpts = float(stats.get('pts_ppr', 0))
        games = float(stats.get('games_played', 1))
        avg_fpts = fpts / games if games else 0
        injury_penalty = 0
        for article in news:
            if "injury" in article['metadata'].get('description', "").lower():
                injury_penalty += 5
        evaluation_score = avg_fpts - injury_penalty
        return {
            "player_id": player_id,
            "average_points": avg_fpts,
            "injury_penalty": injury_penalty,
            "evaluation_score": evaluation_score,
            "news": news
        }

    def evaluate_waiver_wire(self, league_id: str, position: str) -> List[Dict]:
        projections = self._get_json(
            f'projections/nfl/{self.nfl_state["season"]}/{self.nfl_state["display_week"]}?season_type=regular&position[]={position}',
            base_url=self.stats_url
        )
        ranked_players = sorted(projections, key=lambda p: p['stats'].get('pts_ppr', 0), reverse=True)
        recommendations = []
        for p in ranked_players[:5]:
            recommendations.append({
                "player_id": p['player_id'],
                "projected_points": p['stats'].get('pts_ppr', 0),
                "player_info": p.get('player', {})
            })
        return recommendations
