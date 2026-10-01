"""Season resolution and weekNum / season argument parsing.

Week number == MLE "Match" number (mledb.match.match_number), not calendar weeks.
"""
from dataclasses import dataclass
from datetime import datetime

import config
from flamesbot.db import ReadOnlySession
from flamesbot.messages import UserFacingError
from flamesbot.timeutil import as_utc, now_utc

_NUMBER_WORDS = [
    "Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
    "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen",
    "Eighteen", "Nineteen", "Twenty",
]


def number_word(n: int) -> str:
    return _NUMBER_WORDS[n] if 0 <= n < len(_NUMBER_WORDS) else str(n)


@dataclass
class SeasonInfo:
    number: int
    start: datetime
    end: datetime | None

    @property
    def is_over(self) -> bool:
        return self.end is not None and as_utc(self.end) < now_utc()


@dataclass
class MatchWeek:
    id: int
    number: int
    start: datetime
    end: datetime


def parse_week(arg: str | None, command: str) -> int:
    if arg is None or not arg.strip().isdigit():
        raise UserFacingError(
            f"Please give a week number, e.g. `fb.{command} 3`. "
            "Week number = the MLE Match number (Match 1, Match 2, ...)."
        )
    return int(arg)


def parse_season(arg: str | None) -> int | None:
    if arg is None:
        return None
    cleaned = arg.strip().lower().lstrip("s")
    if not cleaned.isdigit():
        raise UserFacingError(f"`{arg}` isn't a season. Use something like `s19` or `19`.")
    return int(cleaned)


def resolve_season(sess: ReadOnlySession, requested: int | None = None) -> SeasonInfo:
    number = requested or config.CURRENT_SEASON
    if number is None:
        row = sess.fetch_one(
            "SELECT season_number FROM mledb.season WHERE start_date <= now() "
            "ORDER BY season_number DESC LIMIT 1"
        )
        if not row:
            raise UserFacingError("I couldn't find any season in the database.")
        number = row["season_number"]

    row = sess.fetch_one(
        "SELECT season_number, start_date, end_date FROM mledb.season WHERE season_number = %(s)s",
        {"s": number},
    )
    if not row:
        raise UserFacingError(f"Season {number} isn't in the database yet.")
    return SeasonInfo(row["season_number"], row["start_date"], row["end_date"])


def resolve_week(sess: ReadOnlySession, season: SeasonInfo, week: int) -> MatchWeek:
    rows = sess.fetch_all(
        'SELECT id, match_number, "from" AS start, "to" AS end FROM mledb.match '
        "WHERE season = %(s)s ORDER BY match_number",
        {"s": season.number},
    )
    if not rows:
        raise UserFacingError(f"Season {season.number} has no match schedule in the database yet.")
    for r in rows:
        if r["match_number"] == week:
            return MatchWeek(r["id"], r["match_number"], r["start"], r["end"])
    numbers = [r["match_number"] for r in rows]
    raise UserFacingError(
        f"Week {week} isn't a match week in Season {season.number}. "
        f"Valid weeks: {min(numbers)}–{max(numbers)}."
    )
