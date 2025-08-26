# src/utils/common_utils.py

import os
import time
import functools
from typing import Callable

from src.common.logging.logger import logger
from src.common.exception.custom_exception import CustomException


def timed(func: Callable) -> Callable:
    """Decorator to measure execution time of a function and log it."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            elapsed = round(time.time() - start_time, 3)
            logger.info(f"Function {func.__name__} executed", extra={"elapsed": elapsed})
            return result
        except Exception as e:
            raise CustomException(f"Error in timed function {func.__name__}", e) from e
    return wrapper


def ensure_dir(path: str) -> str:
    try:
        os.makedirs(path, exist_ok=True)
        return path
    except Exception as e:
        raise CustomException(f"Failed to create directory {path}", e)
