import os
import tempfile
import sqlite3
from pathlib import Path
import pytest
from langchain_core.documents import Document

from src.utils.document_ingestor import DocumentIngestor
from src.common.exception.custom_exception import CustomException


@pytest.fixture
def temp_txt_file():
    """Create a temporary txt file for testing."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w") as f:
        f.write("hello world")
        yield f.name
    os.remove(f.name)


@pytest.fixture
def temp_sqlite_file():
    """Create a temporary SQLite file with one table."""
    db_fd, db_path = tempfile.mkstemp(suffix=".sqlite")
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE test (id INTEGER, name TEXT);")
    conn.execute("INSERT INTO test VALUES (1, 'Alice');")
    conn.commit()
    conn.close()
    yield db_path
    os.close(db_fd)
    os.remove(db_path)


def test_load_file_with_unsupported_ext():
    ingestor = DocumentIngestor()
    with tempfile.NamedTemporaryFile(suffix=".xyz") as f:
        with pytest.raises(CustomException):
            ingestor.load_file(f.name)


def test_load_file_sqlite(temp_sqlite_file):
    ingestor = DocumentIngestor()
    docs = ingestor.load_file(temp_sqlite_file)
    assert isinstance(docs, list)
    assert isinstance(docs[0], Document)
    assert "test" in docs[0].metadata["table"]


def test_load_directory_with_txt(temp_txt_file, monkeypatch):
    ingestor = DocumentIngestor()
    
    # Monkeypatch loader_map to handle .txt
    monkeypatch.setattr(ingestor, "loader_map", {".txt": "langchain_community.document_loaders.TextLoader"})
    
    docs = ingestor.load_directory(Path(temp_txt_file).parent)
    assert all(isinstance(d, Document) for d in docs)
