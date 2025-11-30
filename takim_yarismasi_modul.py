# -*- coding: utf-8 -*-
"""
TAKIM YARIŞMASI MODÜLÜ (SÜRÜM 11 - KESİN KURALLI)
- Kural 1: Aktif takım, elenenlerin puanını geçtiği an KAZANIR (Oyun uzamaz).
- Kural 2: Herkes elendiyse, eşit puanda süreye bakılır.
- Kural 3: En yüksek puan 2'den azsa KAZANAN YOKTUR.
"""

import json
import os
import random
from datetime import datetime
import time

# --- Soru Bankası ve Veritabanı Ayarları ---
SORU_BANKASI_FILE = 'bireysel_soru_bankasi.json'
TAKIM_SKOR_DB_FILE = 'takim_sonuclari.json'

def load_soru_bankasi():
    if not os.path.exists(SORU_BANKASI_FILE): return {"kolay": [], "orta": [], "zor": []}
    try:
        with open(SORU_BANKASI_FILE, 'r', encoding='utf-8') as f:
            sorular = json.load(f)
        return {
            "kolay": [s for s in sorular if s.get('zorluk') == 'kolay'],
            "orta": [s for s in sorular if s.get('zorluk') == 'orta'],
            "zor": [s for s in sorular if s.get('zorluk') == 'zor']
        }
    except: return {"kolay": [], "orta": [], "zor": []}

SORU_BANKASI = load_soru_bankasi()

