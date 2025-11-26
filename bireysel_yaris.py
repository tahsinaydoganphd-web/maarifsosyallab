# -*- coding: utf-8 -*-
"""
Bireysel Yarışma Modülü (TAM SQL ENTEGRASYON)
- Soruları 'bireysel_soru_bankasi.json' dosyasından okur.
- Skorları ve durumları PostgreSQL veritabanından (db_helper) okur ve yazar.
"""

import json
import os
from datetime import datetime
import random
import db_helper  # <-- İŞTE EKSİK OLAN VE HATAYI ÇÖZEN SATIR BU

# Aktif bireysel oyunları hafızada tutar (RAM)
aktif_bireysel_oyunlar = {}

# 100 sorunun tutulduğu dosya
SORU_BANKASI_FILE = 'bireysel_soru_bankasi.json'

# --- Soru Bankası Yönetimi ---
def load_soru_bankasi():
    if not os.path.exists(SORU_BANKASI_FILE):
        return {"kolay": [], "orta": [], "zor": [], "hepsi": []}
    try:
        with open(SORU_BANKASI_FILE, 'r', encoding='utf-8') as f:
            sorular = json.load(f)
        
        # Tüm soruları küçük harf zorluk seviyesine göre ayır
        return {
            "kolay": [s for s in sorular if s.get('zorluk', '').lower() == 'kolay'],
            "orta": [s for s in sorular if s.get('zorluk', '').lower() == 'orta'],
            "zor": [s for s in sorular if s.get('zorluk', '').lower() == 'zor'],
            "hepsi": sorular # Yedek havuz
        }
    except Exception as e:
        print(f"Soru bankası hatası: {e}")
        return {"kolay": [], "orta": [], "zor": [], "hepsi": []}

SORU_BANKASI = load_soru_bankasi()

def _create_10_question_pack():
    """Rastgele 10 soruluk paket oluşturur (Hata Korumalı)"""
    try:
        # Önce ideal senaryoyu dene: 3 Kolay, 4 Orta, 3 Zor
        if (len(SORU_BANKASI["kolay"]) >= 3 and
            len(SORU_BANKASI["orta"]) >= 4 and
            len(SORU_BANKASI["zor"]) >= 3):
            
            kolay = random.sample(SORU_BANKASI["kolay"], 3)
            orta = random.sample(SORU_BANKASI["orta"], 4)
            zor = random.sample(SORU_BANKASI["zor"], 3)
            return kolay + orta + zor
        else:
            # Yeterli dağılım yoksa, "hepsi" havuzundan rastgele 10 tane seç
            print("UYARI: Yeterli zorluk dağılımı yok, karışık soru seçiliyor.")
            all_questions = SORU_BANKASI["hepsi"]
            
            if len(all_questions) == 0:
                return [] # Hiç soru yok
            
            # Eğer toplam soru 10'dan azsa, olanların hepsini döndür
            if len(all_questions) < 10:
                return all_questions
                
            return random.sample(all_questions, 10)
            
    except Exception as e:
        print(f"Paket oluşturma hatası: {e}")
        # Hata durumunda yedek havuzdan ne varsa ver
        return SORU_BANKASI.get("hepsi", [])[:10]


# --- ANA API FONKSİYONLARI ---

def get_ogrenci_durumu(student_no, model=None):
    """SQL Veritabanından öğrenci durumunu kontrol eder"""
    
    # 1. SQL'den veriyi çek
    durum = db_helper.get_bireysel_skor(student_no)
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # 2. Yasak Kontrolleri
    if durum.get("son_elenme_tarihi") == today_str and durum.get("gunluk_elenme_sayisi", 0) >= 3:
        return {"success": False, "giris_yasakli": True, "mesaj": "Bugün 3 kez elendiğiniz için 24 saat boyunca yarışamazsınız."}
        
    if durum.get("altin_rozet_tarihi") == today_str:
        return {"success": False, "giris_yasakli": True, "mesaj": "Bugün Altın Rozet aldınız. Yarın tekrar bekleriz."}

    # 3. Temiz durumu döndür
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
    """Sıradaki soruyu hafızadan (RAM) getirir - AKILLI VERSİYON"""
    global aktif_bireysel_oyunlar
    
    # Oyun hafızada yoksa (Sunucu resetlendiyse veya yeni girişse)
    if student_no not in aktif_bireysel_oyunlar:
        yeni_paket = _create_10_question_pack()
        if not yeni_paket:
            return {"success": False, "data": {"metin": "Soru Bankası hatası veya boş."}}
            
        # --- AKILLI DÜZELTME BURADA ---
        # Veritabanına bak, öğrenci kaçıncı soruda kalmış?
        db_durum = db_helper.get_bireysel_skor(student_no)
        kaldigi_yer = db_durum.get("dogru_soru_sayisi", 0)
        
        # Eğer 10'u geçtiyse mod al (örn: 12. soru -> 2. soru)
        mevcut_index = kaldigi_yer % 10
        
        print(f"[{student_no}] Oyuna {mevcut_index + 1}. sorudan devam ediyor.")
        
        aktif_bireysel_oyunlar[student_no] = {
            "sorular": yeni_paket,
            "mevcut_soru_index": mevcut_index
        }
    
    oyun = aktif_bireysel_oyunlar.get(student_no)
    idx = oyun["mevcut_soru_index"]
    
    # Oyun bitmiş mi kontrolü
    if idx >= len(oyun["sorular"]):
        return {"success": False, "data": {"metin": "Tüm sorular bitti. Tebrikler!"}}
        
    soru = oyun["sorular"][idx]
    
    return {
        "success": True,
        "data": {
            "metin": soru.get("metin"),
            "beceri_adi": soru.get("beceri_adi"),
            "deger_adi": soru.get("deger_adi"),
            "beceri_cumlesi": soru.get("beceri_cumlesi"),
            "deger_cumlesi": soru.get("deger_cumlesi")
        }
    }

