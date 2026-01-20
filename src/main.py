# Path: src/main.py
#!/usr/bin/env python3
import logging
import typer
from rich.console import Console
from typing import Optional
from src.core.config import settings
from src.core.anki_detector import detect_active_profile
from src.core.logging_config import setup_logging
from src.services.pull_service import PullService
from src.services.sync_service import SyncService 
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

def _resolve_profile(profile_arg: Optional[str], yes: bool = False) -> str:
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
            if not yes and not typer.confirm("Do you want to continue?"):
                raise typer.Exit()
    
    return target_profile

# --- Commands ---



@app.command()
def pull(
    profile: Optional[str] = typer.Option(None, "--profile", "-p"),
    force: bool = typer.Option(False, "--force"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmations"),
    verbose: bool = typer.Option(False, "--verbose", "-v")
) -> None:
    """[PULL] Fetch all models, templates, and notes from Anki."""
    _initialize_app(verbose)
    
    # 1. Resolve Profile
    try:
        target_profile = _resolve_profile(profile, yes=yes)
    except Exception:
        return

    # 2. Safety Check
    console.print(f"\n[bold yellow]⚠️  CRITICAL WARNING:[/bold yellow]")
    console.print(f"This will pull ALL data from profile '[bold]{target_profile}[/bold]' into [bold]{settings.ANKI_DATA_DIR}/{target_profile}[/bold].")
    console.print("Existing files (notes.yaml, templates) may be overwritten.")
    
    if not force and not yes:
        if not typer.confirm("Are you sure you want to proceed?"):
            raise typer.Exit()

    # 3. Execute Pull Service
    console.print(f"[bold green]⬇️  Starting Pull for {target_profile}...[/bold green]")
    
    try:
        # Load profile trên Anki trước (nếu chưa đúng)
        adapter = AnkiConnectAdapter()
        # adapter.load_profile(target_profile) # Cẩn thận: Load profile sẽ restart Anki gui sync.
        
        service = PullService(target_profile, adapter)
        service.pull_all_models()
        
        console.print(f"\n[bold green]✅ Pull completed successfully![/bold green]")
        console.print(f"Check your data at: {settings.ANKI_DATA_DIR}/{target_profile}")
        
    except Exception as e:
        logger.exception("Pull failed")
        console.print(f"[bold red]❌ Error during pull:[/bold red] {e}")

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

@app.command()
def sync(
    profile: Optional[str] = typer.Option(None, "--profile", "-p"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Simulate without pushing to Anki"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmations"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logs")
) -> None:
    """[PUSH] Sync data from local YAML files to Anki (Create & Update)."""
    _initialize_app(verbose)
    console.print(f"[bold blue]🚀 Starting Anki-Vibe Sync (Push)[/bold blue]")
    
    # 1. Resolve Profile
    try:
        target_profile = _resolve_profile(profile, yes=yes)
    except Exception:
        return

    console.print(f"Targeting: [green]{target_profile}[/green]")
    
    # 2. Confirm
    if not dry_run:
         # Một chút an toàn: confirm trước khi push
        if not yes and not typer.confirm(f"Do you want to push changes to Anki profile '{target_profile}'?"):
             raise typer.Exit()

    # 3. Execute
    try:
        adapter = AnkiConnectAdapter()
        service = SyncService(target_profile, adapter)
        
        if dry_run:
            console.print("[yellow]Dry run is not fully implemented yet. Skipping execution.[/yellow]")
        else:
            service.push_all_changes()
            console.print(f"\n[bold green]✅ Sync (Push) completed successfully![/bold green]")
            
    except Exception as e:
        logger.exception("Sync failed")
        console.print(f"[bold red]❌ Error during sync:[/bold red] {e}")

def main() -> None:
    app()

if __name__ == "__main__":
    main()