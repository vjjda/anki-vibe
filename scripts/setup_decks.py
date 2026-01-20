import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.adapters import AnkiConnectAdapter

def create_decks():
    adapter = AnkiConnectAdapter()
    decks = ["AnkiVibe::TestDeck", "AnkiVibe::TestDeck::SubDeck"]
    
    for deck in decks:
        try:
            adapter.create_deck(deck)
            print(f"✅ Created deck: {deck}")
        except Exception as e:
            print(f"❌ Failed to create deck {deck}: {e}")

if __name__ == "__main__":
    create_decks()