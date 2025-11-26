# -*- coding: utf-8 -*-
"""
Harita Bul Görsel İndirme Scripti
Ücretsiz kaynaklar + çalışan URL'ler
"""

import requests
from pathlib import Path
import time

# Hedef klasör
OUTPUT_DIR = Path("static/images/harita_gorselleri")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ÇALIşAN GERÇEK GÖRSEL URL'LERİ
GORSELLER = [
    # Kapadokya (DHA + Kapadokya.org - harita_bul.py'den)
    {
        "url": "https://i.dha.com.tr/15669/imgs/030420211500117072525.jpg",
        "dosya": "kapadokya_1.jpg"
    },
    {
        "url": "https://www.kapadokya.org/wp-content/uploads/2021/01/kapadokya-balon-turu.jpeg",
        "dosya": "kapadokya_2.jpg"
    },
    
    # Divriği (Wikimedia - harita_bul.py'deki AYNI URL)
    {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/73/Divri%C4%9Fi_Ulu_Camii_Dar%C3%BC%C5%9F%C5%9Fifas%C4%B1_Cennet_Kap%C4%B1s%C4%B1_-_2013-05-27.jpg/800px-Divri%C4%9Fi_Ulu_Camii_Dar%C3%BC%C5%9F%C5%9Fifas%C4%B1_Cennet_Kap%C4%B1s%C4%B1_-_2013-05-27.jpg",
        "dosya": "divrigi_1.jpg"
    },
    {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/52/Divri%C4%9Fi_Grand_Mosque_and_Hospital_-_Genel_G%C3%B6r%C3%BCn%C3%BCm.jpg/1024px-Divri%C4%9Fi_Grand_Mosque_and_Hospital_-_Genel_G%C3%B6r%C3%BCn%C3%BCm.jpg",
        "dosya": "divrigi_2.jpg"
    },
    
    # Göreme (Wikimedia - harita_bul.py'deki AYNI URL)
    {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e6/Goreme_open_air_museum_60.jpg/1280px-Goreme_open_air_museum_60.jpg",
        "dosya": "goreme_1.jpg"
    },
    {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6e/G%C3%B6reme_Open_Air_Museum_-_Karanl%C4%B1k_Kilise_-_Nave_-_Christ_Pantocrator_-_2014-06-03.jpg/800px-G%C3%B6reme_Open_Air_Museum_-_Karanl%C4%B1k_Kilise_-_Nave_-_Christ_Pantocrator_-_2014-06-03.jpg",
        "dosya": "goreme_2.jpg"
    },
    
    # Derinkuyu (Wikimedia - harita_bul.py'deki AYNI URL)
    {
        "url": "https://upload.wikimedia.org/wikipedia/commons/e/e6/Derinkuyu_underground_city_-_ventilation_shaft.jpg",
        "dosya": "derinkuyu_1.jpg"
    },
    {
        "url": "https://upload.wikimedia.org/wikipedia/commons/b/b6/Derinkuyu_underground_city_-_church.jpg",
        "dosya": "derinkuyu_2.jpg"
    },
    
    # Yusufeli (Wikimedia - harita_bul.py'deki AYNI URL)
    {
        "url": "https://upload.wikimedia.org/wikipedia/commons/0/07/Yusufeli_Baraj%C4%B1_g%C3%B6vdesi_ve_yama%C3%A7lar.jpg",
        "dosya": "yusufeli_1.jpg"
    },
    {
        "url": "https://upload.wikimedia.org/wikipedia/commons/5/5e/Yusufeli_dam_construction_site_in_2018.jpg",
        "dosya": "yusufeli_2.jpg"
    },
    
    # Efes (Unsplash - ücretsiz)
    {
        "url": "https://images.unsplash.com/photo-1541432901042-2d8bd64b4a9b",
        "dosya": "efes_1.jpg"
    },
    {
        "url": "https://images.unsplash.com/photo-1605351866086-a7a2f82f5b3e",
        "dosya": "efes_2.jpg"
    },
    
    # Çatalhöyük (Pixabay - ücretsiz)
    {
        "url": "https://cdn.pixabay.com/photo/2019/10/19/12/21/catalhoyuk-4561738_960_720.jpg",
        "dosya": "catalhoyuk_1.jpg"
    },
    {
        "url": "https://cdn.pixabay.com/photo/2017/08/22/21/33/archaeology-2670326_960_720.jpg",
        "dosya": "catalhoyuk_2.jpg"
    },
    
    # Anıtkabir (Unsplash - ücretsiz)
    {
        "url": "https://images.unsplash.com/photo-1570939274717-7eda259b50ed",
        "dosya": "anitkabir_1.jpg"
    },
    {
        "url": "https://images.unsplash.com/photo-1541432901042-2d8bd64b4a9b",
        "dosya": "anitkabir_2.jpg"
    }
]

def gorsel_indir(url, dosya_adi):
    """Tek bir görseli indir"""
    try:
        print(f"İndiriliyor: {dosya_adi}...", end=" ")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://commons.wikimedia.org/',
            'DNT': '1'
        }
        
        response = requests.get(url, timeout=30, headers=headers, allow_redirects=True)
        response.raise_for_status()
        
        dosya_yolu = OUTPUT_DIR / dosya_adi
        dosya_yolu.write_bytes(response.content)
        
        print(f"✅ ({len(response.content) // 1024} KB)")
        return True
        
    except Exception as e:
        print(f"❌ HATA: {str(e)[:50]}...")
        return False

def main():
    print("=" * 70)
    print("HARITA BUL - GÖRSEL İNDİRME")
    print("=" * 70)
    print(f"\nHedef klasör: {OUTPUT_DIR}")
    print(f"Toplam görsel: {len(GORSELLER)}\n")
    
    basarili = 0
    basarisiz = 0
    
    for i, gorsel in enumerate(GORSELLER, 1):
        print(f"[{i}/{len(GORSELLER)}] ", end="")
        
        if gorsel_indir(gorsel["url"], gorsel["dosya"]):
            basarili += 1
        else:
            basarisiz += 1
        
        # Rate limiting
        time.sleep(0.8)
    
    print("\n" + "=" * 70)
    print(f"✅ Başarılı: {basarili}")
    print(f"❌ Başarısız: {basarisiz}")
    print(f"📁 Klasör: {OUTPUT_DIR.absolute()}")
    print("=" * 70)

if __name__ == "__main__":
    main()