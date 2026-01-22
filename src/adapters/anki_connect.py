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
    # DECK OPERATIONS
    # =========================================================================

    def create_deck(self, deck_name: str) -> int:
        """
        Tạo Deck mới.
        Returns: ID của Deck vừa tạo.
        """
        return self._invoke("createDeck", deck=deck_name)

    def delete_decks(self, deck_names: List[str]) -> None:
        """
        Xóa danh sách Decks.
        """
        self._invoke("deleteDecks", decks=deck_names, cardsToo=True)

    # =========================================================================
    # MODEL OPERATIONS
    # =========================================================================

    def create_model(self, model_name: str, in_order_fields: List[str], css: str = "", is_cloze: bool = False) -> Dict[str, Any]:
        """
        Tạo Note Type (Model) mới.
        """
        params = {
            "modelName": model_name,
            "inOrderFields": in_order_fields,
            "css": css,
            "isCloze": is_cloze,
            "cardTemplates": [
                {
                    "Name": "Card 1",
                    "Front": "{{"+in_order_fields[0]+"}}",
                    "Back": "{{FrontSide}}\n\n<hr id=answer>\n\n" + "\n\n".join(["{{"+f+"}}" for f in in_order_fields[1:]])
                }
            ]
        }
        return self._invoke("createModel", **params)

    # =========================================================================
    # MEDIA OPERATIONS
    # =========================================================================

    def store_media_file(self, filename: str, data_base64: str = None, path: str = None, url: str = None) -> str:
        """
        Lưu file media vào Anki collection.media folder.
        Có thể cung cấp:
        - data_base64: Nội dung file đã mã hóa base64.
        - path: Đường dẫn file local tuyệt đối.
        - url: Đường dẫn tải về từ internet.
        """
        params = {"filename": filename}
        if data_base64:
            params["data"] = data_base64
        elif path:
            params["path"] = path
        elif url:
            params["url"] = url
        else:
            raise ValueError("Must provide either data_base64, path, or url")
            
        return self._invoke("storeMediaFile", **params)

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
    
    # =========================================================================
    # BATCH OPERATIONS (Performance Optimization)
    # =========================================================================

    def multi(self, actions: List[Dict[str, Any]]) -> List[Any]:
        """
        Thực thi hàng loạt action trong 1 HTTP Request.
        Tăng tốc độ sync đáng kể so với gửi lẻ tẻ.
        """
        return self._invoke("multi", actions=actions)

    def add_notes(self, notes: List[Dict[str, Any]], allow_duplicate: bool = False) -> List[Optional[int]]:
        """
        Thêm nhiều ghi chú cùng lúc (Bulk Insert).
        Returns: List các Note ID vừa tạo (theo thứ tự input).
        """
        if allow_duplicate:
            for note in notes:
                note["options"] = {"allowDuplicate": True}
        return self._invoke("addNotes", notes=notes)

    # =========================================================================
    # MODEL MODIFICATION
    # =========================================================================

    def update_model_templates(self, model_name: str, templates: Dict[str, Dict[str, str]]) -> None:
        """
        Cập nhật HTML Template cho Model.
        templates structure: { "Card 1": {"Front": "..", "Back": ".."} }
        """
        # API requires specific structure: model, templates={cardName: {Front:.., Back:..}}
        self._invoke("updateModelTemplates", model={"name": model_name, "templates": templates})

    def update_model_styling(self, model_name: str, css: str) -> None:
        """Cập nhật CSS cho Model."""
        self._invoke("updateModelStyling", model={"name": model_name, "css": css})

    # =========================================================================
    # NOTE MODIFICATION
    # =========================================================================

    def update_note_fields(self, note_id: int, fields: Dict[str, str]) -> None:
        """Cập nhật nội dung fields."""
        note = {"id": note_id, "fields": fields}
        self._invoke("updateNoteFields", note=note)

    def change_note_model(self, note_id: int, new_model_name: str, fields: Dict[str, str], tags: List[str] = None) -> None:
        """
        Chuyển đổi Note sang Model khác.
        Args:
            note_id: ID của note cần chuyển.
            new_model_name: Tên model đích.
            fields: Dictionary map tên field mới -> giá trị mới.
            tags: (Optional) Danh sách tags mới.
        """
        params = {
            "note": {"id": note_id, "modelName": new_model_name, "fields": fields}
        }
        if tags is not None:
            params["note"]["tags"] = tags
        
        self._invoke("updateNoteModel", **params)

    # Helper function to construct an action for 'multi' batch
    @staticmethod
    def create_update_fields_action(note_id: int, fields: Dict[str, str]) -> Dict[str, Any]:
        return {
            "action": "updateNoteFields",
            "params": {"note": {"id": note_id, "fields": fields}}
        }
    
    @staticmethod
    def create_update_tags_action(note_id: int, tags: List[str]) -> Dict[str, Any]:
        # AnkiConnect không có updateTags trực tiếp thay thế toàn bộ, 
        # nhưng có removeTags và addTags.
        # Tuy nhiên, để đơn giản trong batch, ta dùng updateNoteTags nếu có, 
        # hoặc dùng 'notesInfo' để diff rồi add/remove.
        # Hiện tại API 'updateNoteTags' nhận list tags mới thay thế list cũ.
        return {
            "action": "updateNoteTags",
            "params": {"note": note_id, "tags": tags}
        }