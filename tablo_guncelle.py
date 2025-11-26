import db_helper

def tabloyu_sifirla():
    print("⚠️  Eski 'videolar' tablosu yenileniyor...")
    try:
        conn = db_helper.get_db_connection()
        cur = conn.cursor()
        
        # 1. Eski tabloyu tamamen sil (DROP)
        cur.execute("DROP TABLE IF EXISTS videolar;")
        print("✅ Eski tablo silindi.")
        
        # 2. Değişikliği kaydet
        conn.commit() # (autocommit açık olsa da garanti olsun)
        
        cur.close()
        conn.close()
        
        # 3. init_db() fonksiyonunu çağırarak tabloyu YENİ SÜTUNLARLA tekrar oluştur
        print("🔄 Yeni tablo yapısı yükleniyor...")
        db_helper.init_db()
        print("✅ İŞLEM TAMAM! 'videolar' tablosu yeni sütunlarla (thumbnail_url vb.) oluşturuldu.")
        
    except Exception as e:
        print(f"❌ HATA OLUŞTU: {e}")

if __name__ == "__main__":
    tabloyu_sifirla()