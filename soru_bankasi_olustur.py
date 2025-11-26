import google.generativeai as genai
import json
import os
import re
import time

# --- 1. AYAR ---
# LÜTFEN 'sosyallab.py' dosyanızdan API anahtarınızı kopyalayıp buraya yapıştırın
GEMINI_API_KEY = "AIzaSyAi5gR1RQaWihbfRstFP381glOYKbMerIU"

# --- 1B. YENİ AYAR: Çıktı Dosyası ---
OUTPUT_FILE = "bireysel_soru_bankasi.json"

# --- 2. MÜFREDAT ---
PODCAST_CURRICULUM_DATA = """
Süreç Bileşenleri:
SB.5.1.1. Dâhil olduğu gruplar ve bu gruplardaki rolleri arasındaki ilişkileri çözümleyebilme
SB.5.1.2. Kültürel özelliklere saygı duymanın birlikte yaşamaya etkisini yorumlayabilme
SB.5.1.3. Toplumsal birliği sürdürmeye yönelik yardımlaşma ve dayanışma faaliyetlerine katkı sağlayabilme
SB.5.2.1. Yaşadığı ilin göreceli konum özelliklerini belirleyebilme
SB.5.2.2. Yaşadığı ilde doğal ve beşerî çevredeki değişimi neden ve sonuçlarıyla yorumlayabilme
SB.5.2.3. Yaşadığı ilde meydana gelebilecek afetlerin etkilerini azaltmaya yönelik farkındalık etkinlikleri düzenleyebilme
SB.5.2.4. Ülkemize komşu devletler hakkında bilgi toplayabilme
SB.5.3.1. Yaşadığı ildeki ortak miras ögelerine ilişkin oluşturduğu ürünü paylaşabilme
SB.5.3.2. Anadolu’da ilk yerleşimleri kuran toplumların sosyal hayatlarına yönelik bakış açısı geliştirebilme
SB.5.3.3. Mezopotamya ve Anadolu medeniyetlerinin ortak mirasa katkılarını karşılaştırabilme
SB.5.4.1. Demokrasi ve cumhuriyet kavramları arasındaki ilişkiyi çözümleyebilme
SB.5.4.2. Toplum düzenine etkisi bakımından etkin vatandaş olmanın önemine yönelik çıkarımda bulunabilme
SB.5.4.3. Temel insan hak ve sorumluluklarının önemini sorgulayabilme
SB.5.4.4. Bir ihtiyaç hâlinde veya sorun karşısında başvuru yapılabilecek kurumlar hakkında başvuru yapılabilecek kurumlar hakkında bilgi toplayabilme
SB.5.5.1. Kaynakları verimli kullanmanın doğa ve insanlar üzerindeki etkisini yorumlayabilme
SB.5.5.2. İhtiyaç ve isteklerini karşılamak için gerekli bütçeyi planlayabilme
SB.5.5.3. Yaşadığı ildeki ekonomik faaliyetleri özetleyebilme
SB.5.6.1.Teknolojik gelişmelerin toplum hayatına etkilerini tartışabilme
SB.5.6.2. Teknolojik ürünlerin bilinçli kullanımının önemine ilişkin ürün oluşturabilme

Öğrenme Alanları (Konular):
1. ÖĞRENME ALANI: BİRLİKTE YAŞAMAK (Gruplar, roller, haklar, sorumluluklar, kültür, yardımlaşma)
2. ÖĞRENME ALANI: EVİMİZ DÜNYA (Konum, doğal ve beşerî çevre, afetler, komşu devletler)
3. ÖĞRENME ALANI: ORTAK MİRASIMIZ (Ortak miras, Anadolu ve Mezopotamya medeniyetleri)
4. ÖĞRENME ALANI: YAŞAYAN DEMOKRASİMİZ (Demokrasi, cumhuriyet, etkin vatandaş, hak ve sorumluluklar, kurumlar)
5. ÖĞRENME ALANI: HAYATIMIZDAKİ EKONOMİ (Kaynak verimliliği, bütçe, ekonomik faaliyetler)
6. ÖĞRENME ALANI: TEKNOLOJİ ve SOSYAL BİLİMLER (Teknolojik gelişmelerin etkileri, bilinçli kullanım)
"""

# --- 3. PROMPT (Değişiklik yok) ---
def _create_bireysel_yarisma_prompt():
    """Gemini için 10 soruluk (3K, 4O, 3Z) paket prompt'u hazırlar."""
    return f"""
    GÖREV: Sen 5. Sınıf Sosyal Bilgiler (11-13 yaş) için uzman bir içerik üreticisisin.
    Aşağıdaki müfredatı ve kuralları kullanarak 10 soruluk bir yarışma paketi hazırla.

    MÜFREDAT BİLGİSİ (ZORUNLU İLHAM KAYNAĞI):
    ---
    {PODCAST_CURRICULUM_DATA}
    ---

    KURALLAR (ZORUNLU):
    1.  **Beceri/Değer Üret:** Her soru için, müfredattan ilham alarak BASİT ve ANLAŞILIR bir "beceri_adi" (örn: Sorumluluk) ve "deger_adi" (örn: Yardımlaşma) üret.
    2.  **Metin Oluştur:** Bu beceri ve değere uygun, 90-120 kelimelik bir metin yaz.
    3.  **Cümle Bul:** Metinden, beceriyi ve değeri kanıtlayan tam cümleleri ayıkla.
    4.  **Zorluk Belirle:** Her soru seti için "kolay", "orta" veya "zor" şeklinde bir zorluk seviyesi belirle.
    5.  **Paket Oluştur:** Toplam 10 soru üret. Paket ZORUNLU olarak şunları içermelidir:
        - 3 adet "kolay" soru
        - 4 adet "orta" soru
        - 3 adet "zor" soru

    ÇIKTI FORMATI (SADECE JSON, başka hiçbir metin ekleme):
    {{
      "soru_paketi": [
        {{ "zorluk": "kolay", "metin": "...", "beceri_adi": "...", "deger_adi": "...", "beceri_cumlesi": "...", "deger_cumlesi": "..." }},
        ... (toplam 10 soru)
      ]
    }}
    """

