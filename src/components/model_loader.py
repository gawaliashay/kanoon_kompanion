# src\components\model_loader.py

import importlib
from typing import Any, Dict
from src.common.logging.logger import logger
from src.common.exception.custom_exception import CustomException
from src.configuration.config_loader import config
from src.utils.common_utils import timed


class ModelFactory:
    """Factory to dynamically load LLMs and Embeddings using config.yaml."""

    def __init__(self, config_loader=config):
        self.config = config_loader

    @timed
    def load_llm(self, name: str = None) -> Any:
        return self._load_model(self.config.get_llm_config(name), "LLM", name)

    @timed
    def load_embedding(self, name: str = None) -> Any:
        return self._load_model(self.config.get_embedding_config(name), "Embedding", name)

    def _load_model(self, cfg: Dict[str, Any], model_type: str, name: str = None) -> Any:
        try:
            cls = cfg.get("class")
            if cls is None:
                module_path, class_name = cfg["import_path"].rsplit(".", 1)
                module = importlib.import_module(module_path)
                cls = getattr(module, class_name)

            kwargs = {k: v for k, v in cfg.items() if k not in ["import_path", "class"]}
            logger.info(f"Loading {model_type} {name or kwargs.get('model_name')}")
            return cls(**kwargs)

        except Exception as e:
            raise CustomException(f"Failed to load {model_type}", e)
