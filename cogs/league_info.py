"""fb.eligibilty, fb.Matches, fb.WeekResults."""
from discord.ext import commands

from cogs.common import send_replies
from flamesbot.features import eligibility, matches, results
from flamesbot.season import parse_season, parse_week


class LeagueInfo(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Name intentionally spelled "eligibilty"; "eligibility" is an alias.
    @commands.command(name="eligibilty", aliases=["eligibility"])
    async def eligibility_cmd(self, ctx: commands.Context):
        async with ctx.typing():
            replies = await eligibility.build()
        await send_replies(ctx, replies)

    @commands.command(name="matches")
    async def matches_cmd(self, ctx: commands.Context, week: str = None, season: str = None):
        week_num, season_num = parse_week(week, "Matches"), parse_season(season)
        async with ctx.typing():
            replies = await matches.build(week_num, season_num)
        await send_replies(ctx, replies)

    @commands.command(name="weekresults")
    async def week_results_cmd(self, ctx: commands.Context, week: str = None, season: str = None):
        week_num, season_num = parse_week(week, "WeekResults"), parse_season(season)
        async with ctx.typing():
            replies = await results.build(week_num, season_num)
        await send_replies(ctx, replies)


async def setup(bot: commands.Bot):
    await bot.add_cog(LeagueInfo(bot))
