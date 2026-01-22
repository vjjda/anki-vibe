import sys
import requests
from pathlib import Path
from ruamel.yaml import YAML
from bs4 import BeautifulSoup

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))
from src.adapters import AnkiConnectAdapter

def scrape():
    url = "http://www.nemolanguageapps.com/phrasebooks/sinhala"
    print(f"🌍 Fetching {url}...")
    
    try:
        response = requests.get(url)
        response.raise_for_status()
    except Exception as e:
        print(f"❌ Failed to fetch page: {e}")
        return

    print("🔍 Parsing HTML with BeautifulSoup...")
    soup = BeautifulSoup(response.content, "html.parser")
    
    # Tìm tất cả các container chứa phrase. 
    # Dựa trên snippet, các element này thường nằm trong <li> hoặc <div>
    # Cách an toàn nhất là tìm list các target1, translation, audio và zip chúng lại
    # nếu chúng xuất hiện theo thứ tự tương ứng.
    
    target1_list = soup.find_all(class_="target1")
    translation_list = soup.find_all(class_="translation")
    target2_list = soup.find_all(class_="target2")
    
    # Audio thường nằm trong thẻ audio/source ngay cạnh
    # Ta sẽ tìm tất cả source có src đuôi mp3
    # Lưu ý: Có thể có nhiều source (mp3, ogg), ta chỉ lấy mp3
    audio_sources = soup.select('source[src$=".mp3"]')
    
    # Kiểm tra số lượng
    count = min(len(target1_list), len(translation_list), len(target2_list))
    print(f"✨ Found {count} phrases.")
    
    if count == 0:
        print("⚠️ No phrases found. Check CSS selectors.")
        return

    adapter = AnkiConnectAdapter()
    notes = []
    
    print("🚀 Processing phrases...")
    
    for i in range(count):
        # Extract Text
        sinhala = target1_list[i].get_text(strip=True)
        english = translation_list[i].get_text(strip=True)
        ipa = target2_list[i].get_text(strip=True)
        
        # Audio
        # Cần đảm bảo audio map đúng index. 
        # Nếu trang web cấu trúc phẳng, audio_sources[i] có thể đúng.
        # Nếu không, cần traverse từ target1 lên parent rồi tìm audio.
        
        audio_field = ""
        if i < len(audio_sources):
            audio_url_rel = audio_sources[i]['src']
            if audio_url_rel.startswith("/"):
                audio_url = f"http://www.nemolanguageapps.com{audio_url_rel}"
            else:
                audio_url = audio_url_rel
                
            audio_filename = audio_url.split("/")[-1]
            
            try:
                # Upload
                adapter.store_media_file(filename=audio_filename, url=audio_url)
                audio_field = f"[sound:{audio_filename}]"
                if i % 10 == 0: # Log bớt
                    print(f"  [{i+1}/{count}] Processed: {english}")
            except Exception as e:
                print(f"  ⚠️ Audio error for {audio_filename}: {e}")

        # Create Note
        notes.append({
            "id": None,
            "deck": "Nemo Sinhala",
            "tags": ["nemo_sinhala"],
            "fields": {
                "Sinhala": sinhala,
                "English": english,
                "Audio": audio_field,
                "IPA": ipa
            }
        })

    # Save
    output_dir = Path("nemo_project/data")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 4096
    
    with open(output_dir / "notes.yaml", "w", encoding="utf-8") as f:
        yaml.dump(notes, f)
        
    print(f"✅ Successfully generated {len(notes)} notes in {output_dir}/notes.yaml")

if __name__ == "__main__":
    scrape()
