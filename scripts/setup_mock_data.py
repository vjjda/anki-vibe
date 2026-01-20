import sys
from pathlib import Path
from ruamel.yaml import YAML

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.core.config import settings
from src.core.anki_detector import detect_active_profile


def create_mock_data():
    profile = detect_active_profile()
    if not profile:
        print("❌ Please open Anki first!")
        return

    print(f"Creating mock data for profile: {profile}")

    # 1. Tạo folder Project mới
    # Chúng ta đặt tên folder là "Demo_Project"
    project_dir = settings.ANKI_DATA_DIR / profile / "Demo_Project"
    project_dir.mkdir(parents=True, exist_ok=True)

    # 2. Tạo config.yaml
    # Map folder này vào Note Type "Basic" của Anki
    yaml = YAML()
    config = {
        "anki_model_name": "Basic",
        "description": "Mock data created for testing Push feature",
    }
    with open(project_dir / "config.yaml", "w", encoding="utf-8") as f:
        yaml.dump(config, f)

    # 3. Tạo notes.yaml (Chưa có ID)
    # Chúng ta sẽ đẩy vào Deck mới là "AnkiVibe::TestDeck"
    notes = [
        {
            "id": None,  # Chưa có ID -> Sẽ kích hoạt CREATE
            "deck": "AnkiVibe::TestDeck",
            "tags": ["test_vibe", "mock_data"],
            "fields": {
                "Front": "Hello Anki-Vibe",
                "Back": "Xin chào, đây là dữ liệu test từ code.",
            },
        },
        {
            "id": None,
            "deck": "AnkiVibe::TestDeck",
            "tags": ["html_test"],
            "fields": {
                "Front": "<b>Bold Question</b>",
                "Back": "<i>Italic Answer</i> with <br> break line.",
            },
        },
        {
            "id": None,
            "deck": "AnkiVibe::TestDeck::SubDeck",  # Test tạo sub-deck
            "tags": [],
            "fields": {"Front": "Sub Deck Card", "Back": "Nằm trong deck con"},
        },
    ]

    with open(project_dir / "notes.yaml", "w", encoding="utf-8") as f:
        yaml.dump(notes, f)

    print(f"✅ Created mock data at: {project_dir}")
    print("👉 Now run: poetry run python src/main.py sync")


if __name__ == "__main__":
    create_mock_data()
