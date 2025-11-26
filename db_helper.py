import psycopg2
from psycopg2.extras import RealDictCursor
import bcrypt
from datetime import datetime

# --- AYARLAR ---
DB_CONFIG = {
    'dbname': 'sosyallab',
    'user': 'tahsinaydogan', # Kendi postgres kullanıcı adınız (genelde 'postgres'tir)
    'password': '97032647', # <--- ŞİFRE BURAYA
    'host': 'localhost',
    'port': '5432'
}

def get_db_connection():
    """PostgreSQL bağlantısı"""
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True # Otomatik kaydetmeyi açtık
    return conn

def init_db():
    """Tablolar yoksa oluşturur (Sistemi başlatan sihirli fonksiyon)"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 1. Kullanıcılar Tablosu
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                first_name TEXT,
                last_name TEXT,
                school_name TEXT,
                class TEXT,
                role TEXT,
                password TEXT,
                student_no TEXT
            );
        """)
        
        # 2. Kullanım Raporları Tablosu (DÜZELTİLMİŞ HALİ)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS kullanim_raporlari (
                id SERIAL PRIMARY KEY,
                student_no TEXT,
                modul TEXT,          -- Python koduyla uyumlu (modul)
                detay TEXT,          -- Python koduyla uyumlu (detay)
                tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 3. Video İstekleri Tablosu
        cur.execute("""
            CREATE TABLE IF NOT EXISTS video_istekleri (
                id TEXT PRIMARY KEY,
                tarih TIMESTAMP,
                ogretmen TEXT,
                metin TEXT,
                durum TEXT,
                rol TEXT,
                okul TEXT,
                sinif TEXT,
                no TEXT
            );
        """)

        # 4. Bireysel Skorlar
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bireysel_skorlar (
                student_no TEXT PRIMARY KEY,
                dogru_soru_sayisi INTEGER DEFAULT 0,
                toplam_sure_saniye INTEGER DEFAULT 0,
                altin_rozet_tarihi TEXT,
                gunluk_elenme_sayisi INTEGER DEFAULT 0,
                son_elenme_tarihi TEXT
            );
        """)

        # 5. Öğrenci Rozetleri
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ogrenci_rozetler (
                id SERIAL PRIMARY KEY,
                student_no TEXT,
                rozet TEXT
            );
        """)

        # 6. Takım Skorları
        cur.execute("""
            CREATE TABLE IF NOT EXISTS takim_skorlar (
                id SERIAL PRIMARY KEY,
                takim_adi TEXT,
                okul TEXT,
                sinif TEXT,
                rozet TEXT,
                soru_sayisi INTEGER,
                toplam_sure INTEGER,
                tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # 7. Videolar
        cur.execute("""
            CREATE TABLE IF NOT EXISTS videolar (
                video_id TEXT PRIMARY KEY,
                baslik TEXT,
                surec_bileseni TEXT,
                video_url TEXT,
                eklenme_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        print("✅ Veritabanı tabloları (7 adet) kontrol edildi ve güncellendi.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Veritabanı başlatma hatası: {e}")

# ===== USER İŞLEMLERİ =====
def load_users():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM users")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        users = {row['user_id']: dict(row) for row in rows}
        return users
    except Exception as e:
        print(f"Kullanıcı yükleme hatası: {e}")
        return {}

def save_user(user_id, user_data):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Önce var mı diye bak, varsa güncelle, yoksa ekle (Upsert mantığı)
        cur.execute("SELECT 1 FROM users WHERE user_id = %s", (user_id,))
        exists = cur.fetchone()
        
        if exists:
            cur.execute("""
                UPDATE users SET 
                first_name=%s, last_name=%s, school_name=%s, 
                class=%s, role=%s, password=%s, student_no=%s
                WHERE user_id=%s
            """, (
                user_data.get('first_name'), user_data.get('last_name'),
                user_data.get('school_name'), user_data.get('class'),
                user_data.get('role'), user_data.get('password'),
                user_data.get('student_no'), user_id
            ))
        else:
            cur.execute("""
                INSERT INTO users 
                (user_id, first_name, last_name, school_name, class, role, password, student_no)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id, user_data.get('first_name'), user_data.get('last_name'),
                user_data.get('school_name'), user_data.get('class'),
                user_data.get('role'), user_data.get('password'),
                user_data.get('student_no')
            ))
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"User kayıt hatası: {e}")
        return False

# ===== VİDEO İSTEK İŞLEMLERİ (YENİ SQL) =====
def save_video_istek(istek_data):
    """Yeni video isteğini SQL'e kaydeder"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO video_istekleri (id, tarih, ogretmen, metin, durum, rol, okul, sinif, no)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            istek_data['id'], istek_data['tarih'], istek_data['ogretmen'],
            istek_data['metin'], istek_data['durum'], istek_data['rol'],
            istek_data['okul'], istek_data['sinif'], istek_data['no']
        ))
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Video istek kayıt hatası: {e}")
        return False

def get_all_video_istekleri():
    """Tüm istekleri getirir (En yeniden eskiye)"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM video_istekleri ORDER BY tarih DESC")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        # Datetime objelerini string'e çevirmek gerekebilir ama RealDictCursor genelde halleder.
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"İstek listeleme hatası: {e}")
        return []

def delete_video_istek(istek_id):
    """İsteği siler"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM video_istekleri WHERE id = %s", (istek_id,))
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"İstek silme hatası: {e}")
        return False

