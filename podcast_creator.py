import google.generativeai as genai
from google.cloud import texttospeech
import os
import uuid

# --- AYARLAR ---
# Google Cloud JSON Dosyasının Adı
JSON_FILENAME = "google_key.json"

# --- KİMLİK DOĞRULAMA (LOCAL vs RENDER) ---
# Render'da 'Secret Files' yüklediysen dosya genellikle /etc/secrets/ altında olur.
# Lokalde ise projenin ana dizininde olur.

if os.path.exists(f"/etc/secrets/{JSON_FILENAME}"):
    # RENDER ORTAMI
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = f"/etc/secrets/{JSON_FILENAME}"
    print(f"✅ Render ortamı algılandı. Anahtar yolu: /etc/secrets/{JSON_FILENAME}")
elif os.path.exists(os.path.join(os.getcwd(), JSON_FILENAME)):
    # LOCAL (BİLGİSAYAR) ORTAMI
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(os.getcwd(), JSON_FILENAME)
    print(f"✅ Local ortam algılandı. Anahtar yolu: {JSON_FILENAME}")
else:
    print("⚠️ UYARI: google_key.json dosyası bulunamadı! Ses oluşturma çalışmayabilir.")

# -------------------------------------------

def generate_podcast_content(user_text, gemini_model):
    """
    Gemini ile metin oluşturma kısmı.
    """
    prompt = f"""
    GÖREV: Aşağıdaki metni 5. Sınıf öğrencilerine hitap eden, samimi bir öğretmenin anlatacağı
    bir podcast metnine dönüştür. Tek bir kişi konuşsun. Konuşma dili kullan.
    
    METİN:
    "{user_text}"
    """
    try:
        response = gemini_model.generate_content(prompt)
        # Gemini bazen * veya # kullanır, ses motoru okumasın diye temizleyelim
        clean_text = response.text.replace("*", "").replace("#", "").replace("Anlatıcı:", "")
        return clean_text
    except Exception as e:
        print(f"Gemini hatası: {e}")
        return None

def convert_text_to_speech(text, static_folder):
    """
    Google Cloud Text-to-Speech API (Wavenet) kullanır.
    """
    try:
        print("🔊 Google Cloud Wavenet ile ses oluşturuluyor...")
        
        # 1. İstemciyi başlat (Otomatik olarak yukarıdaki JSON yolunu kullanır)
        client = texttospeech.TextToSpeechClient()

        # 2. Metni ayarla
        synthesis_input = texttospeech.SynthesisInput(text=text)

        # 3. SES AYARLARI (KALİTE BURADA BELİRLENİR)
        # language_code='tr-TR' -> Türkçe
        # name='tr-TR-Wavenet-C' -> Tok Erkek Sesi (C). (B=Kadın, A=Kadın, D=Erkek, E=Erkek)
        voice = texttospeech.VoiceSelectionParams(
            language_code="tr-TR",
            name="tr-TR-Wavenet-C", 
            ssml_gender=texttospeech.SsmlVoiceGender.MALE
        )

        # 4. Dosya formatı (MP3)
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )

        # 5. İsteği gönder
        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )

        # 6. Dosyayı kaydet
        file_name = f"podcast_{uuid.uuid4()}.mp3"
        output_path = os.path.join(static_folder, file_name)
        
        with open(output_path, "wb") as out:
            out.write(response.audio_content)
            
        print(f"✅ Wavenet ses dosyası oluşturuldu: {output_path}")
        return f"/static/{file_name}"

    except Exception as e:
        print(f"❌ Google Cloud TTS Hatası: {e}")
        return None
