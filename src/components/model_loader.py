# src\components\model_loader.py

import importlib
import inspect
from typing import Any, Dict
from src.common.logging.logger import logger
from src.common.exception.custom_exception import CustomException
from src.configuration.config_loader import config


# Generic to provider key mapping
GENERIC_TO_PROVIDER = {
    "max_tokens": ["max_tokens", "max_output_tokens", "max_new_tokens"],
    "temperature": ["temperature", "temp"],
    # Add more generic params as needed
}


class ModelFactory:
    """Factory to dynamically load LLMs and Embeddings using config.yaml."""

    def __init__(self, config_loader=config):
        self.config = config_loader

    def load_llm(self, name: str = None) -> Any:
        return self._load_model(self.config.get_llm_config(name), "LLM", name)

    def load_embedding(self, name: str = None) -> Any:
        return self._load_model(self.config.get_embedding_config(name), "Embedding", name)

    def _load_model(self, cfg: Dict[str, Any], model_type: str, name: str = None) -> Any:
        try:
            cls = cfg.get("class")
            if cls is None:
                module_path, class_name = cfg["import_path"].rsplit(".", 1)
                module = importlib.import_module(module_path)
                cls = getattr(module, class_name)

            # Prepare kwargs
            kwargs = {k: v for k, v in cfg.items() if k not in ["import_path", "class"]}

            # Map generic keys to provider-specific keys dynamically
            sig = inspect.signature(cls)
            final_kwargs = {}
            for generic_key, provider_keys in GENERIC_TO_PROVIDER.items():
                if generic_key in kwargs:
                    for pk in provider_keys:
                        if pk in sig.parameters:
                            final_kwargs[pk] = kwargs[generic_key]
                            break
                    kwargs.pop(generic_key)

            # Merge remaining kwargs that are accepted by the constructor
            for k, v in kwargs.items():
                if k in sig.parameters:
                    final_kwargs[k] = v

            logger.info(f"{model_type} config kwargs (mapped): {final_kwargs}")
            return cls(**final_kwargs)

        except Exception as e:
            raise CustomException(f"Failed to load {model_type}", e)
