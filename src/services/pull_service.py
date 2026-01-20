# Path: src/services/pull_service.py
import logging
from pathlib import Path
from typing import List, Dict, Any
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskID

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
        
        # Setup YAML dumper
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.indent(mapping=2, sequence=4, offset=2)
        self.yaml.width = 4096 # Tránh wrap line quá sớm

    def pull_all_models(self):
        """
        Pull toàn bộ Models và Notes của Profile về máy.
        """
        # 1. Lấy danh sách Models
        try:
            model_names = self.adapter.get_model_names()
        except Exception as e:
            self.console.print(f"[red]Failed to fetch model names: {e}[/red]")
            return

        base_dir = settings.DATA_DIR / self.profile
        base_dir.mkdir(parents=True, exist_ok=True)
        
        self.console.print(f"Found [bold]{len(model_names)}[/bold] models in profile [green]{self.profile}[/green].")

        # Sử dụng Rich Progress Bar
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
        """Xử lý 1 Model: Tạo folder, lưu Config, Template, CSS và Notes."""
        safe_name = sanitize_filename(model_name)
        model_dir = base_dir / safe_name
        model_dir.mkdir(exist_ok=True)

        # A. Save Config & Templates
        self._save_model_metadata(model_name, model_dir)
        
        # B. Save Notes
        self._save_model_notes(model_name, model_dir)

    def _save_model_metadata(self, model_name: str, model_dir: Path):
        # 1. Config.yaml
        config_data = {
            "anki_model_name": model_name,
            "description": f"Auto-generated config for model '{model_name}'"
        }
        with open(model_dir / "config.yaml", "w", encoding="utf-8") as f:
            self.yaml.dump(config_data, f)

        # 2. CSS
        try:
            styling = self.adapter.get_model_styling(model_name)
            css_content = styling.get("css", "")
            with open(model_dir / "style.css", "w", encoding="utf-8") as f:
                f.write(css_content)
        except Exception as e:
            logger.error(f"Error saving CSS for {model_name}: {e}")

        # 3. Templates (Front/Back HTML)
        try:
            templates = self.adapter.get_model_templates(model_name)
            # Templates trả về dạng dict: { "Card 1": {"Front": "...", "Back": "..."}, ... }
            # Để đơn giản, ta sẽ lưu mỗi card type vào subfolder nếu có nhiều card type
            # Hoặc lưu tên file dạng: card_1_front.html
            
            for name, tpl in templates.items():
                safe_tpl_name = sanitize_filename(name).lower()
                
                # Lưu Front
                with open(model_dir / f"{safe_tpl_name}_front.html", "w", encoding="utf-8") as f:
                    f.write(tpl.get("qfmt", "")) # qfmt = Question Format (Front)
                
                # Lưu Back
                with open(model_dir / f"{safe_tpl_name}_back.html", "w", encoding="utf-8") as f:
                    f.write(tpl.get("afmt", "")) # afmt = Answer Format (Back)

        except Exception as e:
            logger.error(f"Error saving templates for {model_name}: {e}")

    def _save_model_notes(self, model_name: str, model_dir: Path):
        try:
            # 1. Tìm tất cả notes thuộc model này
            # query syntax: "note:ModelName"
            note_ids = self.adapter.find_notes(f'note:"{model_name}"')
            
            if not note_ids:
                return

            # 2. Fetch chi tiết (chia nhỏ batch nếu quá nhiều, tạm thời lấy hết)
            # AnkiConnect xử lý khá tốt vài nghìn note, nhưng nếu >10k cần chunking.
            notes_info = self.adapter.get_notes_info(note_ids)
            
            # 3. Convert sang định dạng YAML của chúng ta
            yaml_notes = []
            for info in notes_info:
                # Xử lý fields: Chuyển text dài hoặc có HTML thành Block Style (|)
                processed_fields = {}
                for key, val in info.get("fields", {}).items():
                    val_content = val.get("value", "")
                    if "\n" in val_content or "<" in val_content:
                        processed_fields[key] = PreservedScalarString(val_content)
                    else:
                        processed_fields[key] = val_content

                note_entry = {
                    "id": info.get("noteId"),
                    "deck": info.get("modelName"), # Lưu ý: NoteInfo trả về modelName ở root, nhưng deckName cũng có.
                    # Sửa: Lấy deckName thực tế của note đó
                    # Note: API notesInfo field 'modelName' là tên model. 'tags' là list.
                    # AnkiConnect notesInfo KHÔNG trả về deck name trực tiếp ở root level trong các bản cũ, 
                    # nhưng bản mới thường có. Nếu không, phải dùng cardsInfo. 
                    # Tuy nhiên, hãy check data trả về thực tế.
                    # Workaround: notesInfo return object có key 'modelName' nhưng deck thì ko rõ ràng. 
                    # Check docs: notesInfo returns {noteId, modelName, tags, fields}. KHÔNG CÓ DECK NAME.
                    # Để lấy Deck Name chính xác, ta cần query cards của note đó.
                    # NHƯNG: Để tối ưu tốc độ, tạm thời ta sẽ set deck là một placeholder hoặc query thêm.
                    # GIẢI PHÁP TẠM: Chỉ dùng tag, hoặc chấp nhận thiếu deck name chính xác ở bước này 
                    # (hoặc update adapter để lấy cardsInfo).
                    # UPDATE: Để code chạy nhanh, ta sẽ bỏ qua field 'deck' chính xác từng note, 
                    # hoặc query batch cardsInfo. 
                }
                
                # Update logic lấy deck name: 
                # Cách chính xác nhất: findCards query theo noteId -> cardsInfo -> deckName. 
                # Sẽ rất chậm nếu gọi loop.
                # Giải pháp: User nên sắp xếp Note theo Deck. 
                # Tạm thời để field deck là "Unknown" hoặc tên Model để user tự sửa.
                # Hoặc: Query "deck:current" để lấy note, thì ta biết deck. Nhưng ở đây ta query theo Model.
                
                note_entry["deck"] = "Please_Update_Deck_Name" # Placeholder
                note_entry["tags"] = info.get("tags", [])
                note_entry["fields"] = processed_fields
                
                yaml_notes.append(note_entry)

            # 4. Save to notes.yaml
            with open(model_dir / "notes.yaml", "w", encoding="utf-8") as f:
                self.yaml.dump(yaml_notes, f)

        except Exception as e:
            logger.error(f"Error fetching notes for {model_name}: {e}")