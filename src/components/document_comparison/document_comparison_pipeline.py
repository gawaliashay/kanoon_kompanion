# src\document_comparison\document_comparison_pipeline.py

from __future__ import annotations
from typing import List, Dict, Any, Union
import argparse

from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence

from src.components.document_comparison.document_ingestion_comparison import DocumentComparisonIngestor
from src.components.document_comparison.document_preprocessing import ComparisonPreprocessingPipeline
from src.components.document_comparison.comparison_parsers import get_document_comparison_parser
from src.common.logging.logger import logger
from src.common.exception.custom_exception import CustomException
from src.configuration.config_loader import config
from src.configuration.prompts_loader import prompts
from src.components.model_loader import ModelFactory


class DocumentComparisonPipeline:
    """Config-driven pipeline for comparing two sets of documents."""

    def __init__(self):
        try:
            # Ingest + preprocess
            self.ingestor = DocumentComparisonIngestor()
            self.preprocessor = ComparisonPreprocessingPipeline()
            self.parser = get_document_comparison_parser()

            # CLI strategy override
            cli_parser = argparse.ArgumentParser()
            cli_parser.add_argument(
                "--strategy",
                choices=config.get_document_comparison_strategies(),
                help="Choose document comparison strategy (chunkwise/holistic)",
            )
            args, _ = cli_parser.parse_known_args()
            self.strategy = args.strategy or config.get("document_comparison.default_prompt")
            logger.info(f"Using comparison strategy: {self.strategy}")

            # LLM
            factory = ModelFactory(config)
            self.llm = factory.load_llm()

            # ADD THIS DEBUGGING
            logger.info(f"Loaded LLM: {self.llm}")
            logger.info(f"LLM type: {type(self.llm)}")
            if hasattr(self.llm, 'max_tokens'):
                logger.info(f"Actual max_tokens: {self.llm.max_tokens}")
            else:
                logger.warning("LLM has no max_tokens attribute")

            # Load chains dynamically from enabled steps
            steps_cfg = config.get("document_comparison.steps", {})
            self.chains: Dict[str, RunnableSequence] = {}
            for step_name, enabled in steps_cfg.items():
                if not enabled:
                    continue

                prompt_cfg = prompts.get_comparison_prompt(step_name)
                template: str = prompt_cfg["template"]
                augmented_template = (
                    f"{template}\n\nReturn your answer as valid JSON following this schema:\n"
                    "{format_instructions}\n"
                )

                prompt = PromptTemplate(
                    input_variables=list(prompt_cfg["input_variables"]),
                    partial_variables={"format_instructions": self.parser.get_format_instructions()},
                    template=augmented_template,
                )
                self.chains[step_name] = prompt | self.llm | self.parser

            logger.info(f"DocumentComparisonPipeline initialized with chains: {list(self.chains.keys())}")

        except Exception as e:
            logger.error(f"Failed to initialize DocumentComparisonPipeline: {e}")
            raise CustomException("Pipeline initialization failed", e)

    def run_comparison(
        self,
        file_paths_a: List[str] | None = None,
        file_paths_b: List[str] | None = None
    ) -> Dict[str, Any]:
        if (file_paths_a and not file_paths_b) or (file_paths_b and not file_paths_a):
            raise CustomException("Both document sets (A and B) must be provided.", ValueError("missing_inputs"))

        # ---- Ingest ----
        if file_paths_a or file_paths_b:
            # explicit file paths
            docs_a = self.ingestor.loader_a.load_paths(file_paths_a or [])
            docs_b = self.ingestor.loader_b.load_paths(file_paths_b or [])
        else:
            # default directories from config
            docs_a, docs_b = self.ingestor.load_documents_pair()

        if not docs_a or not docs_b:
            raise CustomException("One or both document sets failed to ingest.", ValueError("empty_sets"))

        # ---- Preprocess + chunk ----
        clean_a, clean_b = self.preprocessor.run_pair(docs_a, docs_b)

        # ---- Strategy execution ----
        if self.strategy == "holistic_compare":
            text_a = " ".join([doc.page_content for doc in clean_a]).strip()
            text_b = " ".join([doc.page_content for doc in clean_b]).strip()
            if not text_a or not text_b:
                raise CustomException("After preprocessing, one or both texts are empty.", ValueError("empty_text"))

            result_obj = self.chains["holistic_compare"].invoke({
                "doc1_text": text_a,
                "doc2_text": text_b,
            })
            return {"strategy": "holistic", "result": result_obj.dict()}

        elif self.strategy == "compare_docs":
            comparisons = []
            max_len = max(len(clean_a), len(clean_b))
            for i in range(max_len):
                chunk_a = clean_a[i].page_content if i < len(clean_a) else ""
                chunk_b = clean_b[i].page_content if i < len(clean_b) else ""
                if not chunk_a and not chunk_b:
                    continue
                result_obj = self.chains["compare_docs"].invoke({
                    "doc1_chunk": chunk_a,
                    "doc2_chunk": chunk_b,
                })
                comparisons.append(result_obj.dict())

            # REDUCE step
            combined_text = "\n\n".join([str(c) for c in comparisons])
            reduced_obj = self.chains["chunk_reduce"].invoke({"chunk_comparisons": combined_text})

            return {"strategy": "chunkwise", "comparisons": comparisons, "summary": reduced_obj.dict()}

        else:
            raise CustomException(f"Unknown strategy: {self.strategy}", ValueError("invalid_strategy"))
