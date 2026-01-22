import sys
import regex as re
from pathlib import Path
from ruamel.yaml import YAML
from aksharamukha import transliterate

def syllabify_sinhala(text: str) -> list[str]:
    """
    Tách âm tiết Sinhala (Syllabification).
    """
    base = r'[\u0d85-\u0d96\u0d9a-\u0dc6]'
    marks = r'(?:[\u0dca-\u0df3\u0d82-\u0d83]|\u200d)'
    pattern = f'{base}{marks}*'
    return re.findall(pattern, text)

def generate():
    notes_path = Path("data/anki/Vijjo/Sinhala/notes.yaml")
    
    if not notes_path.exists():
        print(f"❌ Notes file not found at: {notes_path}")
        return

    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 4096
    
    with open(notes_path, "r", encoding="utf-8") as f:
        notes = yaml.load(f) or []
        
    print(f"Processing {len(notes)} notes...")
    
    for note in notes:
        sinhala = note["fields"].get("Sinhala", "")
        if not sinhala:
            continue
            
        words = sinhala.split()
        syl_parts = []
        trans_parts = []
        
        for word in words:
            if not re.search(r'\p{Script=Sinhala}', word):
                syl_parts.append(word)
                trans_parts.append(word)
                continue
                
            syllables = syllabify_sinhala(word)
            
            # Transliterate to ISO
            tr_syllables = []
            for s in syllables:
                try:
                    tr = transliterate.process('Sinhala', 'ISO', s)
                    tr_syllables.append(tr)
                except:
                    tr_syllables.append(s)
            
            if syllables:
                # Format: | s1 | s2 |
                syl_word = "| " + " | ".join(syllables) + " |"
                tr_word = "| " + " | ".join(tr_syllables) + " |"
                
                syl_parts.append(syl_word)
                trans_parts.append(tr_word)
            else:
                syl_parts.append(word)
                trans_parts.append(word)
                
        note["fields"]["Syllable_Segmented"] = " ".join(syl_parts)
        note["fields"]["Transliteration"] = " ".join(trans_parts)

    with open(notes_path, "w", encoding="utf-8") as f:
        yaml.dump(notes, f)
        
    print("✅ Transliteration generated.")

if __name__ == "__main__":
    generate()
