# Path: src/adapters/anki_connect.py
import json
import logging
import requests
from typing import Any, Dict, List, Optional, Union
from src.core.config import settings

__all__ = ["AnkiConnectAdapter", "AnkiConnectError"]

logger = logging.getLogger(__name__)

class AnkiConnectError(Exception):
    """Custom exception for logical errors returned by AnkiConnect."""
    pass

class AnkiConnectAdapter:
    """
    Adapter để giao tiếp với Anki thông qua AnkiConnect Add-on.
    Document: https://foosoft.net/projects/anki-connect/
    """

    def __init__(self, base_url: str = settings.ANKI_CONNECT_URL):
        self.base_url = base_url

    def _invoke(self, action: str, **params: Any) -> Any:
        """
        Gửi request POST đến AnkiConnect API.
        
        Args:
            action: Tên hành động API (ví dụ: 'deckNames', 'addNote').
            params: Các tham số keyword arguments đi kèm.
            
        Returns:
            Giá trị trong trường 'result' của response.
            
        Raises:
            ConnectionError: Nếu không kết nối được với Anki (Anki chưa mở).
            AnkiConnectError: Nếu Anki trả về lỗi logic (ví dụ: sai tên deck).
        """
        payload = {
            "action": action,
            "version": 6,
            "params": params
        }
        
        try:
            # Timeout 30s để tránh treo app nếu Anki đang xử lý nặng
            response = requests.post(self.base_url, json=payload, timeout=30)
            response.raise_for_status() 
            
            response_data = response.json()
            
            # Kiểm tra format chuẩn của AnkiConnect
            if len(response_data) != 2:
                raise AnkiConnectError("Response has an unexpected number of fields.")
                
            if "error" not in response_data:
                raise AnkiConnectError("Response is missing required error field.")
                
            # Kiểm tra lỗi logic từ phía Anki
            if response_data["error"] is not None:
                error_msg = response_data["error"]
                logger.error(f"AnkiConnect Error [{action}]: {error_msg}")
                raise AnkiConnectError(f"{error_msg}")
                
            return response_data["result"]

        except requests.exceptions.ConnectionError:
            logger.error(f"Could not connect to Anki at {self.base_url}. Is Anki running?")
            raise ConnectionError(
                f"Failed to connect to Anki at {self.base_url}. Please make sure Anki is running and AnkiConnect is installed."
            )
        except Exception as e:
            logger.error(f"Unexpected error invoking {action}: {e}")
            raise e

    # =========================================================================
    # SYSTEM & CONNECTION
    # =========================================================================

    def ping(self) -> str:
        """Kiểm tra kết nối và lấy version API."""
        return f"AnkiConnect v{self._invoke('version')}"

    def load_profile(self, name: str) -> bool:
        """
        Chuyển profile Anki.
        Lưu ý: Lệnh này sẽ force sync và reload GUI Anki.
        """
        return self._invoke("loadProfile", name=name)

    # =========================================================================
    # METADATA RETRIEVAL (Decks, Models)
    # =========================================================================

    def get_deck_names(self) -> List[str]:
        """Lấy danh sách tên tất cả các Deck."""
        return self._invoke("deckNames")

    def get_model_names(self) -> List[str]:
        """Lấy danh sách tên tất cả các Note Types (Models)."""
        return self._invoke("modelNames")

    def get_model_field_names(self, model_name: str) -> List[str]:
        """Lấy danh sách tên các Field của một Note Type."""
        return self._invoke("modelFieldNames", modelName=model_name)

    def get_model_templates(self, model_name: str) -> Dict[str, Any]:
        """
        Lấy thông tin templates (Front/Back HTML) của Model.
        Returns: Dict dạng { "Card Name": {"qfmt": "...", "afmt": "..."}, ... }
        """
        return self._invoke("modelTemplates", modelName=model_name)

    def get_model_styling(self, model_name: str) -> Dict[str, str]:
        """
        Lấy CSS của Model.
        Returns: Dict dạng { "css": "..." }
        """
        return self._invoke("modelStyling", modelName=model_name)

    # =========================================================================
    # DATA RETRIEVAL (Notes)
    # =========================================================================

    def find_notes(self, query: str) -> List[int]:
        """
        Tìm kiếm Note IDs dựa trên query string của Anki.
        Ví dụ query: 'deck:current', 'note:Basic', 'tag:hard'.
        """
        return self._invoke("findNotes", query=query)

    def get_notes_info(self, note_ids: List[int]) -> List[Dict[str, Any]]:
        """
        Lấy thông tin chi tiết (fields, tags, model) của danh sách Note IDs.
        """
        if not note_ids:
            return []
        return self._invoke("notesInfo", notes=note_ids)

    # =========================================================================
    # WRITE OPERATIONS (Placeholder for Future Use)
    # =========================================================================
    
    def update_note_fields(self, note_id: int, fields: Dict[str, str]) -> None:
        """
        Cập nhật nội dung fields của một note cụ thể.
        """
        note_data = {
            "id": note_id,
            "fields": fields
        }
        self._invoke("updateNoteFields", note=note_data)
    
    def get_cards_info(self, card_ids: List[int]) -> List[Dict[str, Any]]:
        """
        Lấy thông tin chi tiết của danh sách Card IDs.
        Dùng để xác định Deck Name của một Note.
        """
        if not card_ids:
            return []
        return self._invoke("cardsInfo", cards=card_ids)