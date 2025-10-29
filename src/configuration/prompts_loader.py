# src/configuration/prompts_loader.py

import yaml
from pathlib import Path
from typing import Dict, Any
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
    def _get_prompt(self, section: str, name: str) -> Dict[str, Any]:
        try:
            return self.prompts.get(section, {}).get(name, {})
        except Exception as e:
            logger.error(f"Error fetching prompt [{section}.{name}]: {e}")
            raise CustomException(f"Error fetching prompt [{section}.{name}]", e)

    def get_analysis_prompt(self, name: str = "summary_map") -> Dict[str, Any]:
        """Fetch a document analysis prompt (map or reduce)."""
        return self._get_prompt("document_analysis", name)

    def get_comparison_prompt(self, name: str = "compare_docs") -> Dict[str, Any]:
        """Fetch a document comparison prompt."""
        return self._get_prompt("document_comparison", name)
    
    def get_qa_chat_prompt(self, name: str = "answer_using_context") -> Dict[str, Any]:
        """Fetch a document QA chat prompt."""
        return self._get_prompt("document_qa_chat", name)


# Instantiate prompts at import
prompts = PromptsLoader()
