import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Optional
import structlog

# NOTE:
# - LOG_CONSOLE_DEV=1 => pretty console renderer (dev)
# - LOG_JSON=0 => disable JSON renderer (not recommended for prod)
LOG_CONSOLE_DEV = os.getenv("LOG_CONSOLE_DEV", "0") == "1"
LOG_JSON = os.getenv("LOG_JSON", "1") != "0"


class CustomLogger:
    """
    Structured JSON logger using structlog + rotating file handler.

    Dev tips:
      - set LOG_CONSOLE_DEV=1 to get pretty console output during development
      - keep LOG_JSON=1 in production so logs are stable JSON
    """

    _configured = False

    def __init__(
        self,
        log_dir: str = "logs",
        log_level: int = logging.INFO,
        max_bytes: int = 10_000_000,
        backup_count: int = 5,
    ):
        self.logs_dir = os.path.join(os.getcwd(), log_dir)
        os.makedirs(self.logs_dir, exist_ok=True)

        self.log_file_path = os.path.join(
            self.logs_dir, f"{datetime.now().strftime('%Y%m%d')}.log"
        )
        self.log_level = log_level
        self.max_bytes = max_bytes
        self.backup_count = backup_count

        if not CustomLogger._configured:
            self._configure_structlog()
            CustomLogger._configured = True

    def _configure_structlog(self):
        """Configure structlog processors, handlers, and formatting."""

        # --- Python logging setup (so logs actually go to file/console) ---
        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level)

        # Avoid duplicate handlers if reconfiguring
        if not root_logger.handlers:
            # File handler
            file_handler = RotatingFileHandler(
                self.log_file_path,
                maxBytes=self.max_bytes,
                backupCount=self.backup_count,
                encoding="utf-8",
            )
            file_handler.setLevel(self.log_level)

            # Console handler
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.log_level)

            # Attach handlers
            root_logger.addHandler(file_handler)
            root_logger.addHandler(console_handler)

        # --- Custom key ordering for JSON logs ---
        def key_order_processor(logger, method_name, event_dict):
            key_order = [
                "timestamp",
                "level",
                "event",
                "error_type",
                "file",
                "function",
                "line",
                "message",
                "context",
                "traceback",
            ]
            ordered = {k: event_dict[k] for k in key_order if k in event_dict}
            ordered.update({k: v for k, v in event_dict.items() if k not in ordered})
            return ordered

        # --- Pre-chain processors ---
        pre_chain = [
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
        ]

        # --- Conditional callsite enrichment ---
        def conditional_callsite(logger, method_name, event_dict):
            if method_name in ["error", "warning"]:
                callsite_adder = structlog.processors.CallsiteParameterAdder(
                    parameters=[
                        structlog.processors.CallsiteParameter.FILENAME,
                        structlog.processors.CallsiteParameter.FUNC_NAME,
                        structlog.processors.CallsiteParameter.LINENO,
                    ]
                )
                event_dict = callsite_adder(logger, method_name, event_dict)

                if "filename" in event_dict:
                    event_dict["file"] = os.path.basename(event_dict["filename"])
                    del event_dict["filename"]
                if "lineno" in event_dict:
                    event_dict["line"] = event_dict["lineno"]
                    del event_dict["lineno"]
                if "func_name" in event_dict:
                    event_dict["function"] = event_dict["func_name"]
                    del event_dict["func_name"]

            return event_dict

        # --- Renderer ---
        if LOG_CONSOLE_DEV and not LOG_JSON:
            renderer = structlog.dev.ConsoleRenderer()
        else:
            renderer = structlog.processors.JSONRenderer(sort_keys=False)

        # --- Structlog config ---
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                *pre_chain,
                structlog.processors.format_exc_info,
                conditional_callsite,
                key_order_processor,
                renderer,
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )


    def get_logger(self, name: Optional[str] = None) -> structlog.BoundLogger:
        return structlog.get_logger(name or __name__)

    @staticmethod
    def log_separator():
        logger = structlog.get_logger("separator")
        logger.info("=" * 80)


# Global logger instance
logger = CustomLogger().get_logger(__name__)
