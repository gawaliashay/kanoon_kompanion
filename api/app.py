# app.py

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
import shutil
import tempfile

# Pipelines
from src.components.document_analysis.document_analysis_pipeline import DocumentAnalysisPipeline
from src.components.document_comparison.document_comparison_pipeline import DocumentComparisonPipeline
from src.components.document_qa_chat.document_qa_chat_pipeline import create_document_qa_chat_pipeline

# Session manager
from api.session_manager import save_uploaded_files, save_conversation, get_conversations

# ----------------------------
# Initialize FastAPI
# ----------------------------
app = FastAPI(title="Document Processing API", version="1.0.0")

# Initialize pipelines
analysis_pipeline = DocumentAnalysisPipeline()
comparison_pipeline = DocumentComparisonPipeline()
qa_chat_pipeline = create_document_qa_chat_pipeline()

# ----------------------------
# Response Model
# ----------------------------
class APIResponse(BaseModel):
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None

# ----------------------------
# Welcome Endpoint
# ----------------------------
@app.get("/", response_model=APIResponse, tags=["Welcome"], summary="Welcome", description="API entry point with available routes")
async def welcome():
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
# Document Analysis Endpoints
# ----------------------------
@app.post(
    "/document_analysis",
    response_model=APIResponse,
    tags=["Document Analysis"],
    summary="Upload & Analyze Documents",
    description="Upload one or multiple PDFs to run document analysis."
)
async def document_analysis(files: List[UploadFile] = File(...)):
    try:
        tmp_files = []
        for file in files:
            tmp_path = Path(tempfile.gettempdir()) / file.filename
            with open(tmp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            tmp_files.append(tmp_path)

        session_dir = save_uploaded_files("document_analysis", tmp_files)
        result = analysis_pipeline.run_analysis([str(f) for f in session_dir.iterdir() if f.is_file()])

        return APIResponse(success=True, result={"session": str(session_dir), "analysis": result})
    except Exception as e:
        return JSONResponse(status_code=500, content=APIResponse(success=False, error=str(e)).dict())

@app.get(
    "/document_analysis/recent_files",
    response_model=APIResponse,
    tags=["Document Analysis"],
    summary="Recent Files",
    description="Get all uploaded files grouped by session for Document Analysis."
)
async def recent_files_document_analysis():
    try:
        route_dir = Path("sessions") / "document_analysis"
        sessions = {}
        if route_dir.exists():
            for session_folder in sorted(route_dir.iterdir(), key=lambda x: x.name, reverse=True):
                if session_folder.is_dir() and session_folder.name.startswith("session_"):
                    files = [f.name for f in session_folder.glob("*") if f.is_file()]
                    sessions[session_folder.name] = files
        return APIResponse(success=True, result={"sessions": sessions})
    except Exception as e:
        return JSONResponse(status_code=500, content=APIResponse(success=False, error=str(e)).dict())

# ----------------------------
# Document Comparison Endpoints
# ----------------------------
@app.post(
    "/document_comparison",
    response_model=APIResponse,
    tags=["Document Comparison"],
    summary="Upload & Compare Documents",
    description="Upload two sets of documents (A & B) to run document comparison."
)
async def document_comparison(files_a: List[UploadFile] = File(...), files_b: List[UploadFile] = File(...)):
    try:
        tmp_files_a = []
        for file in files_a:
            tmp_path = Path(tempfile.gettempdir()) / file.filename
            with open(tmp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            tmp_files_a.append(tmp_path)

        tmp_files_b = []
        for file in files_b:
            tmp_path = Path(tempfile.gettempdir()) / file.filename
            with open(tmp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            tmp_files_b.append(tmp_path)

        session_dir = save_uploaded_files("document_comparison", [tmp_files_a, tmp_files_b], comparison=True)
        doc1_files = [str(f) for f in (session_dir / "doc1").glob("*")]
        doc2_files = [str(f) for f in (session_dir / "doc2").glob("*")]

        result = comparison_pipeline.run_comparison(doc1_files, doc2_files)
        return APIResponse(success=True, result={"session": str(session_dir), "comparison": result})
    except Exception as e:
        return JSONResponse(status_code=500, content=APIResponse(success=False, error=str(e)).dict())

@app.get(
    "/document_comparison/recent_files",
    response_model=APIResponse,
    tags=["Document Comparison"],
    summary="Recent Files",
    description="Get all uploaded files grouped by session and doc1/doc2 folders."
)
async def recent_files_document_comparison():
    try:
        route_dir = Path("sessions") / "document_comparison"
        sessions = {}
        if route_dir.exists():
            for session_folder in sorted(route_dir.iterdir(), key=lambda x: x.name, reverse=True):
                if session_folder.is_dir() and session_folder.name.startswith("session_"):
                    doc1_files = [f.name for f in (session_folder / "doc1").glob("*") if f.is_file()]
                    doc2_files = [f.name for f in (session_folder / "doc2").glob("*") if f.is_file()]
                    sessions[session_folder.name] = {"doc1": doc1_files, "doc2": doc2_files}
        return APIResponse(success=True, result={"sessions": sessions})
    except Exception as e:
        return JSONResponse(status_code=500, content=APIResponse(success=False, error=str(e)).dict())

# ----------------------------
# Document QA Chat Endpoints
# ----------------------------
@app.post(
    "/document_qa_chat",
    response_model=APIResponse,
    tags=["Document QA Chat"],
    summary="Upload Documents & Ask a Question",
    description="Upload one or more documents and ask a question for QA. Documents are required."
)
async def document_qa_chat(question: str = Form(...), files: List[UploadFile] = File(...)):
    try:
        if not files:
            return JSONResponse(
                status_code=400,
                content=APIResponse(success=False, error="At least one document must be uploaded for QA session.").dict()
            )

        tmp_files = []
        for file in files:
            tmp_path = Path(tempfile.gettempdir()) / file.filename
            with open(tmp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            tmp_files.append(tmp_path)

        session_dir = save_uploaded_files("document_qa_chat", tmp_files)
        session_number = int(session_dir.name.split("_")[1])

        # Call pipeline without 'docs' argument
        result = qa_chat_pipeline.query(question)

        if result.get("success"):
            save_conversation("document_qa_chat", session_number, question, result.get("answer"))

        return APIResponse(success=True, result={
            "session": str(session_dir),
            "uploaded_files": [f.name for f in session_dir.iterdir() if f.is_file()],
            "qa_result": result
        })
    except Exception as e:
        return JSONResponse(status_code=500, content=APIResponse(success=False, error=str(e)).dict())

@app.get(
    "/document_qa_chat/recent_files",
    response_model=APIResponse,
    tags=["Document QA Chat"],
    summary="Recent Files",
    description="Get all uploaded files grouped by session for QA chat."
)
async def recent_files_document_qa_chat():
    try:
        route_dir = Path("sessions") / "document_qa_chat"
        sessions = {}
        if route_dir.exists():
            for session_folder in sorted(route_dir.iterdir(), key=lambda x: x.name, reverse=True):
                if session_folder.is_dir() and session_folder.name.startswith("session_"):
                    files = [f.name for f in session_folder.glob("*") if f.is_file()]
                    sessions[session_folder.name] = files
        return APIResponse(success=True, result={"sessions": sessions})
    except Exception as e:
        return JSONResponse(status_code=500, content=APIResponse(success=False, error=str(e)).dict())

@app.get(
    "/document_qa_chat/conversation_history/{session_number}",
    response_model=APIResponse,
    tags=["Document QA Chat"],
    summary="Conversation History",
    description="Get the QA chat conversation history for a session."
)
async def conversation_history_qa_chat(session_number: int):
    try:
        history = get_conversations("document_qa_chat", session_number)
        return APIResponse(success=True, result={"conversations": history})
    except Exception as e:
        return JSONResponse(status_code=500, content=APIResponse(success=False, error=str(e)).dict())
