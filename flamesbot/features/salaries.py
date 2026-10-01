"""fb.salUpdate + weekly Monday salary snapshots.

One JSON file per week, data/salaries/YYYY-MM-DD.json, named for that week's
Monday (Pacific). Every snapshot represents the Flames roster *as of Monday
SALARY_SNAPSHOT_TIME Pacific*, so weeks compare like-for-like:

  * Taken on that Monday (by the weekly task or fb.salUpdate): read live from
    mledb.player.
  * Taken late, or a missing previous week: rebuilt from mledb.player_history
    (each history row is a player's state after a change), as of that same
    Monday moment. The file records which source was used.

Players are keyed by mleid, which is stable across name changes and is shared by
mledb.player and mledb.player_history.
"""
import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

import config
from flamesbot import db, leagues
from flamesbot.messages import Reply, embed_replies
from flamesbot.timeutil import fmt_date, local_to_utc, now_utc, week_monday

log = logging.getLogger(__name__)

SOURCE_LIVE = "live"
SOURCE_HISTORY = "player_history"

Roster = dict[str, dict]  # mleid -> {"name", "salary", "league"}


# --- snapshot files --------------------------------------------------------

def snapshot_moment(monday: date) -> datetime:
    return local_to_utc(monday, config.SALARY_SNAPSHOT_TIME, config.DISPLAY_TZ)


def _path(monday: date):
    return config.SALARY_DIR / f"{monday.isoformat()}.json"


def snapshot_dates() -> list[date]:
    dates = []
    if config.SALARY_DIR.is_dir():
        for p in config.SALARY_DIR.glob("*.json"):
            try:
                dates.append(date.fromisoformat(p.stem))
            except ValueError:
                log.warning("Ignoring unexpected file in salary dir: %s", p.name)
    return sorted(dates)


def load_snapshot(monday: date) -> dict | None:
    path = _path(monday)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        log.exception("Could not read salary snapshot %s", path.name)
        return None


