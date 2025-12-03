# Bu dosyanın adı: podcast_creator.py
import google.generativeai as genai
import os
import uuid
from gtts import gTTS

# --- FONKSİYONLAR ---

def generate_podcast_content(user_text, gemini_model=None):
    """
    Kullanıcıdan gelen metni alır ve bunu bir sohbet diyaloğuna dönüştürür.
    NOT: Kotası yüksek olan 'gemini-1.5-flash' modelini ZORLA kullanır.
    """
    
    # 1. MODELİ BURADA ZORLA (Flash Modeli - Yüksek Kota)
    # Dışarıdan gelen 'gemini_model' parametresini yok sayıp kendi modelimizi kuruyoruz.
    try:
        # API Anahtarını al
        api_key = os.getenv('GOOGLE_API_KEY')
        
        if api_key:
            genai.configure(api_key=api_key)
            # KOTA DOSTU MODEL: gemini-1.5-flash
            # Burası çok önemli: Dışarıdan ne gelirse gelsin Flash kullanacak.
            active_model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            # Eğer API key çevresel değişkenlerde yoksa mecburen geleni kullan
            print("UYARI: Podcast creator içinde API Key bulunamadı, app.py'den gelen model kullanılıyor.")
            active_model = gemini_model

        prompt = f"""
        GÖREV: Aşağıda "METİN:" ile belirtilen metni al ve bu metni, bir 5. Sınıf Sosyal Bilgiler öğretmeni tarafından sunulan, 
        sohbet havasında bir podcast metnine dönüştür.

        KURALLAR:
        1. Metni TEK BİR ANLATICI (Öğretmen) sunmalıdır.
        2. Anlatıcı, metindeki ana fikirleri sanki öğrencileriyle konuşuyormuş gibi açıklamalıdır.
        3. Konunun en önemli yerlerini veya kilit kavramları vurgulamalıdır.
        4. Sadece üretilen sohbet metnini döndür. Giriş veya kapanış selamlaması ekleme.
        
        METİN:
        "{user_text}"
        """

        # Oluşturduğumuz Flash modelini kullan
        response = active_model.generate_content(prompt)
        
        # Temizlik: Yıldızları ve gereksiz karakterleri kaldır
        clean_text = response.text.replace("*", "").replace("#", "")
        return clean_text

    except Exception as e:
        print(f"Podcast içerik üretim hatası: {e}")
        return None

def convert_text_to_speech(text, static_folder):
    """
    Metni gTTS (Google Translate TTS) kullanarak MP3'e çevirir.
    TAMAMEN ÜCRETSİZDİR.
    """
    try:
        print("🔊 gTTS ile ses oluşturuluyor...")
        
        # Klasör yoksa oluştur (Garanti olsun diye kontrol ekledim)
        if not os.path.exists(static_folder):
            os.makedirs(static_folder)
        
        # Benzersiz dosya adı oluştur
        file_name = f"podcast_{uuid.uuid4()}.mp3"
        output_path = os.path.join(static_folder, file_name)
        
        # gTTS Nesnesi Oluştur (lang='tr' -> Türkçe)
        tts = gTTS(text=text, lang='tr', slow=False)
        
        # Kaydet
        tts.save(output_path)
        
        if os.path.exists(output_path):
            print(f"✅ Ses dosyası oluşturuldu: {output_path}")
            return f"/static/{file_name}"
        else:
            print(f"❌ HATA: Dosya kaydedilemedi: {output_path}")
            return None

    except Exception as e:
        print(f"❌ gTTS hatası: {e}")
        return None
