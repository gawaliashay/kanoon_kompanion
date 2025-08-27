import pytest
from unittest.mock import MagicMock, patch
from langchain_core.documents import Document

from src.document_comparison.document_comparison_pipeline import DocumentComparisonPipeline
from src.common.exception.custom_exception import CustomException


@pytest.fixture
def sample_docs():
    """Create minimal fake documents for testing."""
    return [Document(page_content="Hello world", metadata={"source": "test.txt"})]


@pytest.fixture
def pipeline():
    """Initialize pipeline with mocks for ingestion, preprocessing, and chain."""
    pipeline = DocumentComparisonPipeline()

    # Mock ingestion
    pipeline.ingestor.load_paths = MagicMock(side_effect=lambda paths: [Document(page_content="Dummy text")])

    # Mock preprocessing
    pipeline.preprocessor.run_pair = MagicMock(
        side_effect=lambda docs_a, docs_b: (
            [Document(page_content="Processed A")],
            [Document(page_content="Processed B")]
        )
    )

    # Mock chain (parser + LLM)
    fake_result = MagicMock()
    fake_result.dict.return_value = {"differences": ["Dummy difference"], "overlaps": ["Dummy overlap"]}
    pipeline.chain.invoke = MagicMock(return_value=fake_result)

    return pipeline


def test_run_comparison_success(pipeline):
    """Test that pipeline runs and returns structured result."""
    result = pipeline.run_comparison(["fileA.txt"], ["fileB.txt"])

    assert "differences" in result
    assert "overlaps" in result
    assert result["differences"] == ["Dummy difference"]
    assert result["overlaps"] == ["Dummy overlap"]

    # Ensure mocks were called
    pipeline.ingestor.load_paths.assert_any_call(["fileA.txt"])
    pipeline.ingestor.load_paths.assert_any_call(["fileB.txt"])
    pipeline.preprocessor.run_pair.assert_called_once()


def test_run_comparison_missing_inputs(pipeline):
    """Should raise error if one document set is missing."""
    with pytest.raises(CustomException):
        pipeline.run_comparison(["fileA.txt"], None)


def test_run_comparison_empty_preprocessed(pipeline):
    """Should raise error if preprocessing returns empty docs."""
    pipeline.preprocessor.run_pair = MagicMock(return_value=([], []))

    with pytest.raises(CustomException):
        pipeline.run_comparison(["fileA.txt"], ["fileB.txt"])
