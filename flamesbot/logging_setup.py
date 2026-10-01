"""Console + rotating file logging, with secrets redacted from every record."""
import logging
import re
from logging.handlers import RotatingFileHandler

import config

_CRED_IN_URL = re.compile(r"(\w+://)[^/\s@]+@")


class RedactSecrets(logging.Filter):
    def __init__(self):
        super().__init__()
        self._secrets = [s for s in (config.DISCORD_TOKEN, config.DB_CONNSTRING) if s]

    def _clean(self, text: str) -> str:
        for secret in self._secrets:
            text = text.replace(secret, "[REDACTED]")
        return _CRED_IN_URL.sub(r"\1[REDACTED]@", text)

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = self._clean(record.getMessage())
        record.args = None
        if record.exc_info and not record.exc_text:
            record.exc_text = logging.Formatter().formatException(record.exc_info)
        if record.exc_text:
            record.exc_text = self._clean(record.exc_text)
        return True


def setup() -> None:
    config.LOG_DIR.mkdir(exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    redact = RedactSecrets()

    console = logging.StreamHandler()
    file = RotatingFileHandler(config.LOG_DIR / "bot.log", maxBytes=2_000_000, backupCount=5, encoding="utf-8")
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for handler in (console, file):
        handler.setFormatter(fmt)
        handler.addFilter(redact)
        root.addHandler(handler)
