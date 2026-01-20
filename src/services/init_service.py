from pathlib import Path
from rich.console import Console

class InitService:
    def __init__(self):
        self.console = Console()

    def create_project(self, path: Path, name: str, profile: str = ""):
        """Tạo file anki-vibe.toml mẫu."""
        config_file = path / "anki-vibe.toml"
        
        if config_file.exists():
            self.console.print(f"[yellow]⚠️  Config file already exists at: {config_file}[/yellow]")
            return

        template = f"""# Anki Vibe Project Configuration
# Document: https://github.com/hieucao/anki-vibe

[project]
name = "{name}"
# Profile Anki mà project này sẽ kết nối (Optional)
anki_profile = "{profile}"

# --- Target 1: Ví dụ một bộ thẻ từ vựng ---
[[targets]]
name = "Vocabulary"
# Model (Note Type) trong Anki. Phải chính xác từng ký tự.
model = "Basic"
# Deck mặc định để chứa các thẻ mới tạo
deck = "Default"
# Query để Pull dữ liệu về. Ví dụ: 'deck:Default note:Basic'
query = 'deck:Default note:Basic'
# Thư mục lưu trữ (tương đối so với file này)
folder = "vocab_data"

# --- Target 2: Ví dụ bộ thẻ Kanji (Uncomment để dùng) ---
# [[targets]]
# name = "Kanji"
# model = "Kanji Model"
# deck = "Japanese::Kanji"
# query = 'tag:kanji'
# folder = "kanji_data"
"""
        with open(config_file, "w", encoding="utf-8") as f:
            f.write(template)
            
        self.console.print(f"[green]✅ Created project config at: {config_file}[/green]")
        self.console.print("👉 Edit this file to match your Anki decks, then run 'anki-vibe pull'.")
