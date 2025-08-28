import os
import sys
import logging
from typing import Optional, Any, Dict, Tuple
from src.common.logging.logger import logger


class CustomException(Exception):
    """
    Structured custom exception that logs a single, clean JSON entry.
    """

    def __init__(
        self,
        error_message: str,
        error_details: Optional[Any] = None,
        context: Optional[Dict[str, Any]] = None,
        include_traceback: Optional[bool] = None,
        log_level: int = logging.ERROR,
    ):
        self.error_message = str(error_message)
        self.context = context or {}
        self.log_level = log_level

        # Get exception info
        self.exc_type, self.exc_value, self.exc_tb = self._get_exception_info(error_details)
        self.root_cause = self.exc_type.__name__ if self.exc_type else "UnknownError"
        self.cause_message = str(self.exc_value) if self.exc_value else None

        # Get error location
        self.file_name, self.lineno, self.func_name = self._get_error_location(self.exc_tb)

        # Traceback handling
        trace_env = os.getenv("LOG_FULL_TRACEBACK", "0") == "1"
        include_full = include_traceback if include_traceback is not None else trace_env
        self.traceback = self._format_traceback(self.exc_tb) if include_full and self.exc_tb else None

        # Log only once
        self._log_exception()

        super().__init__(self.error_message)

    def _get_exception_info(self, error_details: Optional[Any]) -> Tuple:
        """Return (exc_type, exc_value, exc_tb)."""
        if error_details is None:
            return sys.exc_info()
        if isinstance(error_details, BaseException):
            return type(error_details), error_details, error_details.__traceback__
        if isinstance(error_details, tuple) and len(error_details) == 3:
            return error_details
        return None, None, None

    def _get_error_location(self, exc_tb):
        """Return filename, lineno, func_name for the error location."""
        if not exc_tb:
            # Try to get current frame if no traceback
            try:
                frame = sys._getframe(2)  # Skip exception init frames
                return frame.f_code.co_filename, frame.f_lineno, frame.f_code.co_name
            except:
                return "<unknown>", -1, "<unknown>"
        
        # Get the frame where the error actually occurred
        tb = exc_tb
        while tb.tb_next:
            tb = tb.tb_next
        frame = tb.tb_frame
        return frame.f_code.co_filename, tb.tb_lineno, frame.f_code.co_name

    def _format_traceback(self, exc_tb):
        """Return simplified traceback."""
        frames = []
        tb = exc_tb
        max_frames = 10  # Limit traceback length
        
        while tb and len(frames) < max_frames:
            f = tb.tb_frame
            frames.append({
                "file": os.path.basename(f.f_code.co_filename),  # Just filename, not full path
                "line": tb.tb_lineno,
                "function": f.f_code.co_name
            })
            tb = tb.tb_next
        
        return frames

    def _log_exception(self):
        """Emit a single clean structured log entry."""
        # Base payload - use 'event' for the main message
        payload = {
            'event': self.error_message,
            'error_type': self.root_cause,
            'location': f"{os.path.basename(self.file_name)}:{self.lineno}:{self.func_name}",
        }

        # Add context if available
        if self.context:
            payload.update(self.context)  # Merge context into main payload
        
        # Add cause if different from main message
        if self.cause_message and self.cause_message != self.error_message:
            payload['cause'] = self.cause_message
        
        # Add traceback only if explicitly enabled
        if self.traceback:
            payload['traceback'] = self.traceback

        # Log at appropriate level
        if self.log_level >= logging.ERROR:
            logger.error(**payload)
        elif self.log_level >= logging.WARNING:
            logger.warning(**payload)
        else:
            logger.info(**payload)

    def __str__(self):
        return f"{self.error_message} ({self.root_cause}) at {os.path.basename(self.file_name)}:{self.lineno}"

    def __repr__(self):
        return f"CustomException({self.root_cause}: {self.error_message})"