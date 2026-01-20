# Path: src/main.py
#!/usr/bin/env python3
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

def _resolve_profile(profile_arg: Optional[str]) -> str:
    """
    Helper to resolve profile from argument or auto-detection.
    """
    target_profile = profile_arg
    
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
        # Safety warning if mismatch
        detected = detect_active_profile()
        if detected and detected != target_profile:
            console.print(f"[bold yellow]⚠️  WARNING: You are targeting '{target_profile}' but Anki is running '{detected}'[/bold yellow]")
            if not typer.confirm("Do you want to continue?"):
                raise typer.Exit()
    
    return target_profile

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
    [PUSH] Sync data from local YAML files to Anki.
    """
    console.print(f"[bold blue]🚀 Starting Anki-Vibe Sync (Push)[/bold blue]")
    
    target_profile = _resolve_profile(profile)

    console.print(f"Targeting: [green]{target_profile}[/green]")
    console.print(f"Data Directory: {settings.DATA_DIR}")
    
    if dry_run:
        console.print("[yellow]⚠️  DRY RUN MODE: No changes will be made to Anki.[/yellow]")
    
    # TODO: Implement Push Logic
    console.print("[dim]Push logic implementation coming soon...[/dim]")


@app.command()
def pull(
    profile: Optional[str] = typer.Option(None, "--profile", "-p"),
    force: bool = typer.Option(False, "--force", help="Overwrite local files without asking")
) -> None:
    """
    [PULL] Fetch changes from Anki and update local YAML files.
    WARNING: Ensure you have committed your code before running this!
    """
    console.print(f"[bold red]⬇️  Starting Anki-Vibe Pull (Reverse Sync)[/bold red]")
    
    # 1. Resolve Profile
    target_profile = _resolve_profile(profile)
    
    # 2. Safety Check
    console.print(f"\n[bold yellow]⚠️  CRITICAL WARNING:[/bold yellow]")
    console.print(f"You are about to modify local YAML files in [bold]{settings.DATA_DIR}/{target_profile}[/bold] using data from Anki.")
    console.print("This action will overwrite fields in your YAML files.")
    console.print("However, comments and structure will be preserved thanks to ruamel.yaml.")
    console.print("\n[bold]👉 Please ensure you have committed your current changes to Git![/bold]")
    
    if not force:
        if not typer.confirm("Have you committed your code to Git?"):
            console.print("Aborted.")
            raise typer.Exit()
        
        if not typer.confirm(f"Are you sure you want to pull data for profile '{target_profile}'?"):
            console.print("Aborted.")
            raise typer.Exit()

    # TODO: Implement Pull Logic using ruamel.yaml
    console.print("[dim]Pull logic implementation coming soon...[/dim]")
    console.print("[green]✅ Pull process finished (simulation). Check git diff![/green]")

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