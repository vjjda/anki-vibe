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
            # Chỉ log debug để tránh làm rác console nếu fallback hoạt động tốt
            logger.debug(f"AppleScript Error: {result.stderr.strip()}")
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
        # --- CÁCH 1: Dùng Delimiter ||| (FIXED SCOPE) ---
        # Sửa lỗi -1728: Dùng "AppleScript's text item delimiters" thay vì chỉ "text item delimiters"
        script_strict = '''
        tell application "System Events"
            if exists process "Anki" then
                set winList to name of every window of process "Anki"
            else
                return ""
            end if
        end tell
        
        -- Xử lý chuỗi bên ngoài block System Events để tránh lỗi scope
        if winList is {} then return ""
        
        set {TID, AppleScript's text item delimiters} to {AppleScript's text item delimiters, "|||"}
        set resultText to winList as text
        set AppleScript's text item delimiters to TID
        return resultText
        '''
        raw_strict = _run_applescript(script_strict)
        
        if raw_strict:
            titles = raw_strict.split('|||')
        else:
            # --- CÁCH 2: Fallback ---
            logger.debug("Strict detection failed, trying fallback...")
            script_simple = 'tell application "System Events" to get name of every window of process "Anki"'
            raw_simple = _run_applescript(script_simple)
            
            if raw_simple:
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
    
    # [DEBUG] Uncomment dòng dưới nếu muốn debug sâu
    # if clean_titles: print(f"[DEBUG] Detected Windows: {clean_titles}")
        
    return clean_titles

def detect_active_profile() -> Optional[str]:
    """
    Phân tích titles để tìm profile.
    """
    titles = get_all_anki_window_titles()
    pattern = re.compile(r"^(.*?) - Anki$")
    
    for title in titles:
        if title in ["Anki", "Browse", "Add", "Stats", "Debug Console"]:
            continue
        
        # Ưu tiên match chính xác
        match = pattern.match(title)
        if match:
            return match.group(1).strip()

        # Fallback cho trường hợp chuỗi bị dính
        if " - Anki" in title:
            if title.endswith(" - Anki"):
                parts = title.split(", ")
                last_part = parts[-1]
                match_fallback = pattern.match(last_part)
                if match_fallback:
                    return match_fallback.group(1).strip()

    return None