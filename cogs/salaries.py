"""fb.salUpdate and the automatic Monday salary snapshot."""
import asyncio
import logging

from discord.ext import commands, tasks

import config
from cogs.common import send_replies
from flamesbot.features import salaries
from flamesbot.timeutil import now_utc, week_monday

log = logging.getLogger(__name__)


class Salaries(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.weekly_snapshot.start()

    def cog_unload(self):
        self.weekly_snapshot.cancel()

    # Checked every 15 minutes instead of a fixed wall-clock time so DST changes
    # and bot restarts can't make it skip a Monday.
    @tasks.loop(minutes=15)
    async def weekly_snapshot(self):
        now = now_utc()
        monday = week_monday(now, config.DISPLAY_TZ)
        local_now = now.astimezone(config.DISPLAY_TZ)
        if local_now.date() != monday or local_now.time() < config.SALARY_SNAPSHOT_TIME:
            return
        if salaries.load_snapshot(monday):
            return
        try:
            snap, _ = await asyncio.to_thread(salaries.ensure_current_week, now)
            log.info("Weekly salary snapshot saved for %s (%d players)", monday, len(snap["players"]))
        except Exception:
            log.exception("Weekly salary snapshot failed; will retry in 15 minutes")

    @weekly_snapshot.before_loop
    async def _wait_until_ready(self):
        await self.bot.wait_until_ready()

    @commands.command(name="salupdate")
    async def sal_update_cmd(self, ctx: commands.Context):
        async with ctx.typing():
            replies = await salaries.build()
        await send_replies(ctx, replies)


async def setup(bot: commands.Bot):
    await bot.add_cog(Salaries(bot))
