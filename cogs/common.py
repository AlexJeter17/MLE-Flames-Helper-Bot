"""Helpers shared by cogs: sending replies and the admin check."""
import discord
from discord.ext import commands

import config
from flamesbot.messages import Reply

NO_MENTIONS = discord.AllowedMentions.none()


async def send_replies(ctx: commands.Context, replies: list[Reply]) -> None:
    for r in replies:
        await ctx.send(content=r.content, embed=r.embed, allowed_mentions=NO_MENTIONS)


class NotAdmin(commands.CheckFailure):
    pass


def is_admin(ctx: commands.Context) -> bool:
    if ctx.author.id in config.ADMIN_USER_IDS:
        return True
    if ctx.guild is None or not isinstance(ctx.author, discord.Member):
        return False
    if ctx.author.guild_permissions.administrator:
        return True
    return any(role.id in config.ADMIN_ROLE_IDS for role in ctx.author.roles)


async def admin_only(ctx: commands.Context) -> bool:
    """Global check: every command except help is admin-only."""
    if ctx.command and ctx.command.name == "help":
        return True
    if not is_admin(ctx):
        raise NotAdmin("Only server admins can use this command.")
    return True
