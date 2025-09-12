# src/components/document_qa_chat/document_qa_chat_pipeline.py

from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from langchain_core.language_models import BaseLanguageModel
from langchain_core.embeddings import Embeddings
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import Runnable, RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from src.configuration.config_loader import config
from src.configuration.prompts_loader import prompts
from src.common.logging.logger import logger
from src.common.exception.custom_exception import CustomException
from src.components.model_loader import ModelFactory
from src.components.rag_utils import RAGUtils
from src.components.document_chunker import ChunkingUtility
from src.components.document_qa_chat.document_qa_chat_ingestion import DocumentQAChatIngestor
from src.components.document_qa_chat.document_qa_chat_preprocessing import DocumentQAPreprocessor


class DocumentQAChatPipeline:
    """Config-driven conversational document chatbot assistant."""

    def __init__(
        self,
        llm: Optional[BaseLanguageModel] = None,
        embedding: Optional[Embeddings] = None,
        retriever: Optional[BaseRetriever] = None
    ):
        try:
            self.model_factory = ModelFactory()
            self.llm = llm or self.model_factory.load_llm()
            self.embedding = embedding or self.model_factory.load_embedding()
            self.rag_utils = RAGUtils()
            
            # Initialize components
            self.ingestor = DocumentQAChatIngestor()
            self.preprocessor = DocumentQAPreprocessor()
            self.chunker = ChunkingUtility("document_qa_chat")
            
            # Set up retriever (build if not provided)
            self.retriever = retriever
            if not self.retriever:
                self._build_retriever()
                
            # Load prompts
            self.qa_prompt = self._load_qa_prompt()
            
            logger.info("DocumentQAChatPipeline initialized successfully")
            
        except Exception as e:
            raise CustomException("Failed to initialize DocumentQAChatPipeline", e)

    def _load_qa_prompt(self) -> ChatPromptTemplate:
        """Load and create a simple QA prompt."""
        # Use a simple, reliable prompt template
        return ChatPromptTemplate.from_template(
            "You are a helpful assistant that answers questions based on the provided context.\n\n"
            "Context information:\n{context}\n\n"
            "Question: {question}\n\n"
            "Answer the question clearly and concisely using only the context above. "
            "If the answer is not in the context, say 'I don't know'.\n\n"
            "Answer:"
        )

    def _build_retriever(self):
        """Build retriever from documents in QA chat directory."""
        try:
            # Ingest and process documents
            documents = self.ingestor.load_documents()
            if not documents:
                logger.warning("No documents found for QA chat pipeline")
                return
                
            processed_docs = self.preprocessor.preprocess(documents)
            chunks = self.chunker.chunk_documents(processed_docs)
            
            # Build vectorstore and retriever
            vectorstore = self.rag_utils.build_vectorstore(chunks, self.embedding)
            self.retriever = self.rag_utils.get_retriever(vectorstore)
            
            logger.info(f"Retriever built with {len(chunks)} chunks from {len(documents)} documents")
            
        except Exception as e:
            raise CustomException("Failed to build retriever", e)

    def _safe_format_docs(self, docs: List[Document]) -> str:
        """Safely format documents for context."""
        if not docs:
            return "No relevant information found."
        
        formatted = []
        for i, doc in enumerate(docs):
            try:
                content = str(doc.page_content)
                source = doc.metadata.get('source', 'Unknown').split('\\')[-1]  # Just filename
                formatted.append(f"[Document {i+1} from {source}]:\n{content[:800]}...")
            except Exception as e:
                logger.warning(f"Failed to format document {i}: {e}")
                continue
        
        return "\n\n".join(formatted) if formatted else "No relevant information found."

    def query(self, question: str, history: str = "") -> Dict[str, Any]:
        """
        Query the document QA chatbot.
        """
        try:
            if not question.strip():
                return {
                    "answer": "Please provide a question.",
                    "success": False
                }
            
            # Get relevant documents
            retrieved_docs = self.retriever.invoke(question)  # Use invoke instead of deprecated method
            
            # Format context
            context = self._safe_format_docs(retrieved_docs)
            
            # Create the QA chain with proper input formatting
            qa_chain = (
                {
                    "context": lambda x: x["context"],
                    "question": lambda x: x["question"]
                }
                | self.qa_prompt
                | self.llm
                | StrOutputParser()
            )
            
            # Invoke the chain with proper inputs
            answer = qa_chain.invoke({
                "context": context,
                "question": question
            })
            
            logger.info(f"QA query processed: '{question}'")
            return {
                "answer": answer.strip(),
                "question": question,
                "success": True,
                "retrieved_docs_count": len(retrieved_docs)
            }
            
        except Exception as e:
            logger.error(f"Failed to process query: {question} - {e}")
            return {
                "answer": f"Sorry, I encountered an error processing your question.",
                "question": question,
                "success": False,
                "error": str(e)
            }

    def ingest_new_documents(self, paths: List[str]) -> None:
        """Ingest new documents and update the retriever."""
        try:
            documents = self.ingestor.load_documents(paths)
            processed_docs = self.preprocessor.preprocess(documents)
            chunks = self.chunker.chunk_documents(processed_docs)
            
            # Rebuild vectorstore with new documents
            vectorstore = self.rag_utils.build_vectorstore(chunks, self.embedding)
            self.retriever = self.rag_utils.get_retriever(vectorstore)
            
            logger.info(f"Ingested {len(documents)} new documents, total chunks: {len(chunks)}")
            
        except Exception as e:
            raise CustomException("Failed to ingest new documents", e)


def create_document_qa_chat_pipeline(
    llm: Optional[BaseLanguageModel] = None,
    embedding: Optional[Embeddings] = None,
    retriever: Optional[BaseRetriever] = None
) -> DocumentQAChatPipeline:
    """Create a configured Document QA Chat pipeline."""
    return DocumentQAChatPipeline(llm=llm, embedding=embedding, retriever=retriever)