# src\document_analysis\document_preprocessing.py

from __future__ import annotations
from typing import List
from langchain_core.documents import Document

from src.configuration.config_loader import config
from src.utils.preprocessing_utils import DocumentPreprocessor
from src.utils.select_splitter import ChunkingUtility
from src.common.logging.logger import logger
from src.common.exception.custom_exception import CustomException
from src.utils.common_utils import timed


class DocumentPreprocessingPipeline:
    """Config-driven preprocessing + chunking pipeline."""

    def __init__(self):
        self.preproc_cfg = config.get("preprocessing", {}) or {}
        self.preprocessor = DocumentPreprocessor(self.preproc_cfg)
        self.chunker = ChunkingUtility()  # Config-driven chunker
        logger.info(f"DocumentPreprocessingPipeline initialized. preproc_cfg={self.preproc_cfg}")

    @timed
    def run(self, documents: List[Document]) -> List[Document]:
        """Preprocess and chunk documents."""
        if not documents:
            logger.info("No documents to preprocess (0).")
            return []

        try:
            # Step 1: Preprocess
            cleaned_docs = self.preprocessor.transform_documents(documents)
            logger.info(f"Documents preprocessed successfully. count={len(cleaned_docs)}")

            # Step 2: Chunking
            chunked_docs = self.chunker.chunk_documents(cleaned_docs)
            logger.info(f"Documents chunked successfully. chunks={len(chunked_docs)}")

            return chunked_docs

        except Exception as e:
            logger.error(f"Document preprocessing pipeline failed: {e}")
            raise CustomException("Document preprocessing pipeline failed", e)
