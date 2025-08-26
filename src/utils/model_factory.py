# src/utilities/model_factory.py

import importlib
from typing import Any
from src.common.logging.logger import logger
from src.common.exception.custom_exception import CustomException
from src.configuration.config_loader import config
from src.utils.common_utils import timed


class LLMFactory:
    """Factory to dynamically load LLMs and Embeddings using config.yaml."""

    def __init__(self, config_loader=config):
        self.config = config_loader

    @timed
    def load_llm(self, name: str = None) -> Any:
        try:
            llm_cfg = self.config.get_llm_config(name)
            cls = llm_cfg.get("class")
            if cls is None:
                module_path, class_name = llm_cfg["import_path"].rsplit(".", 1)
                module = importlib.import_module(module_path)
                cls = getattr(module, class_name)

            kwargs = {k: v for k, v in llm_cfg.items() if k not in ["import_path", "class"]}
            logger.info(f"Loading LLM {name or self.config.get('defaults.llm')}")
            return cls(**kwargs)
        except Exception as e:
            raise CustomException("Failed to load LLM", e)

    @timed
    def load_embedding(self, name: str = None) -> Any:
        try:
            emb_cfg = self.config.get_embedding_config(name)
            cls = emb_cfg.get("class")
            if cls is None:
                module_path, class_name = emb_cfg["import_path"].rsplit(".", 1)
                module = importlib.import_module(module_path)
                cls = getattr(module, class_name)

            kwargs = {k: v for k, v in emb_cfg.items() if k not in ["import_path", "class"]}
            logger.info(f"Loading Embedding {name or self.config.get('defaults.embedding')}")
            return cls(**kwargs)
        except Exception as e:
            raise CustomException("Failed to load embedding", e)
