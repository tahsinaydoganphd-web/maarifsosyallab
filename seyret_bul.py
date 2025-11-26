# -*- coding: utf-8 -*-
"""
Maarif Modeli Seyret Bul Aracı
5. Sınıf Sosyal Bilgiler için Video Tabanlı Öğrenme Sistemi
(Yeni JSON yapısıyla uyumlu hale getirildi - v2)
"""

import google.generativeai as genai
import json
import os
import random
import time
import re
import db_helper
from datetime import datetime
from flask import current_app
try:
    from moviepy.editor import VideoFileClip
except ImportError:
    from moviepy import VideoFileClip

# --- SABITLER ---
SKORLAR_FILE = "seyret_bul_skorlar.json"
ADMIN_SIFRE = "97032647"

# --- YENİ EKLENDİ: ÜNİTE VE KONU BAŞLIKLARI GRUPLAMASI ---
UNITE_YAPISI = {
    "Birlikte Yaşamak": ["SB.5.1.1.", "SB.5.1.2.", "SB.5.1.3."],
    "Evimiz Dünya": ["SB.5.2.1.", "SB.5.2.2.", "SB.5.2.3.", "SB.5.2.4."],
    "Ortak Mirasımız": ["SB.5.3.1.", "SB.5.3.2.", "SB.5.3.3."],
    "Yaşayan Demokrasimiz": ["SB.5.4.1.", "SB.5.4.2.", "SB.5.4.3.", "SB.5.4.4."],
    "Hayatımızdaki Ekonomi": ["SB.5.5.1.", "SB.5.5.2.", "SB.5.5.3."],
    "Teknoloji ve Sosyal Bilimler": ["SB.5.6.1.", "SB.5.6.2."]
}


# --- SÜREÇ BİLEŞENLERİ ---
SURECLER = {
    "SB.5.1.1.": "Dâhil olduğu gruplar ve bu gruplardaki rolleri arasındaki ilişkileri çözümleyebilme",
    "SB.5.1.2.": "Kültürel özelliklere saygı duymanın birlikte yaşamaya etkisini yorumlayabilme",
    "SB.5.1.3.": "Toplumsal birliği sürdürmeye yönelik yardımlaşma ve dayanışma",
    "SB.5.2.1.": "Yaşadığı ilin göreceli konum özelliklerini belirleyebilme",
    "SB.5.2.2.": "Yaşadığı ilde doğal ve beşerî çevredeki değişimi neden ve sonuçlarıyla yorumlayabilme",
    "SB.5.2.3.": "Yaşadığı ilde meydana gelebilecek afetlerin etkilerini azaltmaya yönelik farkındalık etkinlikleri düzenleyebilme",
    "SB.5.2.4.": "Ülkemize komşu devletler hakkında bilgi toplayabilme",
    "SB.5.3.1.": "Yaşadığı ildeki ortak miras ögelerine ilişkin oluşturduğu ürünü paylaşabilme",
    "SB.5.3.2.": "Anadolu'da ilk yerleşimleri kuran toplumların sosyal hayatlarına yönelik bakış açısı geliştirebilme",
    "SB.5.3.3.": "Mezopotamya ve Anadolu medeniyetlerinin ortak mirasa katkılarını karşılaştırabilme",
    "SB.5.4.1.": "Demokrasi ve cumhuriyet kavramları arasındaki ilişkiyi çözümleyebilme",
    "SB.5.4.2.": "Toplum düzenine etkisi bakımından etkin vatandaş olmanın önemine yönelik çıkarımda bulunabilme",
    "SB.5.4.3.": "Temel insan hak ve sorumluluklarının önemini sorgulayabilme",
    "SB.5.4.4.": "Bir ihtiyaç hâlinde veya sorun karşısında başvuru yapılabilecek kurumlar hakkında bilgi toplayabilme",
    "SB.5.5.1.": "Kaynakları verimli kullanmanın doğa ve insanlar üzerindeki etkisini yorumlayabilme",
    "SB.5.5.2.": "İhtiyaç ve isteklerini karşılamak için gerekli bütçeyi planlayabilme",
    "SB.5.5.3.": "Yaşadığı ildeki ekonomik faaliyetleri özetleyebilme",
    "SB.5.6.1.": "Teknolojik gelişmelerin toplum hayatına etkilerini tartışabilme",
    "SB.5.6.2.": "Teknolojik ürünlerin bilinçli kullanımının önemine ilişkin ürün oluşturabilme"
}

