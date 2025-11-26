import db_helper

def sutunlari_zorla_ekle():
    print("🛠️  Eksik sütunlar 'videolar' tablosuna ekleniyor...")
    try:
        conn = db_helper.get_db_connection()
        cur = conn.cursor()
        
        # Sütunları tek tek eklemeye çalış (Varsa hata vermez)
        komutlar = [
            "ALTER TABLE videolar ADD COLUMN IF NOT EXISTS thumbnail_url TEXT;",
            "ALTER TABLE videolar ADD COLUMN IF NOT EXISTS sure_saniye INTEGER;",
            "ALTER TABLE videolar ADD COLUMN IF NOT EXISTS sorular_json TEXT;"
        ]
        
        for komut in komutlar:
            cur.execute(komut)
            print(f"   -> Çalıştırıldı: {komut}")
            
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Tamir işlemi başarılı! Sütunlar eklendi.")
        
    except Exception as e:
        print(f"❌ HATA: {e}")

if __name__ == "__main__":
    sutunlari_zorla_ekle()