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
import db_helper

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

# --- JSON YERİNE VERİTABANINDAN BİLGİ ÇEKEN YENİ FONKSİYON ---
def get_student_db_status(student_no):
    """Öğrencinin puanını ve rozetlerini Veritabanından (SQL) çeker."""
    try:
        conn = db_helper.get_db_connection()
        cur = conn.cursor()
        
        # Puan ve Rozet bilgilerini al
        cur.execute("""
            SELECT dogru_soru_sayisi, toplam_sure_saniye, altin_rozet_tarihi, 
                   gunluk_elenme_sayisi, son_elenme_tarihi 
            FROM bireysel_skorlar WHERE student_no = %s
        """, (str(student_no),))
        row = cur.fetchone()
        
        cur.execute("SELECT rozet FROM ogrenci_rozetler WHERE student_no = %s", (str(student_no),))
        rozetler = [r[0] for r in cur.fetchall()]
        
        cur.close()
        conn.close()
        
        if row:
            return {
                "dogru_soru_sayisi": row[0] or 0,
                "toplam_sure_saniye": row[1] or 0,
                "altin_rozet_tarihi": str(row[2]) if row[2] else None,
                "gunluk_elenme_sayisi": row[3] or 0,
                "son_elenme_tarihi": str(row[4]) if row[4] else None,
                "rozetler": rozetler
            }
        else:
            return {"dogru_soru_sayisi": 0, "rozetler": [], "toplam_sure_saniye": 0}
    except Exception as e:
        print(f"DB Hatası: {e}")
        return {"dogru_soru_sayisi": 0, "rozetler": []}

# --- Ana API Fonksiyonları (sosyallab.py tarafından çağrılır) ---

def get_leaderboard(users_db, sinif_filtresi=None):
    """
    Liderlik tablosunu doğrudan VERİTABANINDAN (PostgreSQL) çeker.
    Artık JSON dosyasına bakmaz.
    """
    try:
        conn = db_helper.get_db_connection()
        cur = conn.cursor()
        
        # Kullanıcı bilgileriyle skorları birleştir (SQL JOIN işlemi)
        query = """
            SELECT u.student_no, u.first_name, u.last_name, u.school_name, u.class,
                   bs.dogru_soru_sayisi, bs.toplam_sure_saniye
            FROM users u
            JOIN bireysel_skorlar bs ON u.student_no = bs.student_no
            WHERE u.role = 'student' AND bs.dogru_soru_sayisi > 0
        """
        params = []
        if sinif_filtresi:
            query += " AND u.class = %s"
            params.append(sinif_filtresi)
            
        cur.execute(query, tuple(params))
        rows = cur.fetchall()
        
        leaderboard = []
        for row in rows:
            s_no = row[0]
            # Rozetleri ayrıca çek
            cur.execute("SELECT rozet FROM ogrenci_rozetler WHERE student_no = %s", (str(s_no),))
            rozetler = [r[0] for r in cur.fetchall()]
            
            # Puan hesabı
            skor_puani = row[5] # Doğru sayısı
            if "altin" in rozetler: skor_puani += 3000
            elif "gumus" in rozetler: skor_puani += 2000
            elif "bronz" in rozetler: skor_puani += 1000
            
            leaderboard.append({
                "student_no": s_no,
                "isim": row[1],
                "soyisim": row[2],
                "okul": row[3],
                "sube": row[4],
                "rozetler": " ".join([r.capitalize() for r in rozetler]),
                "dogru_soru": row[5],
                "toplam_sure": row[6],
                "skor_puani": skor_puani
            })
            
        conn.close()
        
        # Sıralama: Puana göre azalan, Süreye göre artan
        leaderboard.sort(key=lambda x: (x["skor_puani"], -x["toplam_sure"]), reverse=True)
        return leaderboard[:10]
        
    except Exception as e:
        print(f"Liderlik Tablosu Hatası: {e}")
        return []