# --- API YAPILANDIRMA ---
def api_yapilandir(api_key):
    """Gemini API'yi yapılandırır"""
    if api_key and api_key != "":
        genai.configure(api_key=api_key)
        return genai.GenerativeModel('models/gemini-pro-latest')  # ✓ YENİ
    return None
    
def parse_video_questions(json_str):
    """SQL'den gelen metin formatındaki soruları listeye çevirir."""
    if not json_str: return []
    try:
        return json.loads(json_str)
    except: return []

# --- VIDEO YÖNETİMİ ---
def videolari_yukle():
    """Tüm videoları SQL veritabanından çeker ve sözlüğe çevirir."""
    rows = db_helper.get_all_videos() if hasattr(db_helper, 'get_all_videos') else []
    videos_dict = {}
    
    for row in rows:
        vid_id = row['video_id']
        videos_dict[vid_id] = {
            "video_id": vid_id,
            "baslik": row['baslik'],
            "surec_bileseni": row['surec_bileseni'],
            "url": row['video_url'],
            "thumbnail_url": row.get('thumbnail_url', ''),
            "sure_saniye": row.get('sure_saniye', 0),
            "sorular": parse_video_questions(row.get('sorular_json'))
        }
    return videos_dict

def videolari_kaydet(videos_dict):
    """
    Sözlükteki videoları SQL veritabanına kaydeder/günceller.
    """
    try:
        for vid_id, data in videos_dict.items():
            # SQL için uygun veri yapısını hazırla
            db_data = {
                "video_id": vid_id,
                "baslik": data.get("baslik"),
                "surec_bileseni": data.get("surec_bileseni"),
                "video_url": data.get("url"), # Dict'te 'url', DB'de 'video_url' olabilir, dikkat!
                "thumbnail_url": data.get("thumbnail_url"),
                "sure_saniye": data.get("sure_saniye"),
                # Soruları JSON string formatına çevir
                "sorular_json": json.dumps(data.get("sorular", []), ensure_ascii=False)
            }
            # db_helper üzerinden kaydet
            db_helper.save_video(db_data)
        return True
    except Exception as e:
        print(f"SQL Kayıt Hatası: {e}")
        return False

def videoyu_sil(video_id):
    """Videoyu SQL'den ve diskten siler."""
    video = video_detay_getir(video_id)
    if not video: return {"success": False, "hata": "Video bulunamadı."}
        
    # Lokal dosyayı sil
    video_url = video.get("url", "")
    if video_url.startswith("/videolar/"):
        filename = video_url.split('/')[-1]
        file_path = os.path.join('videolar', filename)
        if os.path.exists(file_path):
            try: os.remove(file_path)
            except: pass
    
    # SQL'den sil
    if db_helper.delete_video(video_id):
        return {"success": True, "mesaj": "Video silindi."}
    else:
        return {"success": False, "hata": "Veritabanı hatası."}

def surece_gore_videolari_getir(surec_kodu):
    """
    Belirli süreç bileşenine ait videoları filtreler
    
    Returns:
        list: Video listesi
    """
    videos = videolari_yukle()
    filtered = []
    
    # Videoları standart bir liste formatına getir
    video_listesi = []
    
    if isinstance(videos, list):
        video_listesi = videos
    else:
        # Dictionary ise listeye çevir
        for video_id, video_data in videos.items():
            video_data["video_id"] = video_id
            video_listesi.append(video_data)
    
    # Sürece göre filtrele
    for video_data in video_listesi:
        if video_data.get("surec_bileseni") == surec_kodu:
            filtered.append({
                "video_id": video_data.get("video_id"),
                "baslik": video_data.get("baslik"),
                "thumbnail_url": video_data.get("thumbnail_url"),
                "sure_saniye": video_data.get("sure_saniye", 0)
            })
    
    return filtered

