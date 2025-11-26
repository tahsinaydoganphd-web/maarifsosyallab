import json
import os

DOSYA_ADI = 'bireysel_soru_bankasi.json'

print(f"Kontrol edilen dosya: {os.path.abspath(DOSYA_ADI)}")

if not os.path.exists(DOSYA_ADI):
    print("❌ HATA: Dosya bulunamadı! İsmini veya klasörünü kontrol edin.")
else:
    try:
        with open(DOSYA_ADI, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✅ Dosya başarılı okundu.")
        print(f"📊 Toplam Soru Sayısı: {len(data)}")
        
        if len(data) > 0:
            print(f"📝 İlk soru örneği: {data[0].get('metin', 'Metin YOK!')[:30]}...")
        else:
            print("⚠️ UYARI: Dosya var ama içi BOŞ (Liste boş).")
            
    except json.JSONDecodeError as e:
        print(f"❌ HATA: JSON Formatı Bozuk! (Virgül veya parantez hatası)")
        print(f"Detay: {e}")
    except Exception as e:
        print(f"❌ Beklenmeyen Hata: {e}")