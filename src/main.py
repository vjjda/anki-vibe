# Path: src/main.py
import typer
from rich.console import Console
from typing import Optional
from src.core.config import settings
from src.core.anki_detector import detect_active_profile

app = typer.Typer(
    name="anki-vibe",
    help="CLI tool to manage Anki decks via Code-as-Source-of-Truth",
    add_completion=False,
)
console = Console()

@app.command()
def sync(
    profile: Optional[str] = typer.Option(
        None, 
        "--profile", 
        "-p", 
        help="The Anki profile name. If not provided, tries to detect active Anki window."
    ),
    dry_run: bool = typer.Option(
        False, 
        "--dry-run", 
        help="Simulate the sync without applying changes."
    )
) -> None:
    """
    Sync data from local YAML files to Anki.
    """
    console.print(f"[bold blue]🚀 Starting Anki-Vibe Sync[/bold blue]")
    
    # 1. Resolve Profile
    target_profile = profile
    
    if not target_profile:
        console.print("[dim]🔍 Attempting to detect active Anki profile...[/dim]")
        detected = detect_active_profile()
        if detected:
            target_profile = detected
            console.print(f"✅ Detected active profile: [bold green]{target_profile}[/bold green]")
        else:
            console.print("[bold red]❌ Error: Could not detect active profile.[/bold red]")
            console.print("👉 Please open a profile in Anki OR specify one using --profile")
            raise typer.Exit(code=1)
    else:
        # Nếu user nhập tay, ta vẫn nên warn nếu nó khác với cái đang mở (Optional safety)
        detected = detect_active_profile()
        if detected and detected != target_profile:
            console.print(f"[bold yellow]⚠️ WARNING: You are targeting '{target_profile}' but Anki is running '{detected}'[/bold yellow]")
            if not typer.confirm("Do you want to continue?"):
                raise typer.Exit()

    console.print(f"Targeting: [green]{target_profile}[/green]")
    console.print(f"Data Directory: {settings.DATA_DIR}")
    
    if dry_run:
        console.print("[yellow]⚠️ DRY RUN MODE: No changes will be made to Anki.[/yellow]")
    
    # TODO: Connect Logic here...
    console.print("[dim]Logic implementation coming soon...[/dim]")

@app.command()
def info() -> None:
    """
    Show current project configuration.
    """
    console.print(f"[bold]Project:[/bold] {settings.PROJECT_NAME}")
    console.print(f"[bold]AnkiConnect:[/bold] {settings.ANKI_CONNECT_URL}")
    
    active = detect_active_profile()
    status = f"[green]{active}[/green]" if active else "[red]Not detected / Anki Closed[/red]"
    console.print(f"[bold]Active Anki Profile:[/bold] {status}")

def main() -> None:
    app()

if __name__ == "__main__":
    main()