def video_detay_getir(video_id):
    """Tek bir videonun tüm bilgilerini getirir"""
    videos = videolari_yukle()
    
    # Eğer videos bir liste ise
    if isinstance(videos, list):
        for video in videos:
            if video.get("video_id") == video_id:
                return video
        return None
    
    # Dictionary ise
    return videos.get(video_id, None)

def video_id_olustur():
    """Benzersiz video ID oluşturur"""
    timestamp = int(time.time() * 1000)
    return f"vid_{timestamp}"

# --- SORU YÖNETİMİ ---

def rastgele_sorular_sec(video_id, adet=3):
    """
    Videodaki sorulardan rastgele 3 soru seçer ve duraklatma zamanına göre sıralar
    
    Returns:
        list: Seçilen sorular
    """
    video = video_detay_getir(video_id)
    
    if not video or "sorular" not in video:
        return []
    
    sorular = video["sorular"]
    
    if len(sorular) < adet:
        secilen = sorular
    else:
        # Rastgele seç
        secilen = random.sample(sorular, adet)
    
    # Duraklatma zamanına göre sırala
    secilen.sort(key=lambda x: x.get("duraklatma_saniyesi", 0))
    
    return secilen

def soru_detay_getir(video_id, soru_id):
    """Belirli bir sorunun detaylarını getirir"""
    video = video_detay_getir(video_id)
    
    if not video or "sorular" not in video:
        return None
    
    for soru in video["sorular"]:
        if soru.get("id") == soru_id:
            return soru
    
    return None

# --- CEVAP DEĞERLENDİRME (GEMİNİ API) ---
# ... (Kodun geri kalanı sizin orijinal dosyanızdaki gibi devam ediyor) ...
# ... (cevap_degerlendir, skorlari_yukle, skor_ekle vb. tüm fonksiyonlar) ...

# --- SADECE BU FONKSİYON BASİT ÖRNEK İÇİN DEĞİŞTİRİLDİ ---
def tum_surecleri_getir():
    """Tüm süreç bileşenlerini SÖZLÜK olarak döndürür"""
    return SURECLER

def sure_formati(saniye):
    """Saniyeyi dakika:saniye formatına çevirir"""
    dakika = saniye // 60
    saniye = saniye % 60
    return f"{dakika}:{saniye:02d}"

def saniye_to_timestamp(saniye):
    """Saniyeyi video timestamp formatına çevirir (00:01:30)"""
    saat = saniye // 3600
    dakika = (saniye % 3600) // 60
    san = saniye % 60
    return f"{saat:02d}:{dakika:02d}:{san:02d}"

def video_sayisi_getir():
    """Sistemdeki toplam video sayısını döndürür"""
    videos = videolari_yukle()
    return len(videos)

def surece_gore_video_sayisi():
    """Her süreç bileşeni için video sayısını döndürür"""
    videos = videolari_yukle()
    sayilar = {}
    
    for surec_kod in SURECLER.keys():
        sayilar[surec_kod] = 0
    
    if isinstance(videos, list):
        video_list = videos
    else:
        video_list = videos.values()
    
    for video_data in video_list:
        surec = video_data.get("surec_bileseni")
        if surec in sayilar:
            sayilar[surec] += 1
    
    return sayilar
# --- YARDIMCI FONKSİYONLAR (Admin Paneli İçin) ---

def json_parse_et(api_yaniti):
    """API'den gelen yanıtı temizleyip JSON'a çevirir."""
    # re modülünün import edildiğinden emin olunmuştur.
    temiz_yanit = re.search(r"```json\s*(\{.*\})\s*```", api_yaniti, re.DOTALL)
    if temiz_yanit:
        try:
            return json.loads(temiz_yanit.group(1))
        except json.JSONDecodeError:
            return None
    try:
        return json.loads(api_yaniti)
    except json.JSONDecodeError:
        return None