def load_takim_skorlari():
    if os.path.exists(TAKIM_SKOR_DB_FILE):
        try: with open(TAKIM_SKOR_DB_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except: return []
    return []

def save_takim_skorlari(data):
    try:
        with open(TAKIM_SKOR_DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except: pass

def kaydet_yarışma_sonucu(takim_adi, rozet, soru_sayisi, toplam_sure, okul, sinif):
    """Liderlik tablosuna kaydeder (Sadece ilk 10)."""
    try:
        skor_tablosu = load_takim_skorlari()
        rozet_degeri = {"altin": 3, "gümüş": 2, "bronz": 1, "yok": 0}
        yeni_skor = {
            "takim_adi": takim_adi, "okul_sinif": f"{okul} / {sinif}",
            "rozet": rozet, "rozet_degeri": rozet_degeri.get(rozet, 0),
            "soru_sayisi": soru_sayisi, "toplam_sure_saniye": round(toplam_sure, 2),
            "tarih": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        skor_tablosu.append(yeni_skor)
        # Sıralama: 1. Rozet Değeri, 2. Soru Sayısı, 3. Süre (Az olan iyi)
        skor_tablosu.sort(key=lambda x: (-x["rozet_degeri"], -x["soru_sayisi"], x["toplam_sure_saniye"]))
        save_takim_skorlari(skor_tablosu[:10])
    except: pass

# --- Ana Sınıf ---

class TakimYarismasi:
    def __init__(self, takimlar_listesi, okul, sinif):
        self.takimlar = self._takimlari_baslat(takimlar_listesi) 
        self.okul = okul
        self.sinif = sinif
        self.yarışma_bitti = False 
        self.bitis_mesaji = "" # Özel bitiş mesajı (Bronz yok vb.)
        self.mevcut_soru_numarasi = 1
        self.mevcut_soru_verisi = None 
        self.kazanan_takim_id = None
        self.aktif_takim_index = 0 
        self.tur_numarasi = 1
        self.son_olay = {"zaman": 0, "mesaj": "", "tur": "", "detay": {}}
        self.dereceye_girdi_mi = False
        self.oyun_soru_listesi = self._oyun_sorularini_olustur()

    def _oyun_sorularini_olustur(self):
        try:
            kolay = random.sample(SORU_BANKASI["kolay"], min(len(SORU_BANKASI["kolay"]), 3))
            orta = random.sample(SORU_BANKASI["orta"], min(len(SORU_BANKASI["orta"]), 4))
            zor = random.sample(SORU_BANKASI["zor"], min(len(SORU_BANKASI["zor"]), 3))
            tam_liste = kolay + orta + zor
            random.shuffle(tam_liste)
            return {i + 1: soru for i, soru in enumerate(tam_liste)}
        except: return {}

    def _takimlari_baslat(self, takimlar_listesi):
        oyun_takimlari = {}
        for i, takim in enumerate(takimlar_listesi):
            uyeler = takim.get('uyeler', [])
            for uye in uyeler: uye['no'] = str(uye.get('no')).strip()
            isim = "-".join([u.get('ad_soyad','').split(' ')[0] for u in uyeler[:3]]) if uyeler else f"Takım {i+1}"
            tid = f"takim_{i}"
            oyun_takimlari[tid] = {
                "id": tid, "isim": isim, "uyeler": uyeler,
                "aktif_uye_index": 0, "aktif": True, "puan": 0, 
                "rozet": "yok", "kalan_deneme_hakki": 3,
                "bulunan_beceri": False, "bulunan_deger": False,
                "toplam_sure_saniye": 0, "son_soru_zamani": None 
            }
        return oyun_takimlari

    def _oyun_bitti_mi_kontrol_et(self):
        """
        KURAL KONTROL MERKEZİ:
        Oyunun bitip bitmediğini senin kurallarına göre denetler.
        Çağrıldığı yerler: get_aktif_takim_id, cevap_ver
        """
        if self.yarışma_bitti: return True

        aktif_takimlar = [t for t in self.takimlar.values() if t["aktif"]]
        elenen_takimlar = [t for t in self.takimlar.values() if not t["aktif"]]
        
        # En yüksek puanlı elenen takımı bul (Eğer hiç elenen yoksa 0 kabul et)
        max_elenen_puan = 0
        if elenen_takimlar:
            max_elenen_puan = max(t["puan"] for t in elenen_takimlar)

        # DURUM 1: Tek Aktif Takım Kaldıysa (SURVIVOR KURALI)
        if len(aktif_takimlar) == 1:
            hayatta_kalan = aktif_takimlar[0]
            # Eğer hayatta kalanın puanı, elenenlerin en iyisinden bile yüksekse
            # VEYA hiç elenen yoksa ama tek takım varsa (bu teorik, oyun başı hariç)
            # Oyun ANINDA biter. Diğerleri onu yakalayamaz.
            if hayatta_kalan["puan"] > max_elenen_puan:
                self._yarismayi_bitir(kazanan_id=hayatta_kalan["id"])
                return True
        
        # DURUM 2: Herkes Elendiyse (TIE-BREAKER KURALI)
        if len(aktif_takimlar) == 0:
            # En yüksek puanı bul
            en_yuksek_puan = max_elenen_puan # Zaten hepsi elendi
            
            # KURAL 3: BRONZ BARAJI (Kimse 2. soruyu bilemediyse)
            if en_yuksek_puan < 2:
                self._yarismayi_bitir(kazanan_id=None, ozel_mesaj="2. Soruyu Bilerek Bronz Rozet Alan Takım Olmadığı İçin 1. Yoktur.")
                return True
            
            # KURAL 2: Eşitlik ve Süre
            # En yüksek puanı alanları filtrele
            liderler = [t for t in elenen_takimlar if t["puan"] == en_yuksek_puan]
            
            # Süresi EN AZ olana göre sırala (Ascending)
            liderler.sort(key=lambda x: x["toplam_sure_saniye"])
            kazanan = liderler[0]
            
            self._yarismayi_bitir(kazanan_id=kazanan["id"])
            return True

        return False

    def get_aktif_takim_id(self):
        # Önce oyun bitmiş mi kontrol et (Survivor kuralı için)
        if self._oyun_bitti_mi_kontrol_et():
            return None

        takim_id_listesi = sorted(list(self.takimlar.keys()), key=lambda x: int(x.split('_')[1]))
        
        # Normal Sıra Döngüsü
        baslangic = self.aktif_takim_index % len(takim_id_listesi)
        for i in range(len(takim_id_listesi)):
            idx = (baslangic + i) % len(takim_id_listesi)
            tid = takim_id_listesi[idx]
            takim = self.takimlar[tid]
            
            if takim["aktif"] and self._tur_kontrolu(takim):
                return tid
        
        # Kimse bu turda oynayamıyorsa -> Tur Atla
        # NOT: Eğer herkes elendiyse yukarıdaki _oyun_bitti_mi zaten yakalardı.
        # Buraya geldiysek, herkes aktif ama herkes barajı geçti demektir.
        self.tur_numarasi += 1
        
        if self.tur_numarasi > 3: 
            # 10. soru bitti, herkes bitirdi. Puan/Süreye bak.
            self._oyun_bitti_mi_kontrol_et() # Bu fonksiyon kazananı belirler
            return None
        
        return self.get_aktif_takim_id()

    def _tur_kontrolu(self, takim):
        p = takim["puan"]
        if self.tur_numarasi == 1: return p < 2
        if self.tur_numarasi == 2: return p < 7
        if self.tur_numarasi == 3: return p < 10
        return False

    def soru_iste(self, takim_id):
        if self.yarışma_bitti: return {"success": False}
        
        # Güvenlik: Oyun bitmiş olabilir
        if self._oyun_bitti_mi_kontrol_et():
             return {"success": False, "hata": "Oyun bitti."}

        self.mevcut_soru_numarasi = self.takimlar[takim_id]["puan"] + 1
        soru = self.oyun_soru_listesi.get(self.mevcut_soru_numarasi)
        
        if not soru: return {"success": False, "hata": "Soru yok"}

        self.takimlar[takim_id]["son_soru_zamani"] = datetime.now().isoformat()
        self.mevcut_soru_verisi = soru
        self.takimlar[takim_id]["bulunan_beceri"] = False
        self.takimlar[takim_id]["bulunan_deger"] = False
        self.takimlar[takim_id]["kalan_deneme_hakki"] = 3
        
        return {"success": True, "metin": soru["metin"], "beceri_adi": soru["beceri_adi"], "deger_adi": soru["deger_adi"]}

    def cevap_ver(self, takim_id, tip, cumle):
        if self.yarışma_bitti or not self.mevcut_soru_verisi: return {"success": False}
        
        takim = self.takimlar[takim_id]
        start = datetime.fromisoformat(takim["son_soru_zamani"])
        gecen = (datetime.now() - start).total_seconds()
        
        # Elenme Kontrolü (Süre)
        if cumle == "SÜRE DOLDU" or gecen > 65:
            takim["aktif"] = False
            takim["toplam_sure_saniye"] += 60 # Ceza süresi
            self.mevcut_soru_verisi = None
            self._olay("Süre doldu, elendiniz.", "error", {"sonuc": "elendi"})
            
            # ELENME OLDUĞU İÇİN OYUN BİTTİ Mİ DİYE BAK (Survivor/Tie-Breaker)
            if self._oyun_bitti_mi_kontrol_et():
                return {"success": True, "sonuc": "elendi", "mesaj": "Süre doldu. Oyun Sona Erdi."}
                
            return {"success": True, "sonuc": "elendi", "mesaj": "Süre doldu."}

        dbeceri = self.mevcut_soru_verisi["beceri_cumlesi"].strip()
        ddeger = self.mevcut_soru_verisi["deger_cumlesi"].strip()
        cumle = cumle.strip()
        
        sonuc, mesaj = "yanlis", "Yanlış!"
        
        if tip == "beceri" and cumle == dbeceri:
            takim["bulunan_beceri"] = True; sonuc = "dogru_parca"; mesaj = "Beceri Doğru!"
        elif tip == "deger" and cumle == ddeger:
            takim["bulunan_deger"] = True; sonuc = "dogru_parca"; mesaj = "Değer Doğru!"
        else:
            takim["kalan_deneme_hakki"] -= 1

        if takim["bulunan_beceri"] and takim["bulunan_deger"]:
            takim["puan"] += 1; takim["toplam_sure_saniye"] += gecen
            self.mevcut_soru_verisi = None
            self._rozet_guncelle(takim)
            
            # PUAN ALDIĞI İÇİN OYUN BİTTİ Mİ DİYE BAK (Survivor Kuralı)
            if self._oyun_bitti_mi_kontrol_et():
                return {"success": True, "sonuc": "oyun_bitti", "mesaj": "TEBRİKLER! OYUNU KAZANDINIZ!"}
            
            p = takim["puan"]
            if p >= 10: 
                # Zaten yukarıdaki kontrol yakalar ama garanti olsun
                self._yarismayi_bitir(takim_id); sonuc = "oyun_bitti"; mesaj = "KAZANDINIZ!"
            elif p in [2, 7]: 
                sonuc = "tur_bitti"; mesaj = f"{p}. soru bitti, tur tamam!"
            else: 
                sonuc = "soru_bitti_devam_et"; mesaj = "Doğru! Devam..."
        
        elif takim["kalan_deneme_hakki"] <= 0:
            takim["aktif"] = False
            takim["toplam_sure_saniye"] += gecen
            self.mevcut_soru_verisi = None
            sonuc = "elendi"; mesaj = "Hak bitti."
            
            # ELENME OLDUĞU İÇİN OYUN BİTTİ Mİ BAK
            if self._oyun_bitti_mi_kontrol_et():
                return {"success": True, "sonuc": "elendi", "mesaj": "Elendiniz. Oyun Sona Erdi."}

        self._olay(mesaj, "success" if "dogru" in sonuc or "KAZANDINIZ" in mesaj else "error", {"tiklanan_cumle": cumle, "sonuc": sonuc})
        if sonuc != "dogru_parca": self._takim_ici_sirayi_degistir(takim_id)
        
        return {"success": True, "sonuc": sonuc, "mesaj": mesaj}

    def _olay(self, m, t, d): self.son_olay = {"zaman": time.time(), "mesaj": m, "tur": t, "detay": d}
    
    def _rozet_guncelle(self, t):
        p = t["puan"]; t["rozet"] = "altin" if p>=10 else "gümüş" if p>=7 else "bronz" if p>=2 else "yok"

    def _takim_ici_sirayi_degistir(self, tid):
        t = self.takimlar[tid]
        if len(t["uyeler"]) > 1: t["aktif_uye_index"] = (t["aktif_uye_index"] + 1) % len(t["uyeler"])

    def siradaki_takima_gec(self):
        if self.yarışma_bitti: return
        self.aktif_takim_index += 1
        self.mevcut_soru_verisi = None

    def _yarismayi_bitir(self, kazanan_id=None, ozel_mesaj=None):
        if self.yarışma_bitti: return self.kazanan_takim_id
        
        self.yarışma_bitti = True
        self.kazanan_takim_id = kazanan_id
        self.mevcut_soru_verisi = None
        self.bitis_mesaji = ozel_mesaj if ozel_mesaj else ""
        
        if kazanan_id:
            k = self.takimlar[kazanan_id]
            # Sadece Rozet "yok" değilse kaydet (İsteğe bağlı, ama genelde kaydedilir)
            kaydet_yarışma_sonucu(k["isim"], k["rozet"], k["puan"], k["toplam_sure_saniye"], self.okul, self.sinif)
            
            # Derece Kontrolü
            s = load_takim_skorlari()
            # Listede 10 kişiden az varsa VEYA Puanı sonuncudan yüksekse VEYA Puan eşit Süre kısaysa
            son = s[-1] if s else None
            if not son or len(s) < 10:
                self.dereceye_girdi_mi = True
            elif k["puan"] > son["soru_sayisi"]:
                self.dereceye_girdi_mi = True
            elif k["puan"] == son["soru_sayisi"] and k["toplam_sure_saniye"] < son["toplam_sure_saniye"]:
                self.dereceye_girdi_mi = True
            else:
                self.dereceye_girdi_mi = False
        
        return self.kazanan_takim_id

    def durumu_json_yap(self, izleyen_no=None, izleyen_rol=None):
        aid = self.get_aktif_takim_id()
        ks = 60; msv = None; kid = None
        
        if aid:
            t = self.takimlar[aid]
            self.mevcut_soru_numarasi = t["puan"] + 1
            if t["uyeler"]: kid = str(t["uyeler"][t["aktif_uye_index"] % len(t["uyeler"])]["no"]).strip()
            
            if self.mevcut_soru_verisi:
                start = datetime.fromisoformat(t["son_soru_zamani"])
                ks = max(0, 60 - int((datetime.now() - start).total_seconds()))
                msv = {
                    "metin": self.mevcut_soru_verisi["metin"],
                    "beceri_adi": self.mevcut_soru_verisi.get("beceri_adi", "Beceri"),
                    "deger_adi": self.mevcut_soru_verisi.get("deger_adi", "Değer")
                }
                
        return {
            "takimlar": list(self.takimlar.values()), "aktif_takim_id": aid,
            "aktif_takim_kaptani_id": kid, "yarışma_bitti": self.yarışma_bitti,
            "kazanan_takim_id": self.kazanan_takim_id, "kalan_saniye": ks,
            "mevcut_soru_numarasi": self.mevcut_soru_numarasi, "mevcut_soru_verisi": msv,
            "son_olay": self.son_olay, "dereceye_girdi_mi": self.dereceye_girdi_mi,
            "bitis_mesaji": self.bitis_mesaji # Frontend bunu yakalamalı
        }
