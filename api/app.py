# api\app.py

from fastapi import FastAPI, UploadFile, File, Form, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
import shutil
import tempfile
import os
import uuid
import json
from datetime import datetime

from src.common.logging.logger import logger
from src.common.exception.custom_exception import CustomException

# Pipelines
from src.components.document_analysis.document_analysis_pipeline import DocumentAnalysisPipeline
from src.components.document_comparison.document_comparison_pipeline import DocumentComparisonPipeline
from src.components.document_qa_chat.document_qa_chat_pipeline import create_document_qa_chat_pipeline

# Session manager
from api.session_manager import save_uploaded_files, save_conversation, get_conversations, save_analysis_result, save_comparison_result

# ----------------------------
# Initialize FastAPI
# ----------------------------
app = FastAPI(title="Document Processing API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
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
        
        tmp_files = []
        for file in files:
            # Create unique filename to avoid conflicts
            unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
            tmp_path = Path(tempfile.gettempdir()) / unique_filename
            
            # Read file content before it gets closed
            content = await file.read()
            with tmp_path.open("wb") as buffer:
                buffer.write(content)
            tmp_files.append(tmp_path)

        session_dir = save_uploaded_files("document_analysis", tmp_files)
        uploaded_files = [f.name for f in session_dir.iterdir() if f.is_file()]

        result = analysis_pipeline.run_analysis([str(f) for f in session_dir.iterdir() if f.is_file()])

        # Save analysis result to session directory
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
        
        tmp_files_a, tmp_files_b = [], []
        
        # Process files_a
        for file in files_a:
            unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
            tmp_path = Path(tempfile.gettempdir()) / unique_filename
            content = await file.read()
            with tmp_path.open("wb") as buffer:
                buffer.write(content)
            tmp_files_a.append(tmp_path)

        # Process files_b
        for file in files_b:
            unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
            tmp_path = Path(tempfile.gettempdir()) / unique_filename
            content = await file.read()
            with tmp_path.open("wb") as buffer:
                buffer.write(content)
            tmp_files_b.append(tmp_path)

        session_dir = save_uploaded_files(
            "document_comparison", 
            tmp_files_a + tmp_files_b, 
            comparison=True
        )

        doc1_files = [f.name for f in (session_dir / "doc1").iterdir() if f.is_file()]
        doc2_files = [f.name for f in (session_dir / "doc2").iterdir() if f.is_file()]

        result = comparison_pipeline.run_comparison(
            [str(f) for f in (session_dir / "doc1").iterdir() if f.is_file()],
            [str(f) for f in (session_dir / "doc2").iterdir() if f.is_file()]
        )

        # Save comparison result to session directory
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
# Document QA Chat
# ----------------------------
@app.post("/document_qa_chat", response_model=APIResponse, tags=["Document QA Chat"])
async def document_qa_chat(
    request: Request,
    question: str = Form(...),
    files: List[UploadFile] = File(None)
):
    """
    Upload documents (required for first request in a session).
    Maintains conversation history per client IP like a chatbot.
    """
    client_id = request.client.host

    try:
        uploaded_files = []
        session_number = None

        # Start new session if files are uploaded
        if files and len(files) > 0:
            tmp_files = []
            for file in files:
                unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
                tmp_path = Path(tempfile.gettempdir()) / unique_filename
                content = await file.read()
                with tmp_path.open("wb") as buffer:
                    buffer.write(content)
                tmp_files.append(tmp_path)

            session_dir = save_uploaded_files("document_qa_chat", tmp_files)
            session_number = int(session_dir.name.split("_")[1])
            user_sessions[client_id] = session_number

            uploaded_doc_paths = [str(f) for f in session_dir.iterdir() if f.is_file()]
            uploaded_files = [Path(f).name for f in uploaded_doc_paths]

            # Ingest new docs
            qa_chat_pipeline.ingest_new_documents(uploaded_doc_paths)
        else:
            # Continue existing session
            session_number = user_sessions.get(client_id)
            if session_number is None:
                return JSONResponse(
                    status_code=400,
                    content=APIResponse(success=False, error="Please upload documents first.").dict()
                )

        # Query pipeline
        result = qa_chat_pipeline.query(question)

        # Save chat
        if result.get("success"):
            save_conversation("document_qa_chat", session_number, question, result.get("answer"), uploaded_files)

        # Full history
        history = get_conversations("document_qa_chat", session_number)

        return APIResponse(success=True, result={
            "session": session_number,
            "uploaded_files": uploaded_files,
            "latest_answer": result.get("answer"),
            "conversation_history": history
        })

    except Exception as e:
        logger.error(f"QA chat error: {str(e)}")
        return JSONResponse(
            status_code=500, 
            content=APIResponse(success=False, error=str(e)).dict()
        )