"""fb.help (replaces discord.py's default help command)."""
from discord.ext import commands

from cogs.common import send_replies
from flamesbot.features import help as help_feature


class Help(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="help", aliases=["commands"])
    async def help_cmd(self, ctx: commands.Context, *_):
        await send_replies(ctx, help_feature.build())


async def setup(bot: commands.Bot):
    await bot.add_cog(Help(bot))
