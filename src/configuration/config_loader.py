# src\configuration\config_loader.py


import os
import re
import yaml
import importlib
from typing import Dict, Any, List
from pathlib import Path
from dotenv import load_dotenv


class ConfigLoader:
    """Unified configuration loader with env resolution, dynamic imports, and validation."""

    def __init__(
        self,
        env_path: str = ".env",
        config_path: str = "src/configuration/config.yaml",
        prompts_path: str = "src/configuration/prompts.yaml"
    ):
        self.env_path = Path(env_path)
        self.config_path = Path(config_path)
        self.prompts_path = Path(prompts_path)

        self.config: Dict[str, Any] = {}
        self.prompts: Dict[str, Any] = {}

        self._load_env()
        self._load_config()
        self._load_prompts()
        self._validate_config()

    # --------------------------
    # Env vars
    # --------------------------
    def _load_env(self):
        if self.env_path.exists():
            load_dotenv(self.env_path)
        else:
            print(f"⚠️ Warning: .env file not found at {self.env_path}, using system env vars")

    def _resolve_env_vars(self, obj):
        """Recursively resolve ${VAR} placeholders with environment variables."""
        if isinstance(obj, dict):
            return {k: self._resolve_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._resolve_env_vars(v) for v in obj]
        elif isinstance(obj, str):
            matches = re.findall(r"\$\{([^}]+)\}", obj)
            for env_var in matches:
                value = os.getenv(env_var)
                if value is None:
                    raise ValueError(f"❌ Environment variable {env_var} is not set")
                obj = obj.replace(f"${{{env_var}}}", value)
        return obj

    # --------------------------
    # Import resolver
    # --------------------------
    def _resolve_imports(self, obj):
        """Recursively resolve import_path into actual class objects."""
        if isinstance(obj, dict):
            if "import_path" in obj and "class" not in obj:
                try:
                    module_name, class_name = obj["import_path"].rsplit(".", 1)
                    module = importlib.import_module(module_name)
                    obj["class"] = getattr(module, class_name)
                except Exception as e:
                    raise ImportError(f"❌ Failed to import {obj['import_path']}: {e}")
            return {k: self._resolve_imports(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._resolve_imports(v) for v in obj]
        return obj

    # --------------------------
    # Load YAML
    # --------------------------
    def _load_config(self):
        if not self.config_path.exists():
            raise FileNotFoundError(f"❌ Config file not found: {self.config_path}")
        with open(self.config_path, "r") as f:
            raw = yaml.safe_load(f)
        resolved = self._resolve_env_vars(raw)
        self.config = self._resolve_imports(resolved)

    def _load_prompts(self):
        if not self.prompts_path.exists():
            raise FileNotFoundError(f"❌ Prompts file not found: {self.prompts_path}")
        with open(self.prompts_path, "r") as f:
            self.prompts = yaml.safe_load(f)

    # --------------------------
    # Validation
    # --------------------------
    def _validate_config(self):
        """Run validations to catch misconfigurations early."""
        for section in ["api_keys", "paths", "models"]:
            if section not in self.config:
                raise KeyError(f"❌ Missing required config section: {section}")

        required_envs = re.findall(r"\$\{([^}]+)\}", open(self.config_path).read())
        missing = [var for var in required_envs if os.getenv(var) is None]
        if missing:
            raise EnvironmentError(f"❌ Missing environment variables: {', '.join(missing)}")

        llm_name = self.get("defaults.llm")
        embedding_name = self.get("defaults.embedding")

        if not self.get(f"models.llms.{llm_name}"):
            raise ValueError(f"❌ Default LLM '{llm_name}' not found in models.llms")
        if not self.get(f"models.embeddings.{embedding_name}"):
            raise ValueError(f"❌ Default embedding '{embedding_name}' not found in models.embeddings")

        vs_name = self.get("vectorstores.default")
        if not self.get(f"vectorstores.{vs_name}"):
            raise ValueError(f"❌ Default vectorstore '{vs_name}' not found in vectorstores")

        print("✅ Config validation passed")

    # --------------------------
    # Accessors
    # --------------------------
    def get(self, key: str, default: Any = None):
        parts = key.split(".")
        val = self.config
        try:
            for p in parts:
                val = val[p]
        except (KeyError, TypeError):
            return default
        return val

    def get_llm_config(self, name: str = None) -> Dict[str, Any]:
        name = name or self.get("defaults.llm")
        return self.get(f"models.llms.{name}", {})

    def get_embedding_config(self, name: str = None) -> Dict[str, Any]:
        name = name or self.get("defaults.embedding")
        return self.get(f"models.embeddings.{name}", {})

    def get_preprocessing_config(self) -> Dict[str, Any]:
        return self.get("preprocessing", {})

    def get_supported_exts(self) -> List[str]:
        return self.get("preprocessing.supported_exts", [])

    def get_loader_map(self) -> Dict[str, str]:
        return self.get("preprocessing.loader_map", {})

    def get_document_analysis_prompt(self) -> Dict[str, Any]:
        default_key = self.get("document_analysis.default_prompt", "summary_map")
        return self.prompts.get("document_analysis", {}).get(default_key, {})

    def get_splitter_config(self, strategy: str = None) -> Dict[str, Any]:
        strategy = strategy or self.get("splitting_configs.default_strategy")
        return self.get(f"splitting_configs.{strategy}", {})

    def get_vectorstore_config(self, name: str = None) -> Dict[str, Any]:
        name = name or self.get("vectorstores.default")
        return self.get(f"vectorstores.{name}", {})


# Instantiate at import time
config = ConfigLoader()
