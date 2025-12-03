# -*- coding: utf-8 -*-
"""
Maarif Modeli Metin Analiz Aracı
5. Sınıf Sosyal Bilgiler için Gemini API ile metin analizi
"""

import google.generativeai as genai
import json
import os
import re

# --- LİMİT SİSTEMİ İÇİN DOSYA ---
LIMIT_FILE = "metin_analiz_limitleri.json"
# --- 5. SINIF SOSYAL BİLGİLER MÜFREDAT VERİSİ (Podcast Modülünden Kopyalandı) ---
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
6. ÖĞRENME ALANI: TEKNOLOJİ ve SOSYAL BİLMİLER (Teknolojik gelişmelerin etkileri, bilinçli kullanım)
"""
# --- BİTTİ ---


def api_yapilandir(api_key):
    """Gemini API'yi yapılandırır"""
    # Şifreyi dışarıdan gelen yerine direkt Render'dan (Environment) alıyoruz:
    guvenli_anahtar = os.getenv('GOOGLE_API_KEY')
    
    if guvenli_anahtar:
        genai.configure(api_key=guvenli_anahtar)
        
        # ESKİSİ: return genai.GenerativeModel('models/gemini-pro')
        # YENİSİ (Hızlı ve Yüksek Kota):
        print("✅ Metin Analiz Modeli yapılandırıldı: models/gemini-2.0-flash")
        return genai.GenerativeModel('models/gemini-2.0-flash')
        
    print("❌ API Anahtarı bulunamadı!")
    return None

