import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from src.adapters import AnkiConnectAdapter

def test_add():
    adapter = AnkiConnectAdapter()
    deck_name = "Devanagari Alphabet"
    model_name = "Devanagari_Master"
    
    note = {
        "deckName": deck_name,
        "modelName": model_name,
        "fields": {
            "Character": "TestChar",
            "Name": "TestName"
        },
        "tags": ["test_manual"]
    }
    
    try:
        res = adapter.add_notes([note])
        print(f"Result: {res}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_add()
