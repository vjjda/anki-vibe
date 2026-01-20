# Path: src/core/anki_detector.py
import sys
import subprocess
import re
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)

def get_all_anki_window_titles() -> List[str]:
    """
    Lấy danh sách tiêu đề của TẤT CẢ các cửa sổ Anki đang mở.
    Hỗ trợ xử lý trường hợp mở nhiều cửa sổ (Browse, Add Note, Stats...).
    """
    platform = sys.platform
    titles = []

    try:
        if platform == "darwin":  # macOS
            # Sử dụng AppleScript để lấy danh sách tên tất cả cửa sổ, ngăn cách bằng dòng mới
            script = '''
            tell application "System Events"
                if exists process "Anki" then
                    set winList to name of every window of process "Anki"
                    set {TID, text item delimiters} to {text item delimiters, "\\n"}
                    set resultText to winList as text
                    set text item delimiters to TID
                    return resultText
                else
                    return ""
                end if
            end tell
            '''
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                titles = result.stdout.strip().split('\n')
            
        elif platform == "win32":  # Windows
            import ctypes
            
            user32 = ctypes.windll.user32
            
            def foreach_window(hwnd, lParam):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value
                    
                    # Chỉ lấy cửa sổ có chữ Anki để tối ưu
                    # Lưu ý: Cửa sổ Main có tên "Profile - Anki"
                    # Cửa sổ Browse có tên "Browse" (không có chữ Anki), 
                    # nhưng ta cần lấy hết hoặc check process ID (phức tạp hơn).
                    # Ở đây ta check lỏng: Nếu title chứa Anki hoặc là window chính
                    # Thực tế trên Windows, EnumWindows quét toàn bộ hệ thống.
                    titles.append(title)
                return True
                
            user32.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)(foreach_window), 0)

        elif platform.startswith("linux"): # Linux
            try:
                # Dùng xdotool search để tìm tất cả window id của Anki
                res = subprocess.run(["xdotool", "search", "--name", "Anki"], capture_output=True, text=True)
                if res.returncode == 0:
                    window_ids = res.stdout.strip().split('\n')
                    for wid in window_ids:
                        if not wid: continue
                        name_res = subprocess.run(["xdotool", "getwindowname", wid], capture_output=True, text=True)
                        if name_res.returncode == 0:
                            titles.append(name_res.stdout.strip())
            except FileNotFoundError:
                pass

    except Exception as e:
        logger.warning(f"Error scanning window titles: {e}")
        return []
    
    return titles

def detect_active_profile() -> Optional[str]:
    """
    Phân tích danh sách window title để tìm tên Profile.
    Ưu tiên tìm pattern: "ProfileName - Anki"
    """
    titles = get_all_anki_window_titles()
    
    # Regex pattern: Bắt đầu bằng (tên), kết thúc bằng " - Anki"
    # Ví dụ: "Vijjo - Anki" -> match
    # "Browse" -> no match
    # "Add" -> no match
    pattern = re.compile(r"^(.*?) - Anki$")
    
    for title in titles:
        # Bỏ qua cửa sổ login hoặc cửa sổ không liên quan
        if title.strip() == "Anki":
            continue
            
        match = pattern.match(title)
        if match:
            profile_name = match.group(1)
            # Loại trừ một số cửa sổ hệ thống giả mạo nếu có
            if profile_name.strip():
                return profile_name
    
    return None