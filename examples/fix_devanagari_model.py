import sys
from pathlib import Path
# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))
from src.adapters import AnkiConnectAdapter

def fix_model():
    adapter = AnkiConnectAdapter()
    model_name = "Devanagari_Master"
    
    target_fields = [
        "Character", "Name", "IPA", "Category", "Description", 
        "Image_Stroke_1", "Image_Stroke_2", "Image_Static", "Examples", "Example_Audio_Source"
    ]
    
    try:
        current_fields = adapter.get_model_field_names(model_name)
        print(f"Current fields: {current_fields}")
    except Exception as e:
        print(f"❌ Model not found or error: {e}")
        return

    for f in target_fields:
        if f not in current_fields:
            try:
                adapter.add_model_field(model_name, f)
                print(f"✅ Added field: {f}")
            except Exception as e:
                print(f"❌ Failed to add field {f}: {e}")
        else:
            print(f"ℹ️  Field {f} exists.")

if __name__ == "__main__":
    fix_model()
