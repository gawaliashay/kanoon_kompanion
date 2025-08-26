import sys
import traceback
from typing import Optional, Any, Dict
from src.common.logging.logger import logger


class CustomException(Exception):
    """
    A structured, production-grade custom exception class.
    Logs enriched error details, context, and traceback information.
    """

    def __init__(
        self,
        error_message: str,
        error_details: Optional[Any] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        # Normalize message
        self.error_message = str(error_message)

        # Resolve exc_info (prefer provided details, else sys.exc_info())
        exc_type, exc_value, exc_tb = self._get_exception_info(error_details)

        # Extract error location (file + line)
        self.file_name, self.lineno = self._get_error_location(exc_tb)
        self.context = context or {}

        # Structured traceback (list instead of raw multiline string)
        if exc_type and exc_tb:
            self.traceback_list = traceback.format_exception(exc_type, exc_value, exc_tb)
        else:
            self.traceback_list = []

        # Log immediately on creation
        self._log_exception()

        super().__init__(self.__str__())

    def _get_exception_info(self, error_details: Optional[Any]):
        """Extract exception info from error_details or fallback to sys.exc_info()."""
        if error_details is None:
            return sys.exc_info()
        elif isinstance(error_details, BaseException):
            return type(error_details), error_details, error_details.__traceback__
        return sys.exc_info()

    def _get_error_location(self, exc_tb):
        """Find the most relevant traceback location."""
        if not exc_tb:
            return "<unknown>", -1

        last_tb = exc_tb
        while last_tb and last_tb.tb_next:
            last_tb = last_tb.tb_next

        return (
            last_tb.tb_frame.f_code.co_filename if last_tb else "<unknown>",
            last_tb.tb_lineno if last_tb else -1
        )

    def _log_exception(self):
        """Log the exception with structured context."""
        log_context = {
            "file": self.file_name,
            "line": self.lineno,
            "error_message": self.error_message,
            "traceback": self.traceback_list,
            **self.context
        }

        logger.error("CustomException occurred", **log_context)

    def __str__(self):
        return f"Error in [{self.file_name}] at line [{self.lineno}] | Message: {self.error_message}"

    def __repr__(self):
        return (
            f"CustomException(file={self.file_name!r}, "
            f"line={self.lineno}, message={self.error_message!r})"
        )


# --- Example usage ---
if __name__ == "__main__":
    try:
        a = 1 / 0
    except Exception as e:
        raise CustomException(
            "Division failed",
            e,
            {"operation": "division", "dividend": 1, "divisor": 0}
        )

    try:
        file_path = "nonexistent.txt"
        open(file_path)
    except Exception as e:
        raise CustomException(
            "File operation failed",
            e,
            {"file_path": file_path, "user_id": 123, "action": "file_open"}
        )
