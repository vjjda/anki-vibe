# Path: src/services/pull_service.py
import logging
import shutil # Import thêm shutil để xóa folder
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed

from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskID
)

# Sử dụng ruamel.yaml
from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import PreservedScalarString

from src.core.config import settings
from src.adapters import AnkiConnectAdapter
from src.utils.text_utils import sanitize_filename

logger = logging.getLogger(__name__)

MAX_WORKERS = 5 

class PullService:
    """
    Service chịu trách nhiệm kéo dữ liệu từ Anki về lưu trữ local.
    Hỗ trợ Multithreading và Cleanup dữ liệu cũ.
    """

    def __init__(self, profile_name: str, adapter: AnkiConnectAdapter):
        self.profile = profile_name
        self.adapter = adapter
        self.console = Console()

    def _create_yaml_dumper(self) -> YAML:
        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.indent(mapping=2, sequence=4, offset=2)
        yaml.width = 4096
        return yaml

    def pull_all_models(self) -> None:
        """
        Main entry point: Pull toàn bộ Models và dọn dẹp các Model đã bị xóa trên Anki.
        """
        # 1. Fetch Model Names
        try:
            model_names = self.adapter.get_model_names()
        except Exception as e:
            logger.error(f"Failed to fetch model names: {e}")
            self.console.print(f"[bold red]❌ Failed to fetch model names:[/bold red] {e}")
            return

        base_dir = settings.ANKI_DATA_DIR / self.profile
        base_dir.mkdir(parents=True, exist_ok=True)
        
        # Danh sách các folder hợp lệ (Active) để dùng cho việc Cleanup sau này
        active_folder_names: Set[str] = set()

        total_models = len(model_names)
        self.console.print(f"Found [bold cyan]{total_models}[/bold cyan] models. Starting sync...")

        # 2. Sync Loop
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
                    # Lưu lại tên folder dự kiến sẽ tạo
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

        # 3. Cleanup Step (Dọn dẹp rác)
        self._cleanup_stale_models(base_dir, active_folder_names)

    def _cleanup_stale_models(self, base_dir: Path, active_folder_names: Set[str]) -> None:
        """
        Xóa các folder trong local không còn tồn tại trên Anki.
        """
        self.console.print("\n[dim]🔍 Checking for stale data...[/dim]")
        
        # Lấy danh sách tất cả folder hiện có trong data/Profile
        # Chỉ lấy folder, bỏ qua file
        existing_folders = {item.name for item in base_dir.iterdir() if item.is_dir()}
        
        # Tính toán folder thừa: Có trong Local nhưng không có trong Active List
        stale_folders = existing_folders - active_folder_names
        
        # Loại trừ các folder đặc biệt (ví dụ _archive, .git nếu có lọt vào)
        stale_folders = {f for f in stale_folders if not f.startswith(("_", "."))}

        if not stale_folders:
            self.console.print("[green]✨ Clean workspace. No stale files found.[/green]")
            return

        self.console.print(f"[yellow]⚠️  Found {len(stale_folders)} stale model folders (deleted on Anki):[/yellow]")
        for folder in stale_folders:
            self.console.print(f"  - {folder}")

        # Xóa (Tự động hoặc hỏi - ở đây tôi để tự động xóa để đúng nghĩa Sync)
        # Nếu muốn an toàn hơn, bạn có thể move vào folder `_trash` thay vì `rmtree`.
        for folder_name in stale_folders:
            folder_path = base_dir / folder_name
            try:
                shutil.rmtree(folder_path) # Xóa vĩnh viễn folder
                logger.info(f"Deleted stale folder: {folder_path}")
                self.console.print(f"  [red]🗑️  Deleted:[/red] {folder_name}")
            except Exception as e:
                logger.error(f"Failed to delete {folder_path}: {e}")
                self.console.print(f"  [red]❌ Failed to delete {folder_name}: {e}[/red]")

    def _process_single_model(self, model_name: str, base_dir: Path) -> None:
        try:
            safe_name = sanitize_filename(model_name)
            model_dir = base_dir / safe_name
            model_dir.mkdir(exist_ok=True)

            self._save_model_metadata(model_name, model_dir)
            self._save_model_notes(model_name, model_dir)
            
        except Exception as e:
            raise e

    def _save_model_metadata(self, model_name: str, model_dir: Path) -> None:
        yaml = self._create_yaml_dumper()

        config_data = {
            "anki_model_name": model_name,
            "description": f"Auto-generated config for model '{model_name}'"
        }
        with open(model_dir / "config.yaml", "w", encoding="utf-8") as f:
            yaml.dump(config_data, f)

        try:
            styling = self.adapter.get_model_styling(model_name)
            css_content = styling.get("css", "")
            if css_content:
                with open(model_dir / "style.css", "w", encoding="utf-8") as f:
                    f.write(css_content)
        except Exception as e:
            logger.warning(f"Could not save CSS for {model_name}: {e}")

        try:
            templates = self.adapter.get_model_templates(model_name)
            for tpl_name, tpl_content in templates.items():
                safe_tpl_name = sanitize_filename(tpl_name).lower()
                with open(model_dir / f"{safe_tpl_name}_front.html", "w", encoding="utf-8") as f:
                    f.write(tpl_content.get("qfmt", ""))
                with open(model_dir / f"{safe_tpl_name}_back.html", "w", encoding="utf-8") as f:
                    f.write(tpl_content.get("afmt", ""))
        except Exception as e:
            logger.warning(f"Could not save templates for {model_name}: {e}")

    def _save_model_notes(self, model_name: str, model_dir: Path) -> None:
        yaml = self._create_yaml_dumper()

        escaped_model_name = model_name.replace('"', '\\"')
        note_ids = self.adapter.find_notes(f'note:"{escaped_model_name}"')
        
        if not note_ids:
            # Nếu model không có note nào, ta vẫn để folder nhưng có thể xóa file notes.yaml cũ nếu có
            if (model_dir / "notes.yaml").exists():
                (model_dir / "notes.yaml").unlink()
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

            note_entry = {
                "id": info.get("noteId"),
                "deck": deck_name,
                "tags": info.get("tags", []),
                "fields": processed_fields
            }
            yaml_notes.append(note_entry)

        if yaml_notes:
            with open(model_dir / "notes.yaml", "w", encoding="utf-8") as f:
                yaml.dump(yaml_notes, f)