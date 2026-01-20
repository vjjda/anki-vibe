# Path: src/services/pull_service.py
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskID
)

# Sử dụng ruamel.yaml để giữ format và comment
from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import PreservedScalarString

from src.core.config import settings
from src.adapters import AnkiConnectAdapter
from src.utils.text_utils import sanitize_filename

# Khởi tạo Logger
logger = logging.getLogger(__name__)

# Số lượng luồng tối đa.
MAX_WORKERS = 5 

class PullService:
    """
    Service chịu trách nhiệm kéo dữ liệu từ Anki về lưu trữ local.
    Hỗ trợ Multithreading để tăng tốc độ xử lý I/O và Network.
    """

    def __init__(self, profile_name: str, adapter: AnkiConnectAdapter):
        self.profile = profile_name
        self.adapter = adapter
        self.console = Console()
        # Lưu ý: Không khởi tạo self.yaml ở đây nữa vì nó không thread-safe.

    def _create_yaml_dumper(self) -> YAML:
        """
        Tạo một instance YAML mới cho mỗi luồng xử lý.
        Điều này bắt buộc để tránh lỗi 'I/O operation on closed file' khi chạy multithread.
        """
        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.indent(mapping=2, sequence=4, offset=2)
        yaml.width = 4096
        return yaml

    def pull_all_models(self) -> None:
        """
        Main entry point: Pull toàn bộ Models và Notes sử dụng Multithreading.
        """
        # 1. Lấy danh sách Models (Thực hiện tuần tự vì rất nhanh)
        try:
            model_names = self.adapter.get_model_names()
        except Exception as e:
            logger.error(f"Failed to fetch model names: {e}")
            self.console.print(f"[bold red]❌ Failed to fetch model names:[/bold red] {e}")
            return

        # Tạo thư mục gốc
        base_dir = settings.DATA_DIR / self.profile
        base_dir.mkdir(parents=True, exist_ok=True)
        
        total_models = len(model_names)
        self.console.print(f"Found [bold cyan]{total_models}[/bold cyan] models. Starting sync with {MAX_WORKERS} threads...")

        # 2. Setup Progress Bar và ThreadPool
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
                # Submit tất cả các task vào pool
                future_to_model = {
                    executor.submit(self._process_single_model, model_name, base_dir): model_name 
                    for model_name in model_names
                }
                
                # Xử lý khi các task hoàn thành (as_completed)
                for future in as_completed(future_to_model):
                    model_name = future_to_model[future]
                    try:
                        future.result() # Check exception
                        # Update UI (Optional: chỉ update text, progress bar tự advance)
                    except Exception as e:
                        progress.console.print(f"[red]Failed to process {model_name}: {e}[/red]")
                        logger.error(f"Error in thread for model {model_name}", exc_info=True)
                    finally:
                        progress.advance(main_task)

    def _process_single_model(self, model_name: str, base_dir: Path) -> None:
        """
        Xử lý logic cho 1 Model cụ thể.
        Hàm này sẽ chạy trong một Thread riêng biệt.
        """
        try:
            # Tạo tên thư mục
            safe_name = sanitize_filename(model_name)
            model_dir = base_dir / safe_name
            model_dir.mkdir(exist_ok=True)

            # A. Metadata (Config, CSS, Templates)
            self._save_model_metadata(model_name, model_dir)
            
            # B. Data (Notes)
            self._save_model_notes(model_name, model_dir)
            
        except Exception as e:
            raise e

    def _save_model_metadata(self, model_name: str, model_dir: Path) -> None:
        """Lưu config, css, template."""
        
        # Tạo instance YAML cục bộ cho luồng này
        yaml = self._create_yaml_dumper()

        # 1. Config
        config_data = {
            "anki_model_name": model_name,
            "description": f"Auto-generated config for model '{model_name}'"
        }
        with open(model_dir / "config.yaml", "w", encoding="utf-8") as f:
            yaml.dump(config_data, f)

        # 2. CSS
        try:
            styling = self.adapter.get_model_styling(model_name)
            css_content = styling.get("css", "")
            if css_content:
                with open(model_dir / "style.css", "w", encoding="utf-8") as f:
                    f.write(css_content)
        except Exception as e:
            logger.warning(f"Could not save CSS for {model_name}: {e}")

        # 3. Templates
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
        """Fetch và lưu Notes."""
        
        # Tạo instance YAML cục bộ cho luồng này
        yaml = self._create_yaml_dumper()

        # 1. Tìm Note IDs
        escaped_model_name = model_name.replace('"', '\\"')
        note_ids = self.adapter.find_notes(f'note:"{escaped_model_name}"')
        
        if not note_ids:
            return

        # 2. Fetch Note Info (Batch)
        notes_info = self.adapter.get_notes_info(note_ids)
        
        # 3. Resolve Deck Names (Batch Processing Logic)
        all_card_ids = []
        for info in notes_info:
            cards = info.get("cards", [])
            if cards:
                all_card_ids.extend(cards)
        
        card_deck_map: Dict[int, str] = {}
        if all_card_ids:
            try:
                # Gọi API cardsInfo
                cards_info_list = self.adapter.get_cards_info(all_card_ids)
                for c in cards_info_list:
                    if 'cardId' in c and 'deckName' in c:
                        card_deck_map[c['cardId']] = c['deckName']
            except Exception as e:
                logger.error(f"Failed to fetch card details: {e}")

        # 4. Build YAML structure
        yaml_notes = []
        for info in notes_info:
            # Resolve Deck
            note_cards = info.get("cards", [])
            deck_name = "Unknown"
            if note_cards:
                first_card_id = note_cards[0]
                deck_name = card_deck_map.get(first_card_id, "Unknown")

            # Process Fields
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

        # 5. Write to Disk
        if yaml_notes:
            with open(model_dir / "notes.yaml", "w", encoding="utf-8") as f:
                yaml.dump(yaml_notes, f)