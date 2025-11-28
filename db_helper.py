import psycopg2
from psycopg2.extras import RealDictCursor
import os
import bcrypt

def get_db_connection():
    # 1. Önce Render'ın verdiği adresi kontrol et
    database_url = os.getenv('DATABASE_URL')
    
    if database_url:
        # --- İNTERNETTEYSEK (RENDER) ---
        conn = psycopg2.connect(database_url, sslmode='require')
    else:
        # --- BİLGİSAYARDAYSAK (LOCAL) ---
        conn = psycopg2.connect(
            dbname='sosyallab',
            user='tahsinaydogan',
            password='97032647', # Burası sadece lokalde lazım
            host='localhost',
            port='5432'
        )
    
    conn.autocommit = True
    return conn

# --- AŞAĞIDAKİLER SENİN KODLARININ AYNISI (DOKUNMA) ---

def init_db():
    """Tabloları oluşturur"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Kullanıcılar
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
        
        # Raporlar
        cur.execute("""
            CREATE TABLE IF NOT EXISTS kullanim_raporlari (
                id SERIAL PRIMARY KEY,
                student_no TEXT,
                modul TEXT,
                detay TEXT,
                tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Video İstekleri
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
        
        cur.close()
        conn.close()
        print("✅ Veritabanı tabloları hazır.")
    except Exception as e:
        print(f"❌ DB Başlatma hatası: {e}")

def load_users():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM users")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        # Listeyi sözlüğe çevir
        return {row['user_id']: dict(row) for row in rows}
    except Exception as e:
        print(f"Kullanıcı yükleme hatası: {e}")
        return {}

def save_user(user_id, user_data):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
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

def save_video_istek(istek_data):
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
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM video_istekleri ORDER BY tarih DESC")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"İstek listeleme hatası: {e}")
        return []

def delete_video_istek(istek_id):
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

def verify_password(plain_password, hashed_password):
    if not hashed_password or not plain_password: return False
    if hashed_password.startswith('$2b$'):
         try:
            return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
         except:
             return False
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
        
        cur.execute("""
            SELECT 
            EXTRACT(WEEK FROM kr.tarih) as hafta,
            kr.student_no as student_no,
            u.first_name as ad,
            u.last_name as soyad,
            u.first_name || ' ' || u.last_name as ad_soyad,
            kr.modul as modul_adi,
            COUNT(*) as kullanim_sayisi
        FROM kullanim_raporlari kr
        LEFT JOIN users u ON kr.student_no = u.student_no
        WHERE u.school_name = %s 
            AND u.class = %s
            AND TO_CHAR(kr.tarih, 'YYYY-MM') = %s
        GROUP BY EXTRACT(WEEK FROM kr.tarih), kr.student_no, u.first_name, u.last_name, kr.modul
        ORDER BY hafta, u.first_name, kr.modul
        """, (okul, sinif, ay))
        
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"Haftalık rapor hatası: {e}")
        return []