def soru_uretme_promptu_olustur(video_metni):
    """Gemini'ye gönderilecek prompt'u hazırlar (3 Tip - 9 Soru)."""
    prompt = f"""
    Aşağıdaki metin, 5. sınıf Sosyal Bilgiler seviyesinde bir eğitim videosunun deşifre edilmiş halidir. Bu metni analiz et ve metindeki önemli noktalara odaklanarak toplam 9 adet soru oluştur.

    Soru Tipleri:
    1.  3 adet "CoktanSecmeli" (4 şıklı)
    2.  3 adet "BoslukDoldurma" (Metinden bir cümlenin önemli bir kelimesi boşluk olarak verilir, cevap bu kelimedir)
    3.  3 adet "KisaCevap" (Cevabı 3-5 kelime olan, yoruma dayalı veya doğrudan bilgiyi ölçen kısa cevaplı soru)

    Tüm soruları, cevapları ve duraklatma saniyelerini içeren, aşağıdaki formatta TEK BİR JSON objesi döndür.
    Duraklatma saniyesi (duraklatma_saniyesi) alanı, sorunun sorulmasının uygun olacağı, videonun süresiyle orantılı tahmini bir saniye değeri olmalıdır.

    JSON Formatı:
    ```json
    {{
        "sorular": [
            {{
                "id": "q1",
                "tip": "CoktanSecmeli",
                "soru": "Birinci çoktan seçmeli soru metni.",
                "duraklatma_saniyesi": 35,
                "dogru_cevap": "A",
                "cevaplar": [
                    "A şıkkı metni",
                    "B şıkkı metni",
                    "C şıkkı metni",
                    "D şıkkı metni"
                ]
            }},
            {{
                "id": "q2",
                "tip": "CoktanSecmeli",
                "soru": "İkinci çoktan seçmeli soru metni.",
                "duraklatma_saniyesi": 60,
                "dogru_cevap": "C",
                "cevaplar": ["A...", "B...", "C...", "D..."]
            }},
            {{
                "id": "q3",
                "tip": "CoktanSecmeli",
                "soru": "Üçüncü çoktan seçmeli soru metni.",
                "duraklatma_saniyesi": 90,
                "dogru_cevap": "B",
                "cevaplar": ["A...", "B...", "C...", "D..."]
            }},
            {{
                "id": "q4",
                "tip": "BoslukDoldurma",
                "soru": "Metne göre, Mezopotamya'da kullanılan yazıya '...' denir.",
                "duraklatma_saniyesi": 45,
                "dogru_cevap": "Çivi Yazısı"
            }},
            {{
                "id": "q5",
                "tip": "BoslukDoldurma",
                "soru": "...",
                "duraklatma_saniyesi": 75,
                "dogru_cevap": "..."
            }},
            {{
                "id": "q6",
                "tip": "BoslukDoldurma",
                "soru": "...",
                "duraklatma_saniyesi": 100,
                "dogru_cevap": "..."
            }},
            {{
                "id": "q7",
                "tip": "KisaCevap",
                "soru": "Metne göre, Sümerlerin en önemli icadı nedir?",
                "duraklatma_saniyesi": 50
            }},
            {{
                "id": "q8",
                "tip": "KisaCevap",
                "soru": "Yaşadığımız bölgedeki kültürel miras ögelerine iki örnek verin.",
                "duraklatma_saniyesi": 80
            }},
            {{
                "id": "q9",
                "tip": "KisaCevap",
                "soru": "...",
                "duraklatma_saniyesi": 110
            }}
        ]
    }}
    ```

    VİDEO METNİ:
    ---
    {video_metni}
    ---
    """
    return prompt

# --- ANA KAYIP FONKSİYON (sorular_uret_ve_kaydet) ---

