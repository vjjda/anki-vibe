# Path: scripts/test_models.py
import sys
from pathlib import Path
import yaml
from rich.console import Console

# Add project root to path để import được module src
sys.path.append(str(Path(__file__).parent.parent))

from src.models import AnkiNote, ModelFileSystemConfig
from src.core.anki_detector import detect_active_profile
from src.core.config import settings

console = Console()

def test_load_data_for_active_profile():
    console.print("[bold blue]🔍 Testing Data Loading with Active Profile[/bold blue]")

    # 1. Detect Profile
    active_profile = detect_active_profile()
    
    if not active_profile:
        console.print("[bold red]❌ No Anki profile detected![/bold red]")
        console.print("👉 Please open Anki with profile 'Vijjo' running.")
        return

    console.print(f"✅ Detected Active Profile: [bold green]{active_profile}[/bold green]")

    # 2. Define Path
    profile_dir = settings.DATA_DIR / active_profile
    if not profile_dir.exists():
        console.print(f"[bold yellow]⚠️  Warning: No data folder found for profile '{active_profile}'[/bold yellow]")
        console.print(f"   Expected path: {profile_dir}")
        console.print("   Please rename 'data/UserA' to 'data/Vijjo' if needed.")
        return

    # 3. Scan Model Folders
    # Giả sử trong folder profile có folder Model là "Basic_Vocabulary"
    # Trong thực tế ta sẽ loop qua tất cả sub-folder
    model_name = "Basic_Vocabulary" 
    model_dir = profile_dir / model_name
    
    if not model_dir.exists():
        console.print(f"[red]❌ Model folder '{model_name}' not found in {active_profile}[/red]")
        return

    # 4. Test Load Config
    config_path = model_dir / "config.yaml"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            raw_config = yaml.safe_load(f)
            config = ModelFileSystemConfig(**raw_config)
            console.print(f"\n📂 [bold]Model Config Loaded:[/bold]")
            console.print(f"   - Anki Model Name: [cyan]{config.anki_model_name}[/cyan]")
            console.print(f"   - Description: {config.description}")
    else:
        console.print("[red]❌ config.yaml missing![/red]")

    # 5. Test Load Notes
    note_path = model_dir / "lesson_01.yaml"
    if note_path.exists():
        with open(note_path, "r", encoding="utf-8") as f:
            raw_notes = yaml.safe_load(f)
            # Parse list of notes
            notes = [AnkiNote(**n) for n in raw_notes]
            
            console.print(f"\n📝 [bold]Notes Loaded from {note_path.name}:[/bold]")
            for i, note in enumerate(notes, 1):
                front = note.fields.get('Front', 'N/A')
                deck = note.deck
                console.print(f"   {i}. [yellow]{front}[/yellow] (Deck: {deck})")
                
            console.print(f"\n[bold green]✨ SUCCESS: Data structure for '{active_profile}' is valid![/bold green]")
    else:
        console.print(f"[red]❌ Data file {note_path.name} missing![/red]")

if __name__ == "__main__":
    test_load_data_for_active_profile()