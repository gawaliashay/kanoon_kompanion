# api\app.py

from fastapi import FastAPI, UploadFile, File, Form, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
from datetime import datetime

from src.common.logging.logger import logger
from src.common.exception.custom_exception import CustomException

# Pipelines
from src.components.document_analysis.document_analysis_pipeline import DocumentAnalysisPipeline
from src.components.document_comparison.document_comparison_pipeline import DocumentComparisonPipeline
from src.components.document_qa_chat.document_qa_chat_pipeline import create_document_qa_chat_pipeline

# Storage / Session managers
from storage_manager.file_manager import (
    save_uploaded_files,
    save_analysis_result,
    save_comparison_result,
    save_conversation_file,
    load_conversation_file,
)

# ----------------------------
# Initialize FastAPI
# ----------------------------
app = FastAPI(title="Document Processing API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Pipelines
analysis_pipeline = DocumentAnalysisPipeline()
comparison_pipeline = DocumentComparisonPipeline()
qa_chat_pipeline = create_document_qa_chat_pipeline()

# Active sessions per client IP
user_sessions: dict[str, int] = {}
conversation_cache: dict[str, list] = {}  # cache per client until END

# ----------------------------
# Response Model
# ----------------------------
class APIResponse(BaseModel):
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None

# ----------------------------
# Welcome
# ----------------------------
@app.get("/", response_class=HTMLResponse)
async def welcome(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api", response_model=APIResponse, tags=["Welcome"])
async def api_welcome():
    return APIResponse(
        success=True,
        result={
            "message": "🚀 Welcome to Document Processing API",
            "routes": {
                "Document Analysis": "/document_analysis",
                "Document Comparison": "/document_comparison",
                "Document QA Chat": "/document_qa_chat",
            },
        },
    )

# ----------------------------
# Document Analysis
# ----------------------------
@app.post("/document_analysis", response_model=APIResponse, tags=["Document Analysis"])
async def document_analysis(files: List[UploadFile] = File(...)):
    try:
        if not files:
            raise HTTPException(status_code=400, detail="No files uploaded")

        session_dir = save_uploaded_files("document_analysis", files)
        uploaded_files = [f.name for f in session_dir.iterdir() if f.is_file()]

        result = analysis_pipeline.run_analysis([str(f) for f in session_dir.iterdir() if f.is_file()])

        session_number = int(session_dir.name.split("_")[1])
        save_analysis_result("document_analysis", session_number, result, uploaded_files)

        return APIResponse(success=True, result={
            "session": str(session_dir),
            "uploaded_files": uploaded_files,
            "analysis": result
        })
    except Exception as e:
        logger.error(f"Document analysis error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content=APIResponse(success=False, error=str(e)).dict()
        )

# ----------------------------
# Document Comparison
# ----------------------------
@app.post("/document_comparison", response_model=APIResponse, tags=["Document Comparison"])
async def document_comparison(
    files_a: List[UploadFile] = File(...),
    files_b: List[UploadFile] = File(...)
):
    try:
        if not files_a or not files_b:
            raise HTTPException(status_code=400, detail="Both file sets are required")

        session_dir = save_uploaded_files(
            "document_comparison",
            files_a + files_b,
            comparison=True
        )

        doc1_dir = session_dir / "doc1"
        doc2_dir = session_dir / "doc2"

        doc1_files = [f.name for f in doc1_dir.iterdir() if f.is_file()]
        doc2_files = [f.name for f in doc2_dir.iterdir() if f.is_file()]

        result = comparison_pipeline.run_comparison(
            [str(f) for f in doc1_dir.iterdir() if f.is_file()],
            [str(f) for f in doc2_dir.iterdir() if f.is_file()]
        )

        session_number = int(session_dir.name.split("_")[1])
        save_comparison_result("document_comparison", session_number, result, doc1_files, doc2_files)

        return APIResponse(success=True, result={
            "session": str(session_dir),
            "uploaded_files": {"doc1": doc1_files, "doc2": doc2_files},
            "comparison": result
        })
    except Exception as e:
        logger.error(f"Document comparison error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content=APIResponse(success=False, error=str(e)).dict()
        )

# ----------------------------
# Document QA Chat - FIXED
# ----------------------------
from pydantic import BaseModel
from typing import Optional, List

class ChatRequest(BaseModel):
    question: Optional[str] = None
    files: List[str] = []  # This will be handled separately for file uploads

@app.post("/document_qa_chat", response_model=APIResponse, tags=["Document QA Chat"])
async def document_qa_chat(
    request: Request,
    question: Optional[str] = Form(None),
    files: List[UploadFile] = File(None)
):
    client_id = request.client.host
    logger.info(f"QA Chat request from {client_id}: question={question}, files={files}")

    try:
        # -----------------------------------
        # Step 1: Handle new document upload
        # -----------------------------------
        if files and len(files) > 0:
            logger.info(f"Processing file upload: {[f.filename for f in files]}")
            
            # Check if user already has an active session
            existing_session = user_sessions.get(client_id)
            if existing_session is not None:
                # Save existing conversation before starting new session
                old_history = conversation_cache.pop(client_id, [])
                if old_history:
                    save_conversation_file("document_qa_chat", existing_session, old_history)

            # Create a new session for this document upload
            session_dir = save_uploaded_files("document_qa_chat", files)
            session_number = int(session_dir.name.split("_")[1])
            user_sessions[client_id] = session_number

            uploaded_doc_paths = [str(f) for f in session_dir.iterdir() if f.is_file()]
            uploaded_files_names = [Path(f).name for f in uploaded_doc_paths]

            # Ingest the new documents
            qa_chat_pipeline.ingest_new_documents(uploaded_doc_paths)

            # Initialize conversation cache for this session
            conversation_cache[client_id] = [{
                "timestamp": datetime.utcnow().isoformat(),
                "type": "document_upload",
                "uploaded_files": uploaded_files_names,
                "message": "Documents uploaded successfully"
            }]

            return APIResponse(
                success=True,
                result={
                    "session": session_number,
                    "uploaded_files": uploaded_files_names,
                    "message": "Documents uploaded and session started",
                    "conversation_history": conversation_cache[client_id]
                }
            )

        # -----------------------------------
        # Step 2: Handle question query
        # -----------------------------------
        if not question:
            return JSONResponse(
                status_code=422,
                content=APIResponse(success=False, error="Question is required when no files are provided").dict()
            )

        session_number = user_sessions.get(client_id)
        if session_number is None:
            return JSONResponse(
                status_code=400,
                content=APIResponse(success=False, error="Please upload documents first.").dict()
            )

        # Query the pipeline
        result = qa_chat_pipeline.query(question)
        answer = result.get("answer", "I'm sorry, I couldn't process your question.")

        # Append to conversation cache
        conversation_cache.setdefault(client_id, []).append({
            # "timestamp": datetime.utcnow().isoformat(),
            # "type": "qa",
            "question": question,
            "answer": answer
        })

        return APIResponse(
            success=True,
            result={
                "session": session_number,
                "latest_answer": answer,
                "conversation_history": conversation_cache[client_id]
            }
        )

    except Exception as e:
        logger.error(f"QA chat error: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content=APIResponse(success=False, error=f"Internal server error: {str(e)}").dict()
        )

# ----------------------------
# Get Current Chat Session - FIXED
# ----------------------------
@app.get("/document_qa_chat/session", response_model=APIResponse, tags=["Document QA Chat"])
async def get_current_session(request: Request):
    """Get current active session and conversation history"""
    client_id = request.client.host
    session_number = user_sessions.get(client_id)
    
    if session_number is None:
        return APIResponse(
            success=False, 
            error="No active session",
            result={"session": None, "conversation_history": []}
        )
    
    history = conversation_cache.get(client_id, [])
    
    return APIResponse(
        success=True,
        result={
            "session": session_number,
            "conversation_history": history
        }
    )

# ----------------------------
# End QA Chat - FIXED
# ----------------------------
@app.post("/document_qa_chat/end", response_model=APIResponse, tags=["Document QA Chat"])
async def end_chat(request: Request):
    client_id = request.client.host
    session_number = user_sessions.pop(client_id, None)

    if session_number is None:
        return APIResponse(success=False, error="No active session to end")

    history = conversation_cache.pop(client_id, [])
    if history:
        save_conversation_file("document_qa_chat", session_number, history)

    return APIResponse(
        success=True,
        result={
            "message": "Chat session ended and conversation saved",
            "session": session_number,
            "conversation_history": history
        }
    )

# ----------------------------
# Clear Chat Session (for testing) - FIXED
# ----------------------------
@app.post("/document_qa_chat/clear", response_model=APIResponse, tags=["Document QA Chat"])
async def clear_chat_session(request: Request):
    """Clear current chat session"""
    client_id = request.client.host
    session_number = user_sessions.pop(client_id, None)
    conversation_cache.pop(client_id, None)
    
    return APIResponse(
        success=True,
        result={
            "message": "Chat session cleared",
            "session": session_number
        }
    )