# ===== RAPORLAMA VE YARDIMCI FONKSİYONLAR =====
def verify_password(plain_password, hashed_password):
    if not hashed_password or not plain_password: return False
    return plain_password == hashed_password

def kaydet_kullanim(student_no, modul_adi, aciklama):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO kullanim_raporlari (student_no, modul, detay, tarih)
            VALUES (%s, %s, %s, NOW())
        """, (student_no, modul_adi, aciklama))
        
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Log hatası: {e}")
        return False

def get_kullanim_raporu(okul=None, sinif=None, baslangic=None, bitis=None):
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        query = """
            SELECT kr.*, u.first_name, u.last_name, u.school_name, u.class 
            FROM kullanim_raporlari kr
            LEFT JOIN users u ON kr.student_no = u.student_no
            WHERE 1=1
        """
        params = []
        if okul:
            query += " AND u.school_name = %s"
            params.append(okul)
        if sinif:
            query += " AND u.class = %s"
            params.append(sinif)
        
        query += " ORDER BY kr.tarih DESC"
        cur.execute(query, tuple(params))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"Rapor hatası: {e}")
        return []

def get_haftalik_rapor(okul, sinif, ay):
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # TARAYICI İLE TAM UYUMLU SÜRÜM
        cur.execute("""
            SELECT 
                EXTRACT(WEEK FROM kr.tarih) as hafta,
                kr.student_no as no,
                u.first_name as ad,
                u.last_name as soyad,
                u.first_name || ' ' || u.last_name as ad_soyad,
                kr.modul as modul_adi,
                kr.modul,
                COUNT(*) as kullanim_sayisi,
                COUNT(*) as kullanim
            FROM kullanim_raporlari kr
            LEFT JOIN users u ON kr.student_no = u.student_no
            WHERE u.school_name = %s 
                AND u.class = %s
                AND TO_CHAR(kr.tarih, 'YYYY-MM') = %s
            GROUP BY hafta, kr.student_no, u.first_name, u.last_name, kr.modul
            ORDER BY hafta, u.first_name, kr.modul
        """, (okul, sinif, ay))
        
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        print(f"🔍 Haftalık rapor: {len(rows)} kayıt bulundu")
        
        # DEBUG: Hangi alanlar dönüyor görelim
        if rows:
            print("📋 Dönen alanlar:", list(rows[0].keys()))
        
        return [dict(row) for row in rows]
        
    except Exception as e:
        print(f"Haftalık rapor hatası: {e}")
        return []
        
# ==========================================
# BİREYSEL YARIŞMA VE TAKIM SQL İŞLEMLERİ
# (db_helper.py dosyasının en altına ekleyin)
# ==========================================

def get_bireysel_skor(student_no):
    """Öğrencinin skorunu ve rozetlerini getirir"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Skor tablosundan çek
        cur.execute("SELECT * FROM bireysel_skorlar WHERE student_no = %s", (student_no,))
        row = cur.fetchone()
        
        if not row:
            cur.close()
            conn.close()
            return {} # Kayıt yoksa boş sözlük dön
            
        # Rozetleri çek
        cur.execute("SELECT rozet FROM ogrenci_rozetler WHERE student_no = %s", (student_no,))
        row['rozetler'] = [r['rozet'] for r in cur.fetchall()]
        
        cur.close()
        conn.close()
        return dict(row)
    except Exception as e:
        print(f"Bireysel skor okuma hatası: {e}")
        return {}