def kaydet_soru_sonucu(student_no, soru_suresi_saniye):
    """Doğru cevabı SQL veritabanına işler - DÜZELTİLMİŞ VERSİYON"""
    global aktif_bireysel_oyunlar
    
    # 1. Mevcut veriyi çek
    durum = db_helper.get_bireysel_skor(student_no)
    if not durum: # İlk kez oynuyorsa
        durum = {"dogru_soru_sayisi": 0, "toplam_sure_saniye": 0, "rozetler": [], "gunluk_elenme_sayisi": 0}

    # 2. Puanı artır
    durum["dogru_soru_sayisi"] = durum.get("dogru_soru_sayisi", 0) + 1
    durum["toplam_sure_saniye"] = durum.get("toplam_sure_saniye", 0) + soru_suresi_saniye
    
    # 3. Rozet Kontrolü
    yeni_rozet_mesaji = ""
    rozetler = durum.get("rozetler", [])
    if not isinstance(rozetler, list): rozetler = []
    
    if durum["dogru_soru_sayisi"] == 10 and "altin" not in rozetler:
        rozetler.append("altin")
        durum["altin_rozet_tarihi"] = datetime.now().strftime("%Y-%m-%d")
        yeni_rozet_mesaji = "MÜKEMMEL! ALTIN ROZET kazandınız!"
    elif durum["dogru_soru_sayisi"] == 7 and "gumus" not in rozetler:
        rozetler.append("gumus")
        yeni_rozet_mesaji = "Harika! GÜMÜŞ ROZET kazandınız!"
    elif durum["dogru_soru_sayisi"] == 2 and "bronz" not in rozetler:
        rozetler.append("bronz")
        yeni_rozet_mesaji = "Tebrikler! BRONZ ROZET kazandınız!"
    
    durum["rozetler"] = rozetler
    
    # 4. SQL'e Kaydet
    db_helper.save_bireysel_skor(student_no, durum)
    
    # 5. Hafızadaki oyunu ilerlet
    oyun = aktif_bireysel_oyunlar.get(student_no)
    if oyun:
        oyun["mevcut_soru_index"] += 1
        # Oyun bitti mi?
        if oyun["mevcut_soru_index"] >= len(oyun["sorular"]):
            del aktif_bireysel_oyunlar[student_no]
    
    return {
        "success": True,
        "yeni_dogru_sayisi": durum["dogru_soru_sayisi"],
        "rozet_sonucu": {
            "yeni_rozet": bool(yeni_rozet_mesaji),
            "mesaj": yeni_rozet_mesaji,
            # EKSİK OLAN KISIM BURASIYDI:
            "yeni_durum": { "rozetler": durum["rozetler"] }
        }
    }
def kaydet_elenme_sonucu(student_no, harcanan_sure_saniye):
    """Elenmeyi SQL veritabanına işler"""
    global aktif_bireysel_oyunlar
    
    durum = db_helper.get_bireysel_skor(student_no)
    if not durum: durum = {"dogru_soru_sayisi": 0, "gunluk_elenme_sayisi": 0, "toplam_sure_saniye": 0}

    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # Günlük elenme sayısını artır
    if durum.get("son_elenme_tarihi") == today_str:
        durum["gunluk_elenme_sayisi"] = durum.get("gunluk_elenme_sayisi", 0) + 1
    else:
        durum["gunluk_elenme_sayisi"] = 1
        durum["son_elenme_tarihi"] = today_str

    durum["toplam_sure_saniye"] += harcanan_sure_saniye
    durum["dogru_soru_sayisi"] = 0 # Puanı sıfırla

    # SQL'e Kaydet
    db_helper.save_bireysel_skor(student_no, durum)

    # Aktif oyunu bitir
    if student_no in aktif_bireysel_oyunlar:
        del aktif_bireysel_oyunlar[student_no]

    return {"success": True, "mesaj": "Elenme kaydedildi."}

def get_leaderboard(users_db, sinif_filtresi=None):
    """Liderlik tablosunu SQL'den oluşturur"""
    # Tüm skorları SQL'den tek seferde çekiyoruz
    tum_skorlar = db_helper.get_all_bireysel_scores()
    leaderboard = []

    for student_no, user_data in users_db.items():
        if user_data.get('role') != 'student': continue
        if sinif_filtresi and user_data.get('class') != sinif_filtresi: continue
            
        skor_data = tum_skorlar.get(student_no)
        if skor_data and skor_data.get("dogru_soru_sayisi", 0) > 0:
            
            puan = skor_data.get("dogru_soru_sayisi", 0)
            rozetler = skor_data.get("rozetler", [])
            if "altin" in rozetler: puan += 3000
            elif "gumus" in rozetler: puan += 2000
            elif "bronz" in rozetler: puan += 1000

            leaderboard.append({
                "student_no": student_no,
                "isim": user_data.get("first_name", ""),
                "soyisim": user_data.get("last_name", ""),
                "okul": user_data.get("school_name", "Bilinmiyor"),
                "sube": user_data.get('class', 'N/A'),
                "rozetler": " ".join([r.capitalize() for r in rozetler]),
                "dogru_soru": skor_data.get("dogru_soru_sayisi", 0),
                "toplam_sure": skor_data.get("toplam_sure_saniye", 0),
                "skor_puani": puan
            })

    leaderboard.sort(key=lambda x: (x["skor_puani"], -x["toplam_sure"]), reverse=True)
    return leaderboard[:5] if sinif_filtresi else leaderboard[:10]
