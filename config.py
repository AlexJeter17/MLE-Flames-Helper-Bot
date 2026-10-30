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

# All times shown to users are Eastern (DST handled by zoneinfo).
DISPLAY_TZ = ZoneInfo(os.getenv("DISPLAY_TZ", "America/New_York"))
DISPLAY_TZ_LABEL = os.getenv("DISPLAY_TZ_LABEL", "Eastern")

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
# Weekly snapshot moment: Monday at this time, in SALARY_TZ (Pacific).
SALARY_TZ = ZoneInfo(os.getenv("SALARY_TZ", "America/Los_Angeles"))
SALARY_SNAPSHOT_TIME = time(0, 5)

# --- Evidence reports ------------------------------------------------------
# {match_id} is the Sprocket match id (sprocket.match.id).
EVIDENCE_URL_TEMPLATE = os.getenv(
    "EVIDENCE_URL_TEMPLATE", "https://evidence.mlesports.gg/matchups/{match_id}/"
)
EVIDENCE_CHECK_TIMEOUT = float(os.getenv("EVIDENCE_CHECK_TIMEOUT", "4"))

# --- Emojis ----------------------------------------------------------------
# Written as :Name: and swapped for the server's custom emoji of that name when
# the bot sends (see cogs/common.py). A full <:name:id> string also works.
# Set EMOJI_ML="" in .env to use plain text (**ML**).
LEAGUE_EMOJIS = {
    "MASTER": os.getenv("EMOJI_ML", ":ML:"),
    "CHAMPION": os.getenv("EMOJI_CL", ":CL:"),
    "ACADEMY": os.getenv("EMOJI_AL", ":AL:"),
    "FOUNDATION": os.getenv("EMOJI_FL", ":FL:"),
}
WIN_EMOJI = os.getenv("EMOJI_WIN", ":FlamesDub:")
LOSS_EMOJI = os.getenv("EMOJI_LOSS", ":FeelsFlames:")

# --- Logging ---------------------------------------------------------------
LOG_DIR = BASE_DIR / "logs"
