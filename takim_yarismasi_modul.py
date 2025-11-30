# -*- coding: utf-8 -*-
"""
TAKIM YARIŞMASI MODÜLÜ (SÜRÜM 10 - FİNAL DÜZELTME)
- Tek takım/Çok takım ayrımı kaldırıldı.
- Oyunun anında bitmesi engellendi.
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
        print(f"Soru bankası hatası: {e}")
        return {"kolay": [], "orta": [], "zor": []}

SORU_BANKASI = load_soru_bankasi()
TAKIM_SKOR_DB_FILE = 'takim_sonuclari.json'

def load_takim_skorlari():
    if os.path.exists(TAKIM_SKOR_DB_FILE):
        try:
            with open(TAKIM_SKOR_DB_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except: return []
    return []

def save_takim_skorlari(data):
    try:
        with open(TAKIM_SKOR_DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except: pass

def kaydet_yarışma_sonucu(takim_adi, rozet, soru_sayisi, toplam_sure, okul, sinif):
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
        skor_tablosu.sort(key=lambda x: (-x["rozet_degeri"], -x["soru_sayisi"], x["toplam_sure_saniye"]))
        save_takim_skorlari(skor_tablosu[:10])
    except: pass

# --- Ana Yarışma Sınıfı ---

class TakimYarismasi:
    def __init__(self, takimlar_listesi, okul, sinif):
        self.takimlar = self._takimlari_baslat(takimlar_listesi) 
        self.okul = okul
        self.sinif = sinif
        self.yarışma_bitti = False 
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

    def get_aktif_takim_id(self):
        """HATA DÜZELTİLDİ: Tek takım olsa bile döngüye girer, oyunu bitirmez."""
        if self.yarışma_bitti: return None
        
        takim_id_listesi = sorted(list(self.takimlar.keys()), key=lambda x: int(x.split('_')[1]))
        aktifler = [t for t in self.takimlar.values() if t["aktif"]]
        
        if not aktifler: return self._yarismayi_bitir()

        # Normal Sıra Kontrolü
        baslangic = self.aktif_takim_index % len(takim_id_listesi)
        for i in range(len(takim_id_listesi)):
            idx = (baslangic + i) % len(takim_id_listesi)
            tid = takim_id_listesi[idx]
            takim = self.takimlar[tid]
            
            # Takım aktif mi VE bu turda oynaması gerekiyor mu?
            if takim["aktif"] and self._tur_kontrolu(takim):
                return tid
        
        # Eğer kimse bu turda oynayamıyorsa -> Tur Atla
        print(f"Tur {self.tur_numarasi} bitti. Yeni tura geçiliyor.")
        self.tur_numarasi += 1
        
        if self.tur_numarasi > 3: 
            kazanan = max(aktifler, key=lambda t: t['puan'])
            return self._yarismayi_bitir(kazanan_id=kazanan['id'])
        
        # Tur atladıktan sonra tekrar dene (Recursive)
        return self.get_aktif_takim_id()

    def _tur_kontrolu(self, takim):
        p = takim["puan"]
        if self.tur_numarasi == 1: return p < 2
        if self.tur_numarasi == 2: return p < 7
        if self.tur_numarasi == 3: return p < 10
        return False

    def soru_iste(self, takim_id):
        if self.yarışma_bitti: return {"success": False}
        
        aktif_id = self.get_aktif_takim_id()
        if aktif_id != takim_id and not self.yarışma_bitti:
             pass 

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
        
        if cumle == "SÜRE DOLDU" or gecen > 65:
            takim["aktif"] = False
            self.mevcut_soru_verisi = None
            self._olay("Süre doldu, elendiniz.", "error", {"sonuc": "elendi"})
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
            
            p = takim["puan"]
            if p >= 10: 
                self._yarismayi_bitir(takim_id); sonuc = "oyun_bitti"; mesaj = "KAZANDINIZ!"
            elif p in [2, 7]: 
                sonuc = "tur_bitti"; mesaj = f"{p}. soru bitti, tur tamam!"
            else: 
                sonuc = "soru_bitti_devam_et"; mesaj = "Doğru! Devam..."
        
        elif takim["kalan_deneme_hakki"] <= 0:
            takim["aktif"] = False; self.mevcut_soru_verisi = None; sonuc = "elendi"; mesaj = "Hak bitti."

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

    def _yarismayi_bitir(self, kazanan_id=None):
        if self.yarışma_bitti: return self.kazanan_takim_id
        self.yarışma_bitti = True
        self.kazanan_takim_id = kazanan_id
        self.mevcut_soru_verisi = None
        
        if kazanan_id:
            k = self.takimlar[kazanan_id]
            kaydet_yarışma_sonucu(k["isim"], k["rozet"], k["puan"], k["toplam_sure_saniye"], self.okul, self.sinif)
            
            s = load_takim_skorlari()
            self.dereceye_girdi_mi = len(s) < 10 or (k["puan"] > s[-1]["soru_sayisi"])
            
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
            "son_olay": self.son_olay, "dereceye_girdi_mi": self.dereceye_girdi_mi
        }
