import sys
import re
import subprocess
import platform
from pathlib import Path
from typing import Tuple, Optional
from concurrent.futures import ProcessPoolExecutor
from ruamel.yaml import YAML
from rich.console import Console
from rich.progress import Progress

console = Console()

def get_anki_media_path(profile: str) -> Path:
    system = platform.system()
    home = Path.home()
    if system == "Darwin": # MacOS
        base = home / "Library/Application Support/Anki2"
    elif system == "Windows":
        base = home / "AppData/Roaming/Anki2"
    else: # Linux
        base = home / ".local/share/Anki2"
    
    media_path = base / profile / "collection.media"
    if not media_path.exists():
        # Fallback check for common custom paths or raise
        raise FileNotFoundError(f"Could not find Anki media folder at {media_path}")
    return media_path

def process_audio_file(args: Tuple[Path, Path]) -> Optional[str]:
    """
    Worker function to process one audio file using FFmpeg.
    Returns: None on success, error string on failure.
    """
    input_path, output_path = args
    
    if not input_path.exists():
        # Có thể file chưa được sync về máy? Hoặc tên sai.
        return f"File not found: {input_path.name}"
    
    if output_path.exists():
        return None # Skip if exists

    # FFmpeg Filter Complex
    # 1. Trim Silence Start (-65dB)
    # 2. Reverse -> Trim Silence End -> Reverse
    # 3. Loudnorm (-15 LUFS)
    # 4. Pad 200ms Start & End
    filter_cmd = (
        "silenceremove=start_periods=1:start_duration=0:start_threshold=-65dB:detection=peak,"
        "areverse,"
        "silenceremove=start_periods=1:start_duration=0:start_threshold=-65dB:detection=peak,"
        "areverse,"
        "loudnorm=I=-15:TP=-1.5:LRA=11,"
        "adelay=200|200,"
        "apad=pad_dur=0.2"
    )

    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-i", str(input_path),
        "-af", filter_cmd,
        str(output_path)
    ]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        return None
    except subprocess.CalledProcessError as e:
        return f"FFmpeg error for {input_path.name}: {e.stderr.decode()}"

def main():
    profile = "Vijjo"
    yaml_path = Path("data/anki/Vijjo/Sinhala/notes.yaml")
    
    # 1. Setup paths
    try:
        media_dir = get_anki_media_path(profile)
        console.print(f"[green]Found Anki Media Dir:[/green] {media_dir}")
    except Exception as e:
        console.print(f"[red]{e}[/red]")
        return

    if not yaml_path.exists():
        console.print(f"[red]Notes YAML not found at {yaml_path}[/red]")
        return

    # 2. Load YAML & Collect Files
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 4096
    
    with open(yaml_path, "r", encoding="utf-8") as f:
        notes = yaml.load(f) or []

    tasks = [] # List of (input, output)
    replacements = {} # Map old_filename -> new_filename
    
    # Filter notes with tag "nemo_sinhala"
    nemo_notes = [n for n in notes if "nemo_sinhala" in n.get("tags", [])]
    console.print(f"Scanning {len(nemo_notes)} Nemo notes...")

    for note in nemo_notes:
        for field_name, field_value in note["fields"].items():
            # Find all audio tags in this field
            matches = list(re.finditer(r'\[sound:(.+?)\]', field_value))
            for match in matches:
                filename = match.group(1)
                
                # Check suffix
                if "-standardized" in filename:
                    continue 
                
                name_stem = Path(filename).stem
                ext = Path(filename).suffix
                new_filename = f"{name_stem}-standardized{ext}"
                
                input_file = media_dir / filename
                output_file = media_dir / new_filename
                
                tasks.append((input_file, output_file))
                
                # Store replacement needed (Scope: Global replacements map might be risky if filenames clash, 
                # but Anki media filenames are flat, so it's okay)
                replacements[filename] = new_filename

    # 3. Execute Multiprocessing
    unique_tasks = list(set(tasks)) # Remove duplicates
    
    if not unique_tasks:
        console.print("[yellow]No new audio files to process.[/yellow]")
    else:
        console.print(f"Processing [bold cyan]{len(unique_tasks)}[/bold cyan] audio files with FFmpeg...")
        
        with Progress() as progress:
            task_id = progress.add_task("Standardizing...", total=len(unique_tasks))
            
            with ProcessPoolExecutor() as executor:
                results = executor.map(process_audio_file, unique_tasks)
                
                for res in results:
                    if res:
                        console.print(f"[red]Error:[/red] {res}")
                    progress.advance(task_id)

    # 4. Update YAML References
    if replacements:
        console.print("Updating notes.yaml references...")
        updates_count = 0
        for note in nemo_notes:
            note_updated = False
            for field_name, field_value in note["fields"].items():
                new_value = field_value
                for old, new in replacements.items():
                    if old in new_value:
                        new_value = new_value.replace(old, new)
                
                if new_value != field_value:
                    note["fields"][field_name] = new_value
                    note_updated = True
            
            if note_updated:
                updates_count += 1

        if updates_count > 0:
            with open(yaml_path, "w", encoding="utf-8") as f:
                yaml.dump(notes, f)
            console.print(f"[green]Updated {updates_count} notes in YAML.[/green]")
            console.print("👉 Now run [bold]anki-vibe sync[/bold] to push changes.")
        else:
            console.print("No YAML updates applied (Logic check needed).")
    else:
        console.print("No replacements needed.")

if __name__ == "__main__":
    main()
