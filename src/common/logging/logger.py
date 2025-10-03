# src\common\logging\logger.py

import os
import sys
import logging
import re
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Optional
import structlog

# NOTE:
# - LOG_CONSOLE_DEV=1 => pretty console renderer (dev)
# - LOG_JSON=0 => disable JSON renderer (not recommended for prod)
LOG_CONSOLE_DEV = os.getenv("LOG_CONSOLE_DEV", "0") == "1"
LOG_JSON = os.getenv("LOG_JSON", "1") != "0"


class SensitiveDataProcessor:
    """Processor to mask sensitive data in logs - shows only keys, not values"""
    
    def __init__(self):
        # Patterns to match sensitive key-value pairs
        self.sensitive_patterns = [
            # API keys in config
            r'api_key[\'"]?\s*:\s*[\'"][^\'"]+[\'"]',
            r'api_key\s*=\s*[^\s,]+',
            # Environment variables
            r'OPENAI_API_KEY=[^\s]+',
            r'MISTRAL_API_KEY=[^\s]+', 
            r'GROQ_API_KEY=[^\s]+',
            r'PINECONE_API_KEY=[^\s]+',
            r'HUGGINGFACEHUB_API_TOKEN=[^\s]+',
            r'GOOGLE_API_KEY=[^\s]+',
            r'S3_BUCKET=[^\s]+',
            # Secret strings in messages
            r'secret[\'"]?\s*:\s*[\'"][^\'"]+[\'"]',
            r'token[\'"]?\s*:\s*[\'"][^\'"]+[\'"]',
            r'password[\'"]?\s*:\s*[\'"][^\'"]+[\'"]',
            r'key[\'"]?\s*:\s*[\'"][^\'"]+[\'"]',
        ]
        
        # Keys to mask in event_dict (structlog context)
        self.sensitive_keys = {
            'api_key', 'api_secret', 'secret', 'token', 'password', 'key',
            'mistral_api_key', 'openai_api_key', 'groq_api_key', 
            'pinecone_api_key', 'huggingfacehub_api_token', 'google_api_key'
        }
    
    def __call__(self, logger, method_name, event_dict):
        # Mask sensitive values in the event message
        if 'event' in event_dict and event_dict['event']:
            event_dict['event'] = self._mask_sensitive_string(str(event_dict['event']))
        
        # Mask sensitive keys in the event_dict context
        for key in list(event_dict.keys()):
            if key in self.sensitive_keys:
                event_dict[key] = '[MASKED]'
            elif isinstance(event_dict[key], str):
                event_dict[key] = self._mask_sensitive_string(event_dict[key])
            elif isinstance(event_dict[key], dict):
                event_dict[key] = self._mask_sensitive_dict(event_dict[key])
        
        return event_dict
    
    def _mask_sensitive_string(self, text):
        """Mask sensitive data in string messages"""
        for pattern in self.sensitive_patterns:
            text = re.sub(pattern, self._mask_replacement, text)
        return text
    
    def _mask_sensitive_dict(self, obj):
        """Recursively mask sensitive data in dictionaries"""
        if not isinstance(obj, dict):
            return obj
            
        masked = {}
        for key, value in obj.items():
            if key in self.sensitive_keys:
                masked[key] = '[MASKED]'
            elif isinstance(value, str):
                masked[key] = self._mask_sensitive_string(value)
            elif isinstance(value, dict):
                masked[key] = self._mask_sensitive_dict(value)
            elif isinstance(value, list):
                masked[key] = [self._mask_sensitive_dict(item) if isinstance(item, dict) 
                              else self._mask_sensitive_string(item) if isinstance(item, str) 
                              else item for item in value]
            else:
                masked[key] = value
        return masked
    
    def _mask_replacement(self, match):
        """Replace sensitive values with masked indicators"""
        matched_text = match.group(0)
        
        # For key=value patterns, keep key but mask value
        if '=' in matched_text:
            key, value = matched_text.split('=', 1)
            # Show that the key exists but mask the value
            return f"{key}=[MASKED]"
        # For key: value patterns in JSON/dict
        elif ':' in matched_text:
            parts = matched_text.split(':', 1)
            if len(parts) == 2:
                return f"{parts[0]}:[MASKED]"
        
        # For other patterns, show key exists but mask everything else
        if any(keyword in matched_text.lower() for keyword in ['api_key', 'secret', 'token', 'password']):
            return re.sub(r'[\'"][^\'"]+[\'"]', "'[MASKED]'", matched_text)
        
        return '[MASKED]'


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

        # ✅ ADD SENSITIVE DATA PROCESSOR HERE
        sensitive_processor = SensitiveDataProcessor()

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
                sensitive_processor,  # ✅ ADDED: Mask sensitive data before rendering
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