# api/session_manager.py
import json
import time
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError

from api.config import settings

# Initialize S3 client
s3_client = boto3.client('s3', region_name=settings.aws_region)

# In-memory cache for active sessions
conversation_cache: Dict[str, Dict[int, List[Dict[str, Any]]]] = {}
analysis_cache: Dict[str, Dict[int, Dict[str, Any]]] = {}
comparison_cache: Dict[str, Dict[int, Dict[str, Any]]] = {}


# ----------------------------
# S3 Session Storage
# ----------------------------
def _get_s3_key(route_name: str, session_number: int, file_type: str) -> str:
    """Generate S3 key for session files"""
    return f"sessions/{route_name}/session_{session_number}/{file_type}.json"


def _save_to_s3(data: Dict[str, Any], key: str) -> None:
    """Save data to S3"""
    try:
        s3_client.put_object(
            Bucket=settings.s3_bucket,
            Key=key,
            Body=json.dumps(data, ensure_ascii=False),
            ContentType='application/json'
        )
    except ClientError as e:
        print(f"Error saving to S3: {e}")
        raise


def _load_from_s3(key: str) -> Optional[Dict[str, Any]]:
    """Load data from S3"""
    try:
        response = s3_client.get_object(
            Bucket=settings.s3_bucket,
            Key=key
        )
        return json.loads(response['Body'].read().decode('utf-8'))
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            return None
        print(f"Error loading from S3: {e}")
        raise


# ----------------------------
# File Upload Management
# ----------------------------
def save_uploaded_files(
    route_name: str,
    file_contents: List[tuple],  # (filename, file_content)
    comparison: bool = False
) -> int:
    """
    Save uploaded files to S3 and return session number
    """
    session_number = _get_next_session_number()
    
    if comparison:
        # Split files into two groups
        half = len(file_contents) // 2
        files_a = file_contents[:half]
        files_b = file_contents[half:]
        
        # Upload files to S3
        for filename, content in files_a:
            s3_key = f"uploads/{route_name}/session_{session_number}/doc1/{filename}"
            s3_client.put_object(
                Bucket=settings.s3_bucket,
                Key=s3_key,
                Body=content,
                ContentType='application/octet-stream'
            )
        
        for filename, content in files_b:
            s3_key = f"uploads/{route_name}/session_{session_number}/doc2/{filename}"
            s3_client.put_object(
                Bucket=settings.s3_bucket,
                Key=s3_key,
                Body=content,
                ContentType='application/octet-stream'
            )
    else:
        for filename, content in file_contents:
            s3_key = f"uploads/{route_name}/session_{session_number}/{filename}"
            s3_client.put_object(
                Bucket=settings.s3_bucket,
                Key=s3_key,
                Body=content,
                ContentType='application/octet-stream'
            )
    
    return session_number




def _get_next_session_number() -> int:
    return int(time.time() * 1000)  # millisecond precision




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
    """Save conversation to S3"""
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

    # Save to S3
    key = _get_s3_key(route_name, session_number, "conversations")
    _save_to_s3(conversation_cache[route_name][session_number], key)


def get_conversations(route_name: str, session_number: int) -> List[Dict[str, Any]]:
    """Load conversations from S3"""
    # Check cache first
    if route_name in conversation_cache and session_number in conversation_cache[route_name]:
        return conversation_cache[route_name][session_number]

    # Load from S3
    key = _get_s3_key(route_name, session_number, "conversations")
    data = _load_from_s3(key)
    if data:
        if route_name not in conversation_cache:
            conversation_cache[route_name] = {}
        conversation_cache[route_name][session_number] = data
        return data
    
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
    """Save analysis result to S3"""
    if route_name not in analysis_cache:
        analysis_cache[route_name] = {}
    
    analysis_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "uploaded_files": uploaded_files,
        "analysis_result": result
    }
    
    analysis_cache[route_name][session_number] = analysis_data

    # Save to S3
    key = _get_s3_key(route_name, session_number, "analysis_result")
    _save_to_s3(analysis_data, key)


def get_analysis_result(route_name: str, session_number: int) -> Optional[Dict[str, Any]]:
    """Load analysis result from S3"""
    if route_name in analysis_cache and session_number in analysis_cache[route_name]:
        return analysis_cache[route_name][session_number]

    key = _get_s3_key(route_name, session_number, "analysis_result")
    data = _load_from_s3(key)
    if data:
        if route_name not in analysis_cache:
            analysis_cache[route_name] = {}
        analysis_cache[route_name][session_number] = data
        return data
    
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
    """Save comparison result to S3"""
    if route_name not in comparison_cache:
        comparison_cache[route_name] = {}
    
    comparison_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "doc1_files": doc1_files,
        "doc2_files": doc2_files,
        "comparison_result": result
    }
    
    comparison_cache[route_name][session_number] = comparison_data

    key = _get_s3_key(route_name, session_number, "comparison_result")
    _save_to_s3(comparison_data, key)


def get_comparison_result(route_name: str, session_number: int) -> Optional[Dict[str, Any]]:
    """Load comparison result from S3"""
    if route_name in comparison_cache and session_number in comparison_cache[route_name]:
        return comparison_cache[route_name][session_number]

    key = _get_s3_key(route_name, session_number, "comparison_result")
    data = _load_from_s3(key)
    if data:
        if route_name not in comparison_cache:
            comparison_cache[route_name] = {}
        comparison_cache[route_name][session_number] = data
        return data
    
    return None