# main_analysis.py

from typing import List
from src.components.document_analysis.document_analysis_pipeline import DocumentAnalysisPipeline
from src.common.logging.logger import logger
from src.common.exception.custom_exception import CustomException
from src.configuration.config_loader import config


def main():
    """Main entry point for running the document analysis workflow."""
    try:
        logger.info("🚀 Starting Document Analysis Workflow")

        # Get input directory from config
        input_dir: str = config.get("paths.analysis_dir", "data/analysis")
        logger.info(f"Using input directory: {input_dir}")

        # Initialize pipeline
        pipeline = DocumentAnalysisPipeline()

        # Run workflow
        result = pipeline.run_analysis([input_dir])

        # Output result
        logger.info("✅ Workflow completed successfully")
        print("\n===== DOCUMENT ANALYSIS RESULT =====\n")
        print(result)

    except CustomException as ce:
        logger.error("❌ Workflow failed with custom exception", error=str(ce))
    except Exception as e:
        logger.error("❌ Workflow failed with unexpected exception", error=str(e))


if __name__ == "__main__":
    main()
