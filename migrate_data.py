import psycopg2
import json
import bcrypt
from datetime import datetime

# Bağlan
conn = psycopg2.connect(
    dbname="sosyallab",
    user="tahsinaydogan",
    password="",
    host="localhost",
    port="5432"
)
cur = conn.cursor()

print("🔄 Veri aktarımı başlıyor...")

# 1. USERS.JSON
print("📂 users.json aktarılıyor...")
with open('users.json', 'r', encoding='utf-8') as f:
    users = json.load(f)
    
for user_id, data in users.items():
    # Şifreyi hashle
    hashed_pw = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    cur.execute("""
        INSERT INTO users (id, first_name, last_name, class, password, school_name, role, student_no)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO NOTHING
    """, (
        user_id,
        data.get('first_name'),
        data.get('last_name'),
        data.get('class'),
        hashed_pw,
        data.get('school_name'),
        data.get('role'),
        data.get('student_no', user_id)
    ))

print(f"✅ {len(users)} kullanıcı aktarıldı")

# 2. SORU_URETIM_LIMITS.JSON
print("📂 soru_uretim_limits.json aktarılıyor...")
with open('soru_uretim_limits.json', 'r', encoding='utf-8') as f:
    limits = json.load(f)
    
for student_no, data in limits.items():
    cur.execute("""
        INSERT INTO soru_uretim_limits (student_no, count, reset_date)
        VALUES (%s, %s, %s)
        ON CONFLICT (student_no) DO NOTHING
    """, (student_no, data['count'], data['reset_date']))

print(f"✅ {len(limits)} limit kaydı aktarıldı")

# 3. METIN_ANALIZ_LIMITLERI.JSON
print("📂 metin_analiz_limitleri.json aktarılıyor...")
with open('metin_analiz_limitleri.json', 'r', encoding='utf-8') as f:
    analiz_limits = json.load(f)
    
for student_no, limit_sayisi in analiz_limits.items():
    cur.execute("""
        INSERT INTO metin_analiz_limitleri (student_no, limit_sayisi)
        VALUES (%s, %s)
        ON CONFLICT (student_no) DO NOTHING
    """, (student_no, limit_sayisi))

print(f"✅ {len(analiz_limits)} analiz limiti aktarıldı")

# 4. BIREYSEL_SKORLAR.JSON
print("📂 bireysel_skorlar.json aktarılıyor...")
with open('bireysel_skorlar.json', 'r', encoding='utf-8') as f:
    skorlar = json.load(f)
    
for student_no, data in skorlar.items():
    cur.execute("""
        INSERT INTO bireysel_skorlar 
        (student_no, dogru_soru_sayisi, toplam_sure_saniye, altin_rozet_tarihi, gunluk_elenme_sayisi, son_elenme_tarihi)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (student_no) DO NOTHING
    """, (
        student_no,
        data.get('dogru_soru_sayisi', 0),
        data.get('toplam_sure_saniye', 0),
        data.get('altin_rozet_tarihi'),
        data.get('gunluk_elenme_sayisi', 0),
        data.get('son_elenme_tarihi')
    ))
    
    # Rozetleri ayrı tabloya ekle
    for rozet in data.get('rozetler', []):
        cur.execute("""
            INSERT INTO ogrenci_rozetler (student_no, rozet)
            VALUES (%s, %s)
        """, (student_no, rozet))

print(f"✅ {len(skorlar)} skor kaydı aktarıldı")

# 5. TAKIM_SKORLAR.JSON
print("📂 takim_skorlar.json aktarılıyor...")
with open('takim_skorlar.json', 'r', encoding='utf-8') as f:
    takimlar = json.load(f)
    
for takim_adi, data in takimlar.items():
    cur.execute("""
        INSERT INTO takim_skorlar (takim_adi, kazanma_sayisi)
        VALUES (%s, %s)
        ON CONFLICT (takim_adi) DO NOTHING
    """, (takim_adi, data.get('kazanma_sayisi', 0)))
    
    # Üyeleri ayrı tabloya ekle
    for uye in data.get('uyeler', []):
        cur.execute("""
            INSERT INTO takim_uyeler (takim_adi, uye_adi)
            VALUES (%s, %s)
        """, (takim_adi, uye))

print(f"✅ {len(takimlar)} takım aktarıldı")

# 6. VIDEOS.JSON
print("📂 seyret_bul_videos.json aktarılıyor...")
with open('seyret_bul_videos.json', 'r', encoding='utf-8') as f:
    videos = json.load(f)
    
for video_id, data in videos.items():
    cur.execute("""
        INSERT INTO videos (video_id, surec_bileseni, baslik, url, thumbnail_url, sure_saniye, sorular)
        VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
        ON CONFLICT (video_id) DO NOTHING
    """, (
        video_id,
        data.get('surec_bileseni'),
        data.get('baslik'),
        data.get('url'),
        data.get('thumbnail_url'),
        data.get('sure_saniye'),
        json.dumps(data.get('sorular', []))
    ))

print(f"✅ {len(videos)} video aktarıldı")

# 7. BIREYSEL_SORU_BANKASI.JSON
print("📂 bireysel_soru_bankasi.json aktarılıyor...")
with open('bireysel_soru_bankasi.json', 'r', encoding='utf-8') as f:
    sorular = json.load(f)
    
for soru in sorular:
    cur.execute("""
        INSERT INTO bireysel_soru_bankasi (zorluk, metin, beceri_adi, deger_adi, beceri_cumlesi, deger_cumlesi)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        soru.get('zorluk'),
        soru.get('metin'),
        soru.get('beceri_adi'),
        soru.get('deger_adi'),
        soru.get('beceri_cumlesi'),
        soru.get('deger_cumlesi')
    ))

print(f"✅ {len(sorular)} soru aktarıldı")

conn.commit()
cur.close()
conn.close()

print("\n🎉 TÜM VERİLER BAŞARIYLA AKTARILDI!")
