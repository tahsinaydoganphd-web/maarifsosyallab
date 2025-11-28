# -*- coding: utf-8 -*-
"""
Bireysel Yarışma Modülü (TAM RENDER/POSTGRESQL UYUMLU - FINAL)
- Soruları 'bireysel_soru_bankasi.json' dosyasından okur.
- Skorları, Rozetleri ve İlerlemeyi 'db_helper' ile PostgreSQL'e kaydeder.
- get_ogrenci_durumu ve get_leaderboard fonksiyonları EKSİKSİZDİR.
"""

import json
import os
from datetime import datetime
import random
import db_helper  # Veritabanı bağlantısı

# Aktif bireysel oyunları hafızada tutar
aktif_bireysel_oyunlar = {}

# 100 sorunun tutulduğu dosya (Okuma amaçlı kalabilir)
SORU_BANKASI_FILE = 'bireysel_soru_bankasi.json'

# --- Soru Bankası Yönetimi ---

def load_soru_bankasi():
    """100 soruluk ana bankayı JSON'dan yükler."""
    if not os.path.exists(SORU_BANKASI_FILE):
        return {"kolay": [], "orta": [], "zor": []}
    
    try:
        with open(SORU_BANKASI_FILE, 'r', encoding='utf-8') as f:
            sorular = json.load(f)
        
        banka = {
            "kolay": [s for s in sorular if s.get('zorluk') == 'kolay'],
            "orta": [s for s in sorular if s.get('zorluk') == 'orta'],
            "zor": [s for s in sorular if s.get('zorluk') == 'zor']
        }
        return banka
    except Exception as e:
        print(f"Soru bankası yüklenirken hata: {e}")
        return {"kolay": [], "orta": [], "zor": []}

SORU_BANKASI = load_soru_bankasi()

def _create_10_question_pack():
    """Rastgele 10 soruluk paket oluşturur."""
    try:
        kolay_secim = random.sample(SORU_BANKASI["kolay"], 3)
        orta_secim = random.sample(SORU_BANKASI["orta"], 4)
        zor_secim = random.sample(SORU_BANKASI["zor"], 3)
        return kolay_secim + orta_secim + zor_secim
    except ValueError:
        return SORU_BANKASI["kolay"] + SORU_BANKASI["orta"] + SORU_BANKASI["zor"]
    except Exception:
        return []

# --- Veritabanı Yardımcı Fonksiyonu ---

def get_student_db_status(student_no):
    """
    Öğrencinin anlık durumunu PostgreSQL'den çeker.
    """
    try:
        conn = db_helper.get_db_connection()
        cur = conn.cursor()
        
        # 1. Skor tablosunu kontrol et
        cur.execute("""
            SELECT dogru_soru_sayisi, toplam_sure_saniye, altin_rozet_tarihi, 
                   gunluk_elenme_sayisi, son_elenme_tarihi 
            FROM bireysel_skorlar WHERE student_no = %s
        """, (str(student_no),))
        row = cur.fetchone()
        
        # Eğer kayıt yoksa oluştur (İlk giriş)
        if not row:
            cur.execute("INSERT INTO bireysel_skorlar (student_no) VALUES (%s)", (str(student_no),))
            conn.commit()
            row = (0, 0, None, 0, None)
        
        # 2. Rozetleri çek
        cur.execute("SELECT rozet FROM ogrenci_rozetler WHERE student_no = %s", (str(student_no),))
        rozetler = [r[0] for r in cur.fetchall()]
        
        cur.close()
        conn.close()
        
        return {
            "dogru_soru_sayisi": row[0] or 0,
            "toplam_sure_saniye": row[1] or 0,
            "altin_rozet_tarihi": str(row[2]) if row[2] else None,
            "gunluk_elenme_sayisi": row[3] or 0,
            "son_elenme_tarihi": str(row[4]) if row[4] else None,
            "rozetler": rozetler
        }
    except Exception as e:
        print(f"DB Status Hatası: {e}")
        return {"dogru_soru_sayisi": 0, "rozetler": [], "toplam_sure_saniye": 0}

# --- Ana API Fonksiyonları ---

# İŞTE EKSİK OLAN VE HATAYA SEBEP OLAN FONKSİYON BU:
def get_ogrenci_durumu(student_no, model=None):
    """
    /basla tarafından çağrılır. Veritabanındaki durumu kontrol eder.
    """
    durum = get_student_db_status(student_no)
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # Yasak Kontrolleri
    if durum.get("son_elenme_tarihi") == today_str and durum.get("gunluk_elenme_sayisi", 0) >= 3:
        return {"success": False, "giris_yasakli": True, "mesaj": "Bugün 3 kez elendiniz. Yarın tekrar deneyin."}
        
    if durum.get("altin_rozet_tarihi") == today_str:
        return {"success": False, "giris_yasakli": True, "mesaj": "Bugün Altın Rozet aldınız. Yarın tekrar deneyin."}

    # Eski günden kalan rozet varsa temizle (Yeni gün kontrolü)
    if "altin" in durum["rozetler"] and durum["altin_rozet_tarihi"] != today_str:
        # Veritabanını sıfırla (Yeni oyun için)
        try:
            conn = db_helper.get_db_connection()
            cur = conn.cursor()
            cur.execute("UPDATE bireysel_skorlar SET dogru_soru_sayisi=0, toplam_sure_saniye=0 WHERE student_no=%s", (str(student_no),))
            cur.execute("DELETE FROM ogrenci_rozetler WHERE student_no=%s", (str(student_no),))
            conn.commit()
            conn.close()
            # Durumu güncelle
            durum["dogru_soru_sayisi"] = 0
            durum["rozetler"] = []
        except:
            pass

    return {
        "success": True,
        "giris_yasakli": False,
        "durum": {
            "dogru_soru_sayisi": durum.get("dogru_soru_sayisi", 0),
            "rozetler": durum.get("rozetler", []),
            "toplam_sure_saniye": durum.get("toplam_sure_saniye", 0)
        }
    }

def get_yeni_soru_from_gemini(model, student_no):
    """
    Sıradaki soruyu hafızadan veya VERİTABANI SKORUNA GÖRE çeker.
    """
    global aktif_bireysel_oyunlar
    student_no = str(student_no)
    
    # 1. Hafızada oyun yoksa oluştur
    if student_no not in aktif_bireysel_oyunlar:
        print(f"[{student_no}] İçin oyun başlatılıyor...")
        
        # Veritabanından puanı öğren
        durum = get_student_db_status(student_no)
        mevcut_skor = durum.get("dogru_soru_sayisi", 0)
        
        # Kaldığı yerden devam et
        baslangic_index = mevcut_skor if mevcut_skor < 10 else 0
        
        yeni_paket = _create_10_question_pack()
        if not yeni_paket:
            return {"success": False, "data": {"metin": "Soru Bankası hatası."}}
            
        aktif_bireysel_oyunlar[student_no] = {
            "sorular": yeni_paket,
            "mevcut_soru_index": baslangic_index
        }
        print(f"[{student_no}] Başlangıç İndeksi: {baslangic_index}")

    # 2. Soruyu getir
    oyun = aktif_bireysel_oyunlar[student_no]
    idx = oyun["mevcut_soru_index"]
    
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
