"""Run any command against the real DB and print what the bot would send. No Discord needed.

    python preview.py help
    python preview.py eligibility
    python preview.py salupdate
    python preview.py matches 3 [s19]
    python preview.py weekresults 3 [s19]
    python preview.py all            # every command, using week 1

Every message is also checked against Discord's size limits.
Note: salupdate behaves exactly like the real command, so it saves snapshot
files to data/salaries/ (pass --salary-dir DIR to write somewhere else).
"""
import argparse
import asyncio
import logging
import sys
from pathlib import Path

import config
from flamesbot import logging_setup
from flamesbot.features import eligibility, help as help_feature, matches, results, salaries
from flamesbot.messages import Reply, UserFacingError, limit_problems, render_text
from flamesbot.season import parse_season, parse_week


async def run(command: str, args: list[str]) -> list[Reply]:
    week = args[0] if args else None
    season = args[1] if len(args) > 1 else None
    if command == "help":
        return help_feature.build()
    if command in ("eligibility", "eligibilty"):
        return await eligibility.build()
    if command == "salupdate":
        return await salaries.build()
    if command == "matches":
        return await matches.build(parse_week(week, "Matches"), parse_season(season))
    if command == "weekresults":
        return await results.build(parse_week(week, "WeekResults"), parse_season(season))
    raise SystemExit(f"Unknown command: {command}")


def show(command: str, replies: list[Reply]) -> int:
    print(f"\n========== fb.{command} -> {len(replies)} message(s) ==========")
    problems = 0
    for i, reply in enumerate(replies, 1):
        print(f"\n--- message {i} ---")
        print(render_text(reply))
        for p in limit_problems(reply):
            problems += 1
            print(f"!!! DISCORD LIMIT PROBLEM: {p}")
    return problems


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command")
    parser.add_argument("args", nargs="*")
    parser.add_argument("--salary-dir", type=Path, help="Write salary snapshots here instead of data/salaries")
    opts = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # emoji on Windows consoles

    logging_setup.setup()
    logging.getLogger().setLevel(logging.WARNING)
    if opts.salary_dir:
        config.SALARY_DIR = opts.salary_dir.resolve()

    command = opts.command.lower()
    plan = (
        [("help", []), ("eligibility", []), ("salupdate", []), ("matches", ["1"]), ("weekresults", ["1"])]
        if command == "all" else [(command, opts.args)]
    )
    problems = 0
    for name, args in plan:
        try:
            problems += show(name, await run(name, args))
        except UserFacingError as e:
            print(f"\n========== fb.{name} ==========\n(user-facing message) {e}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
