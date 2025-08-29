# src\components\document_loader.py

from __future__ import annotations
import os
import sqlite3
import importlib
from pathlib import Path
from typing import List, Iterable, Dict, Type, Union

import pandas as pd
from langchain_core.documents import Document

from src.common.logging.logger import logger
from src.common.exception.custom_exception import CustomException
from src.utils.common_utils import ensure_dir, timed
from src.configuration.config_loader import config


class DocumentIngestor:
    """Production-grade ingestion with config-driven supported file types and dynamic loaders."""

    def __init__(self, input_dir: str | None = None):
        self.input_dir = ensure_dir(input_dir or config.get("paths.data_dir"))
        self.supported_exts = set(config.get_supported_exts() or [])
        self.loader_map: Dict[str, str] = config.get_loader_map() or {}
        logger.info(f"DocumentIngestor initialized. input_dir={self.input_dir}")
        logger.info(f"Supported file types: {', '.join(sorted(self.supported_exts))}")

    @staticmethod
    def _norm_path(p: str | Path) -> str:
        return str(Path(p).resolve())

    def _get_loader_class(self, ext: str) -> Type | None:
        """Return a loader class from config's loader_map for the given extension."""
        import_path = self.loader_map.get(ext)
        if not import_path:
            return None
        try:
            module_path, class_name = import_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            return getattr(module, class_name)
        except Exception as e:
            raise CustomException(f"Failed to import loader for extension '{ext}' ({import_path})", e)

    @timed
    def load_paths(self, paths: Iterable[str | Path]) -> List[Document]:
        docs: List[Document] = []
        for p in paths:
            p = Path(p)
            try:
                if p.is_dir():
                    docs.extend(self.load_directory(p))
                elif p.is_file():
                    docs.extend(self.load_file(p))
                else:
                    logger.warning(f"Path not found or unsupported: {p}")
            except Exception as e:
                logger.error(f"Failed to load path {p}: {e}")
        if not docs:
            logger.warning("No supported documents found in the provided paths.")
        return docs

    @timed
    def load_directory(self, directory: str | Path | None = None) -> List[Document]:
        directory = Path(directory or self.input_dir)
        if not directory.exists():
            msg = f"Directory not found: {directory}"
            logger.error(msg)
            raise CustomException(msg, FileNotFoundError(directory))

        documents: List[Document] = []
        try:
            for root, _, files in os.walk(directory):
                for f in files:
                    path = Path(root) / f
                    ext = path.suffix.lower()
                    if ext not in self.supported_exts:
                        logger.info(f"Skipped unsupported file type: {path}")
                        continue
                    try:
                        file_docs = self.load_file(path)
                        documents.extend(file_docs)
                        logger.info(f"File ingested: {path} (docs: {len(file_docs)})")
                    except Exception as e:
                        logger.error(f"File skipped due to error: {path} | {e}")
            if not documents:
                logger.warning(f"No supported documents found in directory: {directory}")
            return documents
        except Exception as e:
            logger.error(f"Failed to load directory {directory}: {e}")
            raise CustomException("Failed to load directory", e)

    @timed
    def load_file(self, file_path: str | Path) -> List[Document]:
        file_path = str(file_path)
        ext = Path(file_path).suffix.lower()

        # Special handling for SQLite / DB files
        if ext in {".sqlite", ".db"}:
            return self._load_sqlite(file_path)

        try:
            loader_cls = self._get_loader_class(ext)
            if not loader_cls:
                msg = f"Unsupported file format: {ext}"
                logger.error(msg)
                raise CustomException(msg, ValueError(ext))

            loader = loader_cls(file_path)  # standard LangChain loader signature
            docs: List[Document] = loader.load()
            return self._with_source(docs, file_path)

        except Exception as e:
            logger.error(f"Failed to load file {file_path}: {e}")
            raise CustomException(f"Failed to load file: {file_path}", e)

    def _with_source(self, docs: List[Document], source: str) -> List[Document]:
        source = self._norm_path(source)
        for d in docs:
            d.metadata = {**(d.metadata or {}), "source": source}
        return docs

    def _load_sqlite(self, db_path: str) -> List[Document]:
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            docs: List[Document] = []

            for table in tables:
                df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
                page_content = df.to_csv(index=False)
                docs.append(
                    Document(
                        page_content=page_content,
                        metadata={
                            "source": self._norm_path(db_path),
                            "table": table,
                            "rows": len(df),
                        },
                    )
                )
            conn.close()
            return docs
        except Exception as e:
            logger.error(f"Failed to load SQLite DB {db_path}: {e}")
            raise CustomException(f"Failed to load SQLite DB: {db_path}", e)
