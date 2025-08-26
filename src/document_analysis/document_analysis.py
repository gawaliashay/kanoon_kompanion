# src/document_analysis/document_analysis_pipeline.py

from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Any

from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence

from src.document_analysis.document_ingestion import DocumentIngestor
from src.document_analysis.document_preprocessing import DocumentPreprocessingPipeline
from src.utils.analysis_parsers import get_document_analysis_parser
from src.common.logging.logger import logger
from src.common.exception.custom_exception import CustomException
from src.configuration.config_loader import config
from src.utils.model_factory import ModelFactory


class DocumentAnalysisPipeline:
    """Config-driven document analysis pipeline (No RAG)."""

    def __init__(self):
        # Ingest + preprocess
        self.ingestor = DocumentIngestor()
        self.preprocessor = DocumentPreprocessingPipeline()

        # Output parser (summary + keywords)
        self.parser = get_document_analysis_parser()

        # Load base prompt from config (summary_map)
        prompt_cfg = config.get_document_analysis_prompt()
        base_template: str = prompt_cfg["template"]
        input_vars = list(prompt_cfg["input_variables"])

        # Augment prompt to require structured JSON via parser
        augmented_template = (
            f"{base_template}\n\n"
            "Return your answer as valid JSON following this schema:\n"
            "{format_instructions}\n"
        )

        self.prompt = PromptTemplate(
            input_variables=input_vars,
            partial_variables={"format_instructions": self.parser.get_format_instructions()},
            template=augmented_template,
        )

        # LLM
        factory = ModelFactory(config)
        self.llm = factory.load_llm()

        # Build chain
        self.chain: RunnableSequence = self.prompt | self.llm | self.parser

        logger.info("DocumentAnalysisPipeline initialized (No RAG).")

    def run_analysis(self, file_paths: List[str] | None = None) -> Dict[str, Any]:
        try:
            if not file_paths:
                file_paths = [config.get("paths.data_dir")]

            logger.info(f"Starting document analysis. files={file_paths}")

            # ---- Ingest ----
            docs = self.ingestor.load_paths(file_paths)
            if not docs:
                msg = f"No documents ingested from: {file_paths}"
                logger.error(msg)
                raise CustomException(msg, ValueError(file_paths))

            # ---- Preprocess ----
            clean_docs = self.preprocessor.run(docs)
            full_text = " ".join([doc.page_content for doc in clean_docs]).strip()
            if not full_text:
                msg = "After preprocessing, document text is empty."
                logger.error(msg)
                raise CustomException(msg, ValueError("empty_text"))

            # Optional: basic length log (helpful if you later add chunking)
            logger.info(f"Total characters to analyze: {len(full_text)}")

            # ---- Run analysis (single pass, no RAG) ----
            result_obj = self.chain.invoke({"document_text": full_text})
            logger.info("Document analysis completed successfully.")
            return result_obj.dict()

        except Exception as e:
            logger.error(f"Error in DocumentAnalysisPipeline: {e}")
            raise CustomException("Error in DocumentAnalysisPipeline", e)
