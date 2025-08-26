# src/utils/common_utils.py

import os
import json
import time
import functools
from typing import Any, Dict, Callable
from jsonschema import validate, ValidationError

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


def safe_json_dumps(data: Any, indent: int = 2) -> str:
    try:
        return json.dumps(data, indent=indent, default=str)
    except Exception as e:
        raise CustomException("Failed to serialize object to JSON", e)


def ensure_dir(path: str) -> str:
    try:
        os.makedirs(path, exist_ok=True)
        return path
    except Exception as e:
        raise CustomException(f"Failed to create directory {path}", e)


def flatten_dict(d: Dict[str, Any], parent_key: str = "", sep: str = ".") -> Dict[str, Any]:
    try:
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)
    except Exception as e:
        raise CustomException("Failed to flatten dict", e)


def validate_json_schema(data: Dict[str, Any], schema: Dict[str, Any], context: str = "") -> bool:
    try:
        validate(instance=data, schema=schema)
        return True
    except ValidationError as e:
        logger.error(f"JSON validation failed in {context}: {e}")
        return False
