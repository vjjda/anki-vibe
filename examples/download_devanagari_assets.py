import requests
import os
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

def get_category_members(category_name):
    """Lấy danh sách tên file trong Category."""
    print(f"📡 Listing {category_name}...")
    url = "https://commons.wikimedia.org/w/api.php"
    members = []
    cmcontinue = None
    
    while True:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": category_name,
            "cmlimit": "500",
            "format": "json"
        }
        if cmcontinue:
            params["cmcontinue"] = cmcontinue
            
        headers = {"User-Agent": "AnkiVibeBot/1.0"}
        try:
            res = requests.get(url, params=params, headers=headers).json()
            batch = res.get("query", {}).get("categorymembers", [])
            members.extend([m["title"] for m in batch])
            
            if "continue" in res:
                cmcontinue = res["continue"]["cmcontinue"]
            else:
                break
        except Exception as e:
            print(f"❌ Failed to list category: {e}")
            break
            
    return members

def get_file_urls(titles):
    """Lấy URL cho danh sách titles (max 50)."""
    url = "https://commons.wikimedia.org/w/api.php"
    # Join titles with |
    titles_str = "|".join(titles)
    params = {
        "action": "query",
        "titles": titles_str,
        "prop": "imageinfo",
        "iiprop": "url",
        "format": "json"
    }
    headers = {"User-Agent": "AnkiVibeBot/1.0"}
    
    file_map = {} # title -> url
    try:
        res = requests.get(url, params=params, headers=headers).json()
        pages = res.get("query", {}).get("pages", {})
        for _, page in pages.items():
            if "imageinfo" in page:
                title = page["title"]
                url = page["imageinfo"][0]["url"]
                file_map[title] = url
    except Exception as e:
        print(f"❌ Error getting URLs: {e}")
        
    return file_map

def download_file(args):
    filename, url, dest_dir = args
    # Clean filename (bỏ File: prefix)
    clean_name = filename.replace("File:", "")
    dest_path = dest_dir / clean_name
    
    if dest_path.exists():
        # print(f"Skipping {clean_name}")
        return

    try:
        headers = {"User-Agent": "AnkiVibeBot/1.0 (https://github.com/hieucao/anki-vibe)"}
        res = requests.get(url, headers=headers, stream=True)
        if res.status_code == 200:
            with open(dest_path, 'wb') as f:
                for chunk in res.iter_content(1024):
                    f.write(chunk)
            print(f"✅ Downloaded: {clean_name}")
        else:
            print(f"❌ Failed {clean_name}: {res.status_code}")
    except Exception as e:
        print(f"❌ Error {clean_name}: {e}")

def main():
    dest_dir = Path("devanagari_project/media_dump")
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    categories = [
        "Category:Devanagari_stroke_order_(GIF)",
        "Category:Devanagari_stroke_order_(SVG)"
    ]
    
    all_titles = []
    for cat in categories:
        all_titles.extend(get_category_members(cat))
        
    print(f"Found {len(all_titles)} files total.")
    
    # Batch get URLs (50 at a time)
    download_queue = []
    chunk_size = 50
    
    print("📡 Resolving URLs...")
    for i in range(0, len(all_titles), chunk_size):
        chunk = all_titles[i:i + chunk_size]
        url_map = get_file_urls(chunk)
        for title, url in url_map.items():
            download_queue.append((title, url, dest_dir))
        time.sleep(0.5) # Be nice to API
            
    print(f"Ready to download {len(download_queue)} files.")
    
    # Download Parallel
    # Giới hạn 5 worker để tránh 429
    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(download_file, download_queue)
        
    print("🎉 All downloads finished.")

if __name__ == "__main__":
    main()
