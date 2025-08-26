import os
from pathlib import Path

list_of_files = [
    # Configuration
    "configuration/__init__.py",
    "configuration/config.yaml",
    "configuration/config_loader.py",
    
    # Source - Common
    "src/__init__.py",
    "src/common/__init__.py",
    "src/common/logging/__init__.py",
    "src/common/logging/logger.py",
    "src/common/exception/__init__.py",
    "src/common/exception/custom_exception.py",
    
    # Source - Utilities
    "src/utilities/__init__.py",
    "src/utilities/file_utils.py",
    "src/utilities/document_loader.py",
    "src/utilities/text_processing.py",
    "src/utilities/embedding_utils.py",
    "src/utilities/vectorstore_utils.py",
    "src/utilities/llm_utils.py",
    
    # Source - Document Analysis
    "src/document_analysis/__init__.py",
    "src/document_analysis/ingestion.py",
    "src/document_analysis/retrieval.py",
    "src/document_analysis/analysis.py",
    "src/document_analysis/analysis_prompt.py",

    # Source - Document Comparison
    "src/document_comparison/__init__.py",
    "src/document_comparison/ingestion.py",
    "src/document_comparison/retrieval.py",
    "src/document_comparison/comparator.py",
    "src/document_comparison/comparison_prompt.py",
    
    # Source - Document Chat
    "src/document_chat/__init__.py",
    "src/document_chat/ingestion.py",
    "src/document_chat/retrieval.py",
    "src/document_chat/chatbot.py",
    "src/document_chat/doc_chat_prompt.py",
    
    # API
    "api/main.py",
    
    # Root level files
    "requirements.txt",
    "Dockerfile",
    ".dockerignore",
    "setup.py",
    "README.md",
    "app.py",
]

for filepath in list_of_files:
    filepath = Path(filepath)
    filedir, filename = os.path.split(filepath)
    
    # Create directory if it doesn't exist
    if filedir != "":
        os.makedirs(filedir, exist_ok=True)
    
    # Create file if it doesn't exist or is empty
    if filename:  # Only for files, not directories
        if (not os.path.exists(filepath)) or (os.path.getsize(filepath) == 0):
            with open(filepath, "w") as f:
                pass
            print(f"Created: {filepath}")
        else:
            print(f"File already present: {filepath}")
    else:
        print(f"Directory created: {filepath}")