# -*- coding: utf-8 -*-
"""
Bireysel Yarışma Modülü (SÜRÜM 8 - STATİK SORU BANKASI)
- Tüm soruları 'bireysel_soru_bankasi.json' dosyasından okur.
- Gemini API ÇAĞIRMAZ. (Hızlı ve kotasız)
- Oyunları 'aktif_bireysel_oyunlar' hafızasında (RAM) tutar.
"""

import json
import os
from datetime import datetime, timedelta
import random

# Aktif bireysel oyunları hafızada tutar
# Yapısı: { "student_no": {"sorular": [10 soruluk paket], "mevcut_soru_index": 0} }
aktif_bireysel_oyunlar = {}

# Skorların tutulduğu dosya
DB_BIREYSEL_FILE = 'bireysel_skorlar.json'
# 100 sorunun tutulduğu dosya
SORU_BANKASI_FILE = 'bireysel_soru_bankasi.json'

# --- Soru Bankası Yönetimi ---

def load_soru_bankasi():
    """100 soruluk ana bankayı JSON'dan yükler."""
    if not os.path.exists(SORU_BANKASI_FILE):
        print(f"HATA: '{SORU_BANKASI_FILE}' bulunamadı!")
        return {"kolay": [], "orta": [], "zor": []}
    
    try:
        with open(SORU_BANKASI_FILE, 'r', encoding='utf-8') as f:
            sorular = json.load(f)
        
        # Soruları zorluk seviyesine göre ayır
        banka = {
            "kolay": [s for s in sorular if s.get('zorluk') == 'kolay'],
            "orta": [s for s in sorular if s.get('zorluk') == 'orta'],
            "zor": [s for s in sorular if s.get('zorluk') == 'zor']
        }
        print(f"Soru Bankası yüklendi: {len(banka['kolay'])} Kolay, {len(banka['orta'])} Orta, {len(banka['zor'])} Zor soru.")
        return banka
    except Exception as e:
        print(f"Soru bankası yüklenirken hata: {e}")
        return {"kolay": [], "orta": [], "zor": []}

# 100 soruluk bankayı sunucu başlarken BİR KEZ hafızaya yükle
SORU_BANKASI = load_soru_bankasi()

def _create_10_question_pack():
    """
    Soru bankasından 3 Kolay, 4 Orta, 3 Zor soru seçerek
    rastgele 10 soruluk bir oyun paketi oluşturur.
    """
    try:
        kolay_secim = random.sample(SORU_BANKASI["kolay"], 3)
        orta_secim = random.sample(SORU_BANKASI["orta"], 4)
        zor_secim = random.sample(SORU_BANKASI["zor"], 3)
        
        # Paket her zaman Kolay -> Orta -> Zor sırasıyla gider
        return kolay_secim + orta_secim + zor_secim
    except ValueError:
        # Bankada yeterli soru yoksa (örn: test için 3 soru eklendiyse)
        # olanların hepsini döndür
        print("UYARI: Bankada 3K-4O-3Z için yeterli soru yok. Olanlar kullanılıyor.")
        return SORU_BANKASI["kolay"] + SORU_BANKASI["orta"] + SORU_BANKASI["zor"]
    except Exception as e:
        print(f"10'luk paket oluşturma hatası: {e}")
        return []

# --- Skor Veritabanı Yönetimi ---

def load_bireysel_db():
    """Bireysel yarışma skorlarını PostgreSQL'den yükler."""
    import db_helper
    conn = db_helper.get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT student_no, dogru_soru_sayisi, toplam_sure_saniye, altin_rozet_tarihi, gunluk_elenme_sayisi, son_elenme_tarihi FROM bireysel_skorlar")
    rows = cur.fetchall()
    skorlar = {}
    for row in rows:
        student_no = row[0]
        cur.execute("SELECT rozet FROM ogrenci_rozetler WHERE student_no = %s", (student_no,))
        rozetler = [r[0] for r in cur.fetchall()]
        skorlar[student_no] = {
            "dogru_soru_sayisi": row[1],
            "toplam_sure_saniye": row[2],
            "rozetler": rozetler,
            "altin_rozet_tarihi": str(row[3]) if row[3] else None,
            "gunluk_elenme_sayisi": row[4] or 0,
            "son_elenme_tarihi": str(row[5]) if row[5] else None
        }
    cur.close()
    conn.close()
    return skorlar


