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

            # Debugging information
            logger.info(f"Loaded LLM: {self.llm}")
            logger.info(f"LLM type: {type(self.llm)}")
            if hasattr(self.llm, 'max_tokens'):
                logger.info(f"Actual max_tokens: {self.llm.max_tokens}")
            else:
                logger.warning("LLM has no max_tokens attribute")

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
                
            # Load prompts from configuration using updated names
            self.rewrite_question_prompt = self._load_prompt("rewrite_question")
            self.answer_using_context_prompt = self._load_prompt("answer_using_context")
            
            logger.info("DocumentQAChatPipeline initialized successfully")
            
        except Exception as e:
            raise CustomException("Failed to initialize DocumentQAChatPipeline", e)

    def _load_prompt(self, prompt_name: str) -> ChatPromptTemplate:
        """Load prompt from configuration and convert to ChatPromptTemplate."""
        try:
            prompt_config = prompts.get_qa_chat_prompt(prompt_name)
            
            if not prompt_config or "messages" not in prompt_config:
                logger.warning(f"Prompt '{prompt_name}' config not found, using fallback")
                return self._get_fallback_prompt(prompt_name)
            
            # Convert the YAML message format to LangChain ChatPromptTemplate
            messages = []
            for msg in prompt_config["messages"]:
                if msg["role"] == "system":
                    messages.append(("system", msg["content"]))
                elif msg["role"] == "human":
                    messages.append(("human", msg["content"]))
                elif msg["role"] == "ai":
                    messages.append(("ai", msg["content"]))
            
            return ChatPromptTemplate.from_messages(messages)
            
        except Exception as e:
            logger.error(f"Failed to load prompt '{prompt_name}' from config: {e}")
            return self._get_fallback_prompt(prompt_name)

    def _get_fallback_prompt(self, prompt_name: str) -> ChatPromptTemplate:
        """Fallback prompts if config loading fails."""
        if prompt_name == "rewrite_question":
            return ChatPromptTemplate.from_template(
                "Given a conversation history and the most recent user query, rewrite the query as a standalone question "
                "that makes sense without relying on the previous context. Do not provide an answer—only reformulate the "
                "question if necessary; otherwise, return it unchanged.\n\n"
                "Conversation History:\n{chat_history}\n\n"
                "User Query: {question}\n\n"
                "Standalone Question:"
            )
        else:  # answer_using_context
            return ChatPromptTemplate.from_template(
                "You are an assistant designed to answer questions using the provided context. Rely only on the retrieved "
                "information to form your response. If the answer is not found in the context, respond with 'I don't know.' "
                "Keep your answer concise and no longer than three sentences.\n\n"
                "Context:\n{context}\n\n"
                "Question: {question}\n\n"
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

    def _rewrite_question(self, question: str, chat_history: str = "") -> str:
        """Make question standalone using conversation history."""
        try:
            if not chat_history.strip():
                return question
                
            # Prepare inputs for the rewrite prompt
            rewrite_inputs = {
                "input": f"Conversation History:\n{chat_history}\n\nUser Query: {question}"
            }
            
            rewrite_chain = self.rewrite_question_prompt | self.llm | StrOutputParser()
            standalone_question = rewrite_chain.invoke(rewrite_inputs)
            
            logger.debug(f"Rewritten question: '{question}' -> '{standalone_question}'")
            return standalone_question.strip()
            
        except Exception as e:
            logger.warning(f"Failed to rewrite question, using original: {e}")
            return question

    def query(self, question: str, chat_history: str = "") -> Dict[str, Any]:
        """
        Query the document QA chatbot with conversation history support.
        
        Args:
            question: The user's question
            chat_history: Previous conversation history as a string
            
        Returns:
            Dictionary containing answer, metadata, and success status
        """
        try:
            if not question.strip():
                return {
                    "answer": "Please provide a question.",
                    "success": False
                }
            
            # Rewrite question if there's chat history
            standalone_question = self._rewrite_question(question, chat_history)
            
            # Get relevant documents using the standalone question
            retrieved_docs = self.retriever.invoke(standalone_question)
            
            # Format context for the answer prompt
            context_text = self._safe_format_docs(retrieved_docs)
            
            # Prepare inputs for the answer prompt
            answer_inputs = {
                "context": context_text,
                "input": standalone_question
            }
            
            # Create and invoke the answer chain
            answer_chain = self.answer_using_context_prompt | self.llm | StrOutputParser()
            answer = answer_chain.invoke(answer_inputs)
            
            logger.info(f"QA query processed: '{question}' -> '{standalone_question}'")
            return {
                "answer": answer.strip(),
                "question": question,
                "standalone_question": standalone_question,
                "success": True,
                "retrieved_docs_count": len(retrieved_docs),
                "has_context": len(retrieved_docs) > 0
            }
            
        except Exception as e:
            logger.error(f"Failed to process query: '{question}' - {e}")
            return {
                "answer": "Sorry, I encountered an error processing your question. Please try again.",
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

    def get_prompt_info(self) -> Dict[str, Any]:
        """Get information about the loaded prompts for debugging."""
        return {
            "rewrite_question_prompt": str(self.rewrite_question_prompt),
            "answer_using_context_prompt": str(self.answer_using_context_prompt),
            "llm_type": type(self.llm).__name__
        }


def create_document_qa_chat_pipeline(
    llm: Optional[BaseLanguageModel] = None,
    embedding: Optional[Embeddings] = None,
    retriever: Optional[BaseRetriever] = None
) -> DocumentQAChatPipeline:
    """Create a configured Document QA Chat pipeline."""
    return DocumentQAChatPipeline(llm=llm, embedding=embedding, retriever=retriever)