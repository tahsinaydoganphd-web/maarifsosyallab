import db_helper
import json
import time

def test_video_system():
    print("--- 1. Veritabanı Başlatma ve Tablo Kontrolü ---")
    try:
        # Tabloların (özellikle 'videolar' tablosunun) varlığını kontrol et
        db_helper.init_db()
        print("✅ Veritabanı bağlantısı ve tablolar hazır.")
    except Exception as e:
        print(f"❌ HATA: Veritabanı başlatılamadı: {e}")
        return

    print("\n--- 2. Video Kayıt Testi (SQL'e Yazma) ---")
    
    # Simüle edilmiş bir video verisi (Seyret Bul'un ürettiği formatta)
    video_id = f"test_vid_{int(time.time())}"
    
    ornek_sorular = [
        {"id": "q1", "soru": "Başkent neresidir?", "cevap": "Ankara"},
        {"id": "q2", "soru": "Cumhuriyet ne zaman ilan edildi?", "cevap": "1923"}
    ]
    
    video_data = {
        "video_id": video_id,
        "baslik": "SQL Test Videosu",
        "surec_bileseni": "SB.5.1.1",
        "video_url": "https://www.youtube.com/watch?v=TEST1234",
        "thumbnail_url": "https://img.youtube.com/vi/TEST1234/mqdefault.jpg",
        "sure_saniye": 150,
        "sorular_json": json.dumps(ornek_sorular) # Python listesini JSON string'e çevirip yolluyoruz
    }

    if db_helper.save_video(video_data):
        print(f"✅ Video başarıyla kaydedildi. (ID: {video_id})")
    else:
        print("❌ HATA: Video kaydedilemedi.")
        return

    print("\n--- 3. Video Okuma ve JSON Kontrolü ---")
    # Kaydettiğimiz videoyu ID ile geri çekelim
    cekilen_video = db_helper.get_video(video_id)
    
    if cekilen_video:
        print(f"✅ Video veritabanından çekildi: {cekilen_video['baslik']}")
        
        # Kritik Nokta: 'sorular_json' alanı düzgün bir string mi?
        raw_json = cekilen_video.get('sorular_json')
        print(f"ℹ️  Veritabanındaki Ham JSON Verisi: {raw_json}")
        
        try:
            # String'i tekrar listeye çevirmeyi dene
            sorular_listesi = json.loads(raw_json)
            print(f"✅ JSON Ayrıştırma Başarılı! Soru Sayısı: {len(sorular_listesi)}")
            
            if sorular_listesi[0]['cevap'] == "Ankara":
                print("✅ Veri bütünlüğü doğrulandı (İçerik bozulmamış).")
            else:
                print("❌ Veri içeriği eşleşmiyor!")
        except Exception as e:
            print(f"❌ HATA: JSON ayrıştırılamadı (Parse Error): {e}")
    else:
        print("❌ HATA: Kaydedilen video bulunamadı!")

    print("\n--- 4. Temizlik (Silme Testi) ---")
    if db_helper.delete_video(video_id):
        print("✅ Test videosu başarıyla silindi.")
    else:
        print("❌ HATA: Silme işlemi başarısız.")

if __name__ == "__main__":
    test_video_system()