# src/components/document_analysis/analysis_parsers.py

from pydantic import BaseModel, Field
from langchain.output_parsers import OutputFixingParser
from langchain_core.output_parsers import PydanticOutputParser
from src.components.model_loader import ModelFactory
from src.configuration.config_loader import config


class DocumentAnalysisResult(BaseModel):
    summary: str = Field(..., description="Document summary")


def get_document_analysis_parser(llm=None):
    """
    Return a robust output parser for document analysis.
    If an LLM is provided, wraps the Pydantic parser with OutputFixingParser
    to automatically repair invalid or non-JSON outputs.
    """
    base_parser = PydanticOutputParser(pydantic_object=DocumentAnalysisResult)

    if llm is not None:
        return OutputFixingParser.from_llm(parser=base_parser, llm=llm)
    return base_parser
