"""Output containers and Discord-limit-aware splitting.

Commands build a list of Reply objects. The bot sends them; preview.py prints them.
Long output is split across fields/embeds/messages rather than truncated.
"""
from dataclasses import dataclass

import discord

MESSAGE_LIMIT = 2000
EMBED_DESCRIPTION_LIMIT = 4096
FIELD_VALUE_LIMIT = 1024
FIELD_NAME_LIMIT = 256
EMBED_FIELDS_LIMIT = 25
EMBED_TOTAL_LIMIT = 6000
# Leave headroom under the 6000 total for title/footer.
_EMBED_BUDGET = 5500

FLAMES_ORANGE = discord.Color.from_rgb(232, 93, 4)


class UserFacingError(Exception):
    """An error whose message is safe and helpful to show in Discord."""


@dataclass
class Reply:
    content: str | None = None
    embed: discord.Embed | None = None


def chunk_lines(lines: list[str], limit: int) -> list[str]:
    """Join lines into chunks no longer than `limit`, never splitting a line unless it alone is too long."""
    chunks: list[str] = []
    current = ""
    for line in lines:
        while len(line) > limit:  # pathological single line
            if current:
                chunks.append(current)
                current = ""
            chunks.append(line[:limit])
            line = line[limit:]
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) > limit:
            chunks.append(current)
            current = line
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def text_replies(lines: list[str]) -> list[Reply]:
    return [Reply(content=c) for c in chunk_lines(lines, MESSAGE_LIMIT)]


def embed_replies(
    title: str,
    sections: list[tuple[str, list[str]]],
    description_lines: list[str] | None = None,
    footer: str | None = None,
    color: discord.Color = FLAMES_ORANGE,
) -> list[Reply]:
    """Build one or more embeds. Each section becomes one or more fields."""
    description_chunks = chunk_lines(description_lines or [], EMBED_DESCRIPTION_LIMIT)

    fields: list[tuple[str, str]] = []
    for name, lines in sections:
        for i, chunk in enumerate(chunk_lines(lines or ["—"], FIELD_VALUE_LIMIT)):
            field_name = name if i == 0 else f"{name} (cont.)"
            fields.append((field_name[:FIELD_NAME_LIMIT], chunk))

    embeds: list[discord.Embed] = []

    def new_embed(first: bool) -> discord.Embed:
        e = discord.Embed(title=title if first else f"{title} (cont.)", color=color)
        if footer:
            e.set_footer(text=footer)
        embeds.append(e)
        return e

    embed = new_embed(True)
    for i, chunk in enumerate(description_chunks):
        if i > 0:
            embed = new_embed(False)
        embed.description = chunk

    for name, value in fields:
        if len(embed.fields) >= EMBED_FIELDS_LIMIT or len(embed) + len(name) + len(value) > _EMBED_BUDGET:
            embed = new_embed(False)
        embed.add_field(name=name, value=value, inline=False)

    return [Reply(embed=e) for e in embeds]


def render_text(reply: Reply) -> str:
    """Plain-text rendering of a Reply, used by preview.py."""
    parts: list[str] = []
    if reply.content:
        parts.append(reply.content)
    if reply.embed:
        e = reply.embed
        parts.append(f"┏━ [EMBED] {e.title or ''}")
        if e.description:
            parts.extend(f"┃ {line}" for line in e.description.splitlines())
        for f in e.fields:
            parts.append("┃")
            parts.append(f"┃ ▸ {f.name}")
            parts.extend(f"┃   {line}" for line in (f.value or "").splitlines())
        if e.footer and e.footer.text:
            parts.append(f"┗━ {e.footer.text}")
        else:
            parts.append("┗━")
    return "\n".join(parts)


def limit_problems(reply: Reply) -> list[str]:
    """Return any Discord limit violations (should always be empty)."""
    problems = []
    if reply.content and len(reply.content) > MESSAGE_LIMIT:
        problems.append(f"content is {len(reply.content)} chars")
    if reply.embed:
        e = reply.embed
        if len(e) > EMBED_TOTAL_LIMIT:
            problems.append(f"embed total is {len(e)} chars")
        if e.description and len(e.description) > EMBED_DESCRIPTION_LIMIT:
            problems.append("embed description too long")
        if len(e.fields) > EMBED_FIELDS_LIMIT:
            problems.append(f"{len(e.fields)} fields")
        for f in e.fields:
            if len(f.value or "") > FIELD_VALUE_LIMIT:
                problems.append(f"field '{f.name}' is {len(f.value)} chars")
    return problems