# --- SÜREÇ BİLEŞENLERİ VE METİN TİPLERİ ---
SURECLER = {
    "SB.5.1.1.": {
        "aciklama": "Dâhil olduğu gruplar ve bu gruplardaki rolleri arasındaki ilişkileri çözümleyebilme",
        "metin_tipleri": ["Örnek Olay (Senaryo)", "Tanımlayıcı Metin (Kavramsal)"]
    },
    "SB.5.1.2.": {
        "aciklama": "Kültürel özelliklere saygı duymanın birlikte yaşamaya etkisini yorumlayabilme",
        "metin_tipleri": ["Tanıtıcı Metin (Merhaba, ben...)", "Haber Metni (Kültürel Etkileşim)"]
    },
    "SB.5.1.3.": {
        "aciklama": "Toplumsal birliği sürdürmeye yönelik yardımlaşma ve dayanışma",
        "metin_tipleri": ["Detaylı Proje Anlatısı", "Tarihsel Bilgi/Örnek"]
    },
    "SB.5.2.1.": {
        "aciklama": "Yaşadığı ilin göreceli konum özelliklerini belirleyebilme",
        "metin_tipleri": ["Betimleyici Bilmece (Ben Hangi İlim?)"]
    },
    "SB.5.2.2.": {
        "aciklama": "Yaşadığı ilde doğal ve beşerî çevredeki değişimi neden ve sonuçlarıyla yorumlayabilme",
        "metin_tipleri": ["Diyalog / Anı (Karşılaştırmalı)", "Örnek Olay (Neden-Sonuç)"]
    },
    "SB.5.2.3.": {
        "aciklama": "Yaşadığı ilde meydana gelebilecek afetlerin etkilerini azaltmaya yönelik farkındalık etkinlikleri düzenleyebilme",
        "metin_tipleri": ["Tanımlayıcı Bilgi Metni (Risk/Afet)", "Deney/Proje Anlatısı"]
    },
    "SB.5.2.4.": {
        "aciklama": "Ülkemize komşu devletler hakkında bilgi toplayabilme",
        "metin_tipleri": ["Tanıtıcı Bilgi Kartı (Komşu Ülke)"]
    },
    "SB.5.3.1.": {
        "aciklama": "Yaşadığı ildeki ortak miras ögelerine ilişkin oluşturduğu ürünü paylaşabilme",
        "metin_tipleri": ["Tanımlayıcı Bilgi Metni (Kavramsal)"]
    },
    "SB.5.3.2.": {
        "aciklama": "Anadolu'da ilk yerleşimleri kuran toplumların sosyal hayatlarına yönelik bakış açısı geliştirebilme",
        "metin_tipleri": ["Tanımlayıcı/Betimleyici Metin (İlk Yerleşim Yeri)"]
    },
    "SB.5.3.3.": {
        "aciklama": "Mezopotamya ve Anadolu medeniyetlerinin ortak mirasa katkılarını karşılaştırabilme",
        "metin_tipleri": ["Medeniyet Tanıtımı (Katkı Odaklı)", "Karşılaştırmalı Bilgi Metni (Hukuk)"]
    },
    "SB.5.4.1.": {
        "aciklama": "Demokrasi ve cumhuriyet kavramları arasındaki ilişkiyi çözümleyebilme",
        "metin_tipleri": ["Tanımlayıcı Bilgi Metni (Kavramsal İlişki)"]
    },
    "SB.5.4.2.": {
        "aciklama": "Toplum düzenine etkisi bakımından etkin vatandaş olmanın önemine yönelik çıkarımda bulunabilme",
        "metin_tipleri": ["Haber Metni (Etkin Vatandaşlık Uygulaması)"]
    },
    "SB.5.4.3.": {
        "aciklama": "Temel insan hak ve sorumluluklarının önemini sorgulayabilme",
        "metin_tipleri": ["Örnek Olay (Çatışan Haklar)", "Haber Metni (Hak İhlali/Koruma)"]
    },
    "SB.5.4.4.": {
        "aciklama": "Bir ihtiyaç hâlinde veya sorun karşısında başvuru yapılabilecek kurumlar hakkında bilgi toplayabilme",
        "metin_tipleri": ["Tanıtıcı Bilgi Metni (Kurum Görevleri)", "Dilekçe Örneği"]
    },
    "SB.5.5.1.": {
        "aciklama": "Kaynakları verimli kullanmanın doğa ve insanlar üzerindeki etkisini yorumlayabilme",
        "metin_tipleri": ["Liste / Bilgi Metni (Tasarruf Yöntemleri)", "Haber Metni (Tasarruf Başarısı)"]
    },
    "SB.5.5.2.": {
        "aciklama": "İhtiyaç ve isteklerini karşılamak için gerekli bütçeyi planlayabilme",
        "metin_tipleri": ["Tanıtıcı Bilgi Metni (İhtiyaç vs. İstek)", "Örnek Olay (Bütçe Planlaması)"]
    },
    "SB.5.5.3.": {
        "aciklama": "Yaşadığı ildeki ekonomik faaliyetleri özetleyebilme",
        "metin_tipleri": ["Tanıtıcı Bilgi Metni (Ekonomik Faaliyet Türü)", "Örnek Metin (İl ve Faaliyet İlişkisi)"]
    },
    "SB.5.6.1.": {
        "aciklama": "Teknolojik gelişmelerin toplum hayatına etkilerini tartışabilme",
        "metin_tipleri": ["Haber Metni (Olumlu/Olumsuz Etki)", "Karşılaştırmalı Uzman Görüşü"]
    },
    "SB.5.6.2.": {
        "aciklama": "Teknolojik ürünlerin bilinçli kullanımının önemine ilişkin ürün oluşturabilme",
        "metin_tipleri": ["Örnek Olay (Dijital Güvenlik Hatası)", "Bilgi Notu (Kavramsal)"]
    }
}

# --- BECERİLER ---
BECERILER = {
    "alan_becerileri": [
        "Mekânı algılama",
        "Zaman ve kronolojiyi algılama",
        "Değişim ve sürekliliği algılama",
        "Kanıt kullanma",
        "Sosyal katılım",
        "Empati",
        "Harita okuryazarlığı",
        "Konum analizi",
        "Çevre okuryazarlığı",
        "Gözlem",
        "Politik okuryazarlık",
        "Ekonomik okuryazarlığı",
        "Hukuk okuryazarlığı"
    ],
    "kavramsal_beceriler": [
        "Eleştirel düşünme",
        "Yaratıcı düşünme",
        "Problem çözme",
        "Karar verme",
        "Araştırma",
        "Bilgi okuryazarlığı",
        "Medya okuryazarlığı",
        "Değişim ve sürekliliği algılama",
        "Sebep-sonuç ilişkisi kurma",
        "Kanıt kullanma",
        "Sorgulama"
    ],
    "sosyal_duygusal_beceriler": [
        "Empati",
        "İşbirliği",
        "Sorumluluk",
        "Saygı",
        "Hoşgörü",
        "Çatışma çözme",
        "İletişim",
        "Sosyal katılım",
        "Öz denetim",
        "Öz güven",
        "Dayanışma",
        "Duyarlılık"
    ]
}

