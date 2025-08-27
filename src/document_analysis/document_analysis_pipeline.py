# src/document_analysis/document_analysis_pipeline.py

from __future__ import annotations
from typing import List, Dict, Any

from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence

from src.common.ingestion.document_ingestor import DocumentIngestor
from src.document_analysis.document_preprocessing import DocumentPreprocessingPipeline
from src.document_analysis.analysis_parsers import get_document_analysis_parser
from src.common.logging.logger import logger
from src.common.exception.custom_exception import CustomException
from src.configuration.config_loader import config
from src.utils.select_model import ModelFactory


class DocumentAnalysisPipeline:
    """Config-driven document analysis pipeline (No RAG). Uses Pydantic parser for safe JSON output."""

    def __init__(self):
        try:
            self.ingestor = DocumentIngestor()
            self.preprocessor = DocumentPreprocessingPipeline()
            self.parser = get_document_analysis_parser()
            factory = ModelFactory(config)
            self.llm = factory.load_llm()
            logger.info("DocumentAnalysisPipeline initialized successfully (No RAG).")
        except Exception as e:
            logger.error(f"Failed to initialize DocumentAnalysisPipeline: {e}")
            raise CustomException("Pipeline initialization failed", e)

    def _build_chain(self, prompt_cfg: Dict[str, Any]) -> RunnableSequence:
        """Build a chain from a prompt dict with LLM + Pydantic parser."""
        try:
            prompt = PromptTemplate(
                input_variables=prompt_cfg["input_variables"],
                partial_variables={"format_instructions": self.parser.get_format_instructions()},
                template=prompt_cfg["template"]
            )
            return prompt | self.llm | self.parser
        except Exception as e:
            logger.error(f"Failed to build chain: {e}")
            raise CustomException("Failed to build chain", e)

    def run_analysis(self, file_paths: List[str] | None = None) -> Dict[str, Any]:
        try:
            file_paths = file_paths or [config.get("paths.data_dir")]
            logger.info(f"Starting document analysis. files={file_paths}")

            # ---- Ingest ----
            docs = self.ingestor.load_paths(file_paths)
            if not docs:
                msg = f"No documents ingested from: {file_paths}"
                logger.error(msg)
                raise CustomException(msg, ValueError(file_paths))

            # ---- Preprocess + Chunk ----
            clean_docs = self.preprocessor.run(docs)
            if not clean_docs:
                msg = "No chunks created from documents."
                logger.error(msg)
                raise CustomException(msg, ValueError("empty_chunks"))

            logger.info(f"Total chunks to analyze: {len(clean_docs)}")

            # ---- Map Step ----
            map_prompt_cfg = config.get_analysis_prompt(step="summary_map")
            if not map_prompt_cfg:
                raise CustomException("Map prompt config 'summary_map' not found", ValueError("missing_map_prompt"))
            map_chain = self._build_chain(map_prompt_cfg)

            chunk_summaries = []
            for chunk in clean_docs:
                try:
                    result = map_chain.invoke({"document_text": chunk.page_content})
                    chunk_summaries.append(result.dict()["summary"])
                except Exception as e:
                    logger.warning(f"Chunk failed to process: {e}")
                    # fallback: raw chunk text
                    chunk_summaries.append(chunk.page_content[:500])

            combined_summaries_text = "\n\n".join(chunk_summaries)
            final_result: Dict[str, Any] = {"summary": combined_summaries_text}

            # ---- Reduce Step ----
            reduce_prompt_cfg = config.get_analysis_prompt(step="summary_reduce")
            if reduce_prompt_cfg:
                try:
                    reduce_chain = self._build_chain(reduce_prompt_cfg)
                    reduce_result = reduce_chain.invoke({"chunk_summaries": combined_summaries_text})
                    final_result["summary"] = reduce_result.dict()["summary"]
                except Exception as e:
                    logger.warning(f"Reduce step skipped due to error: {e}")

            # ---- Keywords ----
            if config.get("document_analysis.steps.keywords", False):
                keywords_prompt_cfg = config.get_analysis_prompt(step="keywords")
                if keywords_prompt_cfg:
                    try:
                        keywords_chain = self._build_chain(keywords_prompt_cfg)
                        keywords_result = keywords_chain.invoke({"document_text": combined_summaries_text})
                        final_result["keywords"] = keywords_result.dict().get("keywords", [])
                    except Exception as e:
                        logger.warning(f"Keyword extraction failed: {e}")

            logger.info("Document analysis completed successfully.")
            return final_result

        except Exception as e:
            logger.error(f"Error in DocumentAnalysisPipeline: {e}")
            raise CustomException("Error in DocumentAnalysisPipeline", e)
