import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import shutil

# Base directory for all sessions
BASE_DIR = Path("sessions")
BASE_DIR.mkdir(exist_ok=True)

# In-memory cache
conversation_cache: Dict[str, Dict[int, List[Dict[str, Any]]]] = {}
analysis_cache: Dict[str, Dict[int, Dict[str, Any]]] = {}
comparison_cache: Dict[str, Dict[int, Dict[str, Any]]] = {}


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
    numbers = []
    for session in existing_sessions:
        try:
            number = int(session.split("_")[1])
            numbers.append(number)
        except (IndexError, ValueError):
            continue
    
    next_number = max(numbers, default=0) + 1

    session_dir = route_dir / f"session_{next_number}"
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def save_uploaded_files(
    route_name: str,
    files: List[Path],
    comparison: bool = False
) -> Path:
    """
    Save uploaded files into a session directory.
    """
    session_dir = _get_next_session_dir(route_name)

    if comparison:
        # Split files into two groups for comparison
        half = len(files) // 2
        files_a = files[:half]
        files_b = files[half:]
        
        # Two sets of files (doc1 vs doc2)
        doc1_dir = session_dir / "doc1"
        doc2_dir = session_dir / "doc2"
        doc1_dir.mkdir(parents=True, exist_ok=True)
        doc2_dir.mkdir(parents=True, exist_ok=True)

        for file_path in files_a:
            shutil.copy2(file_path, doc1_dir / file_path.name)
        for file_path in files_b:
            shutil.copy2(file_path, doc2_dir / file_path.name)
    else:
        for file_path in files:
            shutil.copy2(file_path, session_dir / file_path.name)

    # Clean up temporary files
    for file_path in files:
        try:
            file_path.unlink()
        except:
            pass

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
        json.dump(conversation_cache[route_name][session_number], f, indent=2, ensure_ascii=False)


def get_conversations(route_name: str, session_number: int) -> List[Dict[str, Any]]:
    """
    Load conversations from cache or disk.
    """
    # Check cache first
    if route_name in conversation_cache and session_number in conversation_cache[route_name]:
        return conversation_cache[route_name][session_number]

    # Load from disk if not in cache
    session_dir = BASE_DIR / route_name / f"session_{session_number}"
    log_file = session_dir / "conversations.json"
    
    if not log_file.exists():
        return []

    try:
        with log_file.open("r", encoding="utf-8") as f:
            history = json.load(f)
        
        # Update cache
        if route_name not in conversation_cache:
            conversation_cache[route_name] = {}
        conversation_cache[route_name][session_number] = history
        
        return history
    except (json.JSONDecodeError, FileNotFoundError):
        return []


# ----------------------------
# Analysis Result Management
# ----------------------------
def save_analysis_result(
    route_name: str,
    session_number: int,
    result: Dict[str, Any],
    uploaded_files: List[str]
) -> None:
    """
    Save analysis result to session directory.
    """
    if route_name not in analysis_cache:
        analysis_cache[route_name] = {}
    
    analysis_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "uploaded_files": uploaded_files,
        "analysis_result": result
    }
    
    analysis_cache[route_name][session_number] = analysis_data

    session_dir = BASE_DIR / route_name / f"session_{session_number}"
    session_dir.mkdir(parents=True, exist_ok=True)
    result_file = session_dir / "analysis_result.json"

    with result_file.open("w", encoding="utf-8") as f:
        json.dump(analysis_data, f, indent=2, ensure_ascii=False)


def get_analysis_result(route_name: str, session_number: int) -> Optional[Dict[str, Any]]:
    """
    Load analysis result from cache or disk.
    """
    # Check cache first
    if route_name in analysis_cache and session_number in analysis_cache[route_name]:
        return analysis_cache[route_name][session_number]

    # Load from disk if not in cache
    session_dir = BASE_DIR / route_name / f"session_{session_number}"
    result_file = session_dir / "analysis_result.json"
    
    if not result_file.exists():
        return None

    try:
        with result_file.open("r", encoding="utf-8") as f:
            result_data = json.load(f)
        
        # Update cache
        if route_name not in analysis_cache:
            analysis_cache[route_name] = {}
        analysis_cache[route_name][session_number] = result_data
        
        return result_data
    except (json.JSONDecodeError, FileNotFoundError):
        return None


# ----------------------------
# Comparison Result Management
# ----------------------------
def save_comparison_result(
    route_name: str,
    session_number: int,
    result: Dict[str, Any],
    doc1_files: List[str],
    doc2_files: List[str]
) -> None:
    """
    Save comparison result to session directory.
    """
    if route_name not in comparison_cache:
        comparison_cache[route_name] = {}
    
    comparison_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "doc1_files": doc1_files,
        "doc2_files": doc2_files,
        "comparison_result": result
    }
    
    comparison_cache[route_name][session_number] = comparison_data

    session_dir = BASE_DIR / route_name / f"session_{session_number}"
    session_dir.mkdir(parents=True, exist_ok=True)
    result_file = session_dir / "comparison_result.json"

    with result_file.open("w", encoding="utf-8") as f:
        json.dump(comparison_data, f, indent=2, ensure_ascii=False)


def get_comparison_result(route_name: str, session_number: int) -> Optional[Dict[str, Any]]:
    """
    Load comparison result from cache or disk.
    """
    # Check cache first
    if route_name in comparison_cache and session_number in comparison_cache[route_name]:
        return comparison_cache[route_name][session_number]

    # Load from disk if not in cache
    session_dir = BASE_DIR / route_name / f"session_{session_number}"
    result_file = session_dir / "comparison_result.json"
    
    if not result_file.exists():
        return None

    try:
        with result_file.open("r", encoding="utf-8") as f:
            result_data = json.load(f)
        
        # Update cache
        if route_name not in comparison_cache:
            comparison_cache[route_name] = {}
        comparison_cache[route_name][session_number] = result_data
        
        return result_data
    except (json.JSONDecodeError, FileNotFoundError):
        return None