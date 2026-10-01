"""fb.help: every command, its parameters, what it does, and an example."""
from dataclasses import dataclass

from flamesbot.messages import Reply, embed_replies


@dataclass
class CommandDoc:
    usage: str
    summary: str
    example: str
    aliases: str = ""
    admin_only: bool = True


COMMANDS = [
    CommandDoc(
        usage="fb.eligibilty",
        aliases="fb.eligibility",
        summary=(
            "Scrim-point eligibility for every rostered Flames player (non-playing staff hidden), grouped ML → CL → AL → FL. "
            "Shows current scrim points and a marker: ✅ eligible as of this Monday (good all week), "
            "🔜 has 30+ now but wasn't eligible Monday, 🟡 15–29 pts, 🔴 under 15 pts."
        ),
        example="fb.eligibilty",
    ),
    CommandDoc(
        usage="fb.salUpdate",
        summary=(
            "Salary changes between the last two Monday snapshots: old → new salary and the +/- difference. "
            "Flags Promotions/Demotions when the league changed, and lists players who joined or left. "
            "Saves this week's snapshot first if it doesn't exist yet (snapshots are also taken automatically every Monday)."
        ),
        example="fb.salUpdate",
    ),
    CommandDoc(
        usage="fb.Matches <weekNum> [season]",
        summary=(
            "When each Flames league plays in that Match week, in Pacific time "
            "(2s and 3s times per league). `weekNum` is the MLE Match number. "
            "`season` is optional (e.g. `s19`); defaults to the current season."
        ),
        example="fb.Matches 3",
    ),
    CommandDoc(
        usage="fb.WeekResults <weekNum> [season]",
        summary=(
            "Results for that Match week by league (ML, CL, AL, FL): Doubles and Standard score, "
            "W/L, opponent and Evidence report link. Lists any results not in yet. "
            "Best run on Monday after all matches are played."
        ),
        example="fb.WeekResults 3",
    ),
    CommandDoc(
        usage="fb.help",
        summary="Shows this list.",
        example="fb.help",
        admin_only=False,
    ),
]


def build() -> list[Reply]:
    sections = []
    for c in COMMANDS:
        lines = [c.summary]
        if c.aliases:
            lines.append(f"**Also:** `{c.aliases}`")
        lines.append(f"**Example:** `{c.example}`")
        name = f"{c.usage}" + (" · admins only" if c.admin_only else "")
        sections.append((name, lines))
    description = [
        "Commands start with `fb.` and aren't case-sensitive (`fb.matches 3` works too).",
        "`<…>` = required, `[…]` = optional.",
    ]
    return embed_replies("🔥 Flames Helper Bot — Commands", sections, description)
