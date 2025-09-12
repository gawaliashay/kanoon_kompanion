# src/components/document_chunker.py

from typing import List
from langchain_core.documents import Document
from src.components.rag_utils import RAGUtils
from src.common.logging.logger import logger
from src.common.exception.custom_exception import CustomException

class ChunkingUtility:
    """Universal document chunker, fully config-driven, wraps RAGUtils."""

    def __init__(self, pipeline_name: str):
        """
        pipeline_name: 'document_analysis', 'document_comparison', 'document_qa_chat'
        """
        try:
            self.pipeline_name = pipeline_name
            self.rag = RAGUtils()
            self.splitter = self.rag.get_text_splitter(pipeline_name=pipeline_name)
            self.strategy = getattr(self.splitter, "chunk_strategy", pipeline_name)
            logger.info(f"ChunkingUtility initialized for pipeline='{pipeline_name}', strategy='{self.strategy}'")
        except Exception as e:
            raise CustomException("Failed to initialize ChunkingUtility", e)

    def chunk_documents(self, documents: List[Document]) -> List[Document]:
        """Split documents into chunks using the configured splitter and add metadata."""
        try:
            if not documents:
                logger.info(f"No documents to chunk for pipeline '{self.pipeline_name}'")
                return []

            chunks = self.splitter.split_documents(documents)
            for i, chunk in enumerate(chunks):
                chunk.metadata = {**chunk.metadata, "chunk_id": i, "chunk_strategy": self.strategy}

            logger.info(f"Chunking complete: {len(chunks)} chunks from {len(documents)} docs for pipeline '{self.pipeline_name}'")
            return chunks

        except Exception as e:
            raise CustomException("Failed during document chunking", e)
