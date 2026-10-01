"""Timezone helpers. The DB stores UTC; users see Pacific."""
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import config

UTC = timezone.utc


def now_utc() -> datetime:
    return datetime.now(UTC)


def week_monday(moment: datetime, tz: ZoneInfo) -> date:
    """Date of the Monday starting the week that contains `moment` (in `tz`)."""
    local = moment.astimezone(tz).date()
    return local - timedelta(days=local.weekday())


def local_to_utc(day: date, at: time, tz: ZoneInfo) -> datetime:
    """A wall-clock time on `day` in `tz`, converted to aware UTC (DST-correct)."""
    return datetime.combine(day, at, tzinfo=tz).astimezone(UTC)


def as_utc(dt: datetime) -> datetime:
    """DB timestamps without a zone are UTC; make them aware."""
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


def fmt_day_time(dt: datetime) -> str:
    """'Sunday 9pm' / 'Sunday 9:30pm' in Pacific."""
    local = as_utc(dt).astimezone(config.DISPLAY_TZ)
    hour = local.strftime("%I").lstrip("0")
    minutes = "" if local.minute == 0 else f":{local.minute:02d}"
    return f"{local.strftime('%A')} {hour}{minutes}{local.strftime('%p').lower()}"


def fmt_date(d: date) -> str:
    return f"{d.strftime('%a %b')} {d.day}, {d.year}"


def fmt_datetime(dt: datetime) -> str:
    local = as_utc(dt).astimezone(config.DISPLAY_TZ)
    return f"{fmt_date(local.date())} {fmt_day_time(dt).split(' ', 1)[1]} {local.tzname()}"
