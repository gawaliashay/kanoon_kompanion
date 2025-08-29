# src\document_comparison\document_ingestion.py

from pathlib import Path
from typing import List, Tuple, Union
from langchain_core.documents import Document
from src.components.document_loader import DocumentIngestor
from src.common.logging.logger import logger
from src.common.exception.custom_exception import CustomException


class ComparisonDocumentIngestor(DocumentIngestor):
    """Extends base ingestor with pairwise ingestion for comparison tasks."""

    def __init__(self, input_dir: str | None = None):
        super().__init__(input_dir=input_dir)
        logger.info("ComparisonDocumentIngestor initialized.")

    def load_doc_pair(
        self, path1: Union[str, Path], path2: Union[str, Path]
    ) -> Tuple[List[Document], List[Document]]:
        try:
            docs1 = self.load_paths([path1])
            docs2 = self.load_paths([path2])
            if not docs1 or not docs2:
                raise CustomException(
                    f"One or both paths did not return any documents. path1={path1}, path2={path2}",
                    ValueError("Empty docs"),
                )
            logger.info(f"Loaded {len(docs1)} docs from {path1}, {len(docs2)} docs from {path2}")
            return docs1, docs2
        except Exception as e:
            raise CustomException("Failed to load document pair", e)

    def load_multiple_pairs(
        self, pairs: List[Tuple[Union[str, Path], Union[str, Path]]]
    ) -> List[Tuple[List[Document], List[Document]]]:
        results = []
        for p1, p2 in pairs:
            try:
                results.append(self.load_doc_pair(p1, p2))
            except Exception as e:
                logger.error(f"Skipping pair ({p1}, {p2}) due to error: {e}")
        return results
