# -*- coding: utf-8 -*-
"""
TAKIM YARIŞMASI MODÜLÜ (SÜRÜM 10 - DÜZELTİLMİŞ)
- Tek takım/Çok takım ayrımı kaldırıldı (Standart Tur Mantığı).
- 'get_aktif_takim_id' artık oyunu agresif şekilde bitirmiyor.
- Veri güvenliği artırıldı.
"""

import json
import os
import random
from datetime import datetime
import time

# --- Soru Bankası Yükleyicisi ---
SORU_BANKASI_FILE = 'bireysel_soru_bankasi.json'

def load_soru_bankasi():
    if not os.path.exists(SORU_BANKASI_FILE):
        return {"kolay": [], "orta": [], "zor": []}
    try:
        with open(SORU_BANKASI_FILE, 'r', encoding='utf-8') as f:
            sorular = json.load(f)
        return {
            "kolay": [s for s in sorular if s.get('zorluk') == 'kolay'],
            "orta": [s for s in sorular if s.get('zorluk') == 'orta'],
            "zor": [s for s in sorular if s.get('zorluk') == 'zor']
        }
    except Exception as e:
        print(f"Soru bankası yüklenirken hata: {e}")
        return {"kolay": [], "orta": [], "zor": []}

SORU_BANKASI = load_soru_bankasi()
TAKIM_SKOR_DB_FILE = 'takim_sonuclari.json'

