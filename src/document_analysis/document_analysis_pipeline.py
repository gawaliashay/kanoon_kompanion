# src/document_analysis/document_analysis_pipeline.py

from __future__ import annotations
from typing import List, Dict, Any

from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence

from src.common.ingestion.document_ingestor import DocumentIngestor
from src.document_analysis.document_preprocessing import DocumentPreprocessingPipeline
from src.document_analysis.analysis_parsers import get_document_analysis_parser, get_keywords_parser
from src.common.logging.logger import logger
from src.common.exception.custom_exception import CustomException
from src.configuration.config_loader import config
from src.utils.select_model import ModelFactory


class DocumentAnalysisPipeline:
    """Config-driven document analysis pipeline (No RAG). Batch-wise, config-controlled."""

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

            
    def _build_chain(self, prompt_cfg: Dict[str, Any], step: str) -> RunnableSequence:
        try:
            if step == "keywords":
                parser = get_keywords_parser()
            else:
                parser = self.parser  # default summary+reduce parser

            prompt = PromptTemplate(
                input_variables=prompt_cfg["input_variables"],
                partial_variables={"format_instructions": parser.get_format_instructions()},
                template=prompt_cfg["template"]
            )
            return prompt | self.llm | parser
        except Exception as e:
            logger.error(f"Failed to build chain: {e}")
            raise CustomException("Failed to build chain", e)


    def _batch_process_chunks(self, chunks: List[str], prompt_step: str) -> List[str]:
        """Process chunks in batches using map-step prompts from config."""
        results = []
        prompt_cfg = config.get_analysis_prompt(step=prompt_step)
        if not prompt_cfg:
            raise CustomException(f"Prompt config '{prompt_step}' not found", ValueError(prompt_step))
        chain = self._build_chain(prompt_cfg, prompt_step)

        batch_size = config.get("document_analysis.batch_size", 10)  # configurable
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            for chunk_text in batch:
                try:
                    result = chain.invoke({"document_text": chunk_text})
                    results.append(result.dict()["summary"])
                except Exception as e:
                    logger.warning(f"Chunk failed: {e}")
                    results.append(chunk_text[:config.get("document_analysis.chunk_fallback_length", 500)])
        return results


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

            # Extract raw text from chunks
            chunk_texts = [chunk.page_content for chunk in clean_docs]

            # ---- Map Step (chunk-wise) ----
            chunk_summaries = self._batch_process_chunks(chunk_texts, prompt_step="summary_map")

            # ---- Reduce Step (always run) ----
            reduce_prompt_cfg = config.get_analysis_prompt(step="summary_reduce")
            if not reduce_prompt_cfg:
                raise CustomException(
                    "Reduce prompt config 'summary_reduce' not found", 
                    ValueError("missing_reduce_prompt")
                )

            reduce_chain = self._build_chain(reduce_prompt_cfg, step="summary_reduce")
            combined_text = "\n\n".join(chunk_summaries)
            try:
                reduce_result = reduce_chain.invoke({"chunk_summaries": combined_text})
                final_summary = reduce_result.dict()["summary"]
            except Exception as e:
                logger.warning(f"Reduce step failed: {e}. Falling back to combined chunk summaries.")
                final_summary = combined_text

            final_result: Dict[str, Any] = {"summary": final_summary}

            # ---- Keywords (optional) ----
            if config.get("document_analysis.steps.keywords", False):
                keywords_prompt_cfg = config.get_analysis_prompt(step="keywords")
                if keywords_prompt_cfg:
                    try:
                        keywords_chain = self._build_chain(keywords_prompt_cfg, step="keywords")
                        keywords_result = keywords_chain.invoke({"document_text": final_summary})
                        final_result["keywords"] = keywords_result.dict().get("keywords", [])
                    except Exception as e:
                        logger.warning(f"Keyword extraction failed: {e}")

            logger.info("Document analysis completed successfully.")
            return final_result

        except Exception as e:
            logger.error(f"Error in DocumentAnalysisPipeline: {e}")
            raise CustomException("Error in DocumentAnalysisPipeline", e)
