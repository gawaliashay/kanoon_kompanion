# src\components\document_qa\document_qa_chat_ingestion.py

from pathlib import Path
from typing import List, Union
from src.configuration.config_loader import config
from src.components.common_document_loader import CommonDocumentLoader


class DocumentQAChatIngestor:
    """Ingest documents specifically for the Document QA Chat workflow."""

    def __init__(self, input_dir: str | None = None):
        self.input_dir = input_dir or config.get("paths.document_qa_chat_dir")
        self.supported_exts = set(config.get_supported_exts())
        self.loader_map = config.get_loader_map()

        self.loader = CommonDocumentLoader(
            input_dir=self.input_dir,
            supported_exts=self.supported_exts,
            loader_map=self.loader_map,
        )

    def load_documents(self, paths: List[Union[str, Path]] | None = None) -> List:
        """
        Load documents from the given paths or default QA chat directory.

        Args:
            paths: List of file paths or directories.
        Returns:
            List of Document objects.
        """
        if paths:
            return self.loader.load_paths(paths)
        return self.loader.load_directory()
