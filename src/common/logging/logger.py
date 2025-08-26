import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Optional

import structlog


class CustomLogger:
    """
    Production-grade structured JSON logger using structlog + rotating file handler.
    """

    _configured = False

    def __init__(
        self,
        log_dir: str = "logs",
        log_level: int = logging.INFO,
        max_bytes: int = 10_000_000,
        backup_count: int = 5
    ):
        self.logs_dir = os.path.join(os.getcwd(), log_dir)
        os.makedirs(self.logs_dir, exist_ok=True)

        # Daily log file with rotation
        log_file = os.path.join(self.logs_dir, f"{datetime.now().strftime('%Y%m%d')}.log")
        self.log_file_path = log_file
        self.log_level = log_level
        self.max_bytes = max_bytes
        self.backup_count = backup_count

        if not CustomLogger._configured:
            self._configure_structlog()
            CustomLogger._configured = True

    def _configure_structlog(self):
        """Configure structlog processors, logging formatters, and file handlers."""

        # Pre-chain processors (metadata enrichment)
        pre_chain = [
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,  # structured exc_info
            structlog.processors.CallsiteParameterAdder(
                parameters=[
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                    structlog.processors.CallsiteParameter.LINENO,
                ]
            ),
        ]

        # Configure stdlib logging (console + rotating file)
        logging.basicConfig(
            level=self.log_level,
            format="%(message)s",
            handlers=[
                logging.StreamHandler(sys.stdout),
                RotatingFileHandler(
                    self.log_file_path,
                    maxBytes=self.max_bytes,
                    backupCount=self.backup_count,
                    encoding="utf-8"
                ),
            ]
        )

        # Configure structlog for JSON output
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                *pre_chain,
                structlog.processors.JSONRenderer(sort_keys=True)  # stable JSON logs
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

    def get_logger(self, name: Optional[str] = None) -> structlog.BoundLogger:
        """Return a structured JSON logger with full module path."""
        if name is None:
            name = __name__
        return structlog.get_logger(name)


# Global logger instance (safe for app-wide imports)
logger = CustomLogger().get_logger(__name__)


# --- Example usage ---
if __name__ == "__main__":
    logger = CustomLogger().get_logger(__name__)

    logger.info("Application started", service="document-portal", version="1.0.0")
    logger.warning("High memory usage", memory="512MB", user="test-user")

    try:
        1 / 0
    except Exception:
        logger.exception("Unhandled exception", request_id="abc-123")
