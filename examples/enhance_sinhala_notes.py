import sys
from pathlib import Path
from ruamel.yaml import YAML
from aksharamukha import transliterate
import regex as re

def syllabify_sinhala(text: str) -> list[str]:
    """
    Tách âm tiết Sinhala sử dụng Unicode Range cụ thể.
    """
    # Base chars: Nguyên âm độc lập (0D85-0D96) & Phụ âm (0D9A-0DC6)
    base = r'[\u0d85-\u0d96\u0d9a-\u0dc6]'
    # Marks: Dấu nguyên âm, Virama (0DCA-0DF3), ZWJ (\u200d), Anusvara/Visarga (0D82-0D83)
    # ZWJ: \u200d
    marks = r'(?:[\u0dca-\u0df3\u0d82-\u0d83]|\u200d)'
    
    pattern = f'{base}{marks}*'
    return re.findall(pattern, text)

def enhance_notes():
    notes_path = Path("data/anki/Vijjo/Sinhala/notes.yaml")
    
    if not notes_path.exists():
        print(f"❌ Notes file not found at: {notes_path}")
        return

    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 4096
    
    with open(notes_path, "r", encoding="utf-8") as f:
        notes = yaml.load(f) or []
        
    print(f"Scanning {len(notes)} notes in collection...")
    count = 0
    
    for note in notes:
        if "nemo_sinhala" not in note.get("tags", []):
            continue
            
        sinhala_text = note["fields"].get("Sinhala", "")
        if not sinhala_text:
            continue
            
        words = sinhala_text.split()
        seg_parts = []
        ipa_parts = []
        
        for word in words:
            # Check if Sinhala script
            if not re.search(r'\p{Script=Sinhala}', word):
                seg_parts.append(word)
                ipa_parts.append(word)
                continue

            # Transliterate whole word for better accuracy
            try:
                tr = transliterate.process('Sinhala', 'IPA', word)
                ipa_parts.append(tr)
                seg_parts.append(word)
            except Exception as e:
                print(f"Error transliterating {word}: {e}")
                ipa_parts.append(word)
                seg_parts.append(word)

        # Join with " | "
        segmented = " | ".join(seg_parts)
        ipa = " | ".join(ipa_parts)
        
        note["fields"]["Sinhala_Segmented"] = segmented
        note["fields"]["IPA"] = ipa
        count += 1
        
        if count <= 3:
            print(f"Origin: {sinhala_text}")
            print(f"Seg:    {segmented}")
            print(f"IPA:    {ipa}")
            print("-" * 20)

    with open(notes_path, "w", encoding="utf-8") as f:
        yaml.dump(notes, f)
        
    print(f"✅ Enhanced {count} notes.")

if __name__ == "__main__":
    enhance_notes()
