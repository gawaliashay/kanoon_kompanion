# src\utilities\rag_utils.py

from typing import List, Any
import importlib
from langchain.text_splitter import (
    RecursiveCharacterTextSplitter,
    CharacterTextSplitter,
    TokenTextSplitter,
    MarkdownTextSplitter
)

from src.common.logging.logger import logger
from src.common.exception.custom_exception import CustomException
from src.configuration.config_loader import ConfigLoader
from src.utils.common_utils import timed


class RAGUtils:
    """Utilities for text splitting, vectorstore loading, and retrieval."""

    def __init__(self, config: ConfigLoader):
        self.config = config

    @timed
    def get_text_splitter(self, strategy: str = None) -> Any:
        try:
            splitter_cfg = self.config.get_splitter_config(strategy)
            strategy = strategy or self.config.get("splitting_configs.default_strategy")

            if strategy == "recursive_character":
                return RecursiveCharacterTextSplitter(**splitter_cfg)
            elif strategy == "character":
                return CharacterTextSplitter(**splitter_cfg)
            elif strategy == "token":
                return TokenTextSplitter(**splitter_cfg)
            elif strategy == "markdown":
                return MarkdownTextSplitter(**splitter_cfg)
            else:
                raise ValueError(f"Unknown text splitter strategy: {strategy}")
        except Exception as e:
            raise CustomException("Failed to initialize text splitter", e)

    @timed
    def build_vectorstore(self, documents: List[Any], embedding: Any, name: str = None) -> Any:
        try:
            vs_cfg = self.config.get_vectorstore_config(name)
            module_path, class_name = vs_cfg["import_path"].rsplit(".", 1)
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)

            kwargs = {k: v for k, v in vs_cfg.items() if k not in ["import_path", "class"]}
            logger.info(f"Building vectorstore {name or self.config.get('vectorstores.default')}")
            return cls.from_documents(documents=documents, embedding=embedding, **kwargs)
        except Exception as e:
            raise CustomException("Failed to build vectorstore", e)

    @timed
    def get_retriever(self, vectorstore: Any) -> Any:
        try:
            retr_cfg = self.config.get("retrieval")
            search_type = retr_cfg.get("search_type", "similarity")
            top_k = retr_cfg.get("similarity_top_k", 5)
            logger.info(f"Creating retriever with search_type={search_type}, top_k={top_k}")
            return vectorstore.as_retriever(search_type=search_type, search_kwargs={"k": top_k})
        except Exception as e:
            raise CustomException("Failed to get retriever", e)