def sorular_uret_ve_kaydet(surec_bileseni, baslik, video_url, video_metni, admin_sifre, video_sure_saniye):
    """
    Video metnini ve bilgileri alır, Gemini ile soruları üretir ve kaydeder.
    Bu, /api/seyret-bul/admin/soru-uret rotası tarafından çağrılan eksik fonksiyondur.
    """
    
    # 1. Admin şifresi kontrolü 
    if admin_sifre != ADMIN_SIFRE:
        return {"success": False, "mesaj": "Admin şifresi hatalı."}

    # 2. Gemini modelini yapılandır
    try:
        # Flask'ın uygulamasından API key'i almayı dener.
        # Not: current_app, seyret_bul.py'nin en üstüne import edilmelidir.
        gemini_api_key = os.environ.get("GEMINI_API_KEY") or current_app.config.get('GEMINI_API_KEY')
        model = api_yapilandir(gemini_api_key) 
    except Exception:
        model = api_yapilandir(os.environ.get("GEMINI_API_KEY")) 
        
    if not model:
        return {"success": False, "mesaj": "Gemini API anahtarı ayarlanmamış veya model yüklenemedi. (Lütfen anahtarınızı kontrol edin)."}
    
    # 3. Prompt oluştur
    prompt = soru_uretme_promptu_olustur(video_metni)
    
    # 4. API çağrısı ve JSON alma
    try:
        response = model.generate_content(prompt, request_options={'timeout': 90})
        soru_json = json_parse_et(response.text) 
    except Exception as e:
        hata_mesaji = str(e)
        if "response.prompt_feedback" in hata_mesaji:
            hata_mesajik = "Gemini güvenlik filtrelerine takıldı. Metni düzenleyin."
        elif "DeadlineExceeded" in hata_mesaji:
             hata_mesajik = "API isteği zaman aşımına uğradı. Tekrar deneyin."
        else:
             hata_mesajik = str(e)
             
        return {"success": False, "mesaj": f"Gemini API çağrısı hatası: {hata_mesajik}"}
    
    if not soru_json or 'sorular' not in soru_json or not isinstance(soru_json['sorular'], list):
        return {"success": False, "mesaj": "Gemini yanıtı işlenemedi (JSON formatı hatalı)."}

    # 5. Kayıt verisini hazırla (SQL İÇİN)
    video_id = video_id_olustur()
    # Thumbnail URL'sini oluştur
    thumbnail_url = ""
    if "youtube.com" in video_url or "youtu.be" in video_url:
        thumbnail_url = video_url.replace("watch?v=", "embed/").split('&')[0].replace("youtube.com/", "img.youtube.com/vi/") + "/mqdefault.jpg"

    # SQL veritabanına uygun sözlük yapısı
    db_data = {
        "video_id": video_id,
        "surec_bileseni": surec_bileseni,
        "baslik": baslik,
        "video_url": video_url, # db_helper'da bu alanın adı video_url
        "thumbnail_url": thumbnail_url,
        "sure_saniye": video_sure_saniye,
        "sorular_json": json.dumps(soru_json['sorular'], ensure_ascii=False) # Listeyi JSON string'e çevir
    }

    # 6. Doğrudan SQL'e Kaydet (Eski yöntemi kullanma)
    if db_helper.save_video(db_data):
        return {"success": True, "mesaj": "Sorular başarıyla üretildi ve veritabanına kaydedildi.", "video_id": video_id}
    else:
        return {"success": False, "mesaj": "Veritabanı kayıt hatası."}

def get_video_duration(video_path):
    """Lokal videonun süresini saniye cinsinden döndürür"""
    try:
        clip = VideoFileClip(video_path)
        duration = int(clip.duration)
        clip.close()
        return duration
    except Exception as e:
        print(f"Video süresi alınamadı: {e}")
        return 0
        
# --- TEST BÖLÜMÜ ---
if __name__ == "__main__":
    print("=" * 70)
    print("Maarif Modeli Seyret Bul Aracı - Test Modu (v2 - Yeni JSON Uyumlu)")
    print("=" * 70)
    print("NOT: Bu modül sosyallab.py tarafından import edilecektir.")
    print("Gerçek kullanım için Gemini API anahtarı gereklidir.")
    print("=" * 70)
