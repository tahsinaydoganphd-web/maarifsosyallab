# -*- coding: utf-8 -*-
"""
TAKIM YARIŞMASI MODÜLÜ (SÜRÜM 9 - NİHAİ STATİK BANKA)
- Bu sürüm, Gemini'yi TAMAMEN kaldırır.
- Tüm soruları 'bireysel_soru_bankasi.json' dosyasından okur.
- Kullanıcının 15 kuralını (Tur Atlama, Puanlama, Eleme) uygular.
"""

import json
import os
import random
from datetime import datetime

# --- Soru Bankası Yükleyicisi ---
SORU_BANKASI_FILE = 'bireysel_soru_bankasi.json'

def load_soru_bankasi():
    """100 soruluk ana bankayı JSON'dan yükler."""
    if not os.path.exists(SORU_BANKASI_FILE):
        print(f"HATA: '{SORU_BANKASI_FILE}' bulunamadı!")
        return {"kolay": [], "orta": [], "zor": []}
    
    try:
        with open(SORU_BANKASI_FILE, 'r', encoding='utf-8') as f:
            sorular = json.load(f)
        
        banka = {
            "kolay": [s for s in sorular if s.get('zorluk') == 'kolay'],
            "orta": [s for s in sorular if s.get('zorluk') == 'orta'],
            "zor": [s for s in sorular if s.get('zorluk') == 'zor']
        }
        print(f"Takım Yarışması için Soru Bankası yüklendi: {len(banka['kolay'])} Kolay, {len(banka['orta'])} Orta, {len(banka['zor'])} Zor.")
        return banka
    except Exception as e:
        print(f"Soru bankası yüklenirken hata: {e}")
        return {"kolay": [], "orta": [], "zor": []}

# 100 soruluk bankayı sunucu başlarken BİR KEZ hafızaya yükle
SORU_BANKASI = load_soru_bankasi()
# --- BİTTİ ---

# --- Veritabanı Ayarları (Skor Tablosu) ---
TAKIM_SKOR_DB_FILE = 'takim_sonuclari.json'