# --- 4. YARDIMCI FONKSİYONLAR (Akıllı Kayıt) ---
def load_existing_bank():
    """Mevcut bankayı yükler (kaldığı yerden devam etmek için)."""
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            print(f"Uyarı: '{OUTPUT_FILE}' bulundu ama okunamadı. Sıfırdan başlanıyor.")
            return []
    return []

def save_to_bank(soru_listesi):
    """Listeyi JSON dosyasına kaydeder."""
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(soru_listesi, f, ensure_ascii=False, indent=4)
        print(f"Başarılı! Banka '{OUTPUT_FILE}' dosyasına kaydedildi. (Toplam {len(soru_listesi)} soru)")
    except Exception as e:
        print(f"HATA: Dosyaya yazma hatası: {e}")

# --- 5. ANA ÇALIŞTIRICI (Daha Akıllı ve Sabırlı) ---
def main():
    if GEMINI_API_KEY == "BURAYA_sosyallab.py_DOSYANIZDAKİ_API_ANAHTARINI_YAPIŞTIRIN" or GEMINI_API_KEY == "":
        print("HATA: Lütfen betiğin 11. satırındaki 'GEMINI_API_KEY' değişkenini güncelleyin.")
        return

    print("Soru Bankası Oluşturucu Başlatıldı...")
    print(f"API Anahtarı bulundu: ...{GEMINI_API_KEY[-4:]}")
    
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('models/gemini-pro-latest')
    
    # Kaldığı yerden devam etmek için mevcut soruları yükle
    master_soru_listesi = load_existing_bank()
    print(f"Mevcut soru bankasında {len(master_soru_listesi)} soru bulundu.")
    
    HEDEF_SORU_SAYISI = 100
    
    kac_soru_lazim = HEDEF_SORU_SAYISI - len(master_soru_listesi)
    
    if kac_soru_lazim <= 0:
        print(f"Banka zaten {HEDEF_SORU_SAYISI} veya daha fazla soruya sahip. İşlem tamamlandı.")
        return
        
    # Her pakette 10 soru var. Kaç paket daha lazım? (Yukarı yuvarla)
    kac_paket_lazim = (kac_soru_lazim + 9) // 10 
    print(f"{kac_soru_lazim} soru daha gerekiyor. {kac_paket_lazim} paket istenecek...")
    
    for i in range(kac_paket_lazim):
        print(f"\n--- Paket {i+1} / {kac_paket_lazim} isteniyor ---")
        try:
            prompt = _create_bireysel_yarisma_prompt()
            
            # API çağrısı
            response = model.generate_content(prompt, request_options={'timeout': 120})
            
            # Gelen JSON'u ayrıştır
            match = re.search(r"```json\s*(\{.*\})\s*```", response.text, re.DOTALL)
            if match:
                json_text = match.group(1)
            else:
                json_text = response.text.strip()
                
            data = json.loads(json_text)
            
            soru_paketi = data.get("soru_paketi", [])
            
            if len(soru_paketi) > 0:
                master_soru_listesi.extend(soru_paketi)
                print(f"Başarılı! {len(soru_paketi)} soru eklendi.")
                
                # --- GÜNCELLEME: Her paketten sonra ilerlemeyi kaydet ---
                save_to_bank(master_soru_listesi)
            else:
                print(f"UYARI: Gemini'den beklenen soru paketi gelmedi (boş yanıt).")
                
            # --- GÜNCELLEME: Bekleme süresi 65 saniyeye çıkarıldı ---
            if i < kac_paket_lazim - 1:
                print("Kota limitine (dakikada 2 istek) takılmamak için 65 saniye bekleniyor...")
                time.sleep(65)
                
        except Exception as e:
            print(f"HATA (Paket {i+1}): {e}")
            print("İşlem durduruldu. API anahtarınızı veya internet bağlantınızı kontrol edin.")
            if "DeadlineExceeded" in str(e):
                print("TAVSİYE: API zaman aşımına uğradı. 120 saniyeden uzun sürdü.")
            if "quota" in str(e).lower():
                print("TAVSİYE: API kotasını aştınız. Lütfen 1-2 dakika bekleyip betiği TEKRAR ÇALIŞTIRIN.")
            return # Hata durumunda işlemi durdur
            
    # Döngü bittiğinde
    print(f"\n--- İŞLEM TAMAMLANDI ---")
    print(f"Toplam {len(master_soru_listesi)} soru '{OUTPUT_FILE}' dosyasına başarıyla kaydedildi.")
    print("Artık sosyallab.py sunucusunu çalıştırabilirsiniz.")

if __name__ == "__main__":
    main()