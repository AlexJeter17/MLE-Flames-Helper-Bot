"""fb.eligibilty: scrim-point eligibility for every Flames player.

Points come from mledb.eligibility_data (created_at is UTC). Matching MLEDB's
EligibilityService, a scrim counts until the Monday after its 30th day, so:
  * current points  = points earned after (this Monday 00:00 - 30 days)
  * Monday points   = the same window, but only points earned by Monday 00:00
A player who had 30+ on Monday is good for the rest of the week.
"""
import asyncio
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

import config
from flamesbot import db, leagues
from flamesbot.messages import Reply, embed_replies
from flamesbot.timeutil import fmt_date, local_to_utc, now_utc, week_monday

ELIGIBLE = "✅"
ELIGIBLE_NEXT_WEEK = "🔜"
CLOSE = "🟡"
FAR = "🔴"


@dataclass
class PlayerEligibility:
    name: str
    league: str
    current_points: int
    monday_points: int

    @property
    def marker(self) -> str:
        if self.monday_points >= config.SCRIM_POINTS_REQUIRED:
            return ELIGIBLE
        if self.current_points >= config.SCRIM_POINTS_REQUIRED:
            return ELIGIBLE_NEXT_WEEK
        if self.current_points >= config.SCRIM_POINTS_YELLOW:
            return CLOSE
        return FAR


def load(sess: db.ReadOnlySession, monday: date) -> list[PlayerEligibility]:
    cutoff = local_to_utc(monday, time(0), config.ELIGIBILITY_TZ)
    window_start = cutoff - timedelta(days=config.ELIGIBILITY_WINDOW_DAYS)
    rows = sess.fetch_all(
        """
        SELECT p.name, p.league,
               COALESCE(SUM(e.scrim_points), 0) AS current_points,
               COALESCE(SUM(e.scrim_points) FILTER (WHERE e.created_at <= %(cutoff)s), 0) AS monday_points
        FROM mledb.player p
        LEFT JOIN mledb.eligibility_data e
               ON e.player_id = p.id AND e.created_at > %(window_start)s
        WHERE p.team_name = %(team)s
          -- role NONE = no roster slot (non-playing staff, e.g. the FM): not shown
          AND COALESCE(p.role, 'NONE') <> 'NONE'
        GROUP BY p.id, p.name, p.league
        """,
        {
            # created_at is "timestamp without time zone" holding UTC.
            "cutoff": cutoff.replace(tzinfo=None),
            "window_start": window_start.replace(tzinfo=None),
            "team": config.TEAM_NAME,
        },
    )
    return [
        PlayerEligibility(r["name"], r["league"], int(r["current_points"]), int(r["monday_points"]))
        for r in rows
    ]


def render(players: list[PlayerEligibility], monday: date) -> list[Reply]:
    by_league: dict[str, list[PlayerEligibility]] = {}
    for p in players:
        by_league.setdefault((p.league or "UNKNOWN").upper(), []).append(p)

    def line(p: PlayerEligibility) -> str:
        text = f"{p.marker} **{p.name}** — {p.current_points} pts"
        if p.marker == ELIGIBLE_NEXT_WEEK:
            text += f" (had {p.monday_points} on Monday)"
        return text

    league_keys = list(leagues.LEAGUE_ORDER) + sorted(k for k in by_league if k not in leagues.LEAGUE_ORDER)
    sections = []
    for key in league_keys:
        roster = sorted(by_league.get(key, []), key=lambda p: (-p.current_points, p.name.lower()))
        title = f"{leagues.name(key)} ({leagues.code(key)})"
        sections.append((title, [line(p) for p in roster] or ["_No Flames players_"]))

    eligible = sum(p.marker == ELIGIBLE for p in players)
    tz_name = "Mon 00:00 " + datetime.combine(monday, time(0), tzinfo=config.ELIGIBILITY_TZ).tzname()
    description = [
        f"Week of **{fmt_date(monday)}** · {eligible}/{len(players)} eligible this week",
        "",
        f"{ELIGIBLE} eligible as of Monday (good all week)",
        f"{ELIGIBLE_NEXT_WEEK} {config.SCRIM_POINTS_REQUIRED}+ now, but not on Monday (eligible next Monday)",
        f"{CLOSE} not eligible, {config.SCRIM_POINTS_YELLOW}–{config.SCRIM_POINTS_REQUIRED - 1} pts",
        f"{FAR} not eligible, under {config.SCRIM_POINTS_YELLOW} pts",
    ]
    footer = (
        f"{config.SCRIM_POINTS_REQUIRED} pts needed · points count for "
        f"{config.ELIGIBILITY_WINDOW_DAYS} days, expiring on Mondays · Monday cutoff {tz_name}"
    )
    return embed_replies("🔥 Flames Scrim Eligibility", sections, description, footer)


async def build() -> list[Reply]:
    monday = week_monday(now_utc(), config.ELIGIBILITY_TZ)

    def work():
        with db.session() as sess:
            return load(sess, monday)

    players = await asyncio.to_thread(work)
    return render(players, monday)
