"""fb.Matches <weekNum>: when each Flames league plays that week (Pacific time)."""
import asyncio

from flamesbot import db, leagues
from flamesbot.features.schedule import SeriesRow, group_by_fixture, load_week_series
from flamesbot.messages import Reply, text_replies
from flamesbot.season import number_word, resolve_season, resolve_week
from flamesbot.timeutil import fmt_day_time


def _league_line(league: str, series: list[SeriesRow]) -> str:
    by_mode = {s.mode: s for s in series if s.league == league}
    label = leagues.label(league)
    if not by_mode:
        return f"{label} No match scheduled this week"

    parts = []
    for mode in leagues.MODE_ORDER:
        s = by_mode.get(mode)
        short = leagues.MODE_SHORT[mode]
        if s is None:
            parts.append(f"{short} not scheduled")
        elif s.scheduled_time is None:
            parts.append(f"{short} time TBD")
        else:
            parts.append(f"{short} {fmt_day_time(s.scheduled_time)}")
    return f"{label} " + " · ".join(parts)


def render(season_number: int, week: int, series: list[SeriesRow], season_over: bool) -> list[Reply]:
    lines: list[str] = []
    groups = group_by_fixture(series)
    heading = f"# Match {number_word(week)}"

    if not groups:
        lines.append(heading)
        lines += [f"{leagues.label(lg)} No match scheduled this week" for lg in leagues.LEAGUE_ORDER]
        lines.append(f"-# No Flames fixture found for Match {week} (bye week?) · Season {season_number}")
        return text_replies(lines)

    for i, group in enumerate(groups):
        if lines:
            lines.append("")
        lines.append(heading if len(groups) == 1 else f"{heading} · Day {i + 1}")
        lines += [_league_line(lg, group) for lg in leagues.LEAGUE_ORDER]
        first = group[0]
        where = "home" if first.is_home else "away"
        lines.append(f"-# vs {first.opponent} ({where}) · times in Pacific · Season {season_number}"
                     + (" (completed)" if season_over else ""))
    return text_replies(lines)


async def build(week: int, season: int | None = None) -> list[Reply]:
    def work():
        with db.session() as sess:
            info = resolve_season(sess, season)
            match_week = resolve_week(sess, info, week)
            return info, load_week_series(sess, match_week.id)

    info, series = await asyncio.to_thread(work)
    return render(info.number, week, series, info.is_over)
