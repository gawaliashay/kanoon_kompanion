import tempfile
import pytest
from pathlib import Path
from langchain_core.documents import Document

from src.document_comparison.document_ingestion import ComparisonDocumentIngestor
from src.common.exception.custom_exception import CustomException


@pytest.fixture
def temp_text_files():
    f1 = tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w")
    f2 = tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w")
    f1.write("file1 content")
    f2.write("file2 content")
    f1.close()
    f2.close()
    yield f1.name, f2.name
    Path(f1.name).unlink()
    Path(f2.name).unlink()


def test_load_doc_pair_success(temp_text_files, monkeypatch):
    ingestor = ComparisonDocumentIngestor()

    # Monkeypatch loader_map to handle .txt
    monkeypatch.setattr(ingestor, "loader_map", {".txt": "langchain_community.document_loaders.TextLoader"})

    docs1, docs2 = ingestor.load_doc_pair(temp_text_files[0], temp_text_files[1])
    assert all(isinstance(d, Document) for d in docs1)
    assert all(isinstance(d, Document) for d in docs2)


def test_load_doc_pair_failure(monkeypatch):
    ingestor = ComparisonDocumentIngestor()
    with pytest.raises(CustomException):
        ingestor.load_doc_pair("nonexistent1.txt", "nonexistent2.txt")
