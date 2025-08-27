from typing import List
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser


class ComparisonResult(BaseModel):
    similarities: List[str] = Field(default_factory=list, description="Common points")
    differences: List[str] = Field(default_factory=list, description="Differences")
    unique_doc1: List[str] = Field(default_factory=list, description="Points unique to doc1")
    unique_doc2: List[str] = Field(default_factory=list, description="Points unique to doc2")


def get_document_comparison_parser() -> PydanticOutputParser:
    """Return a parser for document comparison results using Pydantic schema."""
    return PydanticOutputParser(pydantic_object=ComparisonResult)
