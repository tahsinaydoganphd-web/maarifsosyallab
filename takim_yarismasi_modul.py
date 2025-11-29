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

        # --- HİZALAMASI DÜZELTİLEN KISIM ---
        if self.takimlar:
            # takim_0, takim_1 şeklindeki ID'leri numarasına göre sırala
            sirali_idler = sorted(list(self.takimlar.keys()), key=lambda x: int(x.split('_')[1]))
            self.siradaki_takim_id = sirali_idler[0]
        else:
            self.siradaki_takim_id = None

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
        (SÜRÜM 9 - SABİT LİSTE + MÖ DÜZELTMESİ) 
        Senin sistemine uygun olan, listeden sırayla çeken koddur.
        """
        if self.yarışma_bitti:
            return {"success": False, "hata": "Yarışma bitti."}
            
        # 1. Soru Numarasını belirle (Puan 0 ise 1. soru, Puan 1 ise 2. soru)
        self.mevcut_soru_numarasi = self.takimlar[takim_id]["puan"] + 1
        soru_no = self.mevcut_soru_numarasi
        
        # 2. Soruyu SENİN OYUN LİSTENDEN çekiyoruz (Havuzdan değil!)
        secilen_soru = self.oyun_soru_listesi.get(soru_no)
        
        if not secilen_soru:
             # Soru yoksa oyun bitmiştir
             self.oyunu_bitir_ve_kazanani_belirle()
             return {"success": False, "hata": "Sorular bitti."}

        # --- MÖ. 3000 DÜZELTMESİ BURADA ---
        temiz_metin = secilen_soru["metin"]
        temiz_metin = temiz_metin.replace("MÖ.", "MÖ").replace("M.Ö.", "MÖ")
        temiz_metin = temiz_metin.replace("MS.", "MS").replace("M.S.", "MS")
        temiz_metin = temiz_metin.replace("vb.", "vb")
        
        beceri_c = secilen_soru["beceri_cumlesi"].replace("MÖ.", "MÖ").replace("M.Ö.", "MÖ")
        deger_c = secilen_soru["deger_cumlesi"].replace("MÖ.", "MÖ").replace("M.Ö.", "MÖ")

        # Orijinal veriyi bozmadan kopyala ve temizle
        soru_kopya = secilen_soru.copy()
        soru_kopya["metin"] = temiz_metin
        soru_kopya["beceri_cumlesi"] = beceri_c
        soru_kopya["deger_cumlesi"] = deger_c
        # ----------------------------------

        # 3. Oyunu güncelle
        self.takimlar[takim_id]["son_soru_zamani"] = datetime.now().isoformat()
        self.mevcut_soru_verisi = soru_kopya
        
        # Takım durumunu sıfırla (Yeni soruya geçtiği için)
        self.takimlar[takim_id]["bulunan_beceri"] = False
        self.takimlar[takim_id]["bulunan_deger"] = False
        self.takimlar[takim_id]["kalan_deneme_hakki"] = 3
        
        print(f"Takım Yarışması: Soru {soru_no} (Sabit Listeden) yüklendi.")
        
        # 4. Veriyi döndür
        return {
            "success": True,
            "soru_numarasi": self.mevcut_soru_numarasi,
            "metin": soru_kopya["metin"],
            "beceri_adi": soru_kopya["beceri_adi"],
            "deger_adi": soru_kopya["deger_adi"]
        }

    def cevap_ver(self, takim_id, tiklanan_tip, tiklanan_cumle):
        """(DÜZELTİLDİ: Tek Takım Kaldığında Rozet Sonrası Devam Etme)"""
        if self.yarışma_bitti: return {"success": False, "hata": "Yarışma bitti."}
            
        takim = self.takimlar.get(takim_id)
        if not takim or not takim.get("aktif", True) or takim.get("elendi", False):
            return {"success": False, "hata": "Takım elendi."}
        
        if not self.mevcut_soru_verisi: return {"success": False, "hata": "Aktif soru yok."}

        # Cevapları karşılaştır
        dogru_beceri = self.mevcut_soru_verisi["beceri_cumlesi"].strip()
        dogru_deger = self.mevcut_soru_verisi["deger_cumlesi"].strip()
        tiklanan = tiklanan_cumle.strip()

        sonuc = "yanlis"
        mesaj = "Yanlış cevap!"

        # Doğru mu?
        if (tiklanan_tip == "beceri" and tiklanan == dogru_beceri):
            takim["bulunan_beceri"] = True
            sonuc = "dogru_parca"
        elif (tiklanan_tip == "deger" and tiklanan == dogru_deger):
            takim["bulunan_deger"] = True
            sonuc = "dogru_parca"
        else:
            # YANLIŞ -> Hak düşür
            takim["kalan_deneme_hakki"] -= 1
            if takim["kalan_deneme_hakki"] <= 0:
                takim["elendi"] = True
                takim["aktif"] = False
                
                # Aktif takım kaldı mı?
                aktifler = [t for t in self.takimlar.values() if not t.get("elendi", False)]
                
                if len(aktifler) == 0:
                    self.oyunu_bitir_ve_kazanani_belirle()
                    return {"success": False, "sonuc": "elendi", "oyun_bitti": True, "mesaj": "Herkes elendi! Oyun bitti."}
                elif len(aktifler) == 1:
                    self.kazanan_takim_id = aktifler[0]["id"]
                    self.yarışma_bitti = True
                    return {"success": False, "sonuc": "elendi", "oyun_bitti": True, "mesaj": f"Elendiniz! Kazanan: {aktifler[0]['isim']}"}
                else:
                    self.siradaki_takima_gec()
                    return {"success": False, "sonuc": "elendi", "mesaj": "Elendiniz, sıra diğer takımda."}
            else:
                return {"success": False, "sonuc": "yanlis", "mesaj": f"Yanlış! Kalan hak: {takim['kalan_deneme_hakki']}"}

        # Parça Doğruysa Tamamlandı mı?
        if sonuc == "dogru_parca":
            if takim["bulunan_beceri"] and takim["bulunan_deger"]:
                takim["puan"] += 1
                self.mevcut_soru_verisi = None
                
                # Rozet Güncelle
                p = takim["puan"]
                if p >= 10: takim["rozet"] = "altin"
                elif p >= 7: takim["rozet"] = "gümüş"
                elif p >= 2: takim["rozet"] = "bronz"
                
                # --- KAZANMA (10. Soru) ---
                if p >= 10:
                    self.kazanan_takim_id = takim_id
                    self.yarışma_bitti = True
                    return {"success": True, "sonuc": "oyun_bitti", "mesaj": "KAZANDINIZ!"}
                
                # --- ROZET / TUR GEÇİŞ KONTROLÜ (KRİTİK DÜZELTME) ---
                elif p == 2 or p == 7:
                    # Başka aktif takım var mı?
                    baska_aktif_var_mi = False
                    for t_id, t_data in self.takimlar.items():
                        if t_id != takim_id and not t_data.get("elendi", False):
                            baska_aktif_var_mi = True
                            break
                    
                    rozet_adi = "BRONZ" if p == 2 else "GÜMÜŞ"
                    
                    if baska_aktif_var_mi:
                        # Başkası varsa sıra ona geçer (Normal Kural)
                        self.siradaki_takima_gec()
                        return {"success": True, "sonuc": "tur_bitti", "mesaj": f"Tebrikler! {rozet_adi} rozet aldınız. Sıra değişiyor."}
                    else:
                        # Başkası yoksa beklemene gerek yok, DEVAM ET!
                        return {"success": True, "sonuc": "soru_bitti_devam_et", "mesaj": f"Tebrikler! {rozet_adi} rozet aldınız. Tek kaldığınız için devam ediyorsunuz!"}

                else:
                    # Ara sorularda devam
                    return {"success": True, "sonuc": "soru_bitti_devam_et", "mesaj": "Soru bitti, devam!"}
            
            return {"success": True, "sonuc": "dogru_parca", "mesaj": "Doğru, devam et."}
        
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
        """(DÜZELTİLDİ: Kilitlenme Önleyici ve Hata Korumalı)"""
        if self.yarışma_bitti:
            return {"success": False, "hata": "Yarışma bitti."}

        if not self.takimlar: 
            return {"success": False, "hata": "Takım yok."}

        takim_ids = sorted(list(self.takimlar.keys()), key=lambda x: int(x.split('_')[1]))
        
        # --- HATA KORUMASI (ATTRIBUTE ERROR ÇÖZÜMÜ) ---
        if not hasattr(self, 'siradaki_takim_id') or self.siradaki_takim_id is None:
            self.siradaki_takim_id = takim_ids[0]
        # ----------------------------------------------

        # Şu anki takımın indexini bul
        su_anki_index = -1
        if self.siradaki_takim_id in takim_ids:
            su_anki_index = takim_ids.index(self.siradaki_takim_id)

        # Döngüyle sıradaki SAĞLAM takımı ara
        for i in range(1, len(takim_ids) + 1):
            bakiilacak_index = (su_anki_index + i) % len(takim_ids)
            aday_id = takim_ids[bakiilacak_index]
            
            # Bu takım aktif mi (elenmemiş mi)?
            takim = self.takimlar[aday_id]
            is_aktif = takim.get("aktif", True)
            is_elendi = takim.get("elendi", False)
            
            if is_aktif and not is_elendi:
                self.siradaki_takim_id = aday_id
                self.mevcut_soru_verisi = None 
                return {"success": True, "yeni_aktif_takim_id": aday_id}

        # HERKES ELENDİYSE BURAYA DÜŞER VE OYUNU BİTİRİR
        print("⚠️ Kimse kalmadı, oyun bitiriliyor.")
        self.oyunu_bitir_ve_kazanani_belirle()
        return {"success": True, "mesaj": "Herkes elendi, oyun bitti."}

    def _yarismayi_bitir(self, kazanan_id=None):
        """(GÜNCELLENDİ) Yarışmayı bitirir. Kazanan yoksa en yüksek puanlıyı seçer."""
        if self.yarışma_bitti:
            return self.kazanan_takim_id
            
        self.yarışma_bitti = True
        
        if kazanan_id:
             self.kazanan_takim_id = kazanan_id
        else:
            # Kimse 10. soruyu bitiremediyse (Herkes elendi), puanı en yüksek olan kazanır
            sirali = sorted(self.takimlar.values(), key=lambda x: (-x["puan"], x["toplam_sure_saniye"]))
            if sirali:
                self.kazanan_takim_id = sirali[0]["id"]
                print(f"Herkes elendi. Puanla kazanan: {sirali[0]['isim']}")
            else:
                self.kazanan_takim_id = None

        # --- Derece Kontrolü ---
        if self.kazanan_takim_id:
             import takim_yarismasi_modul as ty 
             skorlar = ty.load_takim_skorlari()
             kazanan_takim = self.takimlar[self.kazanan_takim_id]
             
             if len(skorlar) < 10:
                 self.dereceye_girdi_mi = True
             else:
                 en_kotu_skor = skorlar[-1]
                 if (kazanan_takim["puan"] > en_kotu_skor["soru_sayisi"]) or \
                    (kazanan_takim["puan"] == en_kotu_skor["soru_sayisi"] and kazanan_takim["toplam_sure_saniye"] < en_kotu_skor["toplam_sure_saniye"]):
                     self.dereceye_girdi_mi = True
        # -----------------------

        return self.kazanan_takim_id

    def durumu_json_yap(self, izleyen_no=None, izleyen_rol="student"):
        """
        (GÜVENLİK GÜNCELLEMESİ V2) 
        Soruyu gösterme mantığı güçlendirildi ve log eklendi.
        """
        
        aktif_takim_id = self.get_aktif_takim_id()
        kalan_saniye = 60
        mevcut_soru_kisitli_veri = None
        
        # --- 1. KİMLİK KONTROLÜ ---
        soruyu_goster = False
        
        # A. Öğretmense veya Oyun Bittiyse -> HERKES GÖRÜR
        if izleyen_rol in ["teacher", "admin"] or self.yarışma_bitti:
            soruyu_goster = True
            
        # B. Aktif Takım Üyesiyse -> GÖRÜR
        elif aktif_takim_id:
            aktif_takim = self.takimlar[aktif_takim_id]
            
            # İzleyen numarasını temizle (string ve boşluksuz)
            izleyen_temiz = str(izleyen_no).strip().replace(".0", "")
            
            # Takım listesinde var mı kontrol et
            for uye in aktif_takim["uyeler"]:
                uye_no_temiz = str(uye["no"]).strip().replace(".0", "")
                
                if uye_no_temiz == izleyen_temiz:
                    soruyu_goster = True
                    break
            
            # Hata ayıklama için konsola yaz (Sadece soruyu gizlediğimizde)
            if not soruyu_goster:
                print(f"🔒 SORU GİZLENDİ: Sıra {aktif_takim['isim']} takımında. İzleyen No: '{izleyen_temiz}' (Eşleşmedi)")

        # ----------------------------------------------------

        # --- 2. AKTİF KAPTAN KİM? ---
        aktif_takim_kaptani_id = None
        if aktif_takim_id:
            aktif_takim = self.takimlar[aktif_takim_id]
            if aktif_takim["uyeler"]:
                su_anki_index = aktif_takim["aktif_uye_index"] % len(aktif_takim["uyeler"])
                raw_id = aktif_takim["uyeler"][su_anki_index]["no"]
                aktif_takim_kaptani_id = str(raw_id).strip()

        # --- 3. VERİ PAKETİNİ HAZIRLA ---
        if aktif_takim_id:
            self.mevcut_soru_numarasi = self.takimlar[aktif_takim_id]["puan"] + 1

            if self.mevcut_soru_verisi:
                # Süreyi hesapla
                try:
                    zaman = datetime.fromisoformat(self.takimlar[aktif_takim_id]["son_soru_zamani"])
                    fark = (datetime.now() - zaman).total_seconds()
                    kalan_saniye = max(0, 60 - int(fark))
                except:
                    kalan_saniye = 60
                
                # GÜVENLİK FİLTRESİ
                if soruyu_goster:
                    mevcut_soru_kisitli_veri = {
                        "metin": self.mevcut_soru_verisi["metin"],
                        "beceri_adi": self.mevcut_soru_verisi["beceri_adi"],
                        "deger_adi": self.mevcut_soru_verisi["deger_adi"]
                    }
                else:
                    mevcut_soru_kisitli_veri = {
                        "metin": "Sıra diğer takımda. Lütfen bekleyiniz...",
                        "beceri_adi": "???",
                        "deger_adi": "???"
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
            "dereceye_girdi_mi": self.dereceye_girdi_mi,
            "izleyen_kim": str(izleyen_no) 
        }





