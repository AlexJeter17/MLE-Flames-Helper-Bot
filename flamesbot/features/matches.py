"""fb.Matches <weekNum>: when each Flames league plays that week (Eastern time), with results once played."""
import asyncio

import config
from flamesbot import db, leagues
from flamesbot.features.schedule import SeriesRow, group_by_fixture, load_week_series
from flamesbot.messages import Reply, text_replies
from flamesbot.season import number_word, resolve_season, resolve_week
from flamesbot.timeutil import fmt_day_time


def _result(s: SeriesRow) -> str:
    """'| :FlamesDub: 4-1 W' once games are recorded, else ''."""
    if s.games == 0:
        return ""
    score = f"{s.team_wins}-{s.opponent_wins}"
    if s.games < config.SERIES_GAMES and not s.full_ncp:
        return f" | {score} (in progress)"
    if s.team_wins > s.opponent_wins:
        return f" | {config.WIN_EMOJI} {score} W"
    if s.team_wins < s.opponent_wins:
        return f" | {config.LOSS_EMOJI} {score} L"
    return f" | {score} Tie"


def _heading(league: str) -> str:
    return f"### {leagues.label(league)} {leagues.name(league)}"


def _league_block(league: str, series: list[SeriesRow]) -> list[str]:
    by_mode = {s.mode: s for s in series if s.league == league}
    lines = [_heading(league)]
    if not by_mode:
        return lines + ["No match scheduled this week"]

    for mode in leagues.MODE_ORDER:
        s = by_mode.get(mode)
        short = leagues.MODE_SHORT[mode]
        if s is None:
            lines.append(f"{short} not scheduled")
        elif s.scheduled_time is None:
            lines.append(f"{short} time TBD{_result(s)}")
        else:
            lines.append(f"{short} {fmt_day_time(s.scheduled_time)}{_result(s)}")
    return lines


def render(season_number: int, week: int, series: list[SeriesRow], season_over: bool) -> list[Reply]:
    lines: list[str] = []
    groups = group_by_fixture(series)
    heading = f"# Match {number_word(week)}"

    if not groups:
        lines.append(heading)
        for lg in leagues.LEAGUE_ORDER:
            lines += [_heading(lg), "No match scheduled this week"]
        lines.append(f"-# No Flames fixture found for Match {week} (bye week?) · Season {season_number}")
        return text_replies(lines)

    for i, group in enumerate(groups):
        if lines:
            lines.append("")
        lines.append(heading if len(groups) == 1 else f"{heading} · Day {i + 1}")
        for lg in leagues.LEAGUE_ORDER:
            lines += _league_block(lg, group)
        first = group[0]
        where = "home" if first.is_home else "away"
        lines.append(f"-# vs {first.opponent} ({where}) · times in {config.DISPLAY_TZ_LABEL} · Season {season_number}"
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
