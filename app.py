from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List
import tempfile
import os

from src.document_analysis.document_analysis_pipeline import DocumentAnalysisPipeline
from src.common.logging.logger import logger
from src.common.exception.custom_exception import CustomException

# -------------------------------------------------
# App Initialization
# -------------------------------------------------
app = FastAPI(
    title="Document Analysis API",
    description="API to run the document analysis pipeline",
    version="1.0.0"
)

# -------------------------------------------------
# Middleware
# -------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Allow all origins (adjust in prod)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------
# Static + Templates
# -------------------------------------------------
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# -------------------------------------------------
# Routes
# -------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the main HTML page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health", response_class=JSONResponse)
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "message": "Document Analysis API is running"}


@app.post("/analyze", response_class=JSONResponse)
async def analyze_documents(files: List[UploadFile] = File(...)):
    """Trigger the document analysis pipeline on uploaded files."""
    try:
        logger.info(" Starting Document Analysis Workflow via API")

        if not files:
            raise HTTPException(status_code=400, detail="No files uploaded")

        # Create temporary directory to store files
        with tempfile.TemporaryDirectory() as temp_dir:
            file_paths = []

            # Save uploaded files
            for file in files:
                file_path = os.path.join(temp_dir, file.filename)

                content = await file.read()
                with open(file_path, "wb") as f:
                    f.write(content)

                file_paths.append(file_path)
                logger.info(f"Processing file: {file.filename}")

            # Run pipeline
            pipeline = DocumentAnalysisPipeline()
            result = pipeline.run_analysis([temp_dir])

        logger.info(" Workflow completed successfully")

        # Return structured JSON
        return result["summary"]

    except CustomException as ce:
        logger.error(f" Workflow failed with custom exception: {str(ce)}")
        raise HTTPException(status_code=400, detail=str(ce))

    except Exception as e:
        logger.error(f" Workflow failed with unexpected exception: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# -------------------------------------------------
# Local Dev Entry
# -------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", port=8000, reload=True)
