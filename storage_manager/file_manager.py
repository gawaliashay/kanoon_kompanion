# storage_manager\file_manager.py

from pathlib import Path
from typing import List, Dict, Any
import shutil
import json
import uuid
from fastapi import UploadFile
import tempfile
from storage_manager.session_manager import get_next_session_number

BASE_DIR = Path("sessions")
BASE_DIR.mkdir(exist_ok=True)


# ----------------------------
# Save Uploaded Files into Session
# ----------------------------
def save_uploaded_files(route_name: str, files: List[UploadFile], comparison: bool = False) -> Path:
    """
    Save uploaded files into a new session directory.
    If comparison=True, split files into doc1/doc2 folders.
    """
    session_number = get_next_session_number(route_name)
    session_dir = BASE_DIR / route_name / f"session_{session_number}"
    session_dir.mkdir(parents=True, exist_ok=True)

    if comparison:
        half = len(files) // 2
        files_a, files_b = files[:half], files[half:]
        doc1_dir = session_dir / "doc1"
        doc2_dir = session_dir / "doc2"
        doc1_dir.mkdir(parents=True, exist_ok=True)
        doc2_dir.mkdir(parents=True, exist_ok=True)
        for f in files_a:
            f_path = Path(tempfile.gettempdir()) / f.filename
            f.file.seek(0)
            f_path.write_bytes(f.file.read())
            shutil.copy2(f_path, doc1_dir / f.filename)
        for f in files_b:
            f_path = Path(tempfile.gettempdir()) / f.filename
            f.file.seek(0)
            f_path.write_bytes(f.file.read())
            shutil.copy2(f_path, doc2_dir / f.filename)
    else:
        for f in files:
            f_path = Path(tempfile.gettempdir()) / f.filename
            f.file.seek(0)
            f_path.write_bytes(f.file.read())
            shutil.copy2(f_path, session_dir / f.filename)

    return session_dir


# ----------------------------
# Analysis Storage
# ----------------------------
def save_analysis_result(route_name: str, session_number: int, result: Dict[str, Any], uploaded_files: List[str]):
    session_dir = BASE_DIR / route_name / f"session_{session_number}"
    session_dir.mkdir(parents=True, exist_ok=True)
    file_path = session_dir / "analysis_result.json"
    with file_path.open("w", encoding="utf-8") as f:
        json.dump({"uploaded_files": uploaded_files, "analysis_result": result}, f, indent=2)


# ----------------------------
# Comparison Storage
# ----------------------------
def save_comparison_result(route_name: str, session_number: int, result: Dict[str, Any], doc1_files: List[str], doc2_files: List[str]):
    session_dir = BASE_DIR / route_name / f"session_{session_number}"
    session_dir.mkdir(parents=True, exist_ok=True)
    file_path = session_dir / "comparison_result.json"
    with file_path.open("w", encoding="utf-8") as f:
        json.dump({"doc1_files": doc1_files, "doc2_files": doc2_files, "comparison_result": result}, f, indent=2)


# ----------------------------
# Conversation Storage
# ----------------------------
def save_conversation_file(route_name: str, session_number: int, conversation: List[Dict[str, Any]]):
    session_dir = BASE_DIR / route_name / f"session_{session_number}"
    session_dir.mkdir(parents=True, exist_ok=True)
    file_path = session_dir / "conversations.json"
    with file_path.open("w", encoding="utf-8") as f:
        json.dump(conversation, f, indent=2, ensure_ascii=False)


def load_conversation_file(route_name: str, session_number: int) -> List[Dict[str, Any]]:
    session_dir = BASE_DIR / route_name / f"session_{session_number}"
    file_path = session_dir / "conversations.json"
    if not file_path.exists():
        return []
    with file_path.open("r", encoding="utf-8") as f:
        return json.load(f)
