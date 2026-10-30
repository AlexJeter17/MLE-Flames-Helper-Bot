"""fb.WeekResults <weekNum>: Flames results for a Match week, with Evidence links."""
import asyncio

import config
from flamesbot import db, evidence, leagues
from flamesbot.features.matches import league_block, league_heading, result_text
from flamesbot.features.schedule import SeriesRow, group_by_fixture, load_week_series
from flamesbot.messages import Reply, text_replies
from flamesbot.season import MatchWeek, number_word, resolve_season, resolve_week
from flamesbot.timeutil import as_utc, fmt_datetime, now_utc


def _report(s: SeriesRow, link_status: dict[int, str]) -> str:
    if s.sprocket_match_id is None:
        return "no report yet"
    status = link_status.get(s.sprocket_match_id, evidence.UNVERIFIED)
    if status == evidence.NOT_FOUND:
        return "no report yet"
    # <url> stops Discord from unfurling a preview for every link.
    url = evidence.url_for(s.sprocket_match_id)
    return f"[Report](<{url}>)" + (" (unverified)" if status == evidence.UNVERIFIED else "")


def _suffix(link_status: dict[int, str]):
    def suffix(s: SeriesRow) -> str:
        if s.games == 0:
            return " | ⏳ Result not in yet"
        text = result_text(s, partial_note=f"⚠️ only {s.games}/{config.SERIES_GAMES} games recorded")
        if s.full_ncp:
            text += " (NCP)"
        return f"{text} | {_report(s, link_status)}"
    return suffix


def render(season_number: int, week: MatchWeek, series: list[SeriesRow], link_status: dict[int, str]) -> list[Reply]:
    missing = []
    series_w = series_l = 0
    for s in sorted(series, key=lambda s: (leagues.sort_key(s.league), leagues.MODE_ORDER.index(s.mode)
                                           if s.mode in leagues.MODE_ORDER else 9)):
        if s.games == 0:
            missing.append(f"{leagues.code(s.league)} {leagues.MODE_SHORT.get(s.mode, s.mode)}")
        elif s.team_wins > s.opponent_wins:
            series_w += 1
        elif s.team_wins < s.opponent_wins:
            series_l += 1

    lines = [f"# Match {number_word(week.number)} Results",
             f"Series record this week: **{series_w}-{series_l}**"]
    if as_utc(week.end) > now_utc():
        lines.append(f"⏳ This week isn't over yet (ends {fmt_datetime(week.end)}).")
    if missing:
        lines.append(f"⚠️ Missing results: {', '.join(missing)}")
    elif series:
        lines.append("All results are in.")

    groups = group_by_fixture(series)
    if not groups:
        for lg in leagues.LEAGUE_ORDER:
            lines += [league_heading(lg), "No match scheduled this week"]
        lines.append(f"-# No Flames fixture found for Match {week.number} (bye week?) · Season {season_number}")
        return text_replies(lines)

    suffix = _suffix(link_status)
    for i, group in enumerate(groups):
        if len(groups) > 1:
            lines += ["", f"## Day {i + 1}"]
        for lg in leagues.LEAGUE_ORDER:
            lines += league_block(lg, group, suffix)
        first = group[0]
        where = "home" if first.is_home else "away"
        lines.append(f"-# vs {first.opponent} ({where}) · times in {config.DISPLAY_TZ_LABEL} · "
                     f"Season {season_number} · Score = games won-lost · Reports from evidence.mlesports.gg")
    return text_replies(lines)


async def build(week: int, season: int | None = None) -> list[Reply]:
    def work():
        with db.session() as sess:
            info = resolve_season(sess, season)
            match_week = resolve_week(sess, info, week)
            return info, match_week, load_week_series(sess, match_week.id)

    info, match_week, series = await asyncio.to_thread(work)
    link_status = await evidence.check_links([s.sprocket_match_id for s in series if s.sprocket_match_id])
    return render(info.number, match_week, series, link_status)