def load_takim_skorlari():
    if os.path.exists(TAKIM_SKOR_DB_FILE):
        try:
            with open(TAKIM_SKOR_DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: return []
    return []

def save_takim_skorlari(data):
    try:
        with open(TAKIM_SKOR_DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e: print(e)

# --- Ana Yarışma Sınıfı ---

class TakimYarismasi:
    def __init__(self, takimlar_listesi, okul, sinif):
        self.takimlar = self._takimlari_baslat(takimlar_listesi) 
        self.okul = okul
        self.sinif = sinif
        self.yarışma_bitti = False 
        self.mevcut_soru_numarasi = 1
        self.mevcut_soru_verisi = None # Başlangıçta mutlaka None olmalı
        self.kazanan_takim_id = None
        self.aktif_takim_index = 0 
        self.tur_numarasi = 1
        self.son_olay = {"zaman": 0, "mesaj": "", "tur": "", "detay": {}}
        self.dereceye_girdi_mi = False
        self.oyun_soru_listesi = self._oyun_sorularini_olustur()

    def _oyun_sorularini_olustur(self):
        try:
            # Her zorluktan soruları seç
            kolay = random.sample(SORU_BANKASI["kolay"], min(len(SORU_BANKASI["kolay"]), 3))
            orta = random.sample(SORU_BANKASI["orta"], min(len(SORU_BANKASI["orta"]), 4))
            zor = random.sample(SORU_BANKASI["zor"], min(len(SORU_BANKASI["zor"]), 3))
            
            # Eğer yeterli soru yoksa eldekilerle doldur
            if len(kolay) + len(orta) + len(zor) < 10:
                print("UYARI: Yeterli soru yok, mevcutlar karıştırılıyor.")
            
            tam_liste = kolay + orta + zor
            random.shuffle(tam_liste) # Karıştır
            return {i + 1: soru for i, soru in enumerate(tam_liste)}
        except Exception as e:
            print(f"HATA: Soru oluşturma hatası: {e}")
            return {}

    def _takimlari_baslat(self, takimlar_listesi):
        oyun_takimlari = {}
        for i, takim in enumerate(takimlar_listesi):
            uyeler = takim.get('uyeler', [])
            for uye in uyeler: uye['no'] = str(uye.get('no')).strip()

            isim_uyeleri = [uye.get('ad_soyad', 'Bilinmiyor').split(' ')[0] for uye in uyeler[:3]]
            takim_adi = "-".join(isim_uyeleri) if isim_uyeleri else f"Takım {i+1}"
            takim_id = f"takim_{i}"
            
            oyun_takimlari[takim_id] = {
                "id": takim_id, "isim": takim_adi, "uyeler": uyeler,
                "aktif_uye_index": 0, "aktif": True, "puan": 0, 
                "rozet": "yok", "kalan_deneme_hakki": 3,
                "bulunan_beceri": False, "bulunan_deger": False,
                "toplam_sure_saniye": 0, "son_soru_zamani": None 
            }
        return oyun_takimlari

    def get_aktif_takim_id(self):
        """
        DÜZELTİLMİŞ MANTIK: 
        Tek takım olsa bile 'Tur Kontrolü' başarısız olursa (yani bu turdaki hakkını doldurduysa)
        hemen oyunu bitirmez, 'Tur Atlamaya Hazır mı' kontrolüne yönlendirir.
        """
        if self.yarışma_bitti: return None
            
        takim_id_listesi = sorted(list(self.takimlar.keys()), key=lambda x: int(x.split('_')[1]))
        aktif_takimlar = [t for t in self.takimlar.values() if t["aktif"]]
        
        if len(aktif_takimlar) == 0:
            return self._yarismayi_bitir(kazanan_id=None)
        
        # --- DÜZELTME: "Tek Kalan" Bloğu SİLİNDİ ---
        # Artık tek takım da olsa aşağıdaki genel döngüye girip tur kontrolü yapılacak.
        
        # 1. Normal Tur Döngüsü (Round Robin)
        baslangic_index = self.aktif_takim_index % len(takim_id_listesi)
        for i in range(len(takim_id_listesi)):
            idx = (baslangic_index + i) % len(takim_id_listesi)
            takim_id = takim_id_listesi[idx]
            takim = self.takimlar[takim_id]
            
            # Takım aktifse VE bu turda oynaması gerekiyorsa (Puanı turun altında kaldıysa)
            if takim["aktif"] and self._tur_kontrolu(takim):
                return takim_id
        
        # 2. Eğer kimse bu turda oynayamıyorsa -> Tur Atla
        if not self._tur_atlamaya_hazir_mi():
            print(f"--- Tur {self.tur_numarasi} bitti. Yeni tura geçiliyor. ---")
            self.tur_numarasi += 1
            
            if self.tur_numarasi > 3: 
                # 3 Tur bitti, oyun bitti. En yüksek puanlıyı bul.
                en_iyi_takim = max(aktif_takimlar, key=lambda t: t['puan'])
                return self._yarismayi_bitir(kazanan_id=en_iyi_takim['id'])
            
            # Yeni turda tekrar kontrol et
            return self.get_aktif_takim_id()
        
        # Teorik olarak buraya gelmemeli ama gelirse bitir.
        return self._yarismayi_bitir(kazanan_id=None)

    def _tur_kontrolu(self, takim):
        puan = takim["puan"]
        # Tur 1: 2 puana kadar oyna. Tur 2: 7 puana kadar. Tur 3: 10 puana kadar.
        if self.tur_numarasi == 1: return puan < 2      
        if self.tur_numarasi == 2: return puan < 7 
        if self.tur_numarasi == 3: return puan < 10 
        return False

    def _tur_atlamaya_hazir_mi(self):
        """Hala bu turda oynaması gereken (hedefe ulaşmamış) takım var mı?"""
        for takim in self.takimlar.values():
            if takim["aktif"] and self._tur_kontrolu(takim):
                return True 
        return False 

    def soru_iste(self, takim_id):
        if self.yarışma_bitti: return {"success": False, "hata": "Bitti"}
        
        # Eğer aktif takım istenen takım değilse engelle (Güvenlik)
        gercek_aktif_id = self.get_aktif_takim_id()
        if gercek_aktif_id != takim_id:
             # Eğer oyun bittiyse get_aktif_takim_id None döner, o zaman sorun yok
             if not self.yarışma_bitti:
                 print(f"Sıra hatası: {takim_id} istedi ama sıra {gercek_aktif_id}'de")
        
        self.mevcut_soru_numarasi = self.takimlar[takim_id]["puan"] + 1
        secilen_soru = self.oyun_soru_listesi.get(self.mevcut_soru_numarasi)
        
        if not secilen_soru:
             print(f"HATA: Soru {self.mevcut_soru_numarasi} yok!")
             return {"success": False, "hata": "Soru bulunamadı"}

        self.takimlar[takim_id]["son_soru_zamani"] = datetime.now().isoformat()
        self.mevcut_soru_verisi = secilen_soru
        self.takimlar[takim_id]["bulunan_beceri"] = False
        self.takimlar[takim_id]["bulunan_deger"] = False
        self.takimlar[takim_id]["kalan_deneme_hakki"] = 3
        
        print(f"SORU GÖSTERİLDİ: Soru {self.mevcut_soru_numarasi} ({takim_id})")
        
        return {
            "success": True,
            "metin": secilen_soru["metin"],
            "beceri_adi": secilen_soru["beceri_adi"],
            "deger_adi": secilen_soru["deger_adi"]
        }

    def cevap_ver(self, takim_id, tiklanan_tip, tiklanan_cumle):
        if self.yarışma_bitti or not self.mevcut_soru_verisi:
            return {"success": False, "hata": "Geçersiz işlem"}
            
        takim = self.takimlar.get(takim_id)
        
        # Süre Kontrolü
        zaman_baslangici = datetime.fromisoformat(takim["son_soru_zamani"])
        harcanan_sure = (datetime.now() - zaman_baslangici).total_seconds()
        
        if tiklanan_cumle == "SÜRE DOLDU" or harcanan_sure > 65: # 5sn tolerans
            takim["aktif"] = False
            self.mevcut_soru_verisi = None
            self._olay_kaydet("Süre dolduğu için elendiniz.", "error", {"sonuc": "elendi"})
            return {"success": True, "sonuc": "elendi", "mesaj": "Süre doldu."}

        dogru_beceri = self.mevcut_soru_verisi["beceri_cumlesi"].strip()
        dogru_deger = self.mevcut_soru_verisi["deger_cumlesi"].strip()
        tiklanan_cumle = tiklanan_cumle.strip()
        
        sonuc, mesaj = "yanlis", "Yanlış cevap."
        
        if tiklanan_tip == "beceri" and tiklanan_cumle == dogru_beceri:
            takim["bulunan_beceri"] = True
            sonuc, mesaj = "dogru_parca", "Beceri Doğru!"
        elif tiklanan_tip == "deger" and tiklanan_cumle == dogru_deger:
            takim["bulunan_deger"] = True
            sonuc, mesaj = "dogru_parca", "Değer Doğru!"
        else:
            takim["kalan_deneme_hakki"] -= 1

        if takim["bulunan_beceri"] and takim["bulunan_deger"]:
            takim["puan"] += 1
            takim["toplam_sure_saniye"] += harcanan_sure
            self.mevcut_soru_verisi = None 
            self._rozet_guncelle(takim)
            
            puan = takim["puan"]
            if puan >= 10:
                self._yarismayi_bitir(kazanan_id=takim_id)
                sonuc, mesaj = "oyun_bitti", "TEBRİKLER! OYUN BİTTİ!"
            elif puan == 2 or puan == 7:
                sonuc, mesaj = "tur_bitti", f"Tebrikler! {puan}. soruyu geçtiniz."
            else:
                sonuc, mesaj = "soru_bitti_devam_et", "Doğru! Devam..."
        
        elif takim["kalan_deneme_hakki"] <= 0:
            takim["aktif"] = False
            self.mevcut_soru_verisi = None
            sonuc, mesaj = "elendi", "Hakkınız bitti."

        self._olay_kaydet(mesaj, "success" if "dogru" in sonuc or "TEBRİKLER" in mesaj else "error", 
                          {"tiklanan_cumle": tiklanan_cumle, "sonuc": sonuc})

        if sonuc != "dogru_parca": 
            self._takim_ici_sirayi_degistir(takim_id)

        return {"success": True, "sonuc": sonuc, "mesaj": mesaj}

    def _olay_kaydet(self, mesaj, tur, detay):
        self.son_olay = {"zaman": time.time(), "mesaj": mesaj, "tur": tur, "detay": detay}

    def _rozet_guncelle(self, takim):
        p = takim["puan"]
        takim["rozet"] = "altin" if p >= 10 else "gümüş" if p >= 7 else "bronz" if p >= 2 else "yok"
    
    def _takim_ici_sirayi_degistir(self, takim_id):
        takim = self.takimlar[takim_id]
        if len(takim["uyeler"]) > 1:
            takim["aktif_uye_index"] = (takim["aktif_uye_index"] + 1) % len(takim["uyeler"])

    def siradaki_takima_gec(self):
        if self.yarışma_bitti: return
        self.aktif_takim_index += 1
        self.mevcut_soru_verisi = None

    def _yarismayi_bitir(self, kazanan_id=None):
        if self.yarışma_bitti: return self.kazanan_takim_id
        self.yarışma_bitti = True
        self.kazanan_takim_id = kazanan_id
        self.mevcut_soru_verisi = None # Soruyu ekrandan kaldır
        
        # Skor Kaydetme
        if kazanan_id:
             import takim_yarismasi_modul as ty
             skorlar = ty.load_takim_skorlari()
             kazanan = self.takimlar[kazanan_id]
             
             ty.kaydet_yarışma_sonucu(kazanan["isim"], kazanan["rozet"], kazanan["puan"], 
                                      kazanan["toplam_sure_saniye"], self.okul, self.sinif)
             
             # Derece Kontrolü
             self.dereceye_girdi_mi = False
             if len(skorlar) < 10: self.dereceye_girdi_mi = True
             else:
                 son = skorlar[-1]
                 if (kazanan["puan"] > son["soru_sayisi"]) or \
                    (kazanan["puan"] == son["soru_sayisi"] and kazanan["toplam_sure_saniye"] < son["toplam_sure_saniye"]):
                     self.dereceye_girdi_mi = True
        return self.kazanan_takim_id

    def durumu_json_yap(self):
        aktif_takim_id = self.get_aktif_takim_id()
        kalan_saniye = 60
        mevcut_soru_kisitli = None
        aktif_kaptan_id = None

        if aktif_takim_id:
            takim = self.takimlar[aktif_takim_id]
            self.mevcut_soru_numarasi = takim["puan"] + 1
            
            # Kaptan ID
            if takim["uyeler"]:
                idx = takim["aktif_uye_index"] % len(takim["uyeler"])
                aktif_kaptan_id = str(takim["uyeler"][idx]["no"]).strip()

            if self.mevcut_soru_verisi:
                zaman_baslangici = datetime.fromisoformat(takim["son_soru_zamani"])
                gecen = (datetime.now() - zaman_baslangici).total_seconds()
                kalan_saniye = max(0, 60 - int(gecen))
                
                # --- BUTONLARI GARANTİ ALTINA AL ---
                beceri_adi = self.mevcut_soru_verisi.get("beceri_adi")
                if not beceri_adi: beceri_adi = "Beceri" # Boş gelirse varsayılan
                
                deger_adi = self.mevcut_soru_verisi.get("deger_adi")
                if not deger_adi: deger_adi = "Değer" # Boş gelirse varsayılan

                mevcut_soru_kisitli = {
                    "metin": self.mevcut_soru_verisi["metin"],
                    "beceri_adi": beceri_adi, 
                    "deger_adi": deger_adi
                }

        return {
            "takimlar": list(self.takimlar.values()),
            "aktif_takim_id": aktif_takim_id,
            "aktif_takim_kaptani_id": aktif_kaptan_id,
            "yarışma_bitti": self.yarışma_bitti,
            "kazanan_takim_id": self.kazanan_takim_id,
            "kalan_saniye": kalan_saniye,
            "mevcut_soru_numarasi": self.mevcut_soru_numarasi,
            "mevcut_soru_verisi": mevcut_soru_kisitli,
            "son_olay": self.son_olay,
            "dereceye_girdi_mi": self.dereceye_girdi_mi
        }
