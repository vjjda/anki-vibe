# Path: src/services/pull_service.py
import logging
from pathlib import Path
from typing import List, Dict, Any
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import PreservedScalarString

from src.core.config import settings
from src.adapters import AnkiConnectAdapter
from src.utils.text_utils import sanitize_filename

logger = logging.getLogger(__name__)

class PullService:
    def __init__(self, profile_name: str, adapter: AnkiConnectAdapter):
        self.profile = profile_name
        self.adapter = adapter
        self.console = Console()
        
        # Setup YAML
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.indent(mapping=2, sequence=4, offset=2)
        self.yaml.width = 4096 

    def pull_all_models(self):
        """Pull toàn bộ Models và Notes của Profile về máy."""
        try:
            model_names = self.adapter.get_model_names()
        except Exception as e:
            self.console.print(f"[red]Failed to fetch model names: {e}[/red]")
            return

        base_dir = settings.DATA_DIR / self.profile
        base_dir.mkdir(parents=True, exist_ok=True)
        
        self.console.print(f"Found [bold]{len(model_names)}[/bold] models in profile [green]{self.profile}[/green].")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.percentage:>3.0f}%"),
        ) as progress:
            main_task = progress.add_task("[cyan]Syncing Models...", total=len(model_names))
            
            for model_name in model_names:
                progress.update(main_task, description=f"Processing: {model_name}")
                self._process_single_model(model_name, base_dir)
                progress.advance(main_task)

    def _process_single_model(self, model_name: str, base_dir: Path):
        safe_name = sanitize_filename(model_name)
        model_dir = base_dir / safe_name
        model_dir.mkdir(exist_ok=True)

        # A. Metadata
        self._save_model_metadata(model_name, model_dir)
        
        # B. Notes (Updated Logic)
        self._save_model_notes(model_name, model_dir)

    def _save_model_metadata(self, model_name: str, model_dir: Path):
        # ... (Giữ nguyên logic lưu config, css, template như cũ) ...
        # Để tiết kiệm không gian hiển thị, tôi không paste lại đoạn này 
        # vì nó không thay đổi so với phiên bản trước.
        # Bạn giữ nguyên hàm này nhé.
        
        # 1. Config
        config_data = {
            "anki_model_name": model_name,
            "description": f"Auto-generated config for model '{model_name}'"
        }
        with open(model_dir / "config.yaml", "w", encoding="utf-8") as f:
            self.yaml.dump(config_data, f)

        # 2. CSS
        try:
            styling = self.adapter.get_model_styling(model_name)
            with open(model_dir / "style.css", "w", encoding="utf-8") as f:
                f.write(styling.get("css", ""))
        except Exception:
            pass # Ignore error

        # 3. Templates
        try:
            templates = self.adapter.get_model_templates(model_name)
            for name, tpl in templates.items():
                safe_tpl_name = sanitize_filename(name).lower()
                with open(model_dir / f"{safe_tpl_name}_front.html", "w", encoding="utf-8") as f:
                    f.write(tpl.get("qfmt", ""))
                with open(model_dir / f"{safe_tpl_name}_back.html", "w", encoding="utf-8") as f:
                    f.write(tpl.get("afmt", ""))
        except Exception:
            pass

    def _save_model_notes(self, model_name: str, model_dir: Path):
        try:
            # 1. Tìm Note IDs
            note_ids = self.adapter.find_notes(f'note:"{model_name}"')
            if not note_ids:
                return

            # 2. Fetch Note Details
            notes_info = self.adapter.get_notes_info(note_ids)
            
            # --- NEW LOGIC: FETCH DECK NAME VIA CARDS ---
            # Gom tất cả Card IDs từ tất cả các notes
            all_card_ids = []
            for info in notes_info:
                cards = info.get("cards", [])
                if cards:
                    all_card_ids.extend(cards)
            
            # Gọi API cardsInfo (Batch processing)
            # Map: CardID -> DeckName
            card_deck_map = {}
            if all_card_ids:
                # Nếu số lượng quá lớn (>1000), AnkiConnect vẫn xử lý ổn, 
                # nhưng an toàn có thể chia chunk. Ở đây làm đơn giản trước.
                cards_info_list = self.adapter.get_cards_info(all_card_ids)
                for c in cards_info_list:
                    card_deck_map[c['cardId']] = c['deckName']
            # ---------------------------------------------

            yaml_notes = []
            for info in notes_info:
                # Resolve Deck Name
                # Lấy card đầu tiên của note để xác định deck
                note_cards = info.get("cards", [])
                deck_name = "Unknown"
                if note_cards:
                    first_card_id = note_cards[0]
                    deck_name = card_deck_map.get(first_card_id, "Unknown")

                # Process Fields
                processed_fields = {}
                for key, val in info.get("fields", {}).items():
                    val_content = val.get("value", "")
                    # Logic: Nếu có xuống dòng hoặc tag HTML phức tạp -> Block Style
                    if "\n" in val_content or ("<" in val_content and ">" in val_content):
                        processed_fields[key] = PreservedScalarString(val_content)
                    else:
                        processed_fields[key] = val_content

                note_entry = {
                    "id": info.get("noteId"),
                    "deck": deck_name, # ✅ Giờ đã có tên Deck chính xác
                    "tags": info.get("tags", []),
                    "fields": processed_fields
                }
                
                yaml_notes.append(note_entry)

            # 4. Save to notes.yaml
            with open(model_dir / "notes.yaml", "w", encoding="utf-8") as f:
                self.yaml.dump(yaml_notes, f)

        except Exception as e:
            logger.error(f"Error fetching notes for {model_name}: {e}")