def save_bireysel_db(data):
    """Bireysel yarışma skorlarını (JSON) kaydeder."""
    try:
        with open(DB_BIREYSEL_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Bireysel DB kaydetme hatası: {e}")

# --- Ana API Fonksiyonları (sosyallab.py tarafından çağrılır) ---

def get_ogrenci_durumu(student_no, model=None): # model artık kullanılmıyor
    """
    /basla tarafından çağrılır.
    Sadece yasakları kontrol eder. Artık Gemini'yi ÇAĞIRMAZ.
    """
    db = load_bireysel_db()
    durum = db.get(student_no, {})
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    if durum.get("son_elenme_tarihi") == today_str and durum.get("gunluk_elenme_sayisi", 0) >= 3:
        return {"success": False, "giris_yasakli": True, "mesaj": "Bugün 3 kez elendiğiniz için 24 saat boyunca yarışamazsınız."}
        
    if durum.get("altin_rozet_tarihi") == today_str:
        return {"success": False, "giris_yasakli": True, "mesaj": "Bugün 10 soruyu tamamlayıp Altın Rozet aldınız. 24 saat sonra tekrar yarışabilirsiniz."}

    # Öğrencinin veritabanındaki (skor) durumunu döndür
    return {
        "success": True,
        "giris_yasakli": False,
        "durum": {
            "dogru_soru_sayisi": durum.get("dogru_soru_sayisi", 0),
            "rozetler": durum.get("rozetler", []),
            "toplam_sure_saniye": durum.get("toplam_sure_saniye", 0)
        }
    }

def get_yeni_soru_from_gemini(model, student_no): # Adını koruyoruz, 'model' artık kullanılmıyor
    """
    /yeni_soru tarafından çağrılır.
    Artık Gemini'yi ÇAĞIRMAZ.
    Hafızadan (RAM) sıradaki soruyu anında (0.1sn) çeker.
    Eğer hafızada paket yoksa, bankadan yeni 10'luk paket oluşturur.
    """
    global aktif_bireysel_oyunlar
    
    # 1. Öğrencinin aktif oyunu hafızada yoksa, YENİ PAKET OLUŞTUR
    if student_no not in aktif_bireysel_oyunlar:
        print(f"[{student_no}] için Soru Bankasından yeni 10'luk paket oluşturuluyor...")
        yeni_paket = _create_10_question_pack()
        
        if not yeni_paket:
            return {"success": False, "data": {"metin": "Hata: Soru Bankası boş veya okunamıyor. Lütfen 'bireysel_soru_bankasi.json' dosyasını kontrol edin."}}
        
        aktif_bireysel_oyunlar[student_no] = {
            "sorular": yeni_paket,
            "mevcut_soru_index": 0
        }
    
    # 2. Öğrencinin oyununu ve sıradaki sorusunu al
    oyun = aktif_bireysel_oyunlar.get(student_no)
    soru_index = oyun["mevcut_soru_index"]
    
    if soru_index >= len(oyun["sorular"]):
        return {"success": False, "data": {"metin": "Tüm sorular bitti."}}
        
    siradaki_soru = oyun["sorular"][soru_index]
    
    # 3. Sadece gerekli 5 parçayı döndür
    soru_datasi = {
        "metin": siradaki_soru.get("metin"),
        "beceri_adi": siradaki_soru.get("beceri_adi"),
        "deger_adi": siradaki_soru.get("deger_adi"),
        "beceri_cumlesi": siradaki_soru.get("beceri_cumlesi"),
        "deger_cumlesi": siradaki_soru.get("deger_cumlesi")
    }
    
    return {"success": True, "data": soru_datasi}

def kaydet_soru_sonucu(student_no, soru_suresi_saniye):
    """
    Bir soru doğru cevaplandığında:
    1. Skoru DB'ye (json) yazar.
    2. Hafızadaki (RAM) oyunun index'ini 1 artırır.
    3. Eğer 10. soruysa, oyunu hafızadan siler.
    """
    global aktif_bireysel_oyunlar
    db = load_bireysel_db()
    durum = db.get(student_no, {
        "dogru_soru_sayisi": 0,
        "toplam_sure_saniye": 0,
        "rozetler": [],
        "gunluk_elenme_sayisi": 0
    })

    durum["dogru_soru_sayisi"] += 1
    durum["toplam_sure_saniye"] += soru_suresi_saniye
    
    # Rozetleri kontrol et (2-7-10 kuralı)
    yeni_rozet_mesaji = ""
    if durum["dogru_soru_sayisi"] == 10 and "altin" not in durum["rozetler"]:
        durum["rozetler"].append("altin")
        durum["altin_rozet_tarihi"] = datetime.now().strftime("%Y-%m-%d")
        yeni_rozet_mesaji = "MÜKEMMEL! ALTIN ROZET kazandınız! 24 saat dinlenebilirsiniz."
    elif durum["dogru_soru_sayisi"] == 7 and "gumus" not in durum["rozetler"]:
        durum["rozetler"].append("gumus")
        yeni_rozet_mesaji = "Harika! GÜMÜŞ ROZET kazandınız!"
    elif durum["dogru_soru_sayisi"] == 2 and "bronz" not in durum["rozetler"]:
        durum["rozetler"].append("bronz")
        yeni_rozet_mesaji = "Tebrikler! BRONZ ROZET kazandınız!"

    db[student_no] = durum
    save_bireysel_db(db)
    
    # Hafıza (RAM) Güncellemesi
    oyun = aktif_bireysel_oyunlar.get(student_no)
    if oyun:
        oyun["mevcut_soru_index"] += 1
        
        # 10 soruyu da bitirdiyse, oyunu hafızadan sil
        if oyun["mevcut_soru_index"] >= len(oyun["sorular"]):
            print(f"[{student_no}] 10 soruluk paketi tamamladı. Oyun hafızadan siliniyor.")
            del aktif_bireysel_oyunlar[student_no]
    
    return {
        "success": True,
        "yeni_dogru_sayisi": durum["dogru_soru_sayisi"],
        "rozet_sonucu": {
            "yeni_rozet": bool(yeni_rozet_mesaji),
            "mesaj": yeni_rozet_mesaji,
            "yeni_durum": durum
        }
    }

def kaydet_elenme_sonucu(student_no, harcanan_sure_saniye):
    """
    Öğrenci elendiğinde:
    1. Elenme sayısını DB'ye (json) yazar.
    2. PUANINI SIFIRLAR (İsteğiniz).
    3. Aktif oyunu hafızadan (RAM) siler.
    """
    global aktif_bireysel_oyunlar
    db = load_bireysel_db()
    durum = db.get(student_no, {
        "dogru_soru_sayisi": 0,
        "toplam_sure_saniye": 0,
        "rozetler": [],
        "gunluk_elenme_sayisi": 0
    })

    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # Günlük elenme sayacını güncelle
    if durum.get("son_elenme_tarihi") == today_str:
        durum["gunluk_elenme_sayisi"] = durum.get("gunluk_elenme_sayisi", 0) + 1
    else:
        durum["gunluk_elenme_sayisi"] = 1 # Günün ilk elenmesi
        durum["son_elenme_tarihi"] = today_str

    durum["toplam_sure_saniye"] += harcanan_sure_saniye
    
    # İSTEĞİNİZ: Elendiği için bu turdaki ilerlemesi (doğru soru sayısı) sıfırlanır.
    durum["dogru_soru_sayisi"] = 0

    db[student_no] = durum
    save_bireysel_db(db)

    # Hafıza (RAM) Güncellemesi: Elendiği için aktif oyunu sil
    if student_no in aktif_bireysel_oyunlar:
        print(f"[{student_no}] elendi. Oyun hafızadan siliniyor.")
        del aktif_bireysel_oyunlar[student_no]

    return {"success": True, "mesaj": "Elenme kaydedildi."}

def get_leaderboard(users_db, sinif_filtresi=None):
    """
    Ana 'users.json' ve 'bireysel_skorlar.json' veritabanlarını birleştirir,
    sıralar ve döndürür.
    """
    bireysel_db = load_bireysel_db()
    leaderboard = []

    for student_no, user_data in users_db.items():
        if user_data.get('role') != 'student':
            continue
            
        skor_data = bireysel_db.get(student_no)
        
        if sinif_filtresi and user_data.get('class') != sinif_filtresi:
            continue

        # Sadece en az 1 soru çözmüş olanları listeye ekle
        if skor_data and skor_data.get("dogru_soru_sayisi", 0) > 0:
            
            # (Sizdeki skor puanı hesaplamasını koruyoruz)
            skor_puani = skor_data.get("dogru_soru_sayisi", 0)
            if "altin" in skor_data.get("rozetler", []):
                skor_puani += 3000
            elif "gumus" in skor_data.get("rozetler", []):
                skor_puani += 2000
            elif "bronz" in skor_data.get("rozetler", []):
                skor_puani += 1000

            leaderboard.append({
                "student_no": student_no,
                "isim": user_data.get("first_name", ""),
                "soyisim": user_data.get("last_name", ""),
                "okul": user_data.get("school_name", "Bilinmiyor"),
                "sube": user_data.get('class', 'N/A'),
                "rozetler": " ".join([r.capitalize() for r in skor_data.get("rozetler", [])]),
                "dogru_soru": skor_data.get("dogru_soru_sayisi", 0),
                "toplam_sure": skor_data.get("toplam_sure_saniye", 0),
                "skor_puani": skor_puani
            })

    leaderboard.sort(key=lambda x: (x["skor_puani"], -x["toplam_sure"]), reverse=True)

    if sinif_filtresi:
        return leaderboard[:5] # Öğretmen için en iyi 5
    else:
        return leaderboard[:10] # Genel için en iyi 10