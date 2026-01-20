# Path: src/adapters/anki_connect.py
import json
import logging
import requests
from typing import Any, Dict, List, Optional
from src.core.config import settings

__all__ = ["AnkiConnectAdapter"]

logger = logging.getLogger(__name__)

class AnkiConnectError(Exception):
    """Custom exception for AnkiConnect errors."""
    pass

class AnkiConnectAdapter:
    def __init__(self, base_url: str = settings.ANKI_CONNECT_URL):
        self.base_url = base_url

    def _invoke(self, action: str, **params: Any) -> Any:
        """
        Gửi request raw đến AnkiConnect API.
        
        Args:
            action: Tên hành động (ví dụ: 'deckNames', 'addNote').
            params: Các tham số đi kèm (kwargs).
            
        Returns:
            Dữ liệu trả về từ field 'result' của AnkiConnect.
            
        Raises:
            ConnectionError: Nếu không kết nối được với Anki.
            AnkiConnectError: Nếu Anki trả về lỗi logic (ví dụ: deck không tồn tại).
        """
        payload = {
            "action": action,
            "version": 6,
            "params": params
        }
        
        try:
            response = requests.post(self.base_url, json=payload)
            response.raise_for_status() # Check HTTP errors (4xx, 5xx)
            
            response_data = response.json()
            
            # AnkiConnect protocol: check 'error' field
            if len(response_data) != 2:
                raise AnkiConnectError("Response has an unexpected number of fields.")
                
            if "error" not in response_data:
                raise AnkiConnectError("Response is missing required error field.")
                
            if response_data["error"] is not None:
                raise AnkiConnectError(f"Anki Error: {response_data['error']}")
                
            return response_data["result"]

        except requests.exceptions.ConnectionError:
            logger.error(f"Could not connect to Anki at {self.base_url}. Is Anki running?")
            raise ConnectionError(
                f"Failed to connect to Anki at {self.base_url}. Please make sure Anki is running and AnkiConnect is installed."
            )
        except Exception as e:
            logger.error(f"Error invoking {action}: {e}")
            raise e

    # --- Public API Methods ---

    def ping(self) -> str:
        """Kiểm tra kết nối và version."""
        # 'version' action không cần params
        return f"AnkiConnect v{self._invoke('version')}"

    def load_profile(self, name: str) -> bool:
        """Chuyển profile (Chỉ hoạt động nếu chưa load profile nào hoặc đang ở màn hình login)."""
        return self._invoke("loadProfile", name=name)

    def get_deck_names(self) -> List[str]:
        """Lấy danh sách tất cả các Deck."""
        return self._invoke("deckNames")

    def get_model_names(self) -> List[str]:
        """Lấy danh sách tất cả các Note Types (Models)."""
        return self._invoke("modelNames")

    def get_model_field_names(self, model_name: str) -> List[str]:
        """Lấy danh sách tên các Field của một Note Type."""
        return self._invoke("modelFieldNames", modelName=model_name)
    
    # Chúng ta sẽ thêm các method addNote/updateNoteInfo sau khi có Data Model