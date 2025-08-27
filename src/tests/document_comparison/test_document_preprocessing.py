import pytest
from langchain_core.documents import Document

from src.document_comparison.document_preprocessing import ComparisonPreprocessingPipeline


@pytest.fixture
def sample_docs():
    """Fixture that returns a small set of in-memory documents."""
    return [
        Document(page_content="This is a test document. It has some content."),
        Document(page_content="Another sample document for preprocessing."),
    ]


def test_run_single_returns_docs(sample_docs):
    """Pipeline should preprocess + chunk a single document set."""
    pipeline = ComparisonPreprocessingPipeline()
    processed = pipeline.run_single(sample_docs)

    assert isinstance(processed, list)
    assert all(isinstance(doc, Document) for doc in processed)
    assert len(processed) >= len(sample_docs)  # chunker may expand count


def test_run_single_empty():
    """Pipeline should handle empty doc list gracefully."""
    pipeline = ComparisonPreprocessingPipeline()
    processed = pipeline.run_single([])

    assert processed == []


def test_run_pair_returns_both_sets(sample_docs):
    """Pipeline should preprocess + chunk two doc sets in parallel."""
    pipeline = ComparisonPreprocessingPipeline()
    docs1, docs2 = pipeline.run_pair(sample_docs, sample_docs)

    assert isinstance(docs1, list) and isinstance(docs2, list)
    assert all(isinstance(doc, Document) for doc in docs1 + docs2)
    assert len(docs1) >= len(sample_docs)
    assert len(docs2) >= len(sample_docs)


def test_run_pair_handles_empty_sets(sample_docs):
    """Pipeline should handle one or both empty doc sets without error."""
    pipeline = ComparisonPreprocessingPipeline()
    docs1, docs2 = pipeline.run_pair(sample_docs, [])

    assert isinstance(docs1, list)
    assert isinstance(docs2, list)
    assert docs1  # should contain chunks
    assert docs2 == []  # empty second set should remain empty
