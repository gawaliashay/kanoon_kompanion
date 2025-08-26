# src/utilities/analysis_parsers.py


from typing import List
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser


class DocumentAnalysisResult(BaseModel):
    summary: str = Field(..., description="Concise summary of the document")
    keywords: List[str] = Field(..., description="List of key terms")


def get_document_analysis_parser() -> PydanticOutputParser:
    return PydanticOutputParser(pydantic_object=DocumentAnalysisResult)
