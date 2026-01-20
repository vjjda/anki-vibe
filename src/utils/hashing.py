# Path: src/utils/hashing.py
import hashlib
import json
from typing import Dict, List, Any

def compute_hash(data: Any) -> str:
    """
    Tính MD5 hash của một object.
    Sử dụng sort_keys=True để đảm bảo tính nhất quán (không phụ thuộc thứ tự key).
    """
    canonical_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(canonical_str.encode('utf-8')).hexdigest()

def compute_note_hash(deck: str, tags: List[str], fields: Dict[str, str]) -> str:
    """
    Hash đại diện cho nội dung Note.
    """
    payload = {
        "deck": deck,
        "tags": sorted(tags), # Sort tags để [a,b] giống [b,a]
        "fields": fields
    }
    return compute_hash(payload)

def compute_model_hash(css: str, templates: Dict[str, Any]) -> str:
    """
    Hash đại diện cho giao diện Model (CSS + Templates).
    """
    payload = {
        "css": css.strip(),
        "templates": templates
    }
    return compute_hash(payload)