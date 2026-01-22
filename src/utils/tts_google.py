import requests
import base64
import json
import os

class GoogleTTS:
    def __init__(self, api_key):
        self.api_key = api_key
        self.url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={api_key}"

    def synthesize(self, text: str, output_file: str) -> bool:
        """
        Generate audio using Google Cloud TTS (hi-IN Neural2).
        Saves to output_file.
        """
        payload = {
            "input": {"text": text},
            "voice": {
                "languageCode": "hi-IN", 
                "name": "hi-IN-Neural2-A" # Female Neural Voice
            },
            "audioConfig": {
                "audioEncoding": "MP3", 
                "speakingRate": 0.85, # Slightly slower for beginners
                "pitch": 0.0
            }
        }
        
        try:
            res = requests.post(self.url, json=payload, timeout=10)
            if res.status_code == 200:
                audio_content = res.json().get("audioContent")
                if audio_content:
                    with open(output_file, "wb") as f:
                        f.write(base64.b64decode(audio_content))
                    return True
            else:
                print(f"TTS API Error ({res.status_code}): {res.text}")
        except Exception as e:
            print(f"TTS Network Error: {e}")
            
        return False
