"""fb.WeekResults <weekNum>: Flames results for a Match week, with Evidence links."""
import asyncio

import config
from flamesbot import db, evidence, leagues
from flamesbot.features.schedule import SeriesRow, load_week_series
from flamesbot.messages import Reply, embed_replies
from flamesbot.season import MatchWeek, resolve_season, resolve_week
from flamesbot.timeutil import as_utc, fmt_datetime, now_utc


def _report(s: SeriesRow, link_status: dict[int, str]) -> str:
    if s.sprocket_match_id is None:
        return "Report: not found"
    status = link_status.get(s.sprocket_match_id, evidence.UNVERIFIED)
    if status == evidence.NOT_FOUND:
        return "Report: not found"
    url = evidence.url_for(s.sprocket_match_id)
    return f"[Report]({url})" + (" (unverified)" if status == evidence.UNVERIFIED else "")


def _series_line(s: SeriesRow, link_status: dict[int, str]) -> tuple[str, bool]:
    """Returns (line, has_result)."""
    mode = leagues.MODE_SHORT.get(s.mode, s.mode.title())
    if s.games == 0:
        return f"**{mode}** ⏳ Result not in yet · {_report(s, link_status)}", False

    if s.team_wins > s.opponent_wins:
        outcome = "✅ **W**"
    elif s.team_wins < s.opponent_wins:
        outcome = "❌ **L**"
    else:
        outcome = "➖ **Tie**"
    text = f"**{mode}** {outcome} {s.team_wins}-{s.opponent_wins}"
    if s.full_ncp:
        text += " (NCP)"
    if s.games < config.SERIES_GAMES:
        text += f" ⚠️ only {s.games}/{config.SERIES_GAMES} games recorded"
    return f"{text} · {_report(s, link_status)}", True


def render(season_number: int, week: MatchWeek, series: list[SeriesRow], link_status: dict[int, str]) -> list[Reply]:
    sections = []
    missing = []
    series_w = series_l = 0

    for league in leagues.LEAGUE_ORDER:
        rows = sorted((s for s in series if s.league == league),
                      key=lambda s: leagues.MODE_ORDER.index(s.mode) if s.mode in leagues.MODE_ORDER else 9)
        title = f"{leagues.name(league)} ({leagues.code(league)})"
        if not rows:
            sections.append((title, ["No match scheduled this week"]))
            continue
        opponents = sorted({s.opponent for s in rows})
        title += f" vs {', '.join(opponents)}"
        # (sort key, line) so a missing mode lands in its 2s/3s position.
        keyed = [(leagues.MODE_ORDER.index(m), f"**{leagues.MODE_SHORT[m]}** No match scheduled")
                 for m in leagues.MODE_ORDER if m not in {s.mode for s in rows}]
        for s in rows:
            line, has_result = _series_line(s, link_status)
            keyed.append((leagues.MODE_ORDER.index(s.mode) if s.mode in leagues.MODE_ORDER else 9, line))
            if not has_result:
                missing.append(f"{leagues.code(league)} {leagues.MODE_SHORT.get(s.mode, s.mode)}")
            elif s.team_wins > s.opponent_wins:
                series_w += 1
            elif s.team_wins < s.opponent_wins:
                series_l += 1
        sections.append((title, [line for _, line in sorted(keyed, key=lambda k: k[0])]))

    description = [f"Season {season_number} · Series record this week: **{series_w}-{series_l}**"]
    if as_utc(week.end) > now_utc():
        description.append(f"⏳ This week isn't over yet (ends {fmt_datetime(week.end)}).")
    if missing:
        description.append(f"⚠️ Missing results: {', '.join(missing)}")
    elif series:
        description.append("All results are in.")
    if not series:
        description.append("No Flames matches found this week (bye week?).")

    return embed_replies(
        f"🔥 Flames — Match {week.number} Results",
        sections,
        description,
        footer="Score = games won-lost · Reports from evidence.mlesports.gg",
    )


async def build(week: int, season: int | None = None) -> list[Reply]:
    def work():
        with db.session() as sess:
            info = resolve_season(sess, season)
            match_week = resolve_week(sess, info, week)
            return info, match_week, load_week_series(sess, match_week.id)

    info, match_week, series = await asyncio.to_thread(work)
    link_status = await evidence.check_links([s.sprocket_match_id for s in series if s.sprocket_match_id])
    return render(info.number, match_week, series, link_status)
