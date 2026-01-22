import sys
import requests
from pathlib import Path
from ruamel.yaml import YAML
from bs4 import BeautifulSoup

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))
from src.adapters import AnkiConnectAdapter

def scrape_and_generate():
    # 1. Setup Deck
    adapter = AnkiConnectAdapter()
    deck_name = "Nemo Sinhala"
    try:
        adapter.create_deck(deck_name)
        print(f"✅ Deck setup: {deck_name}")
    except Exception as e:
        print(f"ℹ️  Deck setup info: {e}")

    # 2. Fetch Data
    url = "http://www.nemolanguageapps.com/phrasebooks/sinhala"
    print(f"🌍 Fetching {url}...")
    try:
        response = requests.get(url)
        response.raise_for_status()
    except Exception as e:
        print(f"❌ Failed to fetch: {e}")
        return

    soup = BeautifulSoup(response.content, "html.parser")
    target1_list = soup.find_all(class_="target1")
    translation_list = soup.find_all(class_="translation")
    target2_list = soup.find_all(class_="target2")
    audio_sources = soup.select('source[src$=".mp3"]')
    
    count = min(len(target1_list), len(translation_list), len(target2_list))
    print(f"✨ Found {count} phrases.")

    notes = []
    print("🚀 Processing and Mapping to 'Sinhala' Model...")
    
    for i in range(count):
        # Extract
        sinhala_text = target1_list[i].get_text(strip=True)
        english_text = translation_list[i].get_text(strip=True)
        ipa_text = target2_list[i].get_text(strip=True)
        
        # Audio
        audio_field = ""
        if i < len(audio_sources):
            audio_url_rel = audio_sources[i]['src']
            audio_url = f"http://www.nemolanguageapps.com{audio_url_rel}" if audio_url_rel.startswith("/") else audio_url_rel
            audio_filename = audio_url.split("/")[-1]
            
            try:
                adapter.store_media_file(filename=audio_filename, url=audio_url)
                audio_field = f"[sound:{audio_filename}]"
            except Exception as e:
                print(f"  ⚠️ Audio error: {e}")

        # Map to 'Sinhala' Model Fields
        # Fields: ['English', 'Sinhala', 'A_Sinhala_Male', 'A_Sinhala_Female', 'A_English', 'IPA', 'Sinhala_Segmented']
        fields = {
            "English": english_text,
            "Sinhala": sinhala_text,
            "A_Sinhala_Male": audio_field,
            "A_Sinhala_Female": "",
            "A_English": "",
            "IPA": ipa_text,
            "Sinhala_Segmented": ""
        }

        notes.append({
            "id": None, # New Note
            "deck": deck_name,
            "tags": ["nemo_sinhala", "direct_import"],
            "fields": fields
        })

    # 3. Save to Project Data
    output_dir = Path("nemo_sinhala/data")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 4096
    
    with open(output_dir / "notes.yaml", "w", encoding="utf-8") as f:
        yaml.dump(notes, f)
        
    print(f"✅ Generated {len(notes)} notes in {output_dir}/notes.yaml")

if __name__ == "__main__":
    scrape_and_generate()