# --- DEĞERLER ---
DEGERLER = [
    "Adalet",
    "Aile birliğine önem verme",
    "Bağımsızlık",
    "Barış",
    "Bilimsellik",
    "Çalışkanlık",
    "Dayanışma",
    "Duyarlılık",
    "Dürüstlük",
    "Estetik",
    "Özgürlük",
    "Saygı",
    "Sevgi",
    "Sorumluluk",
    "Tasarruf",
    "Vatanseverlik",
    "Yardımseverlik"
]

# --- LİMİT SİSTEMİ FONKSİYONLARI ---

def limitleri_yukle():
    """Analiz limitlerini JSON dosyasından yükler"""
    if os.path.exists(LIMIT_FILE):
        try:
            with open(LIMIT_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def limitleri_kaydet(limitler):
    """Analiz limitlerini JSON dosyasına kaydeder"""
    try:
        with open(LIMIT_FILE, 'w', encoding='utf-8') as f:
            json.dump(limitler, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Limit kaydetme hatası: {e}")

def limit_kontrol(student_no):
    """
    Öğrencinin kalan analiz hakkını kontrol eder
    Returns: dict {"izin": bool, "kalan": int, "mesaj": str}
    """
    limitler = limitleri_yukle()
    kullanilan = limitler.get(str(student_no), 0)
    kalan = 2 - kullanilan
    
    if kalan <= 0:
        return {
            "izin": False,
            "kalan": 0,
            "mesaj": "⚠️ Analiz hakkınız dolmuştur! Maksimum 2 metin analizi yapabilirsiniz."
        }
    
    return {
        "izin": True,
        "kalan": kalan,
        "mesaj": f"✅ Kalan analiz hakkınız: {kalan}"
    }

def limit_artir(student_no):
    """Öğrencinin kullanılan analiz sayısını 1 artırır"""
    limitler = limitleri_yukle()
    student_no = str(student_no)
    limitler[student_no] = limitler.get(student_no, 0) + 1
    limitleri_kaydet(limitler)

# --- YARDIMCI FONKSİYONLAR ---

def kelime_sayisi_hesapla(metin):
    """Metindeki kelime sayısını hesaplar"""
    return len(metin.split())

def json_parse_et(api_yaniti):
    """API yanıtından JSON çıkarır ve parse eder"""
    try:
        # JSON bloğunu bul
        json_match = re.search(r'\{.*\}', api_yaniti, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            return json.loads(json_str)
        
        # Eğer direkt JSON ise
        return json.loads(api_yaniti)
    except:
        return None

# --- PROMPT OLUŞTURMA ---

def analiz_prompt_olustur(metin):
    """Gemini API için analiz promptu oluşturur"""
    
    # Süreç bileşenlerini listeye çevir
    surecler_listesi = []
    for kod, bilgi in SURECLER.items():
        surecler_listesi.append(f"{kod}: {bilgi['aciklama']}")
    
    # Tüm metin tiplerini topla
    metin_tipleri_set = set()
    for bilgi in SURECLER.values():
        metin_tipleri_set.update(bilgi['metin_tipleri'])
    metin_tipleri_listesi = list(metin_tipleri_set)
    
    prompt = f"""
Sen bir 5. Sınıf Sosyal Bilgiler uzmanısın. Sana verilen metni analiz edeceksin.

ANALİZ YAPILACAK METİN:
"{metin}"

GÖREV:
Bu metni aşağıdaki kriterlere göre analiz et ve JSON formatında sonuç döndür.

1. SEVİYE UYGUNLUĞU:
   - Metin 5. sınıf (11-13 yaş) seviyesine uygun mu?
   - Kelime seçimi, cümle yapısı ve kavramlar bu yaşa uygun mu?
   - Cevap: "uygun", "kolay", "zor" olarak belirt ve kısa açıklama yap.

2. SÜREÇ BİLEŞENİ:
   Metin aşağıdaki süreç bileşenlerinden hangisine en uygun? (1-3 tane seç, uygunluk yüzdesi ver)
   
   SÜREÇ BİLEŞENLERİ:
   {chr(10).join(surecler_listesi)}

3. METİN TİPİ:
   Metin aşağıdaki metin tiplerinden hangisine uygun?
   
   METİN TİPLERİ:
   {', '.join(metin_tipleri_listesi)}

4. BECERİLER:
   Metinde aşağıdaki becerilerden hangileri var? (Her kategoriden en fazla 5 tane seç)
   
   ALAN BECERİLERİ: {', '.join(BECERILER['alan_becerileri'])}
   KAVRAMSAL BECERİLER: {', '.join(BECERILER['kavramsal_beceriler'])}
   SOSYAL-DUYGUSAL BECERİLER: {', '.join(BECERILER['sosyal_duygusal_beceriler'])}

5. DEĞERLER:
   Metinde aşağıdaki değerlerden hangileri vurgulanıyor? (En fazla 5 tane seç)
   
   DEĞERLER: {', '.join(DEGERLER)}

ÖNEMLİ: Yanıtını SADECE JSON formatında ver. Başka açıklama ekleme.

JSON FORMATI:
{{
  "seviye_uygunluk": {{
    "durum": "uygun/kolay/zor",
    "aciklama": "Kısa açıklama (max 1 cümle)"
  }},
  "surec_bilesenleri": [
    {{
      "kod": "SB.5.X.X.",
      "aciklama": "Bileşen açıklaması",
      "uygunluk_yuzdesi": 85
    }}
  ],
  "metin_tipi": "Metin tipi adı",
  "beceriler": {{
    "alan": ["beceri1", "beceri2"],
    "kavramsal": ["beceri1", "beceri2"],
    "sosyal_duygusal": ["beceri1", "beceri2"]
  }},
  "degerler": ["değer1", "değer2", "değer3"]
}}
"""
    return prompt

# --- METİN UYGUNLUK KONTROLÜ FONKSİYONLARI (Podcast Modülünden Kopyalandı) ---

def _create_podcast_validation_prompt(user_text):
    """Metnin müfredata uygunluğunu denetlemek için Gemini prompt'u hazırlar (v2 - Bileşen listesi ister)."""
    return f"""
    Görevin, bir 5. Sınıf Sosyal Bilgiler müfredat uzmanı olarak, bir metnin bu müfredatla ne kadar ilgili olduğunu analiz etmektir.

    AŞAĞIDAKİ MÜFREDAT BİLGİSİNİ KULLAN:
    ---
    {PODCAST_CURRICULUM_DATA}
    ---

    ANALİZ EDİLECEK METİN:
    ---
    {user_text}
    ---

    GÖREV:
    1.  Metnin, sağlanan 5. Sınıf Sosyal Bilgiler müfredatıyla (hem süreç bileşenleri hem de öğrenme alanları) ne kadar ilgili olduğunu 0 ile 100 arasında bir yüzde ile derecelendir.
    2.  Eğer uygunluk %70'in altındaysa:
        - "aciklama" alanına neden 5. sınıf Sosyal Bilgiler konusuyla ilgisiz olduğuna dair KISA bir açıklama yap.
        - "uyumlu_bilesenler" alanını boş bir dizi [] olarak bırak.
    3.  Eğer uygunluk %70 veya üzerindeyse:
        - "aciklama" alanına "Metin 5. Sınıf Sosyal Bilgiler müfredatıyla uyumludur." yaz.
        - "uyumlu_bilesenler" alanına, metnin DOĞRUDAN ilgili olduğu süreç bileşeni KODLARINI (örn: "SB.5.1.1") içeren bir dizi (array) ekle.
    4.  Yanıtını SADECE aşağıdaki JSON formatında ver, başka HİÇBİR ŞEY yazma.

    JSON FORMATI (Başarılıysa):
    {{
      "uygunluk_yuzdesi": 85,
      "aciklama": "Metin 5. Sınıf Sosyal Bilgiler müfredatıyla uyumludur.",
      "uyumlu_bilesenler": ["SB.5.3.2", "SB.5.3.3"]
    }}

    JSON FORMATI (Başarısızsa):
    {{
      "uygunluk_yuzdesi": 30,
      "aciklama": "Bu metin daha çok Fen Bilimleri konusudur.",
      "uyumlu_bilesenler": []
    }}
    ---
    JSON ÇIKTIN:
    """

def validate_text_relevance(user_text, model):
    """Metnin müfredata uygunluğunu Gemini ile kontrol eder (v2 - Bileşen listesi alır)."""
    try:
        prompt = _create_podcast_validation_prompt(user_text)
        
        # --- DÜZELTME: ÇİFT {{}} TEK {} OLDU ---
        response = model.generate_content(prompt, request_options={'timeout': 45}) 
        
        # JSON'u ayrıştır
        try:
            match = re.search(r"```json\s*(\{.*\})\s*```", response.text, re.DOTALL)
            if match:
                json_text = match.group(1)
            else:
                json_text = response.text.strip()
            gemini_json = json.loads(json_text)
        except Exception as json_err:
            print(f"Podcast JSON Ayrıştırma Hatası: {json_err} - Yanıt: {response.text}")
            # --- DÜZELTME: ÇİFT {{}} TEK {} OLDU ---
            return {"success": False, "error": f"Gemini'den gelen analiz yanıtı işlenemedi."}

        yuzde = gemini_json.get("uygunluk_yuzdesi")
        aciklama = gemini_json.get("aciklama")
        bilesenler_listesi = gemini_json.get("uyumlu_bilesenler", []) 
        
        if yuzde is None or aciklama is None:
            # --- DÜZELTME: ÇİFT {{}} TEK {} OLDU ---
            return {"success": False, "error": "Gemini analizinden eksik veri ('uygunluk_yuzdesi' veya 'aciklama') alındı."}
        
        # --- DÜZELTME: ÇİFT {{}} TEK {} OLDU ---
        return {
            "success": True, 
            "uygunluk_yuzdesi": int(yuzde), 
            "aciklama": aciklama,
            "uyumlu_bilesenler": bilesenler_listesi
        }

    except Exception as e:
        hata_mesaji = str(e)
        # --- DÜZELTME: 'hata_masaji' -> 'hata_mesaji' OLDU ---
        print(f"Podcast validasyon API hatası: {hata_mesaji}")
        # --- DÜZELTME: ÇİFT {{}} TEK {} ve 'hata_masaji' -> 'hata_mesaji' OLDU ---
        return {"success": False, "error": f"Gemini analiz API'sinde hata: {hata_mesaji}"}

# --- METİN UYGUNLUK KONTROLÜ BİTTİ ---

# --- ANA ANALİZ FONKSİYONU ---

def metin_analiz_et(metin, student_no, model):
    """
    Verilen metni Gemini API ile analiz eder
    
    Args:
        metin: Analiz edilecek metin (max 250 kelime)
        student_no: Öğrenci numarası
        model: Gemini model nesnesi
    
    Returns:
        dict: Analiz sonuçları
    """
    
    # 1. Kelime sayısı kontrolü
    kelime_sayisi = kelime_sayisi_hesapla(metin)
    if kelime_sayisi > 250:
        return {
            "success": False,
            "hata": f"❌ Metin çok uzun! Maksimum 250 kelime olmalı. (Şu an: {kelime_sayisi} kelime)",
            "kelime_sayisi": kelime_sayisi
        }
    
    # 2. Limit kontrolü
    limit_sonuc = limit_kontrol(student_no)
    if not limit_sonuc["izin"]:
        return {
            "success": False,
            "hata": limit_sonuc["mesaj"],
            "kalan_analiz_hakki": 0
        }
    
# 3. Model kontrolü
    if not model:
        return {
            "success": False,
            "hata": "❌ HATA: Gemini API yapılandırılmamış!"
        }
    
    # --- YENİ EKLENDİ: ADIM 3.5 - UYGUNLUK KONTROLÜ ---
    print("Metin Analiz: Metnin müfredata uygunluğu kontrol ediliyor...")
    validation_result = validate_text_relevance(metin, model)

    if not validation_result.get("success"):
        # Analiz API'sinde bir hata oldu (JSON parse vb.)
        return {
            "success": False,
            "hata": f"❌ Uygunluk analizi hatası: {validation_result.get('error')}"
        }

    uygunluk_yuzdesi = validation_result.get("uygunluk_yuzdesi", 0)
    aciklama = validation_result.get("aciklama", "Açıklama yok.")

    if uygunluk_yuzdesi < 70:
        print(f"Metin Analiz: Metin reddedildi. Uygunluk: {uygunluk_yuzdesi}%")
        # Metin uygun değil, analiz etme.
        return {
            "success": False, 
            "hata": f"Metin Reddedildi (Uygunluk: {uygunluk_yuzdesi}%). \n\nAçıklama: {aciklama}"
        }

    print(f"Metin Analiz: Metin onaylandı. (Uygunluk: {uygunluk_yuzdesi}%)")
    # --- UYGUNLUK KONTROLÜ BİTTİ ---
    
    # 4. Prompt oluştur
    prompt = analiz_prompt_olustur(metin)
    
    # 5. API çağrısı
    try:
        response = model.generate_content(prompt, request_options={'timeout': 90})
        
        # 6. Yanıtı parse et
        parsed_data = json_parse_et(response.text)
        
        if not parsed_data:
            return {
                "success": False,
                "hata": "❌ API yanıtı işlenemedi. Lütfen tekrar deneyin.",
                "ham_yanit": response.text
            }
        
        # 7. Limit sayacını artır
        limit_artir(student_no)
        
        # 8. Sonuçları formatla ve döndür
        return {
            "success": True,
            "kelime_sayisi": kelime_sayisi,
            "seviye_uygunluk": parsed_data.get("seviye_uygunluk", {}),
            "surec_bilesenleri": parsed_data.get("surec_bilesenleri", []),
            "metin_tipi": parsed_data.get("metin_tipi", "Belirtilmedi"),
            "beceriler": parsed_data.get("beceriler", {}),
            "degerler": parsed_data.get("degerler", []),
            "kalan_analiz_hakki": limit_kontrol(student_no)["kalan"],
            "mesaj": "✅ Metin başarıyla analiz edildi!"
        }
        
    except Exception as e:
        hata_mesaji = str(e)
        
        # Hata mesajlarını daha anlaşılır hale getir
        if "response.prompt_feedback" in hata_mesaji:
            hata_mesaji = "❌ HATA: İçerik güvenlik filtrelerine takıldı. Lütfen metni kontrol edin."
        elif "DeadlineExceeded" in hata_mesaji:
            hata_mesaji = "❌ HATA: API zaman aşımına uğradı. Lütfen tekrar deneyin."
        
        return {
            "success": False,
            "hata": f"❌ Analiz hatası: {hata_mesaji}"
        }

# --- TEST BÖLÜMÜ ---
if __name__ == "__main__":
    print("=" * 60)
    print("Maarif Modeli Metin Analiz Aracı - Test Modu")
    print("=" * 60)
    
    # Örnek test metni (5. sınıf seviyesi, kültürel zenginlikler konusu)
    test_metni = """
    Türkiye, çok farklı kültürlerin bir arada yaşadığı güzel bir ülkedir. 
    Her bölgenin kendine özgü yemekleri, kıyafetleri ve gelenekleri vardır. 
    Doğu Anadolu'da çay kültürü çok önemlidir. İnsanlar misafirlerine 
    mutlaka çay ikram ederler. Ege Bölgesi'nde ise zeytinyağlı yemekler 
    meşhurdur. Karadeniz'de horon oyunu oynanır, Güneydoğu'da ise sıra 
    gecelerinde türküler söylenir. Bu farklılıklar ülkemizi zenginleştirir. 
    Birbirimizin kültürüne saygı gösterdiğimizde, huzur içinde birlikte 
    yaşarız. Kültürel farklılıklarımız bizim için bir zenginliktir.
    """
    
    print(f"\nTest Metni Kelime Sayısı: {kelime_sayisi_hesapla(test_metni)}")
    print(f"\nÖğrenci: 12345")
    
    # Limit kontrolü
    limit_durumu = limit_kontrol("12345")
    print(f"Limit Durumu: {limit_durumu['mesaj']}")
    
    print("\n" + "=" * 60)
    print("NOT: Bu modül sosyallab.py tarafından import edilecektir.")
    print("Gerçek kullanım için Gemini API anahtarı gereklidir.")
    print("=" * 60)
