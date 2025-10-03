# src\components\rag_utils.py

from typing import List, Any
import importlib
from src.common.logging.logger import logger
from src.common.exception.custom_exception import CustomException
from src.configuration.config_loader import config


class RAGUtils:
    """Utilities for text splitting, vectorstore loading, and retrieval."""

    def __init__(self, config_loader=config):
        self.config = config_loader  # This is fine - it's actually storing config_loader

    
    def get_text_splitter(self, pipeline_name: str = None) -> Any:
        """
        Returns a text splitter configured per pipeline via config.yaml.
        pipeline_name options: 'document_analysis', 'document_comparison', 'document_qa_chat'
        """
        try:
            # Fetch strategy from config loader
            strategy = self.config.get_pipeline_chunking_strategy(pipeline_name)

            # Fetch splitter config
            splitter_cfg = self.config.get_splitter_config(strategy)
            module_path, class_name = splitter_cfg["import_path"].rsplit(".", 1)
            module = importlib.import_module(module_path)
            splitter_cls = getattr(module, class_name)

            # Filter kwargs for constructor
            valid_keys = {k for k in splitter_cfg.keys() if k not in ("import_path", "class")}
            kwargs = {k: splitter_cfg[k] for k in valid_keys}

            splitter = splitter_cls(**kwargs)
            logger.info(f"Initialized text splitter for pipeline='{pipeline_name}', strategy='{strategy}'")
            return splitter

        except Exception as e:
            raise CustomException("Failed to initialize text splitter", e)

    
    def build_vectorstore(self, documents: List[Any], embedding: Any, name: str = None) -> Any:
        try:
            vs_name = name or self.config.get("vectorstores.default")
            vs_cfg = self.config.get_vectorstore_config(vs_name)
            module_path, class_name = vs_cfg["import_path"].rsplit(".", 1)
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)

            logger.info(f"Building vectorstore {vs_name}")

            # Only pass what 'from_documents' supports for this vectorstore
            if vs_name == "faiss":
                # FAISS (community) does not take persist_directory in constructor
                return cls.from_documents(documents=documents, embedding=embedding)
            else:
                # For other vectorstores, pass supported kwargs
                valid_keys = {"persist_directory", "collection_name", "index_name"}
                kwargs = {k: v for k, v in vs_cfg.items() if k in valid_keys}
                return cls.from_documents(documents=documents, embedding=embedding, **kwargs)

        except Exception as e:
            raise CustomException("Failed to build vectorstore", e)

    
    def get_retriever(self, vectorstore: Any) -> Any:
        try:
            retr_cfg = self.config.get("retrieval") or {}  # fallback if missing
            search_type = retr_cfg.get("search_type", "similarity")
            top_k = retr_cfg.get("similarity_top_k", 5)
            logger.info(f"Creating retriever with search_type={search_type}, top_k={top_k}")
            return vectorstore.as_retriever(search_type=search_type, search_kwargs={"k": top_k})
        except Exception as e:
            raise CustomException("Failed to get retriever", e)