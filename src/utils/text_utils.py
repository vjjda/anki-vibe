# Path: src/utils/text_utils.py
import re

def sanitize_filename(name: str) -> str:
    """
    Chuyển đổi string thành tên file/folder an toàn.
    Ví dụ: "Basic (English)" -> "Basic_English"
    """
    # Thay thế ký tự không an toàn bằng _
    s = re.sub(r'[\\/*?:"<>|]', "_", name)
    # Loại bỏ khoảng trắng thừa hoặc dấu _ lặp lại
    s = re.sub(r'\s+', "_", s)
    s = re.sub(r'_+', "_", s)
    return s.strip("_")