def get_yeni_soru_from_gemini(model, student_no):
    """
    Sıradaki soruyu hafızadan veya VERİTABANI SKORUNA GÖRE çeker.
    """
    global aktif_bireysel_oyunlar
    student_no = str(student_no) 
    
    # 1. Hafızada oyun yoksa oluştur
    if student_no not in aktif_bireysel_oyunlar:
        print(f"[{student_no}] İçin oyun başlatılıyor...")
        
        # --- BURASI DEĞİŞTİ: Veritabanından puanı öğren ---
        durum = get_student_db_status(student_no) # Yeni fonksiyonu kullanıyoruz
        mevcut_skor = durum.get("dogru_soru_sayisi", 0)
        
        # Eğer oyun bitmişse (10) sıfırdan başla, değilse kaldığı yerden devam et
        baslangic_index = mevcut_skor if mevcut_skor < 10 else 0
        # ---------------------------------------------------
        
        yeni_paket = _create_10_question_pack()
        if not yeni_paket:
            return {"success": False, "data": {"metin": "Soru Bankası hatası."}}
            
        aktif_bireysel_oyunlar[student_no] = {
            "sorular": yeni_paket,
            "mevcut_soru_index": baslangic_index # <-- SKORA GÖRE BAŞLAT
        }
        print(f"[{student_no}] Oyun yüklendi. Başlangıç İndeksi: {baslangic_index}")

    # 2. Soruyu getir
    oyun = aktif_bireysel_oyunlar[student_no]
    idx = oyun["mevcut_soru_index"]
    
    # Paket bittiyse
    if idx >= len(oyun["sorular"]):
        return {"success": False, "data": {"metin": "Tüm sorular tamamlandı."}}

    soru = oyun["sorular"][idx]
    
    return {"success": True, "data": {
        "metin": soru.get("metin"),
        "beceri_adi": soru.get("beceri_adi"),
        "deger_adi": soru.get("deger_adi"),
        "beceri_cumlesi": soru.get("beceri_cumlesi"),
        "deger_cumlesi": soru.get("deger_cumlesi")
    }}
    
    # 3. Frontend'e gönder
    return {"success": True, "data": {
        "metin": soru.get("metin"),
        "beceri_adi": soru.get("beceri_adi"),
        "deger_adi": soru.get("deger_adi"),
        "beceri_cumlesi": soru.get("beceri_cumlesi"),
        "deger_cumlesi": soru.get("deger_cumlesi")
    }}

