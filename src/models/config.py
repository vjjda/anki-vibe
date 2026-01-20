# Path: src/models/config.py
from typing import Optional
from pydantic import BaseModel, Field

__all__ = ["ModelFileSystemConfig"]

class ModelFileSystemConfig(BaseModel):
    """
    Cấu hình nằm trong file 'config.yaml' tại thư mục gốc của mỗi Note Type.
    Ví dụ: data/UserA/Basic_English/config.yaml
    """
    
    anki_model_name: str = Field(
        ..., 
        description="Tên chính xác của Note Type trong Anki (ví dụ: 'Basic (and reversed card)')"
    )
    
    description: Optional[str] = Field(
        default=None, 
        description="Mô tả ngắn gọn về loại note này (dành cho con người đọc)"
    )
    
    # Có thể mở rộng sau này để chứa template HTML/CSS
    # template_front_file: Optional[str] = "front.html"
    # template_back_file: Optional[str] = "back.html"