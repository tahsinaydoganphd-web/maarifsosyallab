import google.generativeai as genai
from google.cloud import texttospeech
import os
import uuid

# --- AYARLAR ---
JSON_FILENAME = "google_key.json"

# --- KİMLİK DOĞRULAMA ---
if os.path.exists(f"/etc/secrets/{JSON_FILENAME}"):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = f"/etc/secrets/{JSON_FILENAME}"
elif os.path.exists(os.path.join(os.getcwd(), JSON_FILENAME)):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(os.getcwd(), JSON_FILENAME)
else:
    print("⚠️ UYARI: google_key.json dosyası bulunamadı!")

# -------------------------------------------

def generate_podcast_content(user_text, gemini_model):
    """
    Gemini ile metin oluşturma kısmı (NotebookLM Tarzı - Samimi ve Kısa).
    """
    prompt = f"""
    ROLE: Sen "SosyalLab" adında çok popüler bir podcastin sunucususun. Adın "Bilge".
    HEDEF KİTLE: 5. Sınıf öğrencileri.
    
    GÖREV: Aşağıdaki metni al ve mikrofona konuşuyormuş gibi samimi, enerjik ve akıcı bir anlatıma çevir.

    SÜRE KURALI (ÇOK KRİTİK):
    1. Metin seslendirildiğinde KESİNLİKLE 2.5 dakikayı geçmemelidir.
    2. Bunun için üreteceğin metin EN FAZLA 330 KELİME olmalıdır.
    3. Lafı uzatma, gereksiz detayları at, konunun özünü hap bilgi gibi ver.

    ÜSLUP KURALLARI:
    1. ASLA "Giriş müziği", "Güler", "Metniniz hazır" gibi dış sesler veya parantez içi notlar YAZMA.
    2. Doğrudan "Selam millet! Bugün çok ilginç bir konuyla karşınızdayım" gibi enerjik bir giriş yap.
    3. Kitap gibi okuma, sohbet et. "Bakın aslında olay şu...", "Şuna inanabiliyor musunuz?" gibi ifadeler kullan.
    
    HAM METİN:
    "{user_text}"
    """
    try:
        response = gemini_model.generate_content(prompt)
        # Temizlik
        clean_text = response.text.replace("*", "").replace("#", "").replace("Bilge:", "").replace("Sunucu:", "")
        clean_text = clean_text.replace('"', "'")
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
        
        client = texttospeech.TextToSpeechClient()
        synthesis_input = texttospeech.SynthesisInput(text=text)

        # --- SES AYARLARI (BURAYI DEĞİŞTİRDİM) ---
        voice = texttospeech.VoiceSelectionParams(
            language_code="tr-TR",
            # tr-TR-Wavenet-D: Genç ve dinamik erkek sesi (Podcast için iyidir)
            # Kadın istersen: "tr-TR-Wavenet-B" yapabilirsin.
            name="tr-TR-Wavenet-B", 
            ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
        )

        # --- HIZ AYARI (BURASI YENİ) ---
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.15,  # %15 daha hızlı konuşur (Daha enerjik ve kısa sürer)
            pitch=0.0            # Ses tonu normal
        )

        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )

        file_name = f"podcast_{uuid.uuid4()}.mp3"
        output_path = os.path.join(static_folder, file_name)
        
        with open(output_path, "wb") as out:
            out.write(response.audio_content)
            
        print(f"✅ Wavenet ses dosyası oluşturuldu: {output_path}")
        return f"/static/{file_name}"

    except Exception as e:
        print(f"❌ Google Cloud TTS Hatası: {e}")
        return None
