# src\document_analysis\document_analysis_pipeline.py


from __future__ import annotations
from typing import List, Dict, Any

from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence

from src.components.document_loader import DocumentIngestor
from src.components.document_analysis.document_preprocessing import DocumentPreprocessingPipeline
from src.components.document_analysis.analysis_parsers import get_document_analysis_parser
from src.common.logging.logger import logger
from src.common.exception.custom_exception import CustomException
from src.configuration.config_loader import config
from src.components.model_loader import ModelFactory


class DocumentAnalysisPipeline:
    """Config-driven document analysis pipeline (No RAG).
    Always runs summary_map → summary_reduce steps.
    """

    def __init__(self):
        try:
            self.ingestor = DocumentIngestor()
            self.preprocessor = DocumentPreprocessingPipeline()
            self.parser = get_document_analysis_parser()
            factory = ModelFactory(config)
            self.llm = factory.load_llm()
            logger.info("DocumentAnalysisPipeline initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize DocumentAnalysisPipeline: {e}")
            raise CustomException("Pipeline initialization failed", e)

    def _build_chain(self, prompt_cfg: Dict[str, Any]) -> RunnableSequence:
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

    def _batch_process(self, texts: List[str], step: str) -> List[str]:
        """Run a step prompt (e.g., summary_map) across chunks in batches."""
        results = []
        prompt_cfg = config.get_analysis_prompt(step)
        if not prompt_cfg:
            raise CustomException(f"Prompt config '{step}' not found", ValueError(step))
        chain = self._build_chain(prompt_cfg)

        batch_size = config.get("document_analysis.batch_size", 10)
        fallback_len = config.get("document_analysis.chunk_fallback_length", 500)

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            for text in batch:
                try:
                    result = chain.invoke({prompt_cfg["input_variables"][0]: text})
                    results.append(result.dict()["summary"])
                except Exception as e:
                    logger.warning(f"Step '{step}' failed on chunk: {e}")
                    results.append(text[:fallback_len])
        return results

    def run_analysis(self, file_paths: List[str]) -> Dict[str, Any]:
        try:
            logger.info(f"Starting document analysis. files={file_paths}")

            # ---- Ingest ----
            docs = self.ingestor.load_paths(file_paths)
            if not docs:
                raise CustomException("No documents ingested", ValueError(file_paths))

            # ---- Preprocess + Chunk ----
            clean_docs = self.preprocessor.run(docs)
            if not clean_docs:
                raise CustomException("No chunks created from documents", ValueError("empty_chunks"))

            chunk_texts = [chunk.page_content for chunk in clean_docs]
            logger.info(f"Total chunks to analyze: {len(chunk_texts)}")

            # ---- Mandatory Map Step ----
            chunk_summaries = self._batch_process(chunk_texts, "summary_map")

            # ---- Mandatory Reduce Step ----
            combined = "\n\n".join(chunk_summaries)
            reduced = self._batch_process([combined], "summary_reduce")[0]

            logger.info("Document analysis completed successfully.")
            return {"summary": reduced}

        except Exception as e:
            logger.error(f"Error in DocumentAnalysisPipeline: {e}")
            raise CustomException("Error in DocumentAnalysisPipeline", e)
