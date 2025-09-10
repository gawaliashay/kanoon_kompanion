# src\components\document_analysis\document_ingestion_analysis.py

from src.configuration.config_loader import config
from src.components.common_document_loader import CommonDocumentLoader


class DocumentAnalysisIngestor:
    """Ingest documents specifically for the document analysis workflow."""

    def __init__(self, input_dir: str | None = None):
        self.input_dir = input_dir or config.get("paths.analysis_dir")
        self.supported_exts = set(config.get_supported_exts())
        self.loader_map = config.get_loader_map()

        self.loader = CommonDocumentLoader(
            input_dir=self.input_dir,
            supported_exts=self.supported_exts,
            loader_map=self.loader_map,
        )

    def load_documents(self, paths: list[str] | None = None):
        """Load documents from the given paths or default input_dir."""
        if paths:
            return self.loader.load_paths(paths)
        return self.loader.load_directory()
