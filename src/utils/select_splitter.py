# src/utils/select_splitter.py

from typing import List, Dict, Any
from langchain_core.documents import Document
from langchain.text_splitter import (
    RecursiveCharacterTextSplitter,
    CharacterTextSplitter,
    TokenTextSplitter,
    MarkdownTextSplitter,
)
from src.configuration.config_loader import config
from src.common.logging.logger import logger
from src.common.exception.custom_exception import CustomException
import inspect


class ChunkingUtility:
    """Config-driven universal document chunker."""

    SPLITTER_MAP = {
        "recursive_character": RecursiveCharacterTextSplitter,
        "character": CharacterTextSplitter,
        "token": TokenTextSplitter,
        "markdown": MarkdownTextSplitter,
    }

    def __init__(self, strategy: str | None = None):
        try:
            self.strategy = strategy or config.get("splitting_configs.default_strategy")
            self.cfg: Dict[str, Any] = config.get_splitter_config(self.strategy) or {}

            # Ensure safe separators
            if "separators" in self.cfg and "" in self.cfg["separators"]:
                self.cfg["separators"] = [s for s in self.cfg["separators"] if s != ""]

            # Reduce chunk size if needed
            if "chunk_size" in self.cfg and self.cfg["chunk_size"] > 1024:
                self.cfg["chunk_size"] = 1024

            splitter_cls = self.SPLITTER_MAP.get(self.strategy)
            self.splitter = splitter_cls(**self._filter_params(splitter_cls, self.cfg))

            logger.info(f"ChunkingUtility initialized. strategy={self.strategy}, cfg={self.cfg}")

        except Exception as e:
            raise CustomException("Failed to initialize ChunkingUtility", e)

    def _filter_params(self, splitter_cls, cfg: Dict[str, Any]) -> Dict[str, Any]:
        """Filter config to only include params accepted by the splitter class."""
        valid_params = inspect.signature(splitter_cls).parameters
        return {k: v for k, v in cfg.items() if k in valid_params}

    def chunk_documents(self, documents: List[Document]) -> List[Document]:
        """Split documents into chunks using the configured splitter."""
        try:
            if not documents:
                logger.info("No documents to chunk (0).")
                return []

            chunks = self.splitter.split_documents(documents)
            for i, chunk in enumerate(chunks):
                chunk.metadata = {**chunk.metadata, "chunk_id": i, "chunk_strategy": self.strategy}

            logger.info(f"Chunking complete: {len(chunks)} chunks from {len(documents)} docs")
            return chunks

        except Exception as e:
            raise CustomException("Failed during document chunking", e)
