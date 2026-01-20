# Path: src/core/anki_detector.py
import sys
import subprocess
import re
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)

def _run_applescript(script: str) -> str:
    """Helper chạy AppleScript an toàn."""
    try:
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
        if result.returncode != 0:
            logger.debug(f"AppleScript Error: {result.stderr}")
            return ""
        return result.stdout.strip()
    except Exception as e:
        logger.error(f"Subprocess Error: {e}")
        return ""

def get_all_anki_window_titles() -> List[str]:
    """
    Lấy danh sách window title với cơ chế Fallback (Thử nhiều cách).
    """
    platform = sys.platform
    titles = []

    if platform == "darwin":  # macOS
        # --- CÁCH 1: Dùng Delimiter ||| (Chuẩn nhất) ---
        script_strict = '''
        tell application "System Events"
            if exists process "Anki" then
                set winList to name of every window of process "Anki"
                set {TID, text item delimiters} to {text item delimiters, "|||"}
                set resultText to winList as text
                set text item delimiters to TID
                return resultText
            else
                return ""
            end if
        end tell
        '''
        raw_strict = _run_applescript(script_strict)
        
        if raw_strict:
            titles = raw_strict.split('|||')
        else:
            # --- CÁCH 2: Fallback (Giống lệnh tay của bạn) ---
            # Nếu cách 1 fail (do permissions/encoding), thử lấy raw list mặc định
            logger.debug("Strict detection failed, trying fallback...")
            script_simple = 'tell application "System Events" to get name of every window of process "Anki"'
            raw_simple = _run_applescript(script_simple)
            
            if raw_simple:
                # Output dạng: "Browse, User 1 - Anki"
                # Ta tách bằng dấu phẩy + space (cách này rủi ro nếu tên deck có phẩy, nhưng tốt hơn là fail hẳn)
                titles = raw_simple.split(', ')

    elif platform == "win32":  # Windows
        import ctypes
        user32 = ctypes.windll.user32
        
        def foreach_window(hwnd, lParam):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                titles.append(buff.value)
            return True
            
        user32.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)(foreach_window), 0)

    # Clean titles
    clean_titles = [t.strip() for t in titles if t.strip()]
    
    # [DEBUG FORCE] In ra console để bạn thấy Python đang nhìn thấy gì
    if clean_titles:
        print(f"[DEBUG] Detected Windows: {clean_titles}")
        
    return clean_titles

def detect_active_profile() -> Optional[str]:
    """
    Phân tích titles để tìm profile.
    """
    titles = get_all_anki_window_titles()
    
    # Regex pattern: Bắt chuỗi trước " - Anki"
    # Ví dụ: "Vijjo - Anki" -> match "Vijjo"
    pattern = re.compile(r"^(.*?) - Anki$")
    
    for title in titles:
        # Bỏ qua các cửa sổ hệ thống của Anki
        if title in ["Anki", "Browse", "Add", "Stats", "Debug Console"]:
            continue
        
        # Xử lý trường hợp "Browse (n notes...), Vijjo - Anki" bị dính vào nhau nếu split lỗi
        # Ta tìm pattern " - Anki" bất kể nó nằm đâu trong string
        if " - Anki" in title:
            # Nếu title chính xác là "Vijjo - Anki"
            match = pattern.match(title)
            if match:
                return match.group(1).strip()
            
            # Fallback: Nếu string bị dính lẹo (ví dụ: "Browse, Vijjo - Anki")
            # Ta cố gắng tách phần đuôi
            if title.endswith(" - Anki"):
                # Lấy phần trước đó, nhưng cẩn thận dấu phẩy
                parts = title.split(", ")
                last_part = parts[-1] # Hy vọng là "Vijjo - Anki"
                match_fallback = pattern.match(last_part)
                if match_fallback:
                    return match_fallback.group(1).strip()

    return None