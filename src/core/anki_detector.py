# Path: src/core/anki_detector.py
import sys
import subprocess
import re
from typing import Optional

def get_anki_window_title() -> Optional[str]:
    """
    Lấy tiêu đề cửa sổ của ứng dụng Anki đang chạy (Cross-platform).
    """
    platform = sys.platform

    try:
        if platform == "darwin":  # macOS
            # Sử dụng AppleScript để lấy tên cửa sổ của process Anki
            script = 'tell application "System Events" to get name of window 1 of process "Anki"'
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
            
        elif platform == "win32":  # Windows
            import ctypes
            
            # EnumWindows để tìm cửa sổ có class name hoặc title
            # Cách đơn giản: Tìm cửa sổ có title chứa "Anki"
            # Lưu ý: Cách này có thể lấy nhầm nếu có folder tên "Anki" đang mở, 
            # nhưng ta sẽ filter bằng logic regex sau.
            user32 = ctypes.windll.user32
            
            titles = []
            def foreach_window(hwnd, lParam):
                length = user32.GetWindowTextLengthW(hwnd)
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                titles.append(buff.value)
                return True
                
            user32.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)(foreach_window), 0)
            
            # Lọc title có chứa chữ Anki
            for title in titles:
                if "Anki" in title and " - " in title: # Profile title usually has separator
                    return title
            # Fallback nếu ở màn hình login
            if "Anki" in titles:
                return "Anki"

        elif platform.startswith("linux"): # Linux
            # Yêu cầu: xdotool hoặc wmctrl. Ở đây dùng xprop (thường có sẵn)
            # Tìm window id của Anki
            try:
                # Cách đơn giản dùng xdotool nếu có
                res = subprocess.run(["xdotool", "search", "--name", "Anki", "getwindowname"], capture_output=True, text=True)
                if res.returncode == 0:
                    return res.stdout.strip().split('\n')[0]
            except FileNotFoundError:
                pass
            
            # Fallback (phức tạp hơn trên Linux do nhiều Window Manager)
            return None

    except Exception as e:
        # Không crash app chỉ vì không detect được window
        print(f"Warning: Could not detect Anki window: {e}")
        return None
    
    return None

def detect_active_profile() -> Optional[str]:
    """
    Phân tích window title để lấy tên Profile.
    Format thường gặp: "User1 - Anki"
    """
    title = get_anki_window_title()
    
    if not title:
        return None
        
    # Nếu đang ở màn hình chọn profile
    if title.strip() == "Anki":
        return None
        
    # Regex để lấy phần trước " - Anki"
    # Ví dụ: "User A - Anki" -> match "User A"
    match = re.match(r"^(.*?) - Anki$", title)
    if match:
        return match.group(1)
        
    return None