"""Flames Helper Bot entry point:  python bot.py"""
import logging
import sys

import discord
from discord.ext import commands

import config
from cogs.common import NotAdmin, admin_only
from flamesbot import logging_setup
from flamesbot.messages import UserFacingError

log = logging.getLogger("flamesbot")

COGS = ["cogs.league_info", "cogs.salaries", "cogs.help"]


def get_prefix(bot: commands.Bot, message: discord.Message) -> str:
    """Case-insensitive prefix: fb. / FB. / Fb. all work."""
    start = message.content[: len(config.COMMAND_PREFIX)]
    return start if start.lower() == config.COMMAND_PREFIX else config.COMMAND_PREFIX


class FlamesBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True  # only privileged intent requested
        super().__init__(
            command_prefix=get_prefix,
            case_insensitive=True,
            intents=intents,
            help_command=None,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        self.add_check(admin_only)

    async def setup_hook(self):
        for cog in COGS:
            await self.load_extension(cog)

    async def on_ready(self):
        log.info("Logged in as %s (id %s) in %d server(s)", self.user, self.user.id, len(self.guilds))

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CommandNotFound):
            await ctx.send("I don't know that command. Try `fb.help`.")
            return
        if isinstance(error, NotAdmin):
            await ctx.send(str(error))
            return
        if isinstance(error, commands.UserInputError):
            await ctx.send(f"{error} Try `fb.help` for usage.")
            return

        original = getattr(error, "original", error)
        if isinstance(original, UserFacingError):
            await ctx.send(str(original))
            return

        # Never echo exception text to Discord (it could include connection details).
        log.error("Command %r failed", ctx.message.content, exc_info=original)
        await ctx.send("Something went wrong running that command. The error has been logged.")


def main():
    logging_setup.setup()
    if not config.DISCORD_TOKEN:
        log.error("DISCORD_TOKEN is not set. Copy .env.example to .env and fill it in.")
        sys.exit(1)
    if not config.DB_CONNSTRING:
        log.error("connstring is not set in .env.")
        sys.exit(1)
    try:
        FlamesBot().run(config.DISCORD_TOKEN, log_handler=None)
    except discord.PrivilegedIntentsRequired:
        log.error("Discord rejected the connection: enable 'Message Content Intent' under "
                  "Developer Portal -> your application -> Bot -> Privileged Gateway Intents, then Save.")
        sys.exit(1)
    except discord.LoginFailure:
        log.error("Discord rejected the token. Check DISCORD_TOKEN in .env.")
        sys.exit(1)
    except Exception:
        log.exception("Bot crashed")
        sys.exit(1)
    # run() returns normally on Ctrl+C / console close; make that visible in the log.
    log.info("Bot stopped (Ctrl+C, window closed, or shutdown).")


if __name__ == "__main__":
    main()
