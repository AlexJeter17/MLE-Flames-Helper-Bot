"""Shared query: every Flames series in one Match week.

Path: mledb.match (season, match_number) -> fixture (home/away franchise)
      -> series (league, mode, scheduled_time UTC) -> series_replay (games)
Sprocket match id (used for Evidence links) comes via
      mledb_bridge.series_to_match_parent -> sprocket.match.
"""
from dataclasses import dataclass
from datetime import datetime

import config
from flamesbot.db import ReadOnlySession


@dataclass
class SeriesRow:
    fixture_id: int
    series_id: int
    league: str
    mode: str
    scheduled_time: datetime | None
    home: str
    away: str
    full_ncp: bool
    games: int
    team_wins: int
    opponent_wins: int
    sprocket_match_id: int | None

    @property
    def opponent(self) -> str:
        return self.away if self.home == config.TEAM_NAME else self.home

    @property
    def is_home(self) -> bool:
        return self.home == config.TEAM_NAME


def load_week_series(sess: ReadOnlySession, match_id: int) -> list[SeriesRow]:
    rows = sess.fetch_all(
        """
        SELECT f.id AS fixture_id, s.id AS series_id, s.league, s.mode, s.scheduled_time,
               f.home_name, f.away_name, s.full_ncp,
               COUNT(r.id) AS games,
               COUNT(r.id) FILTER (WHERE r.winning_team_name = %(team)s) AS team_wins,
               COUNT(r.id) FILTER (WHERE r.winning_team_name IS NOT NULL
                                     AND r.winning_team_name <> %(team)s) AS opponent_wins,
               (SELECT MIN(sm.id)
                  FROM mledb_bridge.series_to_match_parent b
                  JOIN sprocket.match sm ON sm."matchParentId" = b."matchParentId"
                 WHERE b."seriesId" = s.id) AS sprocket_match_id
        FROM mledb.fixture f
        JOIN mledb.series s ON s.fixture_id = f.id
        LEFT JOIN mledb.series_replay r ON r.series_id = s.id
        WHERE f.match_id = %(match_id)s
          AND %(team)s IN (f.home_name, f.away_name)
        GROUP BY f.id, s.id
        ORDER BY f.id, s.league, s.mode
        """,
        {"match_id": match_id, "team": config.TEAM_NAME},
    )
    return [
        SeriesRow(
            fixture_id=r["fixture_id"], series_id=r["series_id"], league=r["league"], mode=r["mode"],
            scheduled_time=r["scheduled_time"], home=r["home_name"], away=r["away_name"],
            full_ncp=bool(r["full_ncp"]), games=int(r["games"]), team_wins=int(r["team_wins"]),
            opponent_wins=int(r["opponent_wins"]), sprocket_match_id=r["sprocket_match_id"],
        )
        for r in rows
    ]


def group_by_fixture(series: list[SeriesRow]) -> list[list[SeriesRow]]:
    """One group per Flames fixture ("match day"), earliest scheduled first."""
    groups: dict[int, list[SeriesRow]] = {}
    for s in series:
        groups.setdefault(s.fixture_id, []).append(s)

    def first_time(group):
        times = [s.scheduled_time for s in group if s.scheduled_time]
        return (min(times).timestamp() if times else float("inf"), group[0].fixture_id)

    return sorted(groups.values(), key=first_time)