def save_bireysel_skor(student_no, data):
    """Skoru ve rozetleri kaydeder (Upsert: Yoksa ekle, Varsa güncelle)"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 1. Ana skoru güncelle
        cur.execute("SELECT 1 FROM bireysel_skorlar WHERE student_no = %s", (student_no,))
        if cur.fetchone():
            cur.execute("""
                UPDATE bireysel_skorlar SET 
                dogru_soru_sayisi=%s, toplam_sure_saniye=%s, 
                altin_rozet_tarihi=%s, gunluk_elenme_sayisi=%s, son_elenme_tarihi=%s
                WHERE student_no=%s
            """, (data.get('dogru_soru_sayisi', 0), data.get('toplam_sure_saniye', 0),
                  data.get('altin_rozet_tarihi'), data.get('gunluk_elenme_sayisi', 0),
                  data.get('son_elenme_tarihi'), student_no))
        else:
            cur.execute("""
                INSERT INTO bireysel_skorlar (student_no, dogru_soru_sayisi, toplam_sure_saniye, altin_rozet_tarihi, gunluk_elenme_sayisi, son_elenme_tarihi)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (student_no, data.get('dogru_soru_sayisi', 0), data.get('toplam_sure_saniye', 0),
                  data.get('altin_rozet_tarihi'), data.get('gunluk_elenme_sayisi', 0),
                  data.get('son_elenme_tarihi')))
        
        # 2. Rozetleri güncelle (Sil ve yeniden ekle)
        cur.execute("DELETE FROM ogrenci_rozetler WHERE student_no = %s", (student_no,))
        for rozet in data.get('rozetler', []):
            cur.execute("INSERT INTO ogrenci_rozetler (student_no, rozet) VALUES (%s, %s)", (student_no, rozet))
            
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Bireysel skor kaydetme hatası: {e}")
        return False

def get_all_bireysel_scores():
    """Liderlik tablosu için tüm veriyi rozetlerle birlikte çeker"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        # Rozetleri array olarak tek sorguda al
        cur.execute("""
            SELECT s.*, COALESCE(array_agg(r.rozet) FILTER (WHERE r.rozet IS NOT NULL), '{}') as rozetler
            FROM bireysel_skorlar s
            LEFT JOIN ogrenci_rozetler r ON s.student_no = r.student_no
            GROUP BY s.student_no
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return {row['student_no']: dict(row) for row in rows}
    except Exception as e:
        print(f"Toplu skor çekme hatası: {e}")
        return {}

def save_takim_skoru(takim_adi, okul, sinif, rozet, soru_sayisi, toplam_sure):
    """Takım yarışması sonucunu kaydeder"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO takim_skorlar (takim_adi, okul, sinif, rozet, soru_sayisi, toplam_sure)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (takim_adi, okul, sinif, rozet, soru_sayisi, toplam_sure))
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Takım skor hatası: {e}")
        return False

# ==========================================
# 7. VİDEO YÖNETİMİ (SEYRET BUL) SQL İŞLEMLERİ
# (Bunu db_helper.py dosyasının en altına ekleyin)
# ==========================================

def save_video(video_data):
    """Videoyu ve sorularını kaydeder (Upsert: Yoksa ekle, Varsa güncelle)"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Güncelleme mi Ekleme mi?
        cur.execute("SELECT 1 FROM videolar WHERE video_id = %s", (video_data['video_id'],))
        exists = cur.fetchone()
        
        if exists:
            cur.execute("""
                UPDATE videolar SET 
                baslik=%s, surec_bileseni=%s, video_url=%s, 
                thumbnail_url=%s, sure_saniye=%s, sorular_json=%s
                WHERE video_id=%s
            """, (video_data.get('baslik'), video_data.get('surec_bileseni'),
                  video_data.get('video_url'), video_data.get('thumbnail_url'),
                  video_data.get('sure_saniye', 0), video_data.get('sorular_json'),
                  video_data['video_id']))
        else:
            cur.execute("""
                INSERT INTO videolar (video_id, baslik, surec_bileseni, video_url, thumbnail_url, sure_saniye, sorular_json)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (video_data['video_id'], video_data.get('baslik'), video_data.get('surec_bileseni'),
                  video_data.get('video_url'), video_data.get('thumbnail_url'),
                  video_data.get('sure_saniye', 0), video_data.get('sorular_json')))
            
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Video kayıt hatası (db_helper): {e}")
        return False

def get_all_videos():
    """Tüm videoları getirir"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM videolar ORDER BY eklenme_tarihi DESC")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        # Row'ları dict'e çevir
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"Video listeleme hatası: {e}")
        return []

def get_video(video_id):
    """Tek bir videoyu getirir"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM videolar WHERE video_id = %s", (video_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            return dict(row)
        return None
    except Exception as e:
        print(f"Video çekme hatası: {e}")
        return None

def delete_video(video_id):
    """Videoyu siler"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM videolar WHERE video_id = %s", (video_id,))
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Video silme hatası: {e}")
        return False
