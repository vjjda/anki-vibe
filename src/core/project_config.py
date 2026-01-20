import tomllib
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field, ValidationError

class TargetConfig(BaseModel):
    name: str = Field(..., description="Tên định danh cho target này")
    model: str = Field(..., description="Anki Note Type (Model) sử dụng")
    deck: str = Field(..., description="Deck mặc định khi tạo Note mới")
    query: str = Field(..., description="Query để lọc Notes khi Pull (ví dụ: 'deck:Japanese')")
    folder: str = Field(default=".", description="Thư mục lưu trữ dữ liệu (tương đối so với file config)")

class ProjectMetadata(BaseModel):
    name: str = Field(default="My Anki Project", description="Tên dự án")
    anki_profile: Optional[str] = Field(default=None, description="Profile Anki cần kết nối")

class ProjectConfig(BaseModel):
    project: ProjectMetadata
    targets: List[TargetConfig] = Field(default_factory=list)
    
    # Internal: Lưu đường dẫn file config để resolve path tương đối
    _config_path: Path = Path(".")

    def resolve_folder(self, target: TargetConfig) -> Path:
        """Trả về đường dẫn tuyệt đối tới folder chứa data của target."""
        return (self._config_path.parent / target.folder).resolve()

def load_project_config(config_path: Path) -> ProjectConfig:
    """Đọc và validate file anki-vibe.toml."""
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found at: {config_path}")
    
    with open(config_path, "rb") as f:
        data = tomllib.load(f)
    
    try:
        config = ProjectConfig(**data)
        config._config_path = config_path
        return config
    except ValidationError as e:
        raise ValueError(f"Invalid config format: {e}")

def find_project_config(start_path: Path = Path(".")) -> Optional[Path]:
    """
    Tìm file anki-vibe.toml ngược từ thư mục hiện tại lên root.
    """
    current = start_path.resolve()
    for _ in range(100): # Limit depth
        config_file = current / "anki-vibe.toml"
        if config_file.exists():
            return config_file
        
        parent = current.parent
        if parent == current: # Reached root
            break
        current = parent
    return None
