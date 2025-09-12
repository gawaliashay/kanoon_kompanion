# src\document_comparison\document_preprocessing.py

from __future__ import annotations
from typing import List, Tuple
from langchain_core.documents import Document
from src.configuration.config_loader import config
from src.utils.preprocessing_utils import DocumentPreprocessor
from src.components.document_chunker import ChunkingUtility
from src.common.logging.logger import logger
from src.common.exception.custom_exception import CustomException
from src.utils.common_utils import timed


class ComparisonPreprocessingPipeline:
    """
    Preprocessing + chunking pipeline for document comparison.
    Applies the same config-driven transformations to two sets of documents.
    """

    def __init__(self):
        self.preproc_cfg = config.get("preprocessing", {}) or {}
        self.preprocessor = DocumentPreprocessor(self.preproc_cfg)
        self.chunker = ChunkingUtility("document_comparison")
        logger.info(f"ComparisonPreprocessingPipeline initialized. preproc_cfg={self.preproc_cfg}")

    @timed
    def run_single(self, documents: List[Document]) -> List[Document]:
        """Preprocess and chunk a single document set."""
        if not documents:
            logger.info("No documents to preprocess (0).")
            return []
        try:
            cleaned = self.preprocessor.transform_documents(documents)
            chunked = self.chunker.chunk_documents(cleaned)
            logger.info(f"Processed single doc set. chunks={len(chunked)}")
            return chunked
        except Exception as e:
            logger.error(f"Single document preprocessing failed: {e}")
            raise CustomException("Single document preprocessing failed", e)

    @timed
    def run_pair(
        self, docs1: List[Document], docs2: List[Document]
    ) -> Tuple[List[Document], List[Document]]:
        """Preprocess and chunk two sets of documents for comparison."""
        try:
            processed1 = self.run_single(docs1)
            processed2 = self.run_single(docs2)
            logger.info(
                f"Processed pair of document sets. chunks1={len(processed1)}, chunks2={len(processed2)}"
            )
            return processed1, processed2
        except Exception as e:
            logger.error(f"Pairwise document preprocessing failed: {e}")
            raise CustomException("Pairwise document preprocessing failed", e)
