# Path: src/services/pull_service.py
import logging
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed

from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
)

from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import PreservedScalarString

from src.core.config import settings
from src.core.project_config import ProjectConfig
from src.core.state_manager import StateManager
from src.adapters import AnkiConnectAdapter
from src.utils.text_utils import sanitize_filename
from src.utils.hashing import compute_note_hash, compute_model_hash

logger = logging.getLogger(__name__)

MAX_WORKERS = 5 

class PullService:
    """
    Service chịu trách nhiệm kéo dữ liệu từ Anki về lưu trữ local.
    Đồng thời cập nhật State để Sync lần sau không bị dư thừa.
    """

    def __init__(self, profile_name: str, adapter: AnkiConnectAdapter, db_path: Optional[Path] = None):
        self.profile = profile_name
        self.adapter = adapter
        self.console = Console()
        
        # Determine DB path
        if db_path is None:
             db_path = settings.ANKI_DATA_DIR / profile_name / ".anki_vibe.db"
        self.state_manager = StateManager(db_path)

    def _create_yaml_dumper(self) -> YAML:
        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.indent(mapping=2, sequence=4, offset=2)
        yaml.width = 4096
        return yaml

    def pull_project(self, config: ProjectConfig) -> None:
        """Pull dữ liệu dựa trên cấu hình Project."""
        self.console.print(f"Syncing Project: [bold cyan]{config.project.name}[/bold cyan]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.percentage:>3.0f}%"),
            console=self.console
        ) as progress:
            main_task = progress.add_task("Syncing Targets...", total=len(config.targets))
            
            for target in config.targets:
                progress.update(main_task, description=f"Target: {target.name}")
                
                try:
                    target_dir = config.resolve_folder(target)
                    target_dir.mkdir(parents=True, exist_ok=True)
                    
                    # 1. Save Metadata & Update State
                    self._save_model_metadata(target.model, target_dir)
                    
                    # 2. Save Notes & Update State
                    self._save_notes_by_query(target.query, target_dir)
                    
                except Exception as e:
                    self.console.print(f"[red]Failed target '{target.name}': {e}[/red]")
                    logger.error(f"Failed target {target.name}: {e}")
                
                progress.advance(main_task)

    def pull_all_models(self) -> None:
        """Main entry point: Pull toàn bộ Models (Monorepo Legacy)."""
        try:
            model_names = self.adapter.get_model_names()
        except Exception as e:
            logger.error(f"Failed to fetch model names: {e}")
            self.console.print(f"[bold red]❌ Failed to fetch model names:[/bold red] {e}")
            return

        base_dir = settings.ANKI_DATA_DIR / self.profile
        base_dir.mkdir(parents=True, exist_ok=True)
        
        active_folder_names: Set[str] = set()
        total_models = len(model_names)
        self.console.print(f"Found [bold cyan]{total_models}[/bold cyan] models. Starting sync...")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.percentage:>3.0f}%"),
            TextColumn("• [cyan]{task.completed}/{task.total}"),
            console=self.console
        ) as progress:
            
            main_task = progress.add_task("[cyan]Syncing Models...", total=total_models)
            
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                future_to_model = {}
                for model_name in model_names:
                    safe_name = sanitize_filename(model_name)
                    active_folder_names.add(safe_name)
                    future = executor.submit(self._process_single_model, model_name, base_dir)
                    future_to_model[future] = model_name
                
                for future in as_completed(future_to_model):
                    model_name = future_to_model[future]
                    try:
                        future.result()
                    except Exception as e:
                        progress.console.print(f"[red]Failed to process {model_name}: {e}[/red]")
                        logger.error(f"Error in thread for model {model_name}", exc_info=True)
                    finally:
                        progress.advance(main_task)

        self._cleanup_stale_models(base_dir, active_folder_names)

    def _cleanup_stale_models(self, base_dir: Path, active_folder_names: Set[str]) -> None:
        self.console.print("\n[dim]🔍 Checking for stale data...[/dim]")
        existing_folders = {item.name for item in base_dir.iterdir() if item.is_dir()}
        stale_folders = existing_folders - active_folder_names
        stale_folders = {f for f in stale_folders if not f.startswith(("_", "."))}

        if not stale_folders:
            self.console.print("[green]✨ Clean workspace. No stale files found.[/green]")
            return

        self.console.print(f"[yellow]⚠️  Found {len(stale_folders)} stale model folders (deleted on Anki):[/yellow]")
        for folder_name in stale_folders:
            folder_path = base_dir / folder_name
            try:
                shutil.rmtree(folder_path)
                logger.info(f"Deleted stale folder: {folder_path}")
                self.console.print(f"  [red]🗑️  Deleted:[/red] {folder_name}")
            except Exception as e:
                logger.error(f"Failed to delete {folder_path}: {e}")

    def _process_single_model(self, model_name: str, base_dir: Path) -> None:
        safe_name = sanitize_filename(model_name)
        model_dir = base_dir / safe_name
        model_dir.mkdir(exist_ok=True)

        self._save_model_metadata(model_name, model_dir)
        self._save_model_notes(model_name, model_dir)

    def _save_model_metadata(self, model_name: str, model_dir: Path) -> None:
        yaml = self._create_yaml_dumper()

        # Config
        config_data = {
            "anki_model_name": model_name,
            "description": f"Auto-generated config for model '{model_name}'"
        }
        with open(model_dir / "config.yaml", "w", encoding="utf-8") as f:
            yaml.dump(config_data, f)

        # Styling
        css_content = ""
        try:
            styling = self.adapter.get_model_styling(model_name)
            css_content = styling.get("css", "")
            if css_content:
                with open(model_dir / "style.css", "w", encoding="utf-8") as f:
                    f.write(css_content)
        except Exception as e:
            logger.warning(f"Could not save CSS for {model_name}: {e}")

        # Templates
        templates_map = {}
        try:
            templates = self.adapter.get_model_templates(model_name)
            for tpl_name, tpl_content in templates.items():
                qfmt = tpl_content.get("qfmt", "")
                afmt = tpl_content.get("afmt", "")
                
                # Format map để tính Hash
                templates_map[tpl_name] = {"Front": qfmt, "Back": afmt}
                
                safe_tpl_name = sanitize_filename(tpl_name).lower()
                with open(model_dir / f"{safe_tpl_name}_front.html", "w", encoding="utf-8") as f:
                    f.write(qfmt)
                with open(model_dir / f"{safe_tpl_name}_back.html", "w", encoding="utf-8") as f:
                    f.write(afmt)
        except Exception as e:
            logger.warning(f"Could not save templates for {model_name}: {e}")
            
        # Update State
        try:
            new_hash = compute_model_hash(css_content, templates_map)
            self.state_manager.update_model_hash(model_name, new_hash)
        except Exception as e:
            logger.warning(f"Failed to update hash for model {model_name}: {e}")

    def _save_model_notes(self, model_name: str, model_dir: Path) -> None:
        escaped_model_name = model_name.replace('"', '\"')
        query = f'note:"{escaped_model_name}"'
        self._save_notes_by_query(query, model_dir)

    def _save_notes_by_query(self, query: str, target_dir: Path) -> None:
        yaml = self._create_yaml_dumper()
        note_ids = self.adapter.find_notes(query)
        
        if not note_ids:
            if (target_dir / "notes.yaml").exists():
                (target_dir / "notes.yaml").unlink()
            return

        notes_info = self.adapter.get_notes_info(note_ids)
        
        all_card_ids = []
        for info in notes_info:
            cards = info.get("cards", [])
            if cards:
                all_card_ids.extend(cards)
        
        card_deck_map: Dict[int, str] = {}
        if all_card_ids:
            try:
                cards_info_list = self.adapter.get_cards_info(all_card_ids)
                for c in cards_info_list:
                    if 'cardId' in c and 'deckName' in c:
                        card_deck_map[c['cardId']] = c['deckName']
            except Exception as e:
                logger.error(f"Failed to fetch card details: {e}")

        yaml_notes = []
        for info in notes_info:
            note_id = info.get("noteId")
            note_cards = info.get("cards", [])
            deck_name = "Unknown"
            if note_cards:
                first_card_id = note_cards[0]
                deck_name = card_deck_map.get(first_card_id, "Unknown")

            processed_fields = {}
            for key, val in info.get("fields", {}).items():
                val_content = val.get("value", "")
                if "\n" in val_content or ("<" in val_content and ">" in val_content) or len(val_content) > 60:
                    processed_fields[key] = PreservedScalarString(val_content)
                else:
                    processed_fields[key] = val_content

            # Cập nhật State cho từng Note
            try:
                tags = info.get("tags", [])
                h = compute_note_hash(deck_name, tags, processed_fields)
                self.state_manager.update_note_hash(note_id, h)
            except Exception as e:
                logger.warning(f"Failed to compute hash for note {note_id}: {e}")

            note_entry = {
                "id": note_id,
                "deck": deck_name,
                "tags": tags,
                "fields": processed_fields
            }
            yaml_notes.append(note_entry)

        if yaml_notes:
            with open(target_dir / "notes.yaml", "w", encoding="utf-8") as f:
                yaml.dump(yaml_notes, f)
