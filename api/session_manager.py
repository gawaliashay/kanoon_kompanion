# utils/session_manager.py

import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import shutil

BASE_DIR = Path("sessions")
BASE_DIR.mkdir(exist_ok=True)


def _get_next_session_dir(route_name: str) -> Path:
    """
    Return a new session folder path for a given route (session_1, session_2...).
    """
    route_dir = BASE_DIR / route_name
    route_dir.mkdir(parents=True, exist_ok=True)

    # Find next session number
    existing_sessions = [
        d.name for d in route_dir.iterdir()
        if d.is_dir() and d.name.startswith("session_")
    ]
    numbers = [int(s.split("_")[1]) for s in existing_sessions if s.split("_")[1].isdigit()]
    next_number = max(numbers, default=0) + 1
    session_dir = route_dir / f"session_{next_number}"
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def save_uploaded_files(
    route_name: str,
    files: List[Path],
    comparison: bool = False,
    session_dir: Path = None
) -> Path:
    """
    Save uploaded files into a session folder.

    - If session_dir is provided, add files to that session (for QA re-upload)
    - For document_comparison, create doc1/doc2 subfolders
    - Returns the session folder path
    """
    if session_dir is None:
        session_dir = _get_next_session_dir(route_name)

    if comparison:
        # files[0] -> doc1, files[1] -> doc2
        doc1_dir = session_dir / "doc1"
        doc2_dir = session_dir / "doc2"
        doc1_dir.mkdir(parents=True, exist_ok=True)
        doc2_dir.mkdir(parents=True, exist_ok=True)

        for f in files[0]:
            dest = doc1_dir / f.name
            with f.open("rb") as src, dest.open("wb") as dst:
                shutil.copyfileobj(src, dst)

        for f in files[1]:
            dest = doc2_dir / f.name
            with f.open("rb") as src, dest.open("wb") as dst:
                shutil.copyfileobj(src, dst)
    else:
        for f in files:
            dest = session_dir / f.name
            with f.open("rb") as src, dest.open("wb") as dst:
                shutil.copyfileobj(src, dst)

    return session_dir


def save_conversation(route_name: str, session_number: int, question: str, answer: str) -> None:
    """
    Save conversation Q&A inside a session folder.
    """
    session_dir = BASE_DIR / route_name / f"session_{session_number}"
    session_dir.mkdir(parents=True, exist_ok=True)
    log_file = session_dir / "conversations.json"

    if log_file.exists():
        with log_file.open("r", encoding="utf-8") as f:
            history = json.load(f)
    else:
        history = []

    history.append({
        "timestamp": datetime.utcnow().isoformat(),
        "question": question,
        "answer": answer
    })

    with log_file.open("w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)


def get_conversations(route_name: str, session_number: int) -> List[Dict[str, Any]]:
    """
    Return conversation history for a given session.
    """
    log_file = BASE_DIR / route_name / f"session_{session_number}" / "conversations.json"
    if not log_file.exists():
        return []
    with log_file.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_recent_files(route_name: str) -> Dict[str, Any]:
    """
    Return all sessions and files for a given route.
    - For document_comparison, include doc1/doc2 structure
    """
    route_dir = BASE_DIR / route_name
    sessions = {}
    if not route_dir.exists():
        return sessions

    for session_folder in sorted(route_dir.iterdir(), key=lambda x: x.name, reverse=True):
        if session_folder.is_dir() and session_folder.name.startswith("session_"):
            if route_name == "document_comparison":
                doc1_files = [f.name for f in (session_folder / "doc1").glob("*") if f.is_file()]
                doc2_files = [f.name for f in (session_folder / "doc2").glob("*") if f.is_file()]
                sessions[session_folder.name] = {"doc1": doc1_files, "doc2": doc2_files}
            else:
                files = [f.name for f in session_folder.glob("*") if f.is_file()]
                sessions[session_folder.name] = files
    return sessions
