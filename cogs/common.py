"""Helpers shared by cogs: sending replies and the admin check."""
import re

import discord
from discord.ext import commands

import config
from flamesbot.messages import Reply

NO_MENTIONS = discord.AllowedMentions.none()


# :Name: not already inside <:Name:id>.
_EMOJI_NAME = re.compile(r"(?<![<\w]):(\w{2,32}):(?!\d)")


def resolve_emojis(ctx: commands.Context, text: str | None) -> str | None:
    """Swap :Name: for this server's custom emoji of that name (any server the bot is in as fallback)."""
    if not text:
        return text
    by_name = {e.name: e for e in ctx.bot.emojis}
    if ctx.guild:
        by_name.update({e.name: e for e in ctx.guild.emojis})
    return _EMOJI_NAME.sub(lambda m: str(by_name[m[1]]) if m[1] in by_name else m[0], text)


def _resolve_embed(ctx: commands.Context, embed: discord.Embed | None) -> discord.Embed | None:
    if embed is None:
        return None
    embed.description = resolve_emojis(ctx, embed.description)
    for i, f in enumerate(embed.fields):
        embed.set_field_at(i, name=resolve_emojis(ctx, f.name), value=resolve_emojis(ctx, f.value),
                           inline=f.inline)
    return embed


async def send_replies(ctx: commands.Context, replies: list[Reply]) -> None:
    for r in replies:
        await ctx.send(content=resolve_emojis(ctx, r.content), embed=_resolve_embed(ctx, r.embed),
                       allowed_mentions=NO_MENTIONS)


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
