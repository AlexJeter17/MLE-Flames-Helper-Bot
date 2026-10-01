# MLE-Flames-Helper-Bot

Discord helper bot for the MLE Flames franchise. Reads the MLE database
(**read-only**) to report scrim eligibility, weekly salary changes, the match
schedule, and weekly results with Evidence report links.

## Commands

Prefix `fb.`, case-insensitive. All commands except `fb.help` are **admin only**
(Discord *Administrator* permission, or IDs listed in `ADMIN_USER_IDS` / `ADMIN_ROLE_IDS`).

| Command | What it does |
|---|---|
| `fb.eligibilty` (alias `fb.eligibility`) | Every rostered Flames player (non-playing staff hidden) by league (ML, CL, AL, FL) with current scrim points: ✅ eligible as of this Monday, 🔜 30+ now but not on Monday, 🟡 15–29, 🔴 under 15 |
| `fb.salUpdate` | Salary changes between the last two Monday snapshots (old → new, +/-), Promotion/Demotion flags, joins/leaves, plus roster moves since Monday |
| `fb.Matches <weekNum> [season]` | When each league plays (2s and 3s) in that Match week, in Pacific time. Example: `fb.Matches 3` |
| `fb.WeekResults <weekNum> [season]` | Doubles and Standard results per league with Evidence links and missing results. Example: `fb.WeekResults 3` |
| `fb.help` | Command list with examples |

`weekNum` is the MLE **Match number** (Match 1–10), not the calendar week.
`season` is optional (`s19` or `19`) and defaults to `CURRENT_SEASON`.

## Setup

Requires Python 3.11+.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
copy .env.example .env   # then fill in DISCORD_TOKEN and connstring
```

`ca-certificate.crt` (the DigitalOcean CA, same file MLEBB uses) must sit next to
`bot.py`. The DB connection uses `sslmode=verify-ca` with it.

In the Discord Developer Portal, enable **Message Content Intent** (the only
privileged intent the bot uses). Invite it with the `bot` scope and View Channels,
Send Messages, Embed Links, Read Message History.

## Run

```powershell
.venv\Scripts\python bot.py
```

Logs go to the console and `logs/bot.log` (secrets are redacted).

## Test without Discord

`preview.py` runs the same code as the commands against the real DB and prints
what the bot would send, checking Discord's size limits:

```powershell
.venv\Scripts\python preview.py help
.venv\Scripts\python preview.py eligibility
.venv\Scripts\python preview.py salupdate
.venv\Scripts\python preview.py matches 3
.venv\Scripts\python preview.py weekresults 3 s19
.venv\Scripts\python preview.py all
```

`salupdate` saves snapshot files like the real command does. Add `--salary-dir <folder>`
to keep test runs out of `data/salaries/`.

## How it works

- **Database:** PostgreSQL `sprocket_main`, mostly the `mledb` schema. Sprocket
  match IDs for Evidence come via `mledb_bridge.series_to_match_parent` → `sprocket.match`.
  Read-only is enforced three ways: `default_transaction_read_only=on`, a check
  that the session really is read-only, and a guard that only allows a single
  SELECT. All values are bound parameters.
- **Eligibility:** sums `mledb.eligibility_data.scrim_points`. Like MLEDB, points
  count for 30 days and expire on Mondays. "Eligible as of Monday" means 30+
  points in the 30 days before Monday 00:00 (`ELIGIBILITY_TZ`, default Eastern).
  Suspensions and the Premier League exception aren't modeled.
- **Salary snapshots:** `data/salaries/YYYY-MM-DD.json` (that week's Monday),
  taken automatically on Mondays at 00:05 Pacific from `mledb.player`, keyed by
  `mleid`. If a Monday was missed, or there's no previous week on the first run,
  that Monday is rebuilt from `mledb.player_history`. Each file records its `source`.
- **Times:** the DB stores UTC; everything shown is Pacific, DST-aware.
- **Evidence:** `https://evidence.mlesports.gg/matchups/<sprocket match id>/`,
  checked with quick HEAD requests (a few seconds max). Pages that don't exist
  show `Report: not found`. Right now Evidence only hosts recent matches, so S19
  regular-season reports show as not found.

## Configuration

See `config.py` (defaults) and `.env.example` (overrides): `CURRENT_SEASON`,
`EMOJI_ML/CL/AL/FL`, `ADMIN_USER_IDS`, `ADMIN_ROLE_IDS`, `ELIGIBILITY_TZ`,
`EVIDENCE_URL_TEMPLATE`, `TEAM_NAME`.
