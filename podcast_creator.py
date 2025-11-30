# Bu dosyanın adı: podcast_creator.py
import google.generativeai as genai
import os
import subprocess
import uuid
from google.cloud import texttospeech
import json

# --- GOOGLE TTS KURULUMU ---
SERVICE_ACCOUNT_FILE = os.path.join(os.getcwd(), "service-account-key.json")
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = SERVICE_ACCOUNT_FILE

try:
    tts_client = texttospeech.TextToSpeechClient()
    print("✅ Google TTS client başarıyla başlatıldı")
except Exception as e:
    print(f"❌ Google TTS client hatası: {e}")
    tts_client = None

# --- MUTLAK YOL BELİRLEME ---
print(f"🔍 Python çalışma dizini: {os.getcwd()}")
print(f"🔍 podcast_creator.py'nin yeri: {os.path.abspath(__file__)}")

# LOCAL (Windows/macOS) ve RENDER (Linux) ortamlarını otomatik ayır
if os.name == "nt":   # Windows (local)
    BASE_DIR = os.getcwd()
    PIPER_PATH = os.path.join(BASE_DIR, "piper", "piper.exe")
    MODEL_PATH = os.path.join(BASE_DIR, "models", "tr_TR-fahrettin-medium.onnx")
    CONFIG_PATH = os.path.join(BASE_DIR, "models", "tr_TR-fahrettin-medium.onnx.json")
else:                 # Linux (Render)
    BASE_DIR = "/app"
    PIPER_PATH = "/app/piper/piper"   # Linux binary
    MODEL_PATH = "/app/models/tr_TR-fahrettin-medium.onnx"
    CONFIG_PATH = "/app/models/tr_TR-fahrettin-medium.onnx.json"

print(f"✅ BASE_DIR: {BASE_DIR}")
print(f"✅ PIPER_PATH: {PIPER_PATH}")
print(f"🔍 Piper var mı? {os.path.exists(PIPER_PATH)}")
print(f"🔍 Model var mı? {os.path.exists(MODEL_PATH)}")


# --- FONKSİYONLAR ---

def generate_podcast_content(user_text, gemini_model):
    """
    Kullanıcıdan gelen metni alır ve bunu bir sohbet diyaloğuna dönüştürür.
    """

    prompt = f"""
    GÖREV: Aşağıda "METİN:" ile belirtilen metni al ve bu metni, bir 5. Sınıf Sosyal Bilgiler öğretmeni tarafından sunulan, 
    sohbet havasında bir podcast metnine dönüştür.

    KURALLAR:
    1. Metni TEK BİR ANLATICI (Öğretmen) sunmalıdır. (Asla "Anlatıcı 1", "Anlatıcı 2" gibi ayırma.)
    2. Anlatıcı, metindeki ana fikirleri sanki öğrencileriyle konuşuyormuş gibi açıklamalıdır.
    3. Konunun en önemli yerlerini veya kilit kavramları vurgulamalıdır.
    4. Bu önemli yerleri vurgularken, "Burası çok önemli, buna dikkat edin!" veya 
       "İşte bu nokta tam bir sınav sorusu olabilir!" gibi ilgi çekici ifadeler kullanmalıdır.
    5. Sadece üretilen sohbet metnini döndür. Giriş veya kapanış selamlaması ekleme.

    METİN:
    "{user_text}"
    """

    try:
        response = gemini_model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini hatası: {e}")
        return None

def convert_text_to_speech(text, static_folder):
    try:
        from gtts import gTTS
        import uuid
        audio_filename = f"podcast_{uuid.uuid4()}.mp3"
        audio_path = os.path.join(static_folder, audio_filename)
        tts = gTTS(text=text, lang='tr', slow=False)
        tts.save(audio_path)
        return f"/static/{audio_filename}"
    except Exception as e:
        print(f"❌ gTTS hatası: {e}")
        return None
    
    if not os.path.exists(MODEL_PATH):
        print(f"❌ KRİTİK HATA: Model bulunamadı: {MODEL_PATH}")
        return None

    file_name = f"podcast_{uuid.uuid4()}.wav"
    output_path = os.path.join(static_folder, file_name)
    audio_url = f"/static/{file_name}"
    
    # Mutlak yolları kullan
    absolute_piper_path = os.path.abspath(PIPER_PATH)
    absolute_model_path = os.path.abspath(MODEL_PATH)
    absolute_config_path = os.path.abspath(CONFIG_PATH)
    absolute_output_path = os.path.abspath(output_path)
    
    print(f"🔍 Mutlak Piper yolu: {absolute_piper_path}")
    print(f"🔍 Var mı? {os.path.exists(absolute_piper_path)}")
    
    # Piper komut dizesi
    komut_string = (
        f'"{absolute_piper_path}" -m "{absolute_model_path}" '
        f'-c "{absolute_config_path}" -f "{absolute_output_path}" --sentence_silence 0.2'
    )
    
    # Debug removed

    try:
        # Komutu çalıştır
        result = subprocess.run(
            komut_string,
            input=podcast_text.encode('utf-8'),
            check=True,
            shell=True,
            capture_output=True,
            timeout=60
        )
        
        # Piper çıktısını göster
        if result.stdout:
            print(f"✅ Piper STDOUT: {result.stdout.decode('utf-8', errors='ignore')}")
        if result.stderr:
            print(f"ℹ️ Piper STDERR: {result.stderr.decode('utf-8', errors='ignore')}")
        
        # Dosya oluştu mu kontrol et
        if os.path.exists(output_path):
            print(f"✅ Ses dosyası oluşturuldu: {output_path}")
            return audio_url
        else:
            print(f"❌ HATA: Dosya oluşmadı: {output_path}")
            return None

    except subprocess.CalledProcessError as e:
        print(f"❌ Piper HATASI (CalledProcessError):")
        print(f"Exit code: {e.returncode}")
        if e.stderr:
            print(f"STDERR: {e.stderr.decode('utf-8', errors='ignore')}")
        return None
    except subprocess.TimeoutExpired:
        print("❌ HATA: Piper zaman aşımına uğradı (60 saniye)")
        return None
    except Exception as e:
        print(f"❌ Beklenmeyen hata: {e}")
        return None
