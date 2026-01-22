import sys
from pathlib import Path
# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))
from src.adapters import AnkiConnectAdapter

def add_fields():
    adapter = AnkiConnectAdapter()
    model = "Devanagari_Master"
    new_fields = ["Example_IPAs", "Example_Meanings"]
    
    try:
        current = adapter.get_model_field_names(model)
        print(f"Current fields: {current}")
    except Exception as e:
        print(f"❌ Model not found: {e}")
        return

    for f in new_fields:
        if f not in current:
            try:
                adapter.add_model_field(model, f)
                print(f"✅ Added {f}")
            except Exception as e:
                print(f"❌ Error {f}: {e}")
        else:
            print(f"ℹ️  {f} exists")

if __name__ == "__main__":
    add_fields()