def kaydet_soru_sonucu(student_no, soru_suresi_saniye):
    """
    Doğru cevap verildiğinde puanı ve rozeti VERİTABANINA (PostgreSQL) kaydeder.
    """
    global aktif_bireysel_oyunlar
    student_no = str(student_no)
    
    # 1. Mevcut durumu veritabanından öğren
    durum = get_student_db_status(student_no)
    
    # 2. Puanı artır
    yeni_puan = durum["dogru_soru_sayisi"] + 1
    yeni_sure = durum["toplam_sure_saniye"] + soru_suresi_saniye
    mevcut_rozetler = durum["rozetler"]
    
    yeni_rozet_mesaji = ""
    yeni_rozet_eklenecek = None

    # 3. Rozet Kontrolleri
    if yeni_puan == 10 and "altin" not in mevcut_rozetler:
        yeni_rozet_eklenecek = "altin"
        yeni_rozet_mesaji = "MÜKEMMEL! ALTIN ROZET kazandınız! 24 saat dinlenebilirsiniz."
    elif yeni_puan == 7 and "gumus" not in mevcut_rozetler:
        yeni_rozet_eklenecek = "gumus"
        yeni_rozet_mesaji = "Harika! GÜMÜŞ ROZET kazandınız!"
    elif yeni_puan == 2 and "bronz" not in mevcut_rozetler:
        yeni_rozet_eklenecek = "bronz"
        yeni_rozet_mesaji = "Tebrikler! BRONZ ROZET kazandınız!"

    # 4. VERİTABANINA KAYDET (UPDATE / INSERT)
    try:
        conn = db_helper.get_db_connection()
        cur = conn.cursor()
        
        # Önce bu öğrenci tabloda var mı diye bak
        cur.execute("SELECT 1 FROM bireysel_skorlar WHERE student_no = %s", (student_no,))
        exists = cur.fetchone()

        if exists:
            # Varsa GÜNCELLE
            cur.execute("""
                UPDATE bireysel_skorlar 
                SET dogru_soru_sayisi = %s, toplam_sure_saniye = %s, updated_at = CURRENT_TIMESTAMP
                WHERE student_no = %s
            """, (yeni_puan, yeni_sure, student_no))
        else:
            # Yoksa OLUŞTUR
            cur.execute("""
                INSERT INTO bireysel_skorlar (student_no, dogru_soru_sayisi, toplam_sure_saniye)
                VALUES (%s, %s, %s)
            """, (student_no, yeni_puan, yeni_sure))
        
        # Yeni rozet varsa ekle
        if yeni_rozet_eklenecek:
            cur.execute("INSERT INTO ogrenci_rozetler (student_no, rozet) VALUES (%s, %s)", (student_no, yeni_rozet_eklenecek))
            mevcut_rozetler.append(yeni_rozet_eklenecek)
            
            # Altın ise tarihini de işle
            if yeni_rozet_eklenecek == "altin":
                 bugun = datetime.now().strftime("%Y-%m-%d")
                 cur.execute("UPDATE bireysel_skorlar SET altin_rozet_tarihi = %s WHERE student_no = %s", (bugun, student_no))

        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Kayıt Hatası: {e}")

    # 5. Hafızadaki (RAM) oyunu ilerlet
    oyun = aktif_bireysel_oyunlar.get(student_no)
    if oyun:
        oyun["mevcut_soru_index"] += 1
        if oyun["mevcut_soru_index"] >= len(oyun["sorular"]):
            del aktif_bireysel_oyunlar[student_no]
    
    # 6. Sonucu döndür
    durum["dogru_soru_sayisi"] = yeni_puan
    durum["rozetler"] = mevcut_rozetler
    
    return {
        "success": True,
        "yeni_dogru_sayisi": yeni_puan,
        "rozet_sonucu": {
            "yeni_rozet": bool(yeni_rozet_mesaji),
            "mesaj": yeni_rozet_mesaji,
            "yeni_durum": durum
        }
    }
def kaydet_elenme_sonucu(student_no, harcanan_sure_saniye):
    """
    Elenme durumunu Veritabanına kaydeder ve PUANI SIFIRLAR.
    """
    global aktif_bireysel_oyunlar
    student_no = str(student_no)
    
    try:
        conn = db_helper.get_db_connection()
        cur = conn.cursor()
        
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        # Önce mevcut elenme durumunu al
        cur.execute("SELECT son_elenme_tarihi, gunluk_elenme_sayisi FROM bireysel_skorlar WHERE student_no = %s", (student_no,))
        row = cur.fetchone()
        
        son_tarih = str(row[0]) if row and row[0] else ""
        sayi = row[1] if row else 0
        
        # Sayacı ayarla
        if son_tarih == today_str:
            yeni_sayi = sayi + 1
            yeni_tarih = son_tarih
        else:
            yeni_sayi = 1
            yeni_tarih = today_str
            
        # Puanı SIFIRLA, süreyi ekle, elenmeyi güncelle
        # (Eğer kayıt yoksa önce insert yapmamız lazım ama genelde vardır)
        cur.execute("""
            INSERT INTO bireysel_skorlar (student_no, dogru_soru_sayisi, toplam_sure_saniye, gunluk_elenme_sayisi, son_elenme_tarihi)
            VALUES (%s, 0, %s, %s, %s)
            ON CONFLICT (student_no) DO UPDATE SET
            dogru_soru_sayisi = 0,
            toplam_sure_saniye = bireysel_skorlar.toplam_sure_saniye + EXCLUDED.toplam_sure_saniye,
            gunluk_elenme_sayisi = EXCLUDED.gunluk_elenme_sayisi,
            son_elenme_tarihi = EXCLUDED.son_elenme_tarihi
        """, (student_no, harcanan_sure_saniye, yeni_sayi, yeni_tarih))
        
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Elenme Kayıt Hatası: {e}")

    # Hafızadan sil
    if student_no in aktif_bireysel_oyunlar:
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
