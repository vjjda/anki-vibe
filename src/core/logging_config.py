# Path: src/core/logging_config.py
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from rich.logging import RichHandler
from src.core.config import settings

def setup_logging(log_level: str = "INFO") -> None:
    """
    Thiết lập hệ thống logging cho toàn bộ dự án.
    
    - Console: Sử dụng RichHandler để in màu đẹp mắt.
    - File: Sử dụng RotatingFileHandler để lưu log chi tiết, tự động xoay file.
    """
    # 1. Tạo thư mục logs nếu chưa tồn tại
    log_dir = settings.BASE_DIR / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "anki_vibe.log"

    # 2. Định dạng Log
    # Format cho file: Time - Level - Module - Message
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    # Format cho console: Đơn giản hơn vì Rich đã lo phần time/level đẹp rồi
    console_formatter = logging.Formatter("%(message)s")

    # 3. Handlers
    
    # File Handler: Tự động cắt file khi đạt 5MB, giữ lại 3 file cũ nhất
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=5*1024*1024, # 5MB
        backupCount=3,
        encoding="utf-8"
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG) # File luôn lưu chi tiết nhất có thể

    # Console Handler (Rich):
    console_handler = RichHandler(
        rich_tracebacks=True,
        markup=True,
        show_time=False, # Typer/Console của chúng ta đã in thời gian nếu cần
        show_path=False
    )
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(log_level)

    # 4. Root Logger Configuration
    # Lấy root logger và gán handlers
    logging.basicConfig(
        level=log_level,
        handlers=[console_handler, file_handler],
        force=True # Ghi đè các config cũ nếu có
    )

    # Tắt log quá ồn ào từ các thư viện bên thứ 3 (nếu cần)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)