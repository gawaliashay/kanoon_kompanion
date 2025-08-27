# main_comparison.py
 

import argparse
from typing import Dict
from src.document_comparison.document_comparison_pipeline import DocumentComparisonPipeline
from src.common.logging.logger import logger
from src.common.exception.custom_exception import CustomException
from src.configuration.config_loader import config


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for overriding input directories."""
    parser = argparse.ArgumentParser(description="Run Document Comparison Workflow")
    parser.add_argument("--dir_a", type=str, help="Path to first comparison directory")
    parser.add_argument("--dir_b", type=str, help="Path to second comparison directory")
    return parser.parse_args()


def main():
    """Main entry point for running the document comparison workflow."""
    try:
        logger.info("🚀 Starting Document Comparison Workflow")

        args = parse_args()
        paths: Dict[str, str] = config.get_comparison_paths()

        # Allow CLI override
        input_dir_a = args.dir_a or paths["dir_a"]
        input_dir_b = args.dir_b or paths["dir_b"]

        logger.info(f"Using input directories:\n - A: {input_dir_a}\n - B: {input_dir_b}")

        # Initialize pipeline
        pipeline = DocumentComparisonPipeline()

        # Run workflow
        result = pipeline.run_comparison([input_dir_a], [input_dir_b])

        # Output result
        logger.info("✅ Workflow completed successfully")
        print("\n===== DOCUMENT COMPARISON RESULT =====\n")
        print(result)

    except CustomException as ce:
        logger.error("❌ Workflow failed with custom exception", error=str(ce))
    except Exception as e:
        logger.error("❌ Workflow failed with unexpected exception", error=str(e))


if __name__ == "__main__":
    main()
