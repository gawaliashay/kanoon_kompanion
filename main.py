# main.py

from src.document_analysis.document_analysis import DocumentAnalysisPipeline
from src.common.logging.logger import logger
from src.common.exception.custom_exception import CustomException
from src.configuration.config_loader import config


def main():
    """Main entry point for testing the document analysis workflow."""
    try:
        logger.info("🚀 Starting Document Analysis Workflow")

        # Get input directory from config
        input_dir = config.get("paths.data_dir", "data/uploads")
        logger.info(f"Using input directory: {input_dir}")

        # Initialize pipeline
        pipeline = DocumentAnalysisPipeline()

        # Run workflow
        result = pipeline.run_analysis([input_dir])

        # Print result (or persist as needed)
        logger.info("✅ Workflow completed successfully")
        print("\n===== DOCUMENT ANALYSIS RESULT =====\n")
        print(result)

    except CustomException as ce:
        logger.error("❌ Workflow failed with custom exception", error=str(ce))
    except Exception as e:
        logger.error("❌ Workflow failed with unexpected exception", error=str(e))


if __name__ == "__main__":
    main()
