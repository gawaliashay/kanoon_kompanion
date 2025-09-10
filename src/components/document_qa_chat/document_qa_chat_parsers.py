# src/components/document_qa_chat/document_qa_chat_parsers.py

from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser


# --------------------------
# Single QA Answer Parser
# --------------------------
class QAAnswer(BaseModel):
    """Structured output for a single QA response."""
    answer: str = Field(..., description="Concise answer to the user's question")
    sources: Optional[List[str]] = Field(default_factory=list, description="List of document sources referenced")
    confidence: Optional[float] = Field(None, description="Optional confidence score if available")


# --------------------------
# Contextualized Question Parser
# --------------------------
class RewrittenQuestion(BaseModel):
    """Output parser for reformulated questions with context applied."""
    question: str = Field(..., description="Standalone question rewritten with conversation history")


# --------------------------
# List of QA Answers Parser (if returning multiple)
# --------------------------
class QAAnswerList(BaseModel):
    """Output parser for multiple QA answers."""
    answers: List[QAAnswer]


# --------------------------
# Parser callable wrappers
# --------------------------
def qa_answer_parser(output: Any) -> Dict:
    """Parse LLM output into structured QAAnswer dictionary."""
    parser = PydanticOutputParser(pydantic_object=QAAnswer)
    return parser.parse(output)


def question_rewrite_parser(output: Any) -> Dict:
    """Parse LLM output into structured RewrittenQuestion dictionary."""
    parser = PydanticOutputParser(pydantic_object=RewrittenQuestion)
    return parser.parse(output)


def qa_answer_list_parser(output: Any) -> Dict:
    """Parse LLM output into structured list of QAAnswer."""
    parser = PydanticOutputParser(pydantic_object=QAAnswerList)
    return parser.parse(output)
