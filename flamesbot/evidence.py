"""Evidence report links: https://evidence.mlesports.gg/matchups/<sprocket match id>/

Links are checked with concurrent HEAD requests under a hard overall timeout, so a
slow or down site never blocks a command; unchecked links are shown as unverified.
"""
import asyncio
import logging

import aiohttp

import config

log = logging.getLogger(__name__)

FOUND = "found"
NOT_FOUND = "not_found"
UNVERIFIED = "unverified"


def url_for(match_id: int) -> str:
    return config.EVIDENCE_URL_TEMPLATE.format(match_id=match_id)


async def _check(session: aiohttp.ClientSession, match_id: int) -> str:
    try:
        async with session.head(url_for(match_id), allow_redirects=True) as resp:
            if resp.status == 200:
                return FOUND
            if resp.status == 404:
                return NOT_FOUND
            return UNVERIFIED
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        log.info("Evidence check failed for %s: %s", match_id, type(e).__name__)
        return UNVERIFIED


async def check_links(match_ids: list[int]) -> dict[int, str]:
    ids = sorted(set(match_ids))
    if not ids:
        return {}
    timeout = aiohttp.ClientTimeout(total=config.EVIDENCE_CHECK_TIMEOUT)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            results = await asyncio.wait_for(
                asyncio.gather(*(_check(session, i) for i in ids)),
                timeout=config.EVIDENCE_CHECK_TIMEOUT + 2,
            )
        return dict(zip(ids, results))
    except Exception:  # never let link checking break a command
        log.warning("Evidence link check gave up", exc_info=True)
        return {i: UNVERIFIED for i in ids}
