import yaml
from pathlib import Path
from typing import Dict, Any, List
from src.common.logging.logger import logger
from src.common.exception.custom_exception import CustomException


class PromptsLoader:
    """Loader for managing document analysis and comparison prompts."""

    def __init__(self, prompts_path: str = "src/configuration/prompts.yaml"):
        self.prompts_path = Path(prompts_path)
        self.prompts: Dict[str, Any] = {}

        try:
            self._load_prompts()
        except Exception as e:
            logger.error(f"Failed to initialize PromptsLoader: {e}")
            raise CustomException("PromptsLoader initialization failed", e)

    # --------------------------
    # Internal Loader
    # --------------------------
    def _load_prompts(self):
        if not self.prompts_path.exists():
            raise FileNotFoundError(f"Prompts file not found: {self.prompts_path}")

        try:
            with open(self.prompts_path, "r") as f:
                self.prompts = yaml.safe_load(f)
            logger.info(f"Prompts loaded successfully from {self.prompts_path}")
        except Exception as e:
            logger.error(f"Error loading prompts: {e}")
            raise CustomException("Failed to load prompts.yaml", e)

    # --------------------------
    # Accessors
    # --------------------------
    def get_prompt(self, section: str, name: str) -> Dict[str, Any]:
        try:
            return self.prompts.get(section, {}).get(name, {})
        except Exception as e:
            logger.error(f"Error fetching prompt [{section}.{name}]: {e}")
            raise CustomException(f"Error fetching prompt [{section}.{name}]", e)

    def get_analysis_prompt(self, name: str = "summary_map") -> Dict[str, Any]:
        return self.get_prompt("document_analysis", name)

    def get_comparison_prompt(self, name: str = "compare_docs") -> Dict[str, Any]:
        return self.get_prompt("document_comparison", name)

    def get_available_prompts(self, section: str) -> List[str]:
        try:
            return list(self.prompts.get(section, {}).keys())
        except Exception as e:
            logger.error(f"Error listing prompts for section {section}: {e}")
            raise CustomException(f"Error listing prompts for section {section}", e)

    # --------------------------
    # Reload (Hot-swap prompts)
    # --------------------------
    def reload(self, new_prompts_path: str = None):
        try:
            if new_prompts_path:
                self.prompts_path = Path(new_prompts_path)
            self._load_prompts()
            logger.info(f"Prompts reloaded successfully from {self.prompts_path}")
        except Exception as e:
            logger.error(f"Error reloading prompts: {e}")
            raise CustomException("Failed to reload prompts", e)


# Instantiate at import
try:
    prompts = PromptsLoader()
except CustomException:
    prompts = None  # Safe fallback if initialization fails
