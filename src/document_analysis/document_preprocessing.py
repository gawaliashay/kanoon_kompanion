# src/document_analysis/document_preprocessing.py

from __future__ import annotations
from typing import List
from langchain_core.documents import Document

from src.configuration.config_loader import config
from src.utils.preprocessing_utils import DocumentPreprocessor
from src.common.logging.logger import logger
from src.common.exception.custom_exception import CustomException
from src.utils.common_utils import timed


class DocumentPreprocessingPipeline:
    """Config-driven preprocessing pipeline with logging and exceptions."""

    def __init__(self):
        self.preproc_cfg = config.get("preprocessing", {}) or {}
        self.preprocessor = DocumentPreprocessor(self.preproc_cfg)
        logger.info(f"DocumentPreprocessingPipeline initialized. config={self.preproc_cfg}")

    @timed
    def run(self, documents: List[Document]) -> List[Document]:
        try:
            if not documents:
                logger.info("No documents to preprocess (0).")
                return []
            cleaned_docs = self.preprocessor.transform_documents(documents)
            logger.info(f"Documents preprocessed successfully. count={len(cleaned_docs)}")
            return cleaned_docs
        except Exception as e:
            logger.error(f"Document preprocessing pipeline failed: {e}")
            raise CustomException("Document preprocessing pipeline failed", e)
