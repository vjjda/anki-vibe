# Path: src/main.py
#!/usr/bin/env python3
import logging
import typer
from rich.console import Console
from typing import Optional
from src.core.config import settings
from src.core.anki_detector import detect_active_profile
from src.core.logging_config import setup_logging
from src.adapters import AnkiConnectAdapter

# Khởi tạo Logger cho module này
logger = logging.getLogger(__name__)

app = typer.Typer(
    name="anki-vibe",
    help="CLI tool to manage Anki decks via Code-as-Source-of-Truth",
    add_completion=False,
)
console = Console()

# --- Helpers ---

def _initialize_app(verbose: bool) -> None:
    """Common setup for all commands."""
    log_level = "DEBUG" if verbose else "INFO"
    setup_logging(log_level)
    logger.debug(f"App initialized with log level: {log_level}")

def _resolve_profile(profile_arg: Optional[str]) -> str:
    """Helper to resolve profile from argument or auto-detection."""
    target_profile = profile_arg
    
    if not target_profile:
        logger.info("Attempting to detect active Anki profile...")
        detected = detect_active_profile()
        if detected:
            target_profile = detected
            console.print(f"✅ Detected active profile: [bold green]{target_profile}[/bold green]")
        else:
            logger.error("Could not detect active profile.")
            console.print("[bold red]❌ Error: Could not detect active profile.[/bold red]")
            console.print("👉 Please open a profile in Anki OR specify one using --profile")
            raise typer.Exit(code=1)
    else:
        # Safety warning logic
        detected = detect_active_profile()
        if detected and detected != target_profile:
            console.print(f"[bold yellow]⚠️  WARNING: You are targeting '{target_profile}' but Anki is running '{detected}'[/bold yellow]")
            if not typer.confirm("Do you want to continue?"):
                raise typer.Exit()
    
    return target_profile

# --- Commands ---

@app.command()
def sync(
    profile: Optional[str] = typer.Option(None, "--profile", "-p"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logs")
) -> None:
    """[PUSH] Sync data from local YAML files to Anki."""
    _initialize_app(verbose)
    console.print(f"[bold blue]🚀 Starting Anki-Vibe Sync (Push)[/bold blue]")
    
    target_profile = _resolve_profile(profile)
    logger.info(f"Targeting Profile: {target_profile}")
    logger.info(f"Data Directory: {settings.DATA_DIR}")
    
    if dry_run:
        console.print("[yellow]⚠️  DRY RUN MODE: No changes will be made to Anki.[/yellow]")
    
    # TODO: Implement Push Logic
    logger.warning("Push logic implementation coming soon...")

@app.command()
def pull(
    profile: Optional[str] = typer.Option(None, "--profile", "-p"),
    force: bool = typer.Option(False, "--force"),
    verbose: bool = typer.Option(False, "--verbose", "-v")
) -> None:
    """[PULL] Fetch changes from Anki and update local YAML files."""
    _initialize_app(verbose)
    console.print(f"[bold red]⬇️  Starting Anki-Vibe Pull (Reverse Sync)[/bold red]")
    
    target_profile = _resolve_profile(profile)
    
    # Safety Check
    if not force:
        console.print(f"\n[bold yellow]⚠️  CRITICAL WARNING:[/bold yellow]")
        console.print("This will overwrite local YAML files.")
        if not typer.confirm("Have you committed your code to Git?"):
            console.print("Aborted.")
            raise typer.Exit()
        
        if not typer.confirm(f"Pull data for '{target_profile}'?"):
            raise typer.Exit()

    logger.info(f"Starting pull process for profile: {target_profile}")
    # TODO: Implement Pull Logic
    logger.warning("Pull logic implementation coming soon...")
    console.print("[green]✅ Pull process finished (simulation). Check git diff![/green]")

@app.command()
def info(
    verbose: bool = typer.Option(False, "--verbose", "-v")
) -> None:
    """Show current project configuration."""
    _initialize_app(verbose)
    
    console.print(f"[bold]Project:[/bold] {settings.PROJECT_NAME}")
    console.print(f"[bold]AnkiConnect:[/bold] {settings.ANKI_CONNECT_URL}")
    
    # Test Connection
    adapter = AnkiConnectAdapter()
    try:
        version = adapter.ping()
        console.print(f"✅ [bold green]Connected:[/bold green] {version}")
        logger.debug(f"Connection successful: {version}")
        
        decks = adapter.get_deck_names()
        console.print(f"[bold]Available Decks ({len(decks)}):[/bold]")
        for deck in decks[:5]:
            console.print(f"  - {deck}")
            
    except Exception as e:
        logger.exception("Failed to connect to Anki") # Log full traceback to file
        console.print(f"❌ [bold red]Error:[/bold red] {e}")

def main() -> None:
    app()

if __name__ == "__main__":
    main()