import sys
from pathlib import Path
# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))
from src.adapters import AnkiConnectAdapter

def inspect():
    adapter = AnkiConnectAdapter()
    
    # Check specific ID
    note_id = 1769080833963
    info = adapter.get_notes_info([note_id])
    print(f"Info for {note_id}: {info}")
    
    # Check Deck
    deck_name = "Devanagari Alphabet"
    notes = adapter.find_notes(f'deck:"{deck_name}"')
    print(f"Notes in deck '{deck_name}': {len(notes)}")

if __name__ == "__main__":
    inspect()
