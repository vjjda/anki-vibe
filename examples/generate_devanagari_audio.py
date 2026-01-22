import sys
import platform
import time
from pathlib import Path
from ruamel.yaml import YAML
from rich.console import Console
from rich.progress import Progress

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))
from src.utils.tts_google import GoogleTTS

API_KEY = "YOUR_API_KEY"
console = Console()

def get_anki_media_path(profile: str) -> Path:
    system = platform.system()
    home = Path.home()
    if system == "Darwin":
        base = home / "Library/Application Support/Anki2"
    elif system == "Windows":
        base = home / "AppData/Roaming/Anki2"
    else:
        base = home / ".local/share/Anki2"
    return base / profile / "collection.media"

def generate():
    profile = "Vijjo"
    notes_path = Path("devanagari_project/data/notes.yaml")
    
    if not notes_path.exists():
        console.print("[red]Notes not found.[/red]")
        return

    try:
        media_dir = get_anki_media_path(profile)
    except:
        console.print("[red]Media dir not found.[/red]")
        return

    tts = GoogleTTS(API_KEY)
    
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 4096
    
    with open(notes_path, "r", encoding="utf-8") as f:
        notes = yaml.load(f) or []
        
    console.print(f"Generating audio for {len(notes)} notes...")
    
    with Progress() as progress:
        task = progress.add_task("Synthesizing...", total=len(notes))
        
        for note in notes:
            char = note["fields"].get("Character")
            name = note["fields"].get("Name")
            examples = note["fields"].get("Examples", "") # Raw words: "word | word"
            
            # 1. Character Audio
            # Text to speak: "क" (Just the char)
            char_filename = f"Devanagari_Char_{name}.mp3"
            char_path = media_dir / char_filename
            
            if not char_path.exists(): # Idempotent
                if tts.synthesize(char, str(char_path)):
                    note["fields"]["Audio_Character"] = f"[sound:{char_filename}]"
                else:
                    console.print(f"[red]Failed Char:[/red] {char}")
            else:
                # Ensure field is set even if file exists
                note["fields"]["Audio_Character"] = f"[sound:{char_filename}]"

            # 2. Examples Audio
            # Parse examples from the "Examples" field (which currently holds "word | word")
            if examples:
                words = [w.strip() for w in examples.split("|") if w.strip()]
                if words:
                    # Speak with pauses: "Word1. Word2."
                    text_to_speak = ". ".join(words)
                    ex_filename = f"Devanagari_Ex_{name}.mp3"
                    ex_path = media_dir / ex_filename
                    
                    if not ex_path.exists():
                        if tts.synthesize(text_to_speak, str(ex_path)):
                            note["fields"]["Audio_Examples"] = f"[sound:{ex_filename}]"
                        else:
                            console.print(f"[red]Failed Ex:[/red] {name}")
                    else:
                        note["fields"]["Audio_Examples"] = f"[sound:{ex_filename}]"
            
            progress.advance(task)
            # time.sleep(0.1) # Rate limit check? Google TTS is fast usually.

    # Save
    with open(notes_path, "w", encoding="utf-8") as f:
        yaml.dump(notes, f)
        
    console.print("✅ Audio generation complete.")

if __name__ == "__main__":
    generate()