def save_snapshot(monday: date, roster: Roster, source: str) -> dict:
    snap = {
        "snapshot_date": monday.isoformat(),
        "as_of_utc": snapshot_moment(monday).isoformat(),
        "captured_at_utc": now_utc().isoformat(timespec="seconds"),
        "source": source,
        "team": config.TEAM_NAME,
        "players": roster,
    }
    config.SALARY_DIR.mkdir(parents=True, exist_ok=True)
    tmp = _path(monday).with_suffix(".tmp")
    tmp.write_text(json.dumps(snap, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(_path(monday))
    log.info("Saved salary snapshot %s (%s, %d players)", monday, source, len(roster))
    return snap


# --- DB reads --------------------------------------------------------------

def _rows_to_roster(rows) -> Roster:
    return {
        str(r["mleid"]): {"name": r["name"], "salary": float(r["salary"]), "league": r["league"]}
        for r in rows
    }


def fetch_live_roster(sess: db.ReadOnlySession) -> Roster:
    rows = sess.fetch_all(
        "SELECT mleid, name, salary, league FROM mledb.player WHERE team_name = %(team)s",
        {"team": config.TEAM_NAME},
    )
    return _rows_to_roster(rows)


def fetch_roster_as_of(sess: db.ReadOnlySession, at_utc: datetime) -> Roster:
    """Flames roster as it was at `at_utc`.

    player_history has gaps (some moves, e.g. old releases to FP, never wrote a
    row), so it can't be trusted alone. If a player's row hasn't been touched
    since `at_utc`, the current row *is* their state then; otherwise use their
    latest history row from before `at_utc`.
    """
    rows = sess.fetch_all(
        """
        SELECT p.mleid,
               CASE WHEN p.updated_at <= %(at)s THEN p.name   ELSE h.name   END AS name,
               CASE WHEN p.updated_at <= %(at)s THEN p.salary ELSE h.salary END AS salary,
               CASE WHEN p.updated_at <= %(at)s THEN p.league ELSE h.league END AS league
        FROM mledb.player p
        LEFT JOIN LATERAL (
            SELECT hh.name, hh.salary, hh.league, hh.team_name
            FROM mledb.player_history hh
            WHERE hh.mleid = p.mleid AND hh.timestamp <= %(at)s
            ORDER BY hh.timestamp DESC, hh.history_id DESC
            LIMIT 1
        ) h ON TRUE
        WHERE (p.team_name = %(team)s
               OR p.mleid IN (SELECT mleid FROM mledb.player_history WHERE team_name = %(team)s))
          AND CASE WHEN p.updated_at <= %(at)s THEN p.team_name ELSE h.team_name END = %(team)s
        """,
        {"at": at_utc.replace(tzinfo=None), "team": config.TEAM_NAME},
    )
    return _rows_to_roster(rows)


# --- snapshot policy -------------------------------------------------------

def ensure_snapshot(sess: db.ReadOnlySession, monday: date, now: datetime) -> tuple[dict, bool]:
    """Return (snapshot, newly_created) for the given Monday."""
    existing = load_snapshot(monday)
    if existing:
        return existing, False

    on_time = now.astimezone(config.DISPLAY_TZ).date() == monday
    if on_time:
        return save_snapshot(monday, fetch_live_roster(sess), SOURCE_LIVE), True

    roster = fetch_roster_as_of(sess, snapshot_moment(monday))
    if not roster and monday == week_monday(now, config.DISPLAY_TZ):
        # No usable history for this week; live data is the best we have.
        return save_snapshot(monday, fetch_live_roster(sess), SOURCE_LIVE), True
    return save_snapshot(monday, roster, SOURCE_HISTORY), True


def ensure_current_week(now: datetime | None = None) -> tuple[dict, bool]:
    """Used by the weekly task: make sure this week's snapshot exists."""
    now = now or now_utc()
    with db.session() as sess:
        return ensure_snapshot(sess, week_monday(now, config.DISPLAY_TZ), now)


# --- comparison ------------------------------------------------------------

@dataclass
class SalaryChange:
    name: str
    old_salary: float
    new_salary: float
    old_league: str
    new_league: str

    @property
    def diff(self) -> float:
        return round(self.new_salary - self.old_salary, 2)

    @property
    def move(self) -> str | None:
        if self.old_league == self.new_league:
            return None
        up = leagues.RANK.get(self.new_league, 0) > leagues.RANK.get(self.old_league, 0)
        return "Promotion" if up else "Demotion"


@dataclass
class Comparison:
    changes: list[SalaryChange] = field(default_factory=list)
    joined: list[dict] = field(default_factory=list)
    left: list[dict] = field(default_factory=list)


def compare(old: Roster, new: Roster) -> Comparison:
    result = Comparison()
    for key, n in new.items():
        o = old.get(key)
        if o is None:
            result.joined.append(n)
        elif round(o["salary"], 2) != round(n["salary"], 2):
            result.changes.append(SalaryChange(n["name"], o["salary"], n["salary"], o["league"], n["league"]))
    result.left = [o for key, o in old.items() if key not in new]
    result.changes.sort(key=lambda c: (leagues.sort_key(c.new_league), c.name.lower()))
    for group in (result.joined, result.left):
        group.sort(key=lambda p: (leagues.sort_key(p["league"]), p["name"].lower()))
    return result


# --- command ---------------------------------------------------------------

@dataclass
class SalUpdateResult:
    current_monday: date
    current: dict
    current_created: bool
    previous_monday: date | None
    previous: dict | None
    previous_created: bool
    live: Roster


def load(now: datetime) -> SalUpdateResult:
    monday = week_monday(now, config.DISPLAY_TZ)
    with db.session() as sess:
        current, current_created = ensure_snapshot(sess, monday, now)

        earlier = [d for d in snapshot_dates() if d < monday]
        if earlier:
            prev_monday = earlier[-1]
            previous, previous_created = load_snapshot(prev_monday), False
        else:
            # First run: rebuild last week's baseline from player history so the
            # very first comparison is real instead of empty.
            prev_monday = monday - timedelta(days=7)
            roster = fetch_roster_as_of(sess, snapshot_moment(prev_monday))
            if roster:
                previous, previous_created = save_snapshot(prev_monday, roster, SOURCE_HISTORY), True
            else:
                prev_monday, previous, previous_created = None, None, False

        live = fetch_live_roster(sess)

    return SalUpdateResult(monday, current, current_created, prev_monday, previous, previous_created, live)


def _money(x: float) -> str:
    return f"{x:.1f}"


def _player(p: dict) -> str:
    return f"**{p['name']}** — {leagues.code(p['league'])}, {_money(p['salary'])}"


def render(r: SalUpdateResult) -> list[Reply]:
    notes = []
    if r.current_created:
        how = "from live DB" if r.current["source"] == SOURCE_LIVE else "rebuilt from DB player history (it was missed on Monday)"
        notes.append(f"📸 Saved this week's snapshot ({fmt_date(r.current_monday)}) {how}.")
    if r.previous_created:
        notes.append(f"🗂️ No earlier snapshot existed, so last week's ({fmt_date(r.previous_monday)}) was rebuilt from DB player history.")

    if r.previous is None:
        notes.append("This is the first snapshot, so it's saved as the **baseline**. "
                     "Run `fb.salUpdate` next week to see changes.")
        return embed_replies("💰 Flames Salary Update", [], notes, _footer())

    comparison = compare(r.previous["players"], r.current["players"])
    description = [f"Comparing **{fmt_date(r.previous_monday)}** → **{fmt_date(r.current_monday)}**"]
    if r.previous_monday != r.current_monday - timedelta(days=7):
        description.append(f"⚠️ No snapshot for the weeks in between; this covers {(r.current_monday - r.previous_monday).days // 7} weeks.")
    description += notes

    change_lines = []
    for c in comparison.changes:
        sign = "📈" if c.diff > 0 else "📉"
        text = f"{sign} **{c.name}** {_money(c.old_salary)} → {_money(c.new_salary)} (**{c.diff:+.1f}**)"
        if c.move:
            text += f" · **{c.move}**: {leagues.code(c.old_league)} → {leagues.code(c.new_league)}"
        change_lines.append(text)

    sections = [("Salary changes", change_lines or ["No salary changes this week."])]
    if comparison.joined:
        sections.append(("Joined the Flames", [_player(p) for p in comparison.joined]))
    if comparison.left:
        sections.append(("Left the Flames", [_player(p) for p in comparison.left]))

    since_monday = compare(r.current["players"], r.live)
    mid_week = [f"➕ {_player(p)}" for p in since_monday.joined] + [f"➖ {_player(p)}" for p in since_monday.left]
    if mid_week:
        sections.append(("Roster moves since Monday (in next week's update)", mid_week))

    return embed_replies("💰 Flames Salary Update", sections, description, _footer())


def _footer() -> str:
    return f"Snapshots are taken Mondays {config.SALARY_SNAPSHOT_TIME.strftime('%H:%M')} Pacific"


async def build() -> list[Reply]:
    result = await asyncio.to_thread(load, now_utc())
    return render(result)
