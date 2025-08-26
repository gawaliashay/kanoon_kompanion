# src\utils\preprocessing_utils.py

import re
from typing import List, Dict, Any
from langchain_core.documents import Document
from langchain_core.documents.transformers import BaseDocumentTransformer
from src.common.logging.logger import logger
from src.common.exception.custom_exception import CustomException


class DocumentPreprocessor(BaseDocumentTransformer):
    """Config-driven reusable document preprocessor for LangChain pipelines."""

    DEFAULT_CFG = {
        "lowercase": True,
        "strip_whitespace": True,
        "normalize_spaces": True,
        "remove_special_chars": False,
        "remove_numeric": False,
    }

    def __init__(self, preproc_cfg: Dict[str, Any] = None):
        self.preproc_cfg = {**self.DEFAULT_CFG, **(preproc_cfg or {})}

    def transform_documents(self, documents: List[Document]) -> List[Document]:
        try:
            processed_docs = []
            for doc in documents:
                text = doc.page_content

                if self.preproc_cfg.get("lowercase", False):
                    text = text.lower()
                if self.preproc_cfg.get("strip_whitespace", False):
                    text = text.strip()
                if self.preproc_cfg.get("normalize_spaces", False):
                    text = re.sub(r"\s+", " ", text)
                if self.preproc_cfg.get("remove_special_chars", False):
                    text = re.sub(r"[^a-zA-Z0-9\s.,!?;:()'\"]+", " ", text)
                if self.preproc_cfg.get("remove_numeric", False):
                    text = re.sub(r"\d+", " ", text)

                new_doc = Document(
                    page_content=text,
                    metadata={
                        **doc.metadata,
                        "char_length": len(text),
                        "word_count": len(text.split())
                    }
                )
                processed_docs.append(new_doc)

            logger.info(f"Preprocessing complete: {len(processed_docs)} docs processed")
            return processed_docs

        except Exception as e:
            raise CustomException("Failed during document preprocessing", e)
