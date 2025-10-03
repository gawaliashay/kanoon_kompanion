
# storage_manager\session_manager.py

from typing import List, Dict, Any, Optional
from datetime import datetime
from storage_manager.storage_config import storage

# ----------------------------
# In-memory caches
# ----------------------------
conversation_cache: Dict[str, Dict[int, List[Dict[str, Any]]]] = {}  # Permanent sessions
temp_conversation_cache: Dict[str, List[Dict[str, Any]]] = {}       # TEMP sessions before END

BASE_DIR = "sessions"


# ----------------------------
# Session Utilities
# ----------------------------
def get_next_session_number(route_name: str) -> int:
    """Compute the next session number based on existing session folders."""
    from pathlib import Path

    route_dir = Path(BASE_DIR) / route_name
    route_dir.mkdir(parents=True, exist_ok=True)

    existing_sessions = [
        d.name for d in route_dir.iterdir() 
        if d.is_dir() and d.name.startswith("session_")
    ]

    numbers = []
    for session in existing_sessions:
        try:
            numbers.append(int(session.split("_")[1]))
        except (IndexError, ValueError):
            continue

    return max(numbers, default=0) + 1


# ----------------------------
# TEMP Conversation Management
# ----------------------------
def add_temp_conversation(
    client_id: str,
    question: str,
    answer: str,
    uploaded_files: Optional[List[str]] = None
) -> None:
    """Add a conversation entry to TEMP cache for a client until session ends."""
    temp_conversation_cache.setdefault(client_id, [])

    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "question": question,
        "answer": answer,
    }
    if uploaded_files:
        entry["uploaded_files"] = uploaded_files

    temp_conversation_cache[client_id].append(entry)


def end_session(route_name: str, client_id: str) -> int:
    """
    Move TEMP conversation to permanent storage.
    Returns session number. Returns -1 if no TEMP conversation exists.
    """
    if not temp_conversation_cache.get(client_id):
        return -1

    from storage_manager.file_manager import save_conversation_file

    session_number = get_next_session_number(route_name)
    save_conversation_file(route_name, session_number, temp_conversation_cache[client_id])

    # Update permanent in-memory cache
    conversation_cache.setdefault(route_name, {})[session_number] = temp_conversation_cache[client_id]

    # Clear TEMP cache
    temp_conversation_cache[client_id] = []

    return session_number


def get_temp_conversation(client_id: str) -> List[Dict[str, Any]]:
    """Retrieve TEMP conversation for a client."""
    return temp_conversation_cache.get(client_id, [])


def get_conversations(route_name: str, session_number: int) -> List[Dict[str, Any]]:
    """Retrieve conversation from permanent storage, using in-memory cache if available."""
    if route_name in conversation_cache and session_number in conversation_cache[route_name]:
        return conversation_cache[route_name][session_number]

    from storage_manager.file_manager import load_conversation_file

    history = load_conversation_file(route_name, session_number)
    conversation_cache.setdefault(route_name, {})[session_number] = history
    return history
