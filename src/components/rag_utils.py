# src\components\rag_utils.py

from typing import List, Any
import importlib
from src.common.logging.logger import logger
from src.common.exception.custom_exception import CustomException
from src.configuration.config_loader import config
from src.utils.common_utils import timed


class RAGUtils:
    """Utilities for text splitting, vectorstore loading, and retrieval."""

    def __init__(self, config_loader=config):
        self.config = config_loader

    @timed
    def get_text_splitter(self, strategy: str = None) -> Any:
        try:
            strategy = strategy or self.config.get("splitting_configs.default_strategy")
            splitter_cfg = self.config.get_splitter_config(strategy)
            splitter_cls = splitter_cfg["class"]
            kwargs = {k: v for k, v in splitter_cfg.items() if k != "class"}
            return splitter_cls(**kwargs)
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
