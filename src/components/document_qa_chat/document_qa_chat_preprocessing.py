# src\components\document_qa_chat\document_qa_chat_preprocessing.py

from typing import List
from langchain_core.documents import Document
from src.utils.preprocessing_utils import DocumentPreprocessor
from src.configuration.config_loader import config
from src.common.logging.logger import logger
from src.common.exception.custom_exception import CustomException


class DocumentQAPreprocessor:
    """
    Config-driven preprocessing for Document QA Chat workflow.
    Applies transformations like lowercase, whitespace stripping, and more.
    """

    def __init__(self):
        try:
            preproc_cfg = config.get("preprocessing", {})
            self.preprocessor = DocumentPreprocessor(preproc_cfg)
            logger.info(f"DocumentQAPreprocessor initialized with config: {preproc_cfg}")
        except Exception as e:
            raise CustomException("Failed to initialize DocumentQAPreprocessor", e)

    def preprocess(self, documents: List[Document]) -> List[Document]:
        """
        Preprocess documents according to configuration.

        Args:
            documents: List of langchain_core Document objects.

        Returns:
            List of preprocessed Document objects.
        """
        if not documents:
            logger.warning("No documents provided for preprocessing.")
            return []

        try:
            processed_docs = self.preprocessor.transform_documents(documents)
            logger.info(f"Preprocessed {len(processed_docs)} documents")
            return processed_docs
        except Exception as e:
            raise CustomException("Failed during document preprocessing", e)
