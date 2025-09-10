# src/components/document_ingestion_comparison.py

from pathlib import Path
from typing import List, Tuple, Union
from langchain_core.documents import Document
from src.configuration.config_loader import config
from src.common.logging.logger import logger
from src.common.exception.custom_exception import CustomException
from src.components.common_document_loader import CommonDocumentLoader


class DocumentComparisonIngestor:
    """Ingest documents specifically for the document comparison workflow.
    Supports loading default directories, single pairs, and multiple pairs.
    """

    def __init__(self, dir_a: str | None = None, dir_b: str | None = None):
        paths = config.get_comparison_paths()
        self.dir_a = dir_a or paths["dir_a"]
        self.dir_b = dir_b or paths["dir_b"]
        self.supported_exts = set(config.get_supported_exts())
        self.loader_map = config.get_loader_map()

        self.loader_a = CommonDocumentLoader(
            input_dir=self.dir_a,
            supported_exts=self.supported_exts,
            loader_map=self.loader_map,
        )
        self.loader_b = CommonDocumentLoader(
            input_dir=self.dir_b,
            supported_exts=self.supported_exts,
            loader_map=self.loader_map,
        )
        logger.info(f"DocumentComparisonIngestor initialized with A={self.dir_a}, B={self.dir_b}")

    # --------------------------
    # Load default directories
    # --------------------------
    def load_documents_set_a(self) -> List[Document]:
        return self.loader_a.load_directory()

    def load_documents_set_b(self) -> List[Document]:
        return self.loader_b.load_directory()

    def load_documents_pair(self) -> Tuple[List[Document], List[Document]]:
        """Load both default directories and return as a tuple."""
        return self.load_documents_set_a(), self.load_documents_set_b()

    # --------------------------
    # Load arbitrary pairs
    # --------------------------
    def load_doc_pair(
        self, path1: Union[str, Path], path2: Union[str, Path]
    ) -> Tuple[List[Document], List[Document]]:
        """Load documents from two arbitrary paths."""
        try:
            docs1 = self.loader_a.load_paths([path1])
            docs2 = self.loader_b.load_paths([path2])
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
        """Load multiple pairs of paths with safe error handling."""
        results = []
        for p1, p2 in pairs:
            try:
                results.append(self.load_doc_pair(p1, p2))
            except Exception as e:
                logger.error(f"Skipping pair ({p1}, {p2}) due to error: {e}")
        return results
