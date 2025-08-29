# src\configuration\config_loader.py

import os
import re
import yaml
import importlib
from pathlib import Path
from typing import Dict, Any, List
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError
from src.configuration.prompts_loader import PromptsLoader
from src.common.logging.logger import logger
from src.common.exception.custom_exception import CustomException


# --------------------------
# Schema Definitions
# --------------------------

class PathsConfig(BaseModel):
    comparison_dir_a: str = Field(default="data/comparison/set_a")
    comparison_dir_b: str = Field(default="data/comparison/set_b")


class DefaultsConfig(BaseModel):
    llm: str
    embedding: str


class ConfigSchema(BaseModel):
    api_keys: Dict[str, str] = Field(default_factory=dict)
    paths: PathsConfig
    models: Dict[str, Dict[str, Any]]
    defaults: DefaultsConfig
    vectorstores: Dict[str, Any] = Field(default_factory=dict)
    preprocessing: Dict[str, Any] = Field(default_factory=dict)
    splitting_configs: Dict[str, Any] = Field(default_factory=dict)
    document_comparison: Dict[str, Any] = Field(default_factory=dict)
    document_analysis: Dict[str, Any] = Field(default_factory=dict)   # ✅ still needed


# --------------------------
# Config Loader
# --------------------------

class ConfigLoader:
    """Unified configuration loader with schema validation & defaults."""

    def __init__(
        self,
        env_path: str = ".env",
        config_path: str = "src/configuration/config.yaml",
        prompts_path: str = "src/configuration/prompts.yaml"
    ):
        self.env_path = Path(env_path)
        self.config_path = Path(config_path)
        self.prompts_loader = PromptsLoader(prompts_path)
        self.config: ConfigSchema | None = None

        try:
            self._load_env()
            self._load_config()
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
            raise CustomException("Failed to load environment variables", e)

    def _resolve_env_vars(self, obj):
        """Recursively resolve ${VAR} placeholders with environment variables."""
        if isinstance(obj, dict):
            return {k: self._resolve_env_vars(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._resolve_env_vars(v) for v in obj]
        if isinstance(obj, str):
            matches = re.findall(r"\$\{([^}]+)\}", obj)
            for env_var in matches:
                value = os.getenv(env_var)
                if value is None:
                    logger.warning(f"Environment variable {env_var} not set, leaving placeholder")
                else:
                    obj = obj.replace(f"${{{env_var}}}", value)
        return obj

    # --------------------------
    # Dynamic Imports
    # --------------------------
    def _resolve_imports(self, obj):
        """Recursively import modules specified in config (via import_path)."""
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

    # --------------------------
    # Config Loading
    # --------------------------
    def _load_config(self):
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f)

            # Merge env-specific override if exists
            env = os.getenv("ENV", "dev")
            override_path = self.config_path.with_name(f"config.{env}.yaml")
            if override_path.exists():
                with open(override_path, "r", encoding="utf-8") as f:
                    override = yaml.safe_load(f)
                raw = self._merge_dicts(raw, override)

            resolved = self._resolve_env_vars(raw)
            imported = self._resolve_imports(resolved)

            # ✅ Validate against schema
            self.config = ConfigSchema(**imported)
            logger.info(f"Config validated and loaded successfully [{env}]")

        except ValidationError as ve:
            logger.error(f"Schema validation failed: {ve}")
            raise CustomException("Config validation failed", ve)
        except Exception as e:
            raise CustomException("Failed to load config.yaml", e)

    def _merge_dicts(self, base, override):
        """Recursive merge with override priority."""
        for k, v in override.items():
            if isinstance(v, dict) and k in base:
                base[k] = self._merge_dicts(base[k], v)
            else:
                base[k] = v
        return base

    # --------------------------
    # Accessors
    # --------------------------
    def get(self, key: str, default: Any = None):
        try:
            parts = key.split(".")
            val = self.config.dict()
            for p in parts:
                val = val[p]
            return val
        except Exception:
            logger.warning(f"Config key missing: {key}, using default: {default}")
            return default

    def get_llm_config(self, name: str = None) -> Dict[str, Any]:
        return self.get(f"models.llms.{name or self.config.defaults.llm}", {})

    def get_embedding_config(self, name: str = None) -> Dict[str, Any]:
        return self.get(f"models.embeddings.{name or self.config.defaults.embedding}", {})

    def get_supported_exts(self):
        return self.get("preprocessing.supported_exts", [])

    def get_loader_map(self):
        return self.get("preprocessing.loader_map", {})

    def get_splitter_config(self, strategy: str = None):
        return self.get(
            f"splitting_configs.{strategy or self.get('splitting_configs.default_strategy')}", {}
        )

    def get_vectorstore_config(self, name: str = None):
        return self.get(f"vectorstores.{name or self.get('vectorstores.default')}", {})

    def get_comparison_paths(self):
        return {
            "dir_a": self.config.paths.comparison_dir_a,
            "dir_b": self.config.paths.comparison_dir_b,
        }
    
    def get_document_comparison_strategies(self) -> List[str]:
        steps = self.get("document_comparison.steps", {})
        return [k for k, v in steps.items() if v]

    # --------------------------
    # Prompt Accessors
    # --------------------------
    def get_analysis_prompt(self, step: str | None = None):
        """Fetch analysis prompt (summary_map or summary_reduce)."""
        prompts = self.prompts_loader.prompts.get("document_analysis", {})
        return prompts.get(step) if step else prompts

    def get_comparison_prompt(self, name: str = None):
        """Fetch comparison prompt config."""
        return self.prompts_loader.get_comparison_prompt(
            name or self.get("document_comparison.default_prompt", "compare_docs")
        )


# Instantiate at import
config = ConfigLoader()
