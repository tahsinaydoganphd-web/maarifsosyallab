import psycopg2

# Bağlantı ayarları
conn = psycopg2.connect(
    dbname="sosyallab",
    user="tahsinaydogan",  # Mac kullanıcı adın
    password="",  # Localhost'ta genelde boş
    host="localhost",
    port="5432"
)

cur = conn.cursor()

# 1. Users tablosu
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(50) PRIMARY KEY,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    class VARCHAR(20),
    password VARCHAR(255),
    school_name VARCHAR(200),
    role VARCHAR(20),
    student_no VARCHAR(50)
);
""")

# 2. Soru üretim limitleri
cur.execute("""
CREATE TABLE IF NOT EXISTS soru_uretim_limits (
    student_no VARCHAR(50) PRIMARY KEY,
    count INTEGER,
    reset_date DATE,
    FOREIGN KEY (student_no) REFERENCES users(id)
);
""")

# 3. Metin analiz limitleri
cur.execute("""
CREATE TABLE IF NOT EXISTS metin_analiz_limitleri (
    student_no VARCHAR(50) PRIMARY KEY,
    limit_sayisi INTEGER,
    FOREIGN KEY (student_no) REFERENCES users(id)
);
""")

# 4. Bireysel skorlar
cur.execute("""
CREATE TABLE IF NOT EXISTS bireysel_skorlar (
    student_no VARCHAR(50) PRIMARY KEY,
    dogru_soru_sayisi INTEGER DEFAULT 0,
    toplam_sure_saniye INTEGER DEFAULT 0,
    altin_rozet_tarihi DATE,
    gunluk_elenme_sayisi INTEGER DEFAULT 0,
    son_elenme_tarihi DATE,
    FOREIGN KEY (student_no) REFERENCES users(id)
);
""")

# 5. Öğrenci rozetler (AYRI TABLO)
cur.execute("""
CREATE TABLE IF NOT EXISTS ogrenci_rozetler (
    id SERIAL PRIMARY KEY,
    student_no VARCHAR(50),
    rozet VARCHAR(20),
    kazanma_tarihi DATE DEFAULT CURRENT_DATE,
    FOREIGN KEY (student_no) REFERENCES users(id)
);
""")

# 6. Takım skorlar
cur.execute("""
CREATE TABLE IF NOT EXISTS takim_skorlar (
    takim_adi VARCHAR(100) PRIMARY KEY,
    kazanma_sayisi INTEGER DEFAULT 0
);
""")

# 7. Takım üyeler (AYRI TABLO)
cur.execute("""
CREATE TABLE IF NOT EXISTS takim_uyeler (
    id SERIAL PRIMARY KEY,
    takim_adi VARCHAR(100),
    uye_adi VARCHAR(200),
    FOREIGN KEY (takim_adi) REFERENCES takim_skorlar(takim_adi)
);
""")

# 8. Videolar
cur.execute("""
CREATE TABLE IF NOT EXISTS videos (
    video_id VARCHAR(100) PRIMARY KEY,
    surec_bileseni VARCHAR(50),
    baslik VARCHAR(200),
    url TEXT,
    thumbnail_url TEXT,
    sure_saniye INTEGER,
    sorular JSONB
);
""")

# 9. Bireysel soru bankası
cur.execute("""
CREATE TABLE IF NOT EXISTS bireysel_soru_bankasi (
    id SERIAL PRIMARY KEY,
    zorluk VARCHAR(20),
    metin TEXT,
    beceri_adi VARCHAR(100),
    deger_adi VARCHAR(100),
    beceri_cumlesi TEXT,
    deger_cumlesi TEXT
);
""")

# 10. Kullanım raporları (YENİ)
cur.execute("""
CREATE TABLE IF NOT EXISTS kullanim_raporlari (
    id SERIAL PRIMARY KEY,
    student_no VARCHAR(50),
    modul_adi VARCHAR(100),
    tarih DATE DEFAULT CURRENT_DATE,
    saat TIME DEFAULT CURRENT_TIME,
    islem_detay TEXT,
    FOREIGN KEY (student_no) REFERENCES users(id)
);
""")

# 11. Günlük kullanım özeti (YENİ - Raporlama için)
cur.execute("""
CREATE TABLE IF NOT EXISTS gunluk_kullanim_ozet (
    id SERIAL PRIMARY KEY,
    student_no VARCHAR(50),
    modul_adi VARCHAR(100),
    tarih DATE DEFAULT CURRENT_DATE,
    kullanim_sayisi INTEGER DEFAULT 1,
    okul VARCHAR(200),
    sinif VARCHAR(20),
    UNIQUE(student_no, modul_adi, tarih),
    FOREIGN KEY (student_no) REFERENCES users(id)
);
""")

# Index'ler (Hız için)
cur.execute("CREATE INDEX IF NOT EXISTS idx_kullanim_tarih ON kullanim_raporlari(tarih);")
cur.execute("CREATE INDEX IF NOT EXISTS idx_kullanim_student ON kullanim_raporlari(student_no);")

conn.commit()
cur.close()
conn.close()

print("✅ Tüm tablolar başarıyla oluşturuldu!")
