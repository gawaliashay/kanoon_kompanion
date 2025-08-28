# src\document_analysis\analysis_parsers.py


from typing import List
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser


class DocumentAnalysisResult(BaseModel):
    summary: str = Field(..., description="Concise summary of the document")
    keywords: List[str] = Field(default_factory=list, description="Salient keywords from the document")


def get_document_analysis_parser() -> PydanticOutputParser:
    return PydanticOutputParser(pydantic_object=DocumentAnalysisResult)

class KeywordsResult(BaseModel):
    keywords: List[str] = Field(default_factory=list, description="Salient keywords")

def get_keywords_parser() -> PydanticOutputParser:
    return PydanticOutputParser(pydantic_object=KeywordsResult)