def load_takim_skorlari():
    """ Takım yarışması LİDERLİK TABLOSUNU JSON dosyasından yükler. """
    if os.path.exists(TAKIM_SKOR_DB_FILE):
        try:
            with open(TAKIM_SKOR_DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

def save_takim_skorlari(data):
    """ Takım yarışması LİDERLİK TABLOSUNU JSON dosyasına kaydeder. """
    try:
        with open(TAKIM_SKOR_DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Takım skorlarını kaydetme hatası: {e}")

def kaydet_yarışma_sonucu(takim_adi, rozet, soru_sayisi, toplam_sure, okul, sinif):
    """(Kural 11, 13) Kazanan takımın skorunu liderlik tablosuna ekler."""
    try:
        skor_tablosu = load_takim_skorlari()
        
        rozet_degeri = {"altin": 3, "gümüş": 2, "bronz": 1, "yok": 0}
        
        yeni_skor = {
            "takim_adi": takim_adi,
            "okul_sinif": f"{okul} / {sinif}",
            "rozet": rozet,
            "rozet_degeri": rozet_degeri.get(rozet, 0),
            "soru_sayisi": soru_sayisi,
            "toplam_sure_saniye": round(toplam_sure, 2),
            "tarih": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        
        skor_tablosu.append(yeni_skor)
        
        skor_tablosu.sort(
            key=lambda x: (
                -x["rozet_degeri"], 
                -x["soru_sayisi"], 
                x["toplam_sure_saniye"]
            )
        )
        
        guncel_tablo = skor_tablosu[:10] # Sadece ilk 10'u tut
        save_takim_skorlari(guncel_tablo)
        
        return {"success": True, "mesaj": "Skor tablosu güncellendi."}
    except Exception as e:
        print(f"Takım skoru kaydetme hatası: {e}")
        return {"success": False, "hata": str(e)}

# --- Ana Yarışma Sınıfı ---

class TakimYarismasi:
    """
    Bir takım yarışması oturumunun tüm durumunu (state) yöneten sınıf.
    """
    
    def __init__(self, takimlar_listesi, okul, sinif):
        """Sınıf başlatıcı (initializer) - (NİHAİ SÜRÜM)"""
        
        self.takimlar = self._takimlari_baslat(takimlar_listesi) 
        self.okul = okul
        self.sinif = sinif
        self.yarışma_bitti = False 
        self.mevcut_soru_numarasi = 1
        self.mevcut_soru_verisi = None
        self.kazanan_takim_id = None
        self.aktif_takim_index = 0 
        self.tur_numarasi = 1
        # --- YENİ: Son Olay Hafızası (İzleyiciler için) ---
        self.son_olay = {"zaman": 0, "mesaj": "", "tur": "", "detay": {}}
        self.dereceye_girdi_mi = False # İlk 10'a girdi mi?
        
        # --- YENİ EKLENDİ (EKSİK OLAN SATIR) ---
        # Oyunun 10 sorusunu en başta oluşturur ve hafızaya alır
        self.oyun_soru_listesi = self._oyun_sorularini_olustur()
        # --- BİTTİ ---

    def _oyun_sorularini_olustur(self):
        """(YENİ) Soru bankasından 10 soru seçer ve KARIŞTIRIR."""
        try:
            kolay_secim = random.sample(SORU_BANKASI["kolay"], 3)
            orta_secim = random.sample(SORU_BANKASI["orta"], 4)
            zor_secim = random.sample(SORU_BANKASI["zor"], 3)
            
            # Paketi oluştur
            tam_liste = kolay_secim + orta_secim + zor_secim
            
            # 👇👇👇 DÜZELTME: LİSTEYİ KARIŞTIR 👇👇👇
            random.shuffle(tam_liste) 
            # 👆👆👆 ARTIK SORULARIN YERİ HEP FARKLI OLACAK
            
            print("Oyun için 10 soruluk KARIŞIK liste oluşturuldu.")
            return {i + 1: soru for i, soru in enumerate(tam_liste)}
            
        except ValueError as e:
            print(f"UYARI: Bankada yeterli soru yok! {e}")
            return {} 
        except Exception as e:
            print(f"HATA: Oyun soruları oluşturulamadı: {e}")
            return {}

    def _takimlari_baslat(self, takimlar_listesi):
        """Gelen takım listesini oyun formatına çevirir."""
        oyun_takimlari = {}
        for i, takim in enumerate(takimlar_listesi):
            uyeler = takim.get('uyeler', [])
            
            # 👇👇👇 DÜZELTME: Üye ID'lerini string'e çevirerek kaydet 👇👇👇
            for uye in uyeler:
                uye['no'] = str(uye.get('no')).strip()
            # 👆👆👆 BİTTİ 👆👆👆

            isim_uyeleri = [uye.get('ad_soyad', 'Bilinmiyor').split(' ')[0] for uye in uyeler[:3]]
            takim_adi = "-".join(isim_uyeleri) if isim_uyeleri else f"Takım {i+1}"
            
            takim_id = f"takim_{i}"
            
            oyun_takimlari[takim_id] = {
                "id": takim_id,
                "isim": takim_adi,
                "uyeler": uyeler,
                "aktif_uye_index": 0, 
                "aktif": True,
                "puan": 0, 
                "rozet": "yok",
                "kalan_deneme_hakki": 3,
                "bulunan_beceri": False,
                "bulunan_deger": False,
                "toplam_sure_saniye": 0,
                "son_soru_zamani": None 
            }
        return oyun_takimlari

    def get_aktif_takim_id(self):
        """(DÜZELTİLMİŞ) Sırası gelen ve elenmemiş takımın ID'sini döndürür."""
        if self.yarışma_bitti:
            return None
            
        # Takım ID'lerini sıralı bir listeye çevir (Garanti sıra için)
        # Takım ID'leri 'takim_0', 'takim_1' formatında olduğu için sıralama düzgün çalışır
        takim_id_listesi = sorted(list(self.takimlar.keys()), key=lambda x: int(x.split('_')[1]))
        
        # 1. Aktif (elenmemiş) kaç takım kaldı?
        aktif_takimlar_listesi = [t for t in self.takimlar.values() if t["aktif"]]
        
        if len(aktif_takimlar_listesi) == 0:
            return self._yarismayi_bitir(kazanan_id=None)
        
        if len(aktif_takimlar_listesi) == 1:
            tek_kalan = aktif_takimlar_listesi[0]
            # Tek kalan takımın oynaması gereken tur kalmadıysa kazanır
            if not self._tur_kontrolu(tek_kalan):
                return self._yarismayi_bitir(kazanan_id=tek_kalan['id'])

        # 2. Normal tur kontrolü (Sıradaki kişiden başlayarak dön)
        baslangic_index = self.aktif_takim_index % len(takim_id_listesi)
        
        # Listeyi o anki sıradan itibaren döndür (Round Robin)
        for i in range(len(takim_id_listesi)):
            su_anki_index = (baslangic_index + i) % len(takim_id_listesi)
            takim_id = takim_id_listesi[su_anki_index]
            takim = self.takimlar[takim_id]
            
            # Takım aktif mi VE bu turda oynaması gerekiyor mu?
            if takim["aktif"] and self._tur_kontrolu(takim):
                # Buradaki index güncelleme satırını sildik.
                # Sıra sadece "siradaki_takima_gec" çağrıldığında değişecek.
                return takim_id
        
        # 3. Tur atlama kontrolü (Kimse bulunamadıysa tur bitmiştir)
        if not self._tur_atlamaya_hazir_mi():
            print(f"Tur {self.tur_numarasi} bitti, bir sonraki tura geçiliyor.")
            self.tur_numarasi += 1
            
            # 3. Tur da bittiyse oyun biter
            if self.tur_numarasi > 3: 
                return self._yarismayi_bitir(kazanan_id=None)
            
            # Tur atladıktan sonra tekrar (baştan değil, kalınan yerden) kontrol et
            return self.get_aktif_takim_id()
        
        return self._yarismayi_bitir(kazanan_id=None)

    def _tur_kontrolu(self, takim):
        puan = takim["puan"]
        if self.tur_numarasi == 1: return puan < 2      # Herkes 2'ye koşuyor
        if self.tur_numarasi == 2: return 2 <= puan < 7 # Sadece 2'yi geçenler 7'ye koşuyor
        if self.tur_numarasi == 3: return 7 <= puan < 10 # Sadece 7'yi geçenler 10'a koşuyor
        return False

    def _tur_atlamaya_hazir_mi(self):
        """(Kural 6, 7) Hala mevcut turda oynaması gereken bir takım var mı?"""
        for takim in self.takimlar.values():
            if takim["aktif"] and self._tur_kontrolu(takim):
                return True # Evet, hala oynaması gereken var
        return False # Herkes bu turu bitirdi

    def soru_iste(self, takim_id, model=None):
        """
        (SÜRÜM 9 - SABİT LİSTE) Oyunun soru listesinden sıradaki soruyu alır.
        """
        if self.yarışma_bitti:
            return {"success": False, "hata": "Yarışma bitti."}
            
        # 1. Soru Numarasını belirle
        self.mevcut_soru_numarasi = self.takimlar[takim_id]["puan"] + 1
        soru_no = self.mevcut_soru_numarasi
        
        # 2. Soruyu bankadan değil, OYUNUN LİSTESİNDEN al
        secilen_soru = self.oyun_soru_listesi.get(soru_no)
        
        if not secilen_soru:
             print(f"HATA: Soru {soru_no} oyun listesinde bulunamadı! Banka boş olabilir.")
             return {"success": False, "hata": f"Soru {soru_no} oyun listesinde bulunamadı!"}

        # 3. Oyunu güncelle
        self.takimlar[takim_id]["son_soru_zamani"] = datetime.now().isoformat()
        
        # Soru verisini (cevap anahtarı) hafızaya al
        self.mevcut_soru_verisi = secilen_soru
        
        # Takımın durumunu sıfırla
        self.takimlar[takim_id]["bulunan_beceri"] = False
        self.takimlar[takim_id]["bulunan_deger"] = False
        self.takimlar[takim_id]["kalan_deneme_hakki"] = 3
        
        print(f"Takım Yarışması: Soru {soru_no} (Sabit Oyun Listesinden) yüklendi.")
        
        # 4. Veriyi döndür
        return {
            "success": True,
            "soru_numarasi": self.mevcut_soru_numarasi,
            "metin": secilen_soru["metin"],
            "beceri_adi": secilen_soru["beceri_adi"],
            "deger_adi": secilen_soru["deger_adi"]
        }

    def cevap_ver(self, takim_id, tiklanan_tip, tiklanan_cumle):
        """(Kural 1, 60s, Butonlar) Bir takımın cevabını işler."""
        if self.yarışma_bitti:
            return {"success": False, "hata": "Yarışma bitti."}
            
        takim = self.takimlar.get(takim_id)
        if not takim or not takim["aktif"]:
            return {"success": False, "hata": "Takım bulunamadı veya elendi."}
        
        if not self.mevcut_soru_verisi:
            return {"success": False, "hata": "Aktif soru bulunamadı. Lütfen önce 'Soruyu Göster'e basın."}

        # Süre kontrolü (Kural 60s)
        zaman_baslangici = datetime.fromisoformat(takim["son_soru_zamani"])
        harcanan_sure = (datetime.now() - zaman_baslangici).total_seconds()
        
        if tiklanan_cumle == "SÜRE DOLDU" or harcanan_sure > 60:
            takim["aktif"] = False # Elendi
            takim["toplam_sure_saniye"] += 60
            self.mevcut_soru_verisi = None
            print(f"Takım {takim['isim']} süre dolduğu için elendi.")
            return {"success": True, "sonuc": "elendi", "mesaj": "Süre dolduğu için elendiniz.", "guncel_takim_durumu": takim}

        # Cevap anahtarını ve tıklanan cümleyi al
        dogru_beceri_cumlesi = self.mevcut_soru_verisi["beceri_cumlesi"].strip()
        dogru_deger_cumlesi = self.mevcut_soru_verisi["deger_cumlesi"].strip()
        tiklanan_cumle = tiklanan_cumle.strip()

        sonuc = "yanlis"
        mesaj = f"Yanlış eşleştirme. Kalan deneme hakkınız: {takim['kalan_deneme_hakki'] - 1}"

        # 1. Doğru Buton + Doğru Cümle (Beceri)
        if tiklanan_tip == "beceri" and tiklanan_cumle == dogru_beceri_cumlesi:
            takim["bulunan_beceri"] = True
            sonuc = "dogru_parca"
            mesaj = "Beceri cümlesi doğru! Şimdi değeri bulun."
        
        # 2. Doğru Buton + Doğru Cümle (Değer)
        elif tiklanan_tip == "deger" and tiklanan_cumle == dogru_deger_cumlesi:
            takim["bulunan_deger"] = True
            sonuc = "dogru_parca"
            mesaj = "Değer cümlesi doğru! Şimdi beceriyi bulun."
        
        else:
            # SADECE YANLIŞ CEVAPLARDA hak düşür (Kural 1)
            takim["kalan_deneme_hakki"] -= 1
        
        # Durum kontrolü:
        
        # A. Soru Bitti mi? (Her iki parça da bulunduysa)
        if takim["bulunan_beceri"] and takim["bulunan_deger"]:
            takim["puan"] += 1
            takim["toplam_sure_saniye"] += harcanan_sure
            self.mevcut_soru_verisi = None 
            
            self._rozet_guncelle(takim) # Rozeti hesapla
            
            puan = takim["puan"]
            
            # --- YENİ KURAL MANTIĞI (2-7-10 SİSTEMİ) ---
            
            # 1. KAZANMA (10. Soruyu Yapan İlk Takım)
            if puan >= 10:
                self._yarismayi_bitir(kazanan_id=takim_id)
                sonuc = "oyun_bitti"
                mesaj = f"TEBRİKLER! {takim['isim']} 10 soruyu tamamladı ve ALTIN ROZET ile kazandı!"

            # 2. TUR BİTİŞ NOKTALARI (2. ve 7. Sorular - DURAKLAR)
            # Kural: Puan 2 veya 7 olduğunda "tur_bitti" diyerek sırayı diğer takıma salar.
            elif puan == 2: 
                sonuc = "tur_bitti"
                mesaj = f"TEBRİKLER! {takim['isim']} 2. soruyu bildi ve BRONZ rozeti aldı! Sıra diğer takıma geçiyor."
            elif puan == 7:
                sonuc = "tur_bitti"
                mesaj = f"TEBRİKLER! {takim['isim']} 7. soruyu bildi ve GÜMÜŞ rozeti aldı! Sıra diğer takıma geçiyor."
                
            # 3. DEVAM ETME (Ara Sorular: 1, 3, 4, 5, 6, 8, 9)
            # Kural: Durak noktası değilse aynı takım devam eder.
            else:
                sonuc = "soru_bitti_devam_et"
                mesaj = f"Doğru! {puan}. soruyu tamamladınız. Sıradaki soruya devam!"
            # -------------------------------------------

        # B. Elendi mi?
        elif takim["kalan_deneme_hakki"] <= 0:
            takim["aktif"] = False
            takim["toplam_sure_saniye"] += harcanan_sure
            self.mevcut_soru_verisi = None 
            sonuc = "elendi"
            mesaj = "3 deneme hakkınız bittiği için elendiniz."

        # 👇👇👇 BURADAN AŞAĞISINI KONTROL EDİN 👇👇👇
        
        # --- 1. SON OLAYI KAYDET (İzleyiciler İçin) ---
        import time
        
        # Olay türünü belirle (renk için)
        olay_turu = "info"
        if sonuc == "yanlis" or sonuc == "elendi": 
            olay_turu = "error"
        elif sonuc == "dogru_parca" or "TEBRİKLER" in mesaj: 
            olay_turu = "success"

        # Hafızaya kaydet
        self.son_olay = {
            "zaman": time.time(),
            "mesaj": mesaj,
            "tur": olay_turu,
            "detay": {
                "tiklanan_cumle": tiklanan_cumle,
                "tiklanan_tip": tiklanan_tip,
                "sonuc": sonuc
            }
        }

        # --- 2. SIRA DEĞİŞTİRME ---
        # Eğer işlem bittiyse (Soru bildi, Yanlış yaptı, Elendi veya Tur bitti)
        # Sadece "dogru_parca" (yani yarım kalan iş) değilse sıra değişsin.
        if sonuc != "dogru_parca": 
            self._takim_ici_sirayi_degistir(takim_id)

        # --- 3. SONUCU DÖNDÜR ---
        return {"success": True, "sonuc": sonuc, "mesaj": mesaj, "guncel_takim_durumu": takim}
        
    def _rozet_guncelle(self, takim):
        """(Kural 1) Takımın puanına göre rozet durumunu günceller (2-7-10 kuralı)"""
        puan = takim["puan"]
        if puan >= 10:
            takim["rozet"] = "altin"
        elif puan >= 7:
            takim["rozet"] = "gümüş"
        elif puan >= 2:
            takim["rozet"] = "bronz"
        else:
            takim["rozet"] = "yok"
    
    def _takim_ici_sirayi_degistir(self, takim_id):
        """(YENİ) O takımın içindeki kaptanlık sırasını bir sonraki üyeye geçirir."""
        if takim_id in self.takimlar:
            takim = self.takimlar[takim_id]
            uye_sayisi = len(takim["uyeler"])
            if uye_sayisi > 1:
                takim["aktif_uye_index"] = (takim["aktif_uye_index"] + 1) % uye_sayisi
    
    def siradaki_takima_gec(self):
        """Manuel olarak sıradaki takıma geçer."""
        if self.yarışma_bitti:
            return {"success": False, "hata": "Yarışma bitti."}
        
        self.aktif_takim_index = (self.aktif_takim_index + 1) % len(self.takimlar)
        self.mevcut_soru_verisi = None
        
        yeni_aktif_takim_id = self.get_aktif_takim_id()
        if yeni_aktif_takim_id:
            return {"success": True, "yeni_aktif_takim_id": yeni_aktif_takim_id}
        else:
            return {"success": True, "yeni_aktif_takim_id": None, "mesaj": "Oyun bitti."}
            
    def _yarismayi_bitir(self, kazanan_id=None):
        """(Kural 11, 13) Yarışmayı bitirir, kazananı ve dereceyi belirler."""
        if self.yarışma_bitti:
            return self.kazanan_takim_id
            
        self.yarışma_bitti = True
        
        if kazanan_id:
             self.kazanan_takim_id = kazanan_id
             # --- YENİ: Derece Kontrolü ---
             import takim_yarismasi_modul as ty # Kendini import et (skor yüklemek için)
             skorlar = ty.load_takim_skorlari()
             kazanan_takim = self.takimlar[kazanan_id]
             
             # Mevcut 10. skorla karşılaştır
             if len(skorlar) < 10:
                 self.dereceye_girdi_mi = True
             else:
                 en_kotu_skor = skorlar[-1]
                 # Basit karşılaştırma: Puanı yüksekse veya (puan eşitse süresi kısaysa)
                 if (kazanan_takim["puan"] > en_kotu_skor["soru_sayisi"]) or \
                    (kazanan_takim["puan"] == en_kotu_skor["soru_sayisi"] and kazanan_takim["toplam_sure_saniye"] < en_kotu_skor["toplam_sure_saniye"]):
                     self.dereceye_girdi_mi = True
             # -----------------------------
             print(f"Yarışma bitti. Kazanan: {kazanan_id}. Dereceye girdi mi: {self.dereceye_girdi_mi}")
        else:
            # Kimse kazanamadıysa (Herkes elendi)
            self.kazanan_takim_id = None
            self.dereceye_girdi_mi = False

        return self.kazanan_takim_id

    def durumu_json_yap(self):
        """Oyunun mevcut durumunu JSON'a hazırlar."""
        
        aktif_takim_id = self.get_aktif_takim_id()
        
        kalan_saniye = 60
        mevcut_soru_kisitli_veri = None
        
        # --- YENİ: Dönüşümlü Kaptan ID'sini Bulma ---
        aktif_takim_kaptani_id = None
        if aktif_takim_id:
            aktif_takim = self.takimlar[aktif_takim_id]
            if aktif_takim["uyeler"]:
                su_anki_index = aktif_takim["aktif_uye_index"]
                su_anki_index = su_anki_index % len(aktif_takim["uyeler"])
                
                # 👇👇👇 DÜZELTME: ID'yi KESİNLİKLE STRING YAP 👇👇👇
                raw_id = aktif_takim["uyeler"][su_anki_index]["no"]
                aktif_takim_kaptani_id = str(raw_id).strip()
                # 👆👆👆 BİTTİ 👆👆👆

        if aktif_takim_id:
            # Soru numarasını takımın puanına göre ayarla
            self.mevcut_soru_numarasi = self.takimlar[aktif_takim_id]["puan"] + 1

            if self.mevcut_soru_verisi:
                zaman_baslangici = datetime.fromisoformat(self.takimlar[aktif_takim_id]["son_soru_zamani"])
                gecen_saniye = (datetime.now() - zaman_baslangici).total_seconds()
                kalan_saniye = max(0, 60 - int(gecen_saniye))
                
                mevcut_soru_kisitli_veri = {
                    "metin": self.mevcut_soru_verisi["metin"],
                    "beceri_adi": self.mevcut_soru_verisi["beceri_adi"],
                    "deger_adi": self.mevcut_soru_verisi["deger_adi"]
                }
            
        return {
            "takimlar": list(self.takimlar.values()),
            "aktif_takim_id": aktif_takim_id,
            "aktif_takim_kaptani_id": aktif_takim_kaptani_id,
            "tur_numarasi": self.tur_numarasi,
            "yarışma_bitti": self.yarışma_bitti,
            "kazanan_takim_id": self.kazanan_takim_id,
            "kalan_saniye": kalan_saniye,
            "mevcut_soru_numarasi": self.mevcut_soru_numarasi,
            "mevcut_soru_verisi": mevcut_soru_kisitli_veri,
            "son_olay": self.son_olay,
            "dereceye_girdi_mi": self.dereceye_girdi_mi # <-- BU SATIRI EKLEYİN
        }