# main_qa_chat.py

import os
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent))

from src.components.document_qa_chat.document_qa_chat_pipeline import create_document_qa_chat_pipeline
from src.common.logging.logger import logger


def main():
    """Simple demonstration of the Document QA Chat Pipeline."""
    
    print("🚀 Document QA Chat Pipeline")
    print("=" * 50)
    
    try:
        # Create the pipeline
        pipeline = create_document_qa_chat_pipeline()
        
        print("✅ Pipeline initialized successfully!")
        print(f"📁 Loaded documents from: data/document_qa_chat/")
        print("=" * 50)
        
        # Sample questions about anxiety (based on your documents)
        sample_questions = [
            "What are the physical symptoms of anxiety?",
            "How does anxiety affect thinking patterns?"
        ]
        
        for i, question in enumerate(sample_questions, 1):
            print(f"\n💬 Question {i}: {question}")
            print("-" * 40)
            
            # Query the pipeline
            result = pipeline.query(question)
            
            if result['success']:
                print(f"🤖 Answer: {result['answer']}")
                print(f"📊 Retrieved {result['retrieved_docs_count']} relevant documents")
            else:
                print(f"❌ Error: {result['answer']}")
                if 'error' in result:
                    print(f"   Technical details: {result['error']}")
        
        print("\n" + "=" * 50)
        print("🎉 Demo completed successfully!")
        
    except Exception as e:
        print(f"❌ Failed to initialize pipeline: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())