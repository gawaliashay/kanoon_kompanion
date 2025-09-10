import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import shutil

# Base directory for all sessions
BASE_DIR = Path("sessions")
BASE_DIR.mkdir(exist_ok=True)

# In-memory cache
conversation_cache: Dict[str, Dict[int, List[Dict[str, Any]]]] = {}


# ----------------------------
# Session Management
# ----------------------------
def _get_next_session_dir(route_name: str) -> Path:
    route_dir = BASE_DIR / route_name
    route_dir.mkdir(parents=True, exist_ok=True)

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
    session_dir: Optional[Path] = None
) -> Path:
    """
    Save uploaded files into a session directory.
    """
    if session_dir is None:
        session_dir = _get_next_session_dir(route_name)

    if comparison:
        # Two sets of files (doc1 vs doc2)
        doc1_dir = session_dir / "doc1"
        doc2_dir = session_dir / "doc2"
        doc1_dir.mkdir(parents=True, exist_ok=True)
        doc2_dir.mkdir(parents=True, exist_ok=True)

        for f in files[0]:
            shutil.copy(f, doc1_dir / f.name)
        for f in files[1]:
            shutil.copy(f, doc2_dir / f.name)
    else:
        for f in files:
            shutil.copy(f, session_dir / f.name)

    return session_dir


# ----------------------------
# Conversation Management
# ----------------------------
def save_conversation(
    route_name: str,
    session_number: int,
    question: str,
    answer: str,
    uploaded_files: Optional[List[str]] = None
) -> None:
    """
    Save conversation both in-memory and on disk.
    """
    if route_name not in conversation_cache:
        conversation_cache[route_name] = {}
    if session_number not in conversation_cache[route_name]:
        conversation_cache[route_name][session_number] = []

    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "question": question,
        "answer": answer,
    }
    if uploaded_files:
        entry["uploaded_files"] = uploaded_files

    conversation_cache[route_name][session_number].append(entry)

    session_dir = BASE_DIR / route_name / f"session_{session_number}"
    session_dir.mkdir(parents=True, exist_ok=True)
    log_file = session_dir / "conversations.json"

    with log_file.open("w", encoding="utf-8") as f:
        json.dump(conversation_cache[route_name][session_number], f, indent=2)


def get_conversations(route_name: str, session_number: int) -> List[Dict[str, Any]]:
    """
    Load conversations from cache or disk.
    """
    if route_name in conversation_cache and session_number in conversation_cache[route_name]:
        return conversation_cache[route_name][session_number]

    log_file = BASE_DIR / route_name / f"session_{session_number}" / "conversations.json"
    if not log_file.exists():
        return []

    with log_file.open("r", encoding="utf-8") as f:
        history = json.load(f)

    if route_name not in conversation_cache:
        conversation_cache[route_name] = {}
    conversation_cache[route_name][session_number] = history
    return history
