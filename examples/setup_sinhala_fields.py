import sys
from pathlib import Path
# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))
from src.adapters import AnkiConnectAdapter

def setup():
    adapter = AnkiConnectAdapter()
    model = "Sinhala"
    new_fields = ["Syllable_Segmented", "Transliteration"]
    
    try:
        current_fields = adapter.get_model_field_names(model)
        print(f"Current fields: {current_fields}")
    except Exception as e:
        print(f"❌ Could not get model fields: {e}")
        return
    
    for f in new_fields:
        if f not in current_fields:
            try:
                adapter.add_model_field(model, f)
                print(f"✅ Added field: {f}")
            except Exception as e:
                print(f"❌ Failed to add {f}: {e}")
        else:
            print(f"ℹ️  Field {f} already exists.")

if __name__ == "__main__":
    setup()
