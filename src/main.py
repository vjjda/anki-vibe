#!/usr/bin/env python3
# Path: src/main.py
import typer
from rich.console import Console
from src.core.config import settings

# Khởi tạo Typer App
app = typer.Typer(
    name="anki-vibe",
    help="CLI tool to manage Anki decks via Code-as-Source-of-Truth",
    add_completion=False,
)
console = Console()

@app.command()
def sync(
    profile: str = typer.Option(
        ..., 
        "--profile", 
        "-p", 
        help="The Anki profile name to target (e.g., 'UserA')."
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
    console.print(f"Target Profile: [green]{profile}[/green]")
    console.print(f"Data Directory: {settings.DATA_DIR}")
    
    if dry_run:
        console.print("[yellow]⚠️ DRY RUN MODE: No changes will be made to Anki.[/yellow]")
    
    # TODO: Implement connection check and sync logic here
    console.print("[dim]Logic implementation coming soon...[/dim]")

@app.command()
def info() -> None:
    """
    Show current project configuration.
    """
    console.print(f"[bold]Project:[/bold] {settings.PROJECT_NAME}")
    console.print(f"[bold]AnkiConnect:[/bold] {settings.ANKI_CONNECT_URL}")

def main() -> None:
    app()

if __name__ == "__main__":
    main()