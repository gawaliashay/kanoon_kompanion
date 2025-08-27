import os
import re
import yaml
import importlib
from pathlib import Path
from typing import Dict, Any, List
from dotenv import load_dotenv
from src.configuration.prompts_loader import PromptsLoader
from src.common.logging.logger import logger
from src.common.exception.custom_exception import CustomException


class ConfigLoader:
    """Unified configuration loader:
    - Loads .env variables
    - Resolves imports dynamically
    - Validates structure
    - Provides easy config + prompt access
    """

    def __init__(
        self,
        env_path: str = ".env",
        config_path: str = "src/configuration/config.yaml",
        prompts_path: str = "src/configuration/prompts.yaml"
    ):
        self.env_path = Path(env_path)
        self.config_path = Path(config_path)
        self.prompts_loader = PromptsLoader(prompts_path)
        self.config: Dict[str, Any] = {}

        try:
            self._load_env()
            self._load_config()
            self._validate_config()
        except Exception as e:
            logger.error(f"ConfigLoader initialization failed: {e}")
            raise CustomException("ConfigLoader initialization failed", e)

    # --------------------------
    # Environment
    # --------------------------
    def _load_env(self):
        try:
            if self.env_path.exists():
                load_dotenv(self.env_path)
                logger.info(f".env loaded from {self.env_path}")
            else:
                logger.warning(f".env not found at {self.env_path}, using system env vars")
        except Exception as e:
            logger.error(f"Failed to load environment variables: {e}")
            raise CustomException("Failed to load environment variables", e)

    def _resolve_env_vars(self, obj):
        """Recursively resolve ${VAR} placeholders with environment variables."""
        try:
            if isinstance(obj, dict):
                return {k: self._resolve_env_vars(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [self._resolve_env_vars(v) for v in obj]
            if isinstance(obj, str):
                matches = re.findall(r"\$\{([^}]+)\}", obj)
                for env_var in matches:
                    value = os.getenv(env_var)
                    if value is None:
                        raise ValueError(f"Environment variable {env_var} is not set")
                    obj = obj.replace(f"${{{env_var}}}", value)
            return obj
        except Exception as e:
            logger.error(f"Error resolving environment variables: {e}")
            raise CustomException("Failed to resolve env vars", e)

    # --------------------------
    # Dynamic Imports
    # --------------------------
    def _resolve_imports(self, obj):
        """Recursively import modules specified in config (via import_path)."""
        try:
            if isinstance(obj, dict):
                if "import_path" in obj and "class" not in obj:
                    try:
                        module_name, class_name = obj["import_path"].rsplit(".", 1)
                        module = importlib.import_module(module_name)
                        obj["class"] = getattr(module, class_name)
                    except Exception as e:
                        raise ImportError(f"Failed to import {obj['import_path']}: {e}")
                return {k: self._resolve_imports(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [self._resolve_imports(v) for v in obj]
            return obj
        except Exception as e:
            logger.error(f"Error resolving imports: {e}")
            raise CustomException("Failed to resolve imports", e)

    # --------------------------
    # Config Loading
    # --------------------------
    def _load_config(self):
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        try:
            with open(self.config_path, "r") as f:
                raw = yaml.safe_load(f)
            resolved = self._resolve_env_vars(raw)
            self.config = self._resolve_imports(resolved)
            logger.info(f"Config loaded successfully from {self.config_path}")
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            raise CustomException("Failed to load config.yaml", e)

    # --------------------------
    # Validation
    # --------------------------
    def _validate_config(self):
        try:
            for section in ["api_keys", "paths", "models"]:
                if section not in self.config:
                    raise KeyError(f"Missing required config section: {section}")

            llm_name = self.get("defaults.llm")
            embedding_name = self.get("defaults.embedding")

            if not self.get(f"models.llms.{llm_name}"):
                raise ValueError(f"Default LLM '{llm_name}' not found in models.llms")
            if not self.get(f"models.embeddings.{embedding_name}"):
                raise ValueError(f"Default embedding '{embedding_name}' not found in models.embeddings")

            vs_name = self.get("vectorstores.default")
            if not self.get(f"vectorstores.{vs_name}"):
                raise ValueError(f"Default vectorstore '{vs_name}' not found in vectorstores")

            logger.info("Config validation passed")
        except Exception as e:
            logger.error(f"Config validation failed: {e}")
            raise CustomException("Config validation failed", e)

    # --------------------------
    # Config Accessors
    # --------------------------
    def get(self, key: str, default: Any = None):
        try:
            parts = key.split(".")
            val = self.config
            for p in parts:
                val = val[p]
            return val
        except (KeyError, TypeError):
            return default

    def get_llm_config(self, name: str = None) -> Dict[str, Any]:
        return self.get(f"models.llms.{name or self.get('defaults.llm')}", {})

    def get_embedding_config(self, name: str = None) -> Dict[str, Any]:
        return self.get(f"models.embeddings.{name or self.get('defaults.embedding')}", {})

    def get_preprocessing_config(self) -> Dict[str, Any]:
        return self.get("preprocessing", {})

    def get_supported_exts(self) -> List[str]:
        return self.get("preprocessing.supported_exts", [])

    def get_loader_map(self) -> Dict[str, str]:
        return self.get("preprocessing.loader_map", {})

    def get_document_comparison_strategies(self) -> List[str]:
        steps = self.get("document_comparison.steps", {})
        return [k for k, v in steps.items() if v]

    def get_splitter_config(self, strategy: str = None) -> Dict[str, Any]:
        return self.get(f"splitting_configs.{strategy or self.get('splitting_configs.default_strategy')}", {})

    def get_vectorstore_config(self, name: str = None) -> Dict[str, Any]:
        return self.get(f"vectorstores.{name or self.get('vectorstores.default')}", {})

    def get_comparison_paths(self) -> Dict[str, str]:
        return {
            "dir_a": self.get("paths.comparison_dir_a", "data/comparison/set_a"),
            "dir_b": self.get("paths.comparison_dir_b", "data/comparison/set_b"),
        }

    # --------------------------
    # Prompt Accessors
    # --------------------------
    def get_analysis_prompt(self, step: str | None = None):
        try:
            prompts = self.prompts_loader.prompts.get("document_analysis", {})
            return prompts.get(step) if step else prompts
        except Exception as e:
            logger.error(f"Error fetching analysis prompt [{step}]: {e}")
            raise CustomException(f"Error fetching analysis prompt [{step}]", e)

    def get_comparison_prompt(self, name: str = None) -> Dict[str, Any]:
        return self.prompts_loader.get_comparison_prompt(
            name or self.get("document_comparison.default_prompt", "compare_docs")
        )

    def reload_prompts(self, new_prompts_path: str = None):
        try:
            self.prompts_loader.reload(new_prompts_path)
        except Exception as e:
            logger.error(f"Error reloading prompts: {e}")
            raise


# Instantiate at import
config = ConfigLoader()
