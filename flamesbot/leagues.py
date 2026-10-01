"""League ordering, codes and display labels."""
import config

# Display order everywhere: Master, Champion, Academy, Foundation.
LEAGUE_ORDER = ["MASTER", "CHAMPION", "ACADEMY", "FOUNDATION"]

CODES = {
    "PREMIER": "PL",
    "MASTER": "ML",
    "CHAMPION": "CL",
    "ACADEMY": "AL",
    "FOUNDATION": "FL",
}

NAMES = {
    "PREMIER": "Premier League",
    "MASTER": "Master League",
    "CHAMPION": "Champion League",
    "ACADEMY": "Academy League",
    "FOUNDATION": "Foundation League",
}

# Higher = higher league. Used to call a move a promotion or demotion.
RANK = {"FOUNDATION": 1, "ACADEMY": 2, "CHAMPION": 3, "MASTER": 4, "PREMIER": 5}

MODE_SHORT = {"DOUBLES": "2s", "STANDARD": "3s"}
MODE_ORDER = ["DOUBLES", "STANDARD"]


def code(league: str | None) -> str:
    return CODES.get((league or "").upper(), (league or "?").title())


def name(league: str | None) -> str:
    return NAMES.get((league or "").upper(), (league or "Unknown").title())


def label(league: str) -> str:
    """Custom server emoji if configured, otherwise a bold text code like **ML**."""
    emoji = config.LEAGUE_EMOJIS.get(league.upper(), "").strip()
    return emoji or f"**{code(league)}**"


def sort_key(league: str | None) -> int:
    league = (league or "").upper()
    return LEAGUE_ORDER.index(league) if league in LEAGUE_ORDER else len(LEAGUE_ORDER)
