# Path: src/services/sync_service.py
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from ruamel.yaml import YAML

from src.core.config import settings
from src.core.state_manager import StateManager
from src.core.project_config import ProjectConfig
from src.adapters import AnkiConnectAdapter
from src.utils.hashing import compute_note_hash, compute_model_hash

logger = logging.getLogger(__name__)

class SyncService:
    def __init__(self, profile_name: str, adapter: AnkiConnectAdapter, db_path: Optional[Path] = None):
        self.profile = profile_name
        self.adapter = adapter
        
        # Determine DB path: Project-based or Legacy/Monorepo
        if db_path is None:
             db_path = settings.ANKI_DATA_DIR / profile_name / ".anki_vibe.db"
        
        self.state_manager = StateManager(db_path)
        self.console = Console()
        
        # YAML setup (để ghi lại ID)
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.indent(mapping=2, sequence=4, offset=2)
        self.yaml.width = 4096

    def push_project(self, config: ProjectConfig):
        """Push changes based on Project Config."""
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
                target_dir = config.resolve_folder(target)
                if not target_dir.exists():
                     progress.console.print(f"[yellow]Skipping {target.name}: Folder not found.[/yellow]")
                     progress.advance(main_task)
                     continue

                self._sync_target_folder(target.model, target_dir, main_task, progress, f"Target: {target.name}")
                progress.advance(main_task)
            
            self.state_manager.save_state()

    def push_all_changes(self):
        """
        Đẩy toàn bộ thay đổi từ Local lên Anki (Legacy Monorepo Mode).
        """
        profile_dir = settings.ANKI_DATA_DIR / self.profile
        if not profile_dir.exists():
            self.console.print(f"[red]No data found for profile {self.profile}[/red]")
            return

        model_dirs = [d for d in profile_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]
        self.console.print(f"Detected {len(model_dirs)} local models. Checking for changes...")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.percentage:>3.0f}%"),
            console=self.console
        ) as progress:
            main_task = progress.add_task("Syncing...", total=len(model_dirs))

            for model_dir in model_dirs:
                model_name = self._get_model_name_from_config(model_dir)
                if not model_name:
                    progress.advance(main_task)
                    continue

                self._sync_target_folder(model_name, model_dir, main_task, progress)
                progress.advance(main_task)
            
            self.state_manager.save_state()

    def _sync_target_folder(self, model_name: str, model_dir: Path, task_id, progress_obj, desc: str = None):
        """Helper to sync a single folder."""
        description = desc or f"Syncing: {model_name}"
        progress_obj.update(task_id, description=description)
        
        # 1. Sync Model Templates/CSS
        self._sync_model_structure(model_name, model_dir)
        
        # 2. Sync Notes
        self._sync_notes(model_name, model_dir)

    def _get_model_name_from_config(self, model_dir: Path) -> str:
        config_path = model_dir / "config.yaml"
        if not config_path.exists():
            return ""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = self.yaml.load(f)
                return data.get("anki_model_name", "")
        except Exception:
            return ""

    def _sync_model_structure(self, model_name: str, model_dir: Path):
        """Kiểm tra và update CSS/Templates nếu thay đổi."""
        # Đọc files
        css = ""
        templates = {}
        
        try:
            css_path = model_dir / "style.css"
            if css_path.exists():
                css = css_path.read_text(encoding="utf-8")
            
            # Đọc templates (giả sử tên file chuẩn từ pull)
            # Logic đơn giản: Scan file _front.html và _back.html
            for file in model_dir.glob("*_front.html"):
                card_name = file.name.replace("_front.html", "").replace("_", " ").title() # Tên thẻ ước lượng
                back_file = model_dir / file.name.replace("_front.html", "_back.html")
                
                if back_file.exists():
                    templates[card_name] = {
                        "Front": file.read_text(encoding="utf-8"),
                        "Back": back_file.read_text(encoding="utf-8")
                    }
        except Exception as e:
            logger.error(f"Error reading model files for {model_name}: {e}")
            return

        # Tính Hash
        new_hash = compute_model_hash(css, templates)
        old_hash = self.state_manager.get_model_hash(model_name)

        if new_hash != old_hash:
            logger.info(f"Model '{model_name}' changed. Updating Anki...")
            # Update CSS
            self.adapter.update_model_styling(model_name, css)
            
            self.state_manager.update_model_hash(model_name, new_hash)

    def _sync_notes(self, model_name: str, model_dir: Path):
        """Core logic: Batch create/update notes."""
        notes_path = model_dir / "notes.yaml"
        if not notes_path.exists():
            return

        try:
            with open(notes_path, "r", encoding="utf-8") as f:
                notes_data = self.yaml.load(f) or []
        except Exception as e:
            logger.error(f"Failed to load notes.yaml for {model_name}: {e}")
            return

        to_create = [] # List các note object để gửi API addNotes
        to_create_indices = [] # Index trong list notes_data để sau này cập nhật ID
        
        batch_actions = [] # List actions cho lệnh multi
        dirty_note_hashes = {} # Map id -> new_hash để update state sau khi thành công

        # 1. Phân loại (Filter)
        for idx, note in enumerate(notes_data):
            note_id = note.get("id")
            deck = note.get("deck", "Default")
            tags = note.get("tags", [])
            fields = note.get("fields", {})
            
            # Tính hash
            current_hash = compute_note_hash(deck, tags, fields)
            
            # Case A: Note Mới (Chưa có ID)
            if not note_id:
                # Payload cho AnkiConnect addNotes
                anki_note = {
                    "deckName": deck,
                    "modelName": model_name,
                    "fields": fields,
                    "tags": tags
                }
                to_create.append(anki_note)
                to_create_indices.append(idx)
                continue

            # Case B: Note Cũ (Có ID) -> Check Hash
            stored_hash = self.state_manager.get_note_hash(note_id)
            if current_hash != stored_hash:
                # Có thay đổi -> Thêm vào batch update
                # 1. Update Fields
                batch_actions.append(
                    self.adapter.create_update_fields_action(note_id, fields)
                )
                # 2. Update Tags
                batch_actions.append(
                    self.adapter.create_update_tags_action(note_id, tags)
                )
                
                # Lưu hash mới để update state sau
                dirty_note_hashes[note_id] = current_hash

        # 2. Thực thi CREATE (Bulk Add)
        if to_create:
            logger.info(f"Creating {len(to_create)} new notes for {model_name}...")
            try:
                new_ids = self.adapter.add_notes(to_create)
                
                # Gán ID mới ngược lại vào notes_data
                for i, new_id in enumerate(new_ids):
                    if new_id:
                        original_idx = to_create_indices[i]
                        notes_data[original_idx]["id"] = new_id
                        
                        # Update Hash cho note mới
                        note_obj = to_create[i]
                        h = compute_note_hash(note_obj["deckName"], note_obj["tags"], note_obj["fields"])
                        self.state_manager.update_note_hash(new_id, h)
            except Exception as e:
                logger.error(f"Failed to add notes: {e}")

        # 3. Thực thi UPDATE (Batch Multi)
        if batch_actions:
            logger.info(f"Updating {len(dirty_note_hashes)} changed notes for {model_name}...")
            try:
                # Chia nhỏ batch nếu quá lớn
                chunk_size = 500
                for i in range(0, len(batch_actions), chunk_size):
                    chunk = batch_actions[i:i+chunk_size]
                    self.adapter.multi(chunk)
                
                # Nếu không lỗi, update state hash
                for nid, h in dirty_note_hashes.items():
                    self.state_manager.update_note_hash(nid, h)
                    
            except Exception as e:
                logger.error(f"Failed to batch update notes: {e}")

        # 4. Lưu lại ID mới vào file YAML (Nếu có create)
        if to_create:
            with open(notes_path, "w", encoding="utf-8") as f:
                self.yaml.dump(notes_data, f)
