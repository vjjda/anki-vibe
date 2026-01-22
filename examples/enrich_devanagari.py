import sys
from pathlib import Path
from ruamel.yaml import YAML
from aksharamukha import transliterate

# Từ điển thuật ngữ Phật giáo/Sanskrit (Devanagari - Word - Meaning)
# Nguồn: Tri thức tổng hợp
DATA = {
    'अ': [("अनित्य", "Impermanence"), ("अनात्मन्", "Non-self (Anatta)"), ("अहिंसा", "Non-violence")],
    'आ': [("आनन्द", "Bliss/Joy"), ("आर्य", "Noble"), ("आलयविज्ञान", "Storehouse Consciousness")],
    'इ': [("इन्द्रिय", "Faculty/Sense"), ("इतिवुत्तक", "So it was said (Scripture)")],
    'ई': [("ईश्वर", "Lord/God (refuted in Buddhism)"), ("ईर्ष्‍या", "Jealousy")],
    'उ': [("उपादान", "Clinging/Grasping"), ("उपाय", "Skillful Means")],
    'ऊ': [("ऊर्ण", "Tuft of hair (32 marks)"), ("ऊर्ध्व", "Upwards")],
    'ऋ': [("ऋद्धि", "Psychic Power"), ("ऋषि", "Seer/Sage")],
    'ए': [("एकचित्त", "One-pointedness of mind"), ("एकाग्रता", "Concentration")],
    'ऐ': [("ऐरावत", "Airavata (Elephant)"), ("ऐश्वर्य", "Sovereignty")],
    'ओ': [("ओजस्", "Vigor/Vitality"), ("ओघ", "Flood (of passions)")],
    'औ': [("औपपातिक", "Spontaneously born"), ("औषध", "Medicine")],
    'अं': [("अंग", "Limb/Part"), ("अंत", "End/Goal")],
    
    'क': [("करुणा", "Compassion"), ("कर्म", "Karma (Action)"), ("क्लेश", "Defilement")],
    'ख': [("ख", "Space/Void"), ("खण्ड", "Group/Aggregate (Khandha)")], 
    'ग': [("गति", "Realm of existence"), ("गाथा", "Verse"), ("गृध्रकूट", "Vulture Peak")],
    'घ': [("घण्टा", "Bell"), ("घ्राण", "Nose (Sense)")],
    'ङ': [], # Hiếm khi đứng đầu
    
    'च': [("चित्त", "Mind/Consciousness"), ("चक्र", "Wheel (Dharma)"), ("चक्षु", "Eye")],
    'छ': [("छन्द", "Desire/Impulse"), ("छाया", "Shadow")],
    'ज': [("जरा", "Old age/Decay"), ("जाति", "Birth"), ("ज्ञान", "Gnosis/Knowledge")],
    'झ': [("ध्यान", "Jhana (Meditation) - (Pali Jhana maps to Skt Dhyana, but Jha sound related)")], # Dhyana bắt đầu bằng Dh, Jhana bắt đầu bằng Jh (Pali). Devanagari Sanskrit là Dhyana.
    'ञ': [("ज्ञान", "Jnana (Knowledge) - contains Nya")],
    
    'ट': [("ट", "Ta (Sound)")], # Hiếm trong thuật ngữ Phật giáo
    'ठ': [("ठ", "Tha (Sound)")],
    'ड': [("डमरु", "Drum")],
    'ढ': [("ढ", "Dha")],
    'ण': [("रण", "Battle (Defilements) - suffix")],
    
    'त': [("तृष्णा", "Craving (Tanha)"), ("तथागत", "Tathagata"), ("तर्क", "Logic/Debate")],
    'थ': [("थेरवाद", "Theravada (Doctrine of Elders)")],
    'द': [("दुःख", "Suffering (Dukkha)"), ("दान", "Generosity"), ("धर्म", "Dharma")],
    'ध': [("धर्म", "Dharma (Law/Truth)"), ("धातु", "Element"), ("ध्यान", "Meditation")],
    'न': [("निर्वाण", "Nirvana"), ("निरोध", "Cessation"), ("नाम", "Name (Nama)")],
    
    'प': [("प्रज्ञा", "Wisdom (Prajna)"), ("पारमिता", "Perfection"), ("प्रतीत्यसमुत्पाद", "Dependent Origination")],
    'फ': [("फल", "Fruit (Result)"), ("फुस्स", "Touch/Contact")],
    'ब': [("बुद्ध", "Buddha"), ("बोधि", "Awakening"), ("बोधिसत्त्व", "Bodhisattva")],
    'भ': [("भावना", "Cultivation/Meditation"), ("भिक्षु", "Monk"), ("भूमि", "Ground/Stage")],
    'म': [("मैत्री", "Loving-kindness"), ("मोक्ष", "Liberation"), ("महायान", "Great Vehicle")],
    
    'य': [("यान", "Vehicle"), ("योग", "Yoga/Practice"), ("यक्ष", "Yaksha (Spirit)")],
    'र': [("रूप", "Form (Rupa)"), ("राग", "Greed/Lust"), ("रत्न", "Jewel")],
    'ल': [("लोभ", "Greed"), ("लोक", "World")],
    'व': [("वज्र", "Diamond/Thunderbolt"), ("विज्ञान", "Consciousness"), ("वीर्य", "Energy/Effort")],
    
    'श': [("शून्य", "Empty"), ("शून्यता", "Emptiness"), ("शील", "Morality")],
    'ष': [("षडायतन", "Six Sense Bases")],
    'स': [("संसार", "Samsara"), ("समाधि", "Concentration"), ("सुख", "Happiness"), ("संघ", "Sangha")],
    'ह': [("हीनयान", "Lesser Vehicle"), ("हेतु", "Cause")],
    
    'ळ': [],
    'क्ष': [("क्षान्ति", "Patience (Kshanti)"), ("क्षण", "Moment")],
    'ज्ञ': [("ज्ञान", "Knowledge")]
}

def enrich():
    notes_path = Path("devanagari_project/data/notes.yaml")
    
    if not notes_path.exists():
        print("❌ notes.yaml not found.")
        return

    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 4096
    
    with open(notes_path, "r", encoding="utf-8") as f:
        notes = yaml.load(f) or []
        
    count = 0
    for note in notes:
        char = note["fields"].get("Character")
        if char in DATA:
            examples = DATA[char]
            
            ex_words = []
            ex_ipas = []
            ex_means = []
            
            for word, mean in examples:
                # Transliterate to IPA
                # Dùng 'Devanagari' -> 'IPA'
                try:
                    ipa = transliterate.process('Devanagari', 'IPA', word)
                except:
                    ipa = ""
                
                ex_words.append(word)
                ex_ipas.append(ipa)
                ex_means.append(mean)
            
            # Join with " | "
            note["fields"]["Examples"] = " | ".join(ex_words)
            note["fields"]["Example_IPAs"] = " | ".join(ex_ipas)
            note["fields"]["Example_Meanings"] = " | ".join(ex_means)
            note["fields"]["Example_Audio_Source"] = ", ".join(ex_words) # Cho TTS
            
            count += 1

    with open(notes_path, "w", encoding="utf-8") as f:
        yaml.dump(notes, f)
        
    print(f"✅ Enriched {count} notes with Buddhist terminology.")

if __name__ == "__main__":
    enrich()
