# api/app.py
from fastapi import FastAPI, UploadFile, File, Form, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uuid
import json

from api.config import settings
from src.common.logging.logger import logger
from src.common.exception.custom_exception import CustomException

# Pipelines
from src.components.document_analysis.document_analysis_pipeline import DocumentAnalysisPipeline
from src.components.document_comparison.document_comparison_pipeline import DocumentComparisonPipeline
from src.components.document_qa_chat.document_qa_chat_pipeline import create_document_qa_chat_pipeline

# Updated session manager
from api.session_manager import save_uploaded_files, save_conversation, get_conversations, save_analysis_result, save_comparison_result

# ----------------------------
# Initialize FastAPI
# ----------------------------
app = FastAPI(
    title=settings.project_name,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

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
# Health Check (for ALB)
# ----------------------------
@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "service": settings.project_name}


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
            "message": f"Welcome to {settings.project_name}",
            "environment": settings.environment,
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
        
        # Read file contents and prepare for S3 upload
        file_contents = []
        for file in files:
            content = await file.read()
            unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
            file_contents.append((unique_filename, content))

        # Save files to S3 and get session number
        session_number = save_uploaded_files("document_analysis", file_contents)
        uploaded_files = [f[0] for f in file_contents]

        # Process files - you'll need to adapt your pipelines to work with S3
        # For now, using temporary files (not ideal for production)
        import tempfile
        import os
        tmp_files = []
        for filename, content in file_contents:
            tmp_path = os.path.join(tempfile.gettempdir(), filename)
            with open(tmp_path, 'wb') as f:
                f.write(content)
            tmp_files.append(tmp_path)

        result = analysis_pipeline.run_analysis(tmp_files)

        # Cleanup temp files
        for tmp_file in tmp_files:
            try:
                os.unlink(tmp_file)
            except:
                pass

        # Save analysis result
        save_analysis_result("document_analysis", session_number, result, uploaded_files)

        return APIResponse(success=True, result={
            "session": session_number,
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
        
        # Read file contents
        all_files = []
        for file in files_a:
            content = await file.read()
            unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
            all_files.append((unique_filename, content))
        
        for file in files_b:
            content = await file.read()
            unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
            all_files.append((unique_filename, content))

        # Save files to S3 with comparison structure
        session_number = save_uploaded_files("document_comparison", all_files, comparison=True)
        
        doc1_files = [f[0] for f in all_files[:len(all_files)//2]]
        doc2_files = [f[0] for f in all_files[len(all_files)//2:]]

        # Process files (adapt your pipeline for S3)
        import tempfile
        import os
        tmp_files_a = []
        tmp_files_b = []
        
        for i, (filename, content) in enumerate(all_files):
            tmp_path = os.path.join(tempfile.gettempdir(), filename)
            with open(tmp_path, 'wb') as f:
                f.write(content)
            if i < len(all_files)//2:
                tmp_files_a.append(tmp_path)
            else:
                tmp_files_b.append(tmp_path)

        result = comparison_pipeline.run_comparison(tmp_files_a, tmp_files_b)

        # Cleanup
        for tmp_file in tmp_files_a + tmp_files_b:
            try:
                os.unlink(tmp_file)
            except:
                pass

        # Save comparison result
        save_comparison_result("document_comparison", session_number, result, doc1_files, doc2_files)

        return APIResponse(success=True, result={
            "session": session_number,
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
    client_id = request.client.host

    try:
        uploaded_files = []
        session_number = None

        if files and len(files) > 0:
            # Read file contents
            file_contents = []
            for file in files:
                content = await file.read()
                unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
                file_contents.append((unique_filename, content))

            # Save files to S3
            session_number = save_uploaded_files("document_qa_chat", file_contents)
            uploaded_files = [f[0] for f in file_contents]
            user_sessions[client_id] = session_number

            # Process files (adapt your pipeline)
            import tempfile
            import os
            tmp_files = []
            for filename, content in file_contents:
                tmp_path = os.path.join(tempfile.gettempdir(), filename)
                with open(tmp_path, 'wb') as f:
                    f.write(content)
                tmp_files.append(tmp_path)

            # Ingest new docs
            qa_chat_pipeline.ingest_new_documents(tmp_files)

            # Cleanup
            for tmp_file in tmp_files:
                try:
                    os.unlink(tmp_file)
                except:
                    pass
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