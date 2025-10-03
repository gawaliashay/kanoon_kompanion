# src/utils/common_utils.py

import os
import time
import functools
from typing import Callable

from src.common.logging.logger import logger
from src.common.exception.custom_exception import CustomException


def ensure_dir(path: str) -> str:
    try:
        os.makedirs(path, exist_ok=True)
        return path
    except Exception as e:
        raise CustomException(f"Failed to create directory {path}", e)
