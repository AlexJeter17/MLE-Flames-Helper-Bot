"""Bot configuration. Secrets come from .env; everything else has a sensible default here.

Any value can be overridden with an environment variable of the same name in .env.
"""
import os
from datetime import time
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _env_int_list(name: str) -> set[int]:
    raw = os.getenv(name, "")
    return {int(x) for x in raw.replace(" ", "").split(",") if x.isdigit()}


def _env_optional_int(name: str) -> int | None:
    raw = os.getenv(name, "").strip().lower().lstrip("s")
    return int(raw) if raw.isdigit() else None


# --- Secrets (.env only) ---------------------------------------------------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
# Same variable name as MLEBB / MLEDB use.
DB_CONNSTRING = os.getenv("connstring", "")
# DigitalOcean Postgres CA (same file MLEBB uses). Used with sslmode=verify-ca.
DB_SSL_ROOT_CERT = BASE_DIR / os.getenv("DB_SSL_ROOT_CERT", "ca-certificate.crt")
DB_STATEMENT_TIMEOUT_MS = int(os.getenv("DB_STATEMENT_TIMEOUT_MS", "15000"))

# --- Bot -------------------------------------------------------------------
COMMAND_PREFIX = "fb."
TEAM_NAME = os.getenv("TEAM_NAME", "Flames")

# Who may run the admin commands. Anyone with the Discord "Administrator"
# permission in the server is allowed, plus these user / role IDs.
ADMIN_USER_IDS = _env_int_list("ADMIN_USER_IDS")
ADMIN_ROLE_IDS = _env_int_list("ADMIN_ROLE_IDS")

# --- Season / time ---------------------------------------------------------
# Season the bot treats as "current". Unset = latest season that has started.
CURRENT_SEASON = _env_optional_int("CURRENT_SEASON")

# All times shown to users are Pacific (DST handled by zoneinfo).
DISPLAY_TZ = ZoneInfo(os.getenv("DISPLAY_TZ", "America/Los_Angeles"))

# "Eligible as of Monday" = 30+ points in the 30 days before Monday 00:00 in this
# timezone. MLE match weeks start at midnight Eastern, so that's the default.
ELIGIBILITY_TZ = ZoneInfo(os.getenv("ELIGIBILITY_TZ", "America/New_York"))
SCRIM_POINTS_REQUIRED = 30
SCRIM_POINTS_YELLOW = 15
ELIGIBILITY_WINDOW_DAYS = 30

# Number of games in a league-play series (used to flag partial results).
SERIES_GAMES = int(os.getenv("SERIES_GAMES", "5"))

# --- Salary snapshots ------------------------------------------------------
SALARY_DIR = BASE_DIR / "data" / "salaries"
# Weekly snapshot moment: Monday at this time, Pacific.
SALARY_SNAPSHOT_TIME = time(0, 5)

# --- Evidence reports ------------------------------------------------------
# {match_id} is the Sprocket match id (sprocket.match.id).
EVIDENCE_URL_TEMPLATE = os.getenv(
    "EVIDENCE_URL_TEMPLATE", "https://evidence.mlesports.gg/matchups/{match_id}/"
)
EVIDENCE_CHECK_TIMEOUT = float(os.getenv("EVIDENCE_CHECK_TIMEOUT", "4"))

# --- League emojis ---------------------------------------------------------
# Full emoji strings like <:ml:809925633618083870>. Defaults are the MLE main
# server emojis (from sprocket.game_skill_group_profile); they only render if
# the bot is also in that server. Set EMOJI_ML="" in .env to use plain text.
LEAGUE_EMOJIS = {
    "MASTER": os.getenv("EMOJI_ML", "<:ml:809925633618083870>"),
    "CHAMPION": os.getenv("EMOJI_CL", "<:_cl:809925633642725427>"),
    "ACADEMY": os.getenv("EMOJI_AL", "<:al:809925633655570470>"),
    "FOUNDATION": os.getenv("EMOJI_FL", "<:fl:809925633471545364>"),
}

# --- Logging ---------------------------------------------------------------
LOG_DIR = BASE_DIR / "logs"
