from fastapi import FastAPI, UploadFile, File, Form, Request
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
@app.get("/", response_model=APIResponse, tags=["Welcome"])
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
# Document Analysis
# ----------------------------
@app.post("/document_analysis", response_model=APIResponse, tags=["Document Analysis"])
async def document_analysis(files: List[UploadFile] = File(..., multiple=True)):
    try:
        tmp_files = []
        for file in files:
            tmp_path = Path(tempfile.gettempdir()) / file.filename
            with tmp_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            tmp_files.append(tmp_path)

        session_dir = save_uploaded_files("document_analysis", tmp_files)
        uploaded_files = [f.name for f in session_dir.iterdir() if f.is_file()]

        result = analysis_pipeline.run_analysis([str(f) for f in session_dir.iterdir() if f.is_file()])

        return APIResponse(success=True, result={
            "session": str(session_dir),
            "uploaded_files": uploaded_files,
            "analysis": result
        })
    except Exception as e:
        return JSONResponse(status_code=500, content=APIResponse(success=False, error=str(e)).dict())


# ----------------------------
# Document Comparison
# ----------------------------
@app.post("/document_comparison", response_model=APIResponse, tags=["Document Comparison"])
async def document_comparison(
    files_a: List[UploadFile] = File(..., multiple=True),
    files_b: List[UploadFile] = File(..., multiple=True)
):
    try:
        tmp_files_a, tmp_files_b = [], []
        for file in files_a:
            tmp_path = Path(tempfile.gettempdir()) / file.filename
            with tmp_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            tmp_files_a.append(tmp_path)

        for file in files_b:
            tmp_path = Path(tempfile.gettempdir()) / file.filename
            with tmp_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            tmp_files_b.append(tmp_path)

        session_dir = save_uploaded_files("document_comparison", [tmp_files_a, tmp_files_b], comparison=True)

        doc1_files = [f.name for f in (session_dir / "doc1").glob("*")]
        doc2_files = [f.name for f in (session_dir / "doc2").glob("*")]

        result = comparison_pipeline.run_comparison(
            [str(f) for f in (session_dir / "doc1").glob("*")],
            [str(f) for f in (session_dir / "doc2").glob("*")]
        )

        return APIResponse(success=True, result={
            "session": str(session_dir),
            "uploaded_files": {"doc1": doc1_files, "doc2": doc2_files},
            "comparison": result
        })
    except Exception as e:
        return JSONResponse(status_code=500, content=APIResponse(success=False, error=str(e)).dict())


# ----------------------------
# Document QA Chat
# ----------------------------
@app.post("/document_qa_chat", response_model=APIResponse, tags=["Document QA Chat"])
async def document_qa_chat(
    request: Request,
    question: str = Form(...),
    files: List[UploadFile] = File(None, multiple=True)
):
    """
    Upload documents (required for first request in a session).
    Maintains conversation history per client IP like a chatbot.
    """
    client_id = request.client.host

    try:
        uploaded_files = []

        # Start new session if files are uploaded
        if files:
            tmp_files = []
            for file in files:
                tmp_path = Path(tempfile.gettempdir()) / file.filename
                with tmp_path.open("wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
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
                    content={"success": False, "error": "Please upload documents first."}
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
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})
