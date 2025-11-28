from flask import Flask, render_template, request, jsonify, send_file, session, render_template_string, send_from_directory
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()



import pandas as pd
import io
import json
import os
import re 
import sqlite3
import google.generativeai as genai
import time
import metin_uretim
import bireysel_yaris as by_v6
import takim_yarismasi_modul as ty
import podcast_creator
import seyret_bul
import harita_bul
import metin_analiz
import soru_uretim
import db_helper

# 1. API Anahtarını Çek
GEMINI_API_KEY = os.getenv('GOOGLE_API_KEY')

# 2. ÖNEMLİ: Gemini'yi bu anahtarla başlat (BU SATIR EKSİKTİ)
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("UYARI: GOOGLE_API_KEY bulunamadı! Render ayarlarını kontrol et.")

# 3. Flask app'i oluştur
app = Flask(__name__)

# 4. Config'e kaydet
app.config['GEMINI_API_KEY'] = GEMINI_API_KEY
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'varsayilan_gizli_anahtar') # Güvenlik için secret key de env'den alınabilir

# --- Haritada Bul Modülünü Kaydet ---
GOOGLE_MAPS_API_KEY = ""
harita_bul.register_harita_bul_routes(app, GOOGLE_MAPS_API_KEY)


# --- Lokal Videoları (ve Arka Planı) Serve Et ---
# --- Lokal Videoları (ve Arka Planı) Serve Et ---
@app.route('/videolar/<path:filename>')
def serve_video(filename):
    """Videolar klasöründeki dosyaları serve eder"""
    return send_from_directory('videolar', filename)
# --- BİTTİ ---

# --- Kalıcı Veritabanı Ayarları ---
DB_FILE = 'users.json'

# (SİLİNDİ) VIDEO_ISTEKLERI_DB_FILE satırı artık yok.
# (SİLİNDİ) video_istekleri = load_video_istekleri() satırı artık yok.

def check_and_update_soru_limit(student_no):
    from datetime import datetime, timedelta
    
    # load_soru_limits fonksiyonunu güvenli çağırma
    try:
        # Bu fonksiyon app.py'nin aşağılarında tanımlı olmalı veya db_helper'dan gelmeli
        # Eğer yoksa hata vermemesi için boş sözlükle devam ediyoruz
        if 'load_soru_limits' in globals():
            limits = load_soru_limits()
        else:
            limits = {}
    except:
        limits = {}

    today = datetime.now().date()
    user_data = limits.get(student_no, {"count": 0, "reset_date": str(today)})
    
    try:
        reset_date = datetime.strptime(user_data["reset_date"], "%Y-%m-%d").date()
    except:
        reset_date = today

    if today >= reset_date:
        user_data["count"] = 0
        user_data["reset_date"] = str(today + timedelta(days=7))
    
    HAFTALIK_LIMIT = 20
    
    if user_data["count"] >= HAFTALIK_LIMIT:
        kalan_gun = (reset_date - today).days
        return {
            "success": False,
            "hata": f"Haftalık soru üretim limitiniz ({HAFTALIK_LIMIT}) dolmuştur. Lütfen {kalan_gun} gün sonra tekrar deneyin."
        }
    
    user_data["count"] += 1
    limits[student_no] = user_data
    
    # save_soru_limits fonksiyonunu güvenli çağırma
    try:
        if hasattr(db_helper, 'save_soru_limits'):
            db_helper.save_soru_limits(limits)
        elif 'save_soru_limits' in globals():
            save_soru_limits(limits)
    except:
        pass # Kayıt fonksiyonu bulunamazsa çökmesin
            
    return {"success": True}
# --- Soru Üretim Limiti Bitişi ---

# --- KRİTİK EKLEME: Tabloları Başlat ---
# Kullanıcıları yüklemeden önce tabloların varlığından emin oluyoruz
try:
    db_helper.init_db()
    print("✅ Veritabanı tabloları başlatıldı.")
except Exception as e:
    print(f"⚠️ Veritabanı başlatma uyarısı: {e}")

# Öğrenci veritabanını (PostgreSQL'den) yükle
users = db_helper.load_users()

# --- Gemini Modelini Yükle ---
gemini_model = None
try:
    if GEMINI_API_KEY and GEMINI_API_KEY != "":
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel('models/gemini-pro-latest')
        print("Gemini API modeli başarıyla yüklendi.")
    else:
        print("UYARI: Gemini API Anahtarı girilmemiş.")
except Exception as e:
    print(f"Gemini API yüklenirken HATA oluştu: {e}")
# --- BİTTİ ---

# Aktif Takım Yarışmaları
active_team_games = {}

# Video İstekleri
video_istekleri = []
# Video isteklerini PostgreSQL'den yükle
def load_video_istekleri():
    try:
        return db_helper.get_all_video_istekleri()
    except Exception as e:
        print(f"Video istekleri yükleme hatası: {e}")
        return []

# Uygulama başlarken video isteklerini yükle
video_istekleri = load_video_istekleri()

# Otomatik Yönlendirme Kaydı
game_redirects = {}
# --- YENİ EKLENDİ: Çevrimiçi Kullanıcı Takibi ---
online_users = {} # Format: {'ogrenci_no': timestamp}

# --- GİRİŞ/KAYIT SAYFASI HTML KODU (AŞAMA 5 - HATALAR DÜZELTİLDİ) ---


# --- YENİ LİDERLİLK HTML BİTTİ

# ########## YENİ EKLENDİ: TAKIM YARIŞMASI LİDERLİK TABLOSU ##########
TAKIM_LIDERLIK_TABLOSU_HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Takım Yarışması - Liderlik Tablosu</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style> body { font-family: 'Inter', sans-serif; background-color: #f3f4f6; } </style>
</head>
<body class="p-4 md:p-8">
    <div class="max-w-4xl mx-auto">
        <h1 class="text-3xl font-bold text-gray-800 mb-6">Takım Yarışması Liderlik Tablosu (İlk 10)</h1>
        
        <div class="bg-white p-6 rounded-lg shadow-md">
            <table class="w-full text-left">
                <thead class="bg-gray-100 border-b">
                    <tr>
                        <th class="p-3 font-semibold text-sm text-gray-600">Sıra</th>
                        <th class="p-3 font-semibold text-sm text-gray-600">Takım Adı</th>
                        <th class="p-3 font-semibold text-sm text-gray-600">Okul / Sınıf</th>
                        <th class="p-3 font-semibold text-sm text-gray-600">Rozet</th>
                        <th class="p-3 font-semibold text-sm text-gray-600">Soru</th>
                        <th class="p-3 font-semibold text-sm text-gray-600">Süre (sn)</th>
                    </tr>
                </thead>
                <tbody id="leaderboard-body" class="divide-y">
                    <tr><td colspan="6" class="p-4 text-center text-gray-500">Yükleniyor...</td></tr>
                </tbody>
            </table>
        </div>
        <div class="mt-4 text-center">
            <a href="/yarisma-secim" class="bg-blue-500 text-white font-semibold py-2 px-4 rounded-lg hover:bg-blue-600 transition-all">
                Ana Menüye Dön
            </a>
        </div>
    </div>
    <script>
        document.addEventListener('DOMContentLoaded', async () => {
            const tbody = document.getElementById('leaderboard-body');
            try {
                const response = await fetch('/api/takim/get_leaderboard');
                const tablo = await response.json();
                
                if (tablo.length === 0) {
                    tbody.innerHTML = `<tr><td colspan="6" class="p-4 text-center text-gray-500">Henüz kayıtlı bir skor yok.</td></tr>`;
                    return;
                }
                
                tbody.innerHTML = ""; // Temizle
                
                const rozetIkonlari = {
                    'altin': '<i class="fa-solid fa-medal text-yellow-400" title="Altın"></i>',
                    'gümüş': '<i class="fa-solid fa-medal text-gray-400" title="Gümüş"></i>',
                    'bronz': '<i class="fa-solid fa-medal text-yellow-600" title="Bronz"></i>',
                    'yok': '-'
                };
                
                tablo.forEach((entry, index) => {
                    const row = `
                        <tr class="hover:bg-gray-50">
                            <td class="p-3 font-bold">${index + 1}</td>
                            <td class="p-3 font-semibold text-blue-600">${entry.takim_adi}</td>
                            <td class="p-3 text-sm text-gray-600">${entry.okul_sinif}</td>
                            <td class="p-3 text-lg">${rozetIkonlari[entry.rozet] || '-'}</td>
                            <td class="p-3 font-semibold">${entry.soru_sayisi} / 10</td>
                            <td class="p-3">${entry.toplam_sure_saniye} sn</td>
                        </tr>
                    `;
                    tbody.innerHTML += row;
                });
                
            } catch (e) {
                tbody.innerHTML = `<tr><td colspan="6" class="p-4 text-center text-red-500">Liderlik tablosu yüklenemedi: ${e.message}</td></tr>`;
            }
        });
    </script>
</body>
</html>
"""

# --- YENİ LİDERLİLK HTML BİTTİ 

# --- YENİ EKLENDİ: VİDEO İSTEK SAYFASI HTML (800 KELİME LİMİTLİ) ---
# VIDEO_ISTEGI_PAGE_HTML -> templates/video_istek.html konumuna taşındı.
# --- VİDEO İSTEK SAYFASI HTML BİTTİ ---



# ###############################################################
# --- PYTHON (FLASK) ROTALARI ---
# ###############################################################

# ########## YENİ EKLENDİ: TAKIM YARIŞMASI API ROTALARI ##########

@app.route('/api/takim/basla', methods=['POST'])
def takim_yarisma_baslat():
    """Yarışmayı başlatır (EN AZ 2 ONLINE KİŞİ KURALI EKLENDİ)."""
    try:
        data = request.get_json()
        takimlar_listesi = data.get('takimlarListesi')
        okul = data.get('okul')
        sinif = data.get('sinif')

        if not takimlar_listesi or len(takimlar_listesi) < 2:
            return jsonify({"success": False, "hata": "En az 2 takım gereklidir."})

        # --- YENİ KURAL: En az 2 Çevrimiçi Kişi Kontrolü ---
        online_sayisi = 0
        su_an = time.time()
        for takim in takimlar_listesi:
            for uye in takim.get('uyeler', []):
                no = str(uye.get('no'))
                son_gorulme = online_users.get(no, 0)
                if su_an - son_gorulme < 15: # Son 15 saniyede buradaysa
                    online_sayisi += 1
        
        if online_sayisi < 2:
            return jsonify({"success": False, "hata": f"Yarışma başlatılamaz! Şu an sadece {online_sayisi} kişi çevrimiçi. En az 2 çevrimiçi öğrenci gereklidir."})
        # --------------------------------------------------

        # ... (Geri kalan kodlar aynı: Yarışma oluştur, redirect kaydet vb.) ...
        yarisma_id = f"game_{pd.Timestamp.now().strftime('%Y%m%d%H%M%S')}"
        yeni_yarisma = ty.TakimYarismasi(takimlar_listesi, okul, sinif)
        active_team_games[yarisma_id] = yeni_yarisma
        
        if okul and sinif:
            game_redirects[f"{okul}_{sinif}"] = yarisma_id

        return jsonify({"success": True, "yarisma_id": yarisma_id})

    except Exception as e:
        print(f"Hata: {e}")
        return jsonify({"success": False, "hata": str(e)})

@app.route('/api/check_for_game', methods=['POST'])
def check_for_game():
    """Öğrencinin okul/sınıfına ait aktif yarışma olup olmadığını kontrol eder."""
    try:
        data = request.get_json()
        okul = data.get('okul')
        sinif = data.get('sinif')
        
        if not okul or not sinif:
            return jsonify({"found": False})

        redirect_key = f"{okul}_{sinif}"
        yarisma_id = game_redirects.get(redirect_key)
        
        # Eğer bir ID varsa VE o oyun hala hafızada (bitmemiş) ise
        if yarisma_id and yarisma_id in active_team_games:
            return jsonify({"found": True, "yarisma_id": yarisma_id})
        else:
            return jsonify({"found": False})

    except Exception as e:
        print(f"Oyun kontrol hatası: {e}")
        return jsonify({"found": False})

@app.route('/api/ping', methods=['POST'])
def api_ping():
    """Öğrenciden gelen 'ben buradayım' sinyalini kaydeder."""
    try:
        data = request.get_json()
        student_no = data.get('student_no')
        
        # Konsola bilgi yazdıralım ki çalıştığını görelim
        if student_no:
             # online_users sözlüğünü güncelle
            online_users[student_no] = time.time()
            return jsonify({"success": True})
            
        return jsonify({"success": False})
    except Exception as e:
        print(f"Ping hatası: {e}")
        return jsonify({"success": False})

# TODO (SONRAKİ ADIMLAR):
# @app.route('/api/takim/yanit_ver', methods=['POST'])
# @app.route('/api/takim/durum_al', methods=['GET'])

# ########## TAKIM YARIŞMASI API ROTALARI BİTTİ ##########

# Ana sayfa (Giriş ekranı) için route
@app.route('/')
def index():
    """Yeni ana ekranı sunar."""
    return render_template('login.html')

# --- YENİ GİRİŞ ROTALARI (3 ROL İÇİN) ---

@app.route('/login-student', methods=['POST'])
def login_student():
    """Öğrenci girişini (Okul No + Şifre ile) kontrol eder."""
    try:
        data = request.get_json()
        student_no_input = data.get('student_no')
        password_input = data.get('password')

        if not student_no_input or not password_input:
            return jsonify({'success': False, 'message': 'Öğrenci numarası veya şifre boş olamaz.'})

        # --- DÜZELTME: Tüm veritabanını döngüye al ---
        # Artık '100' anahtarını aramıyoruz, 'student_no' alanı '100' olanı arıyoruz.
        for user_id, user_data in users.items():
            
            # Bu kullanıcı bir öğrenci mi?
            if user_data.get('role') != 'student':
                continue # Değilse, sıradakine geç

            # Öğrenci numarası ve şifre tutuyor mu?
            if (user_data.get('student_no') == student_no_input and 
                db_helper.verify_password(password_input, user_data.get('password'))):
                
                # EŞLEŞME BULUNDU!
                user_first_name = user_data.get('first_name', '')
                user_last_name = user_data.get('last_name', 'Kullanıcı')
                user_full_name = f"{user_first_name} {user_last_name}".strip()
                
                return jsonify({
                    'success': True, 
                    'name': user_full_name, 
                    'user_id': user_id, # Benzersiz ID (örn: "100_TOKİ Demokrasi Ortaokulu")
                    'school_name': user_data.get('school_name', ''),
                    'class': user_data.get('class', ''),
                    'user_no': user_data.get('student_no', '') # <-- ÇOK ÖNEMLİ: Orijinal "100" numarasını yolluyoruz
                })

        # Döngü bitti ve eşleşme bulunamadı
        return jsonify({'success': False, 'message': 'Öğrenci numarası veya şifre hatalı.'})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/login-teacher', methods=['POST'])
def login_teacher():
    """Öğretmen girişini (Soyadı ile) kontrol eder."""
    try:
        data = request.get_json()
        lastname = data.get('lastname')
        password = data.get('password')
        
        # Tüm kullanıcıları döngüye al (Öğretmenler soyadıyla girdiği için)
        for user_id, user_data in users.items():
            if (user_data.get('role') == 'teacher' and 
                user_data.get('last_name', '').lower() == lastname.lower() and 
                db_helper.verify_password(password, user_data.get('password'))):
                
                # Session'a bilgileri kaydet
                session["role"] = "teacher"
                session["school_name"] = user_data.get("school_name", "")
                session["class"] = user_data.get("class", "")
                session["user_id"] = user_id
                user_full_name = f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip()
                return jsonify({
                    'success': True, 
                    'name': user_full_name,
                    'user_id': user_id, 
                    'class': user_data.get('class'),
                    'school_name': user_data.get('school_name')  # ← 'school_name' OLMALI!
                })
        
        return jsonify({'success': False, 'message': 'Soyad veya şifre hatalı.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/login-admin', methods=['POST'])
def login_admin():
    """Yönetici girişini (Soyadı ile) kontrol eder."""
    try:
        data = request.get_json()
        username = data.get('username') # Admin de 'soyisim' ile giriş yapıyordu
        password = data.get('password')
        
        for user_id, user_data in users.items():
            if (user_data.get('role') == 'admin' and 
                user_data.get('last_name', '').lower() == username.lower() and 
                db_helper.verify_password(password, user_data.get('password'))):
                
                user_full_name = f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip()
                return jsonify({
                    'success': True, 
                    'name': user_full_name,
                    'user_id': user_id
                })
        
        return jsonify({'success': False, 'message': 'Yönetici adı veya şifre hatalı.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# --- YENİ KAYIT ROTALARI (3 ROL İÇİN) ---

def generate_unique_id(prefix='user'):
    """ 'user_1729384756' gibi benzersiz bir ID oluşturur """
    import time
    return f"{prefix}_{int(time.time() * 1000)}"

@app.route('/register-student', methods=['POST'])
def register_student():
    """Yeni öğrenci kaydı oluşturur. (Okul+No olarak benzersiz ID ile)"""
    try:
        data = request.get_json()
        student_no = data.get('student_no')
        school_name = data.get('school_name') # <-- 1. Okul adını al
        
        if not student_no or not school_name:
             return jsonify({'success': False, 'message': 'Okul numarası veya okul adı boş olamaz.'})

        # --- DÜZELTME: Benzersiz ID oluştur ---
        # Örn: "100_TOKİ Demokrasi Ortaokulu"
        unique_id = f"{student_no}_{school_name}"

        # --- DÜZELTME: Kontrolü unique_id üzerinden yap ---
        if unique_id in users:
            # Artık "100_TOKİ Demokrasi Ortaokulu" kaydı var mı diye bakacak
            return jsonify({'success': False, 'message': 'Bu öğrenci (numara ve okul) zaten kayıtlı!'})
        
        # (Diğer döngüye gerek kalmadı, çünkü anahtarımız zaten benzersiz)

        # --- DÜZELTME: unique_id'yi anahtar olarak kullan ---
        users[unique_id] = {
            'role': 'student',
            'student_no': student_no, # Veriyi içeride tut
            'school_name': school_name,
            'first_name': data.get('first_name'),
            'last_name': data.get('last_name'),
            'class': data.get('class'),
            'password': data.get('password')
        }
        return jsonify({'success': True, 'message': 'Öğrenci kaydı başarılı! Giriş yapabilirsiniz.'})
    
    except Exception as e:
        print(f"Öğrenci kayıt hatası: {e}")
        # Veritabanına kaydet
        db_helper.save_user(unique_id, users[unique_id])
        return jsonify({'success': False, 'message': str(e)})

@app.route('/register-teacher', methods=['POST'])
def register_teacher():
    """Yeni öğretmen kaydı oluşturur."""
    try:
        data = request.get_json()
        lastname = data.get('last_name')
        
        # Öğretmenlerin benzersiz bir ID'ye ihtiyacı var (Öğrenci No gibi değil)
        new_user_id = generate_unique_id(prefix='teacher')
        
        # Bu soyadla başka öğretmen var mı? (Giriş için kritik)
        for user_data in users.values():
            if (user_data.get('role') == 'teacher' and 
                user_data.get('last_name', '').lower() == lastname.lower()):
                return jsonify({'success': False, 'message': 'Bu soyad ile kayıtlı başka bir öğretmen var. Lütfen yöneticinizle iletişime geçin veya soyadınıza bir ek (örn: Yılmaz2) yapın.'})

        users[new_user_id] = {
            'role': 'teacher',
            'school_name': data.get('school_name'),
            'first_name': data.get('first_name'),
            'last_name': lastname,
            'class': data.get('class'), # Sorumlu olduğu sınıf
            'password': data.get('password')
        }
        # Veritabanına kaydet
        db_helper.save_user(new_user_id, users[new_user_id])
        return jsonify({'success': True, 'message': 'Öğretmen kaydı başarılı! Giriş yapabilirsiniz.'})
    
    except Exception as e:
        print(f"Öğretmen kayıt hatası: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/register-admin', methods=['POST'])
def register_admin():
    """Yeni yönetici kaydı oluşturur."""
    try:
        data = request.get_json()
        lastname = data.get('last_name') # Giriş için kullanıcı adı olarak kullanılacak

        new_user_id = generate_unique_id(prefix='admin')
        
        # Bu soyadla başka admin var mı?
        for user_data in users.values():
            if (user_data.get('role') == 'admin' and 
                user_data.get('last_name', '').lower() == lastname.lower()):
                return jsonify({'success': False, 'message': 'Bu soyad ile kayıtlı başka bir yönetici var.'})

        users[new_user_id] = {
            'role': 'admin',
            'school_name': data.get('school_name'),
            'first_name': data.get('first_name'),
            'last_name': lastname,
            'title': data.get('title'), # Unvan
            'password': data.get('password')
        }
        # Veritabanına kaydet
        db_helper.save_user(new_user_id, users[new_user_id])
        return jsonify({"success": True, "message": "Yönetici kaydı başarılı! Giriş yapabilirsiniz."})

    except Exception as e:
        print(f"Yönetici kayıt hatası: {e}")
        return jsonify({'success': False, 'message': str(e)})

# --- KAYIT ROTALARI BİTTİ ---

# Dashboard sayfası
@app.route('/dashboard')
def dashboard():
    """Rol bazlı dashboard"""
    user_role = session.get('role', 'student')
    if user_role == 'teacher':
        return render_template('dashboard_teacher.html')
    return render_template('dashboard.html')

@app.route('/haritada-bul')
def haritada_bul():
    """Haritada Bul sayfası - Geliştirme aşamasında"""
    return render_template('dashboard.html')

# --- Metin Oluşturma Rotaları ---
# ==========================================
# METİN OLUŞTURMA SİSTEMİ (DÜZELTİLMİŞ)
# ==========================================

@app.route('/metin-olusturma')
def metin_olusturma_page():
    """Metin oluşturma sayfasını render eder."""
    
    # Modelin yüklenip yüklenmediğini kontrol edelim
    global gemini_model
    if not gemini_model:
        try:
            # Modeli yüklemeyi dene
            gemini_model = metin_uretim.api_yapilandir(app.config.get('GEMINI_API_KEY', ''))
            if not gemini_model:
                print("Metin oluşturma sayfasında model yüklenemedi.")
                flash("Sunucu hatası: Gemini modeli yüklenemedi.", "danger")
        except Exception as e:
            print(f"Model yükleme hatası: {e}")
            flash(f"Sunucu hatası: {e}", "danger")

    # Şablonu render et (templates/metin_uretim.html dosyasını kullanıyor olmalı)
    # Eğer templates dosyası yoksa, HTML string'i buraya gömülebilir.
    # Ancak senin yapında 'metin_uretim.html' templates klasöründe görünüyor.
    try:
        return render_template(
            'metin_uretim.html',
            prompt_sablonlari=metin_uretim.PROMPT_SABLONLARI,
            metin_tipleri=metin_uretim.PROMPT_SABLONLARI  # Gerekli veri
        )
    except Exception as e:
        return f"Şablon hatası: {str(e)} (templates/metin_uretim.html dosyasını kontrol edin)"

@app.route('/api/generate-text', methods=['POST'])
def api_generate_text():
    """AJAX isteği ile metin üretir."""
    try:
        global gemini_model
        if not gemini_model:
            return jsonify({"success": False, "metin": "Sunucuda Gemini API Anahtarı yapılandırılmamış veya yüklenememiş!", "kelime_sayisi": 0, "uyari": ""})

        data = request.get_json()
        
        # Parametreleri al
        bilesen_kodu = data.get('bilesen_kodu')
        metin_tipi_adi = data.get('metin_tipi_adi')
        student_no = data.get('student_no')  # YENİ: student_no'yu al
        
        print(f"Metin üretme isteği: {bilesen_kodu}, {metin_tipi_adi}")
        
        # Parametre kontrolü
        if not bilesen_kodu or not metin_tipi_adi:
             return jsonify({"success": False, "metin": "Eksik parametre: Süreç Bileşeni veya Metin Tipi seçilmedi."})
        
        # metin_uretim.py'daki fonksiyonu çağır
        result = metin_uretim.metin_uret(bilesen_kodu, metin_tipi_adi, gemini_model)

        # YENİ: RAPORLAMAYA EKLE - Metin başarıyla üretildiyse
        if result.get('success') and student_no:
            db_helper.kaydet_kullanim(student_no, "Metin Oluşturma", "Metin oluşturuldu")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Metin üretme API hatası: {e}")
        if "API_KEY_INVALID" in str(e):
             return jsonify({"success": False, "metin": "Geçersiz Gemini API Anahtarı! Lütfen sunucu kodundaki anahtarı kontrol edin.", "kelime_sayisi": 0, "uyari": ""})
        return jsonify({"success": False, "metin": f"Sunucu hatası: {str(e)}", "kelime_sayisi": 0, "uyari": ""})

# ########## YENİ EKLENDİ: METİN ANALİZ ROTALARI ##########

@app.route('/metin-analiz')
def metin_analiz_page():
    """Metin analiz sayfasını render eder."""
    print("Metin Analiz sayfasına erişim sağlandı")
    return render_template('metin_analiz.html')

@app.route('/api/analyze-text', methods=['POST'])
def api_analyze_text():
    """AJAX isteği ile metni analiz eder."""
    try:
        global gemini_model
        if not gemini_model:
            return jsonify({"success": False, "hata": "Sunucuda Gemini API Anahtarı yapılandırılmamış!"})

        data = request.get_json()
        metin = data.get('metin')
        student_no = data.get('student_no')

        if not metin or not student_no:
             return jsonify({"success": False, "hata": "Eksik parametre: Metin veya Öğrenci No."})

        # metin_analiz.py'deki ana fonksiyonu çağırıyoruz
        result = metin_analiz.metin_analiz_et(metin, student_no, gemini_model)

        # YENİ: RAPORLAMAYA EKLE - Metin analiz başarılıysa
        if result.get('success'):
            db_helper.kaydet_kullanim(student_no, "Metin Analiz", "Metin analiz edildi")

        return jsonify(result)

    except Exception as e:
        print(f"Metin analiz API hatası: {e}")
        if "API_KEY_INVALID" in str(e):
             return jsonify({"success": False, "hata": "Geçersiz Gemini API Anahtarı!"})
        return jsonify({"success": False, "hata": f"Sunucu hatası: {str(e)}"})

# ########## YENİ EKLENDİ: SORU ÜRETİM ROTALARI ##########

@app.route('/soru-uretim')
def soru_uretim_page():
    """Soru üretim sayfasını render eder."""
    print("Soru Üretim sayfasına erişim sağlandı")
    return render_template(
        'soru_uretim.html',
        # soru_uretim.py'den SORU_SABLONLARI verisini HTML'e gönderiyoruz
        soru_sablonlari=soru_uretim.SORU_SABLONLARI
    )

@app.route('/api/generate-question', methods=['POST'])
def api_generate_question():
    try:
        data = request.get_json()
        student_no = data.get('student_no')
        
        # KESİN TEST - Her durumda kayıt yap
        print(f"🎯 KESİN TEST - student_no: {student_no}")
        
        # TEST: Her durumda kayıt yap (başarılı/başarısız fark etmez)
        if student_no:
            print(f"✅ KESİN KAYIT - {student_no} için kayıt yapılıyor")
            db_helper.kaydet_kullanim(student_no, "Soru Üretim", "Soru üretildi")
        else:
            print(f"❌ student_no YOK - data: {data}")
        
        # Mevcut kodun devamı...
        global gemini_model
        if not gemini_model:
            return jsonify({"success": False, "metin": "Sunucuda Gemini API Anahtarı yapılandırılmamış!"})

        bilesen_kodu = data.get('bilesen_kodu')
        soru_tipi_adi = data.get('soru_tipi_adi')

        if not bilesen_kodu or not soru_tipi_adi:
             return jsonify({"success": False, "metin": "Eksik parametre: Süreç Bileşeni veya Soru Tipi."})

        # Limit kontrolü
        limit_result = check_and_update_soru_limit(student_no)
        if not limit_result["success"]:
            return jsonify({"success": False, "metin": limit_result["hata"]})

        result = soru_uretim.soru_uret(bilesen_kodu, soru_tipi_adi, gemini_model)

        return jsonify({
            "success": result.get("success", False),
            "metin": result.get("metin", "Hata oluştu."),
            "rubrik_cevap": result.get("rubrik_cevap"),
            "is_mcq": result.get("is_mcq", False),
            "kelime_sayisi": result.get("kelime_sayisi", 0)
        })

    except Exception as e:
        print(f"❌ SORU ÜRETİM HATASI: {e}")
        return jsonify({"success": False, "metin": f"Sunucu hatası: {str(e)}"})
# ########## YARIŞMA ROTALARI (GÜNCELLENDİ) ##########
@app.route('/api/takim/get_sinif_listesi', methods=['POST'])
def get_sinif_listesi():
    """Okul ve sınıf seçimine göre filtrelenmiş öğrenci listesini döndürür."""
    try:
        data = request.get_json()
        okul = data.get('okul')
        sinif = data.get('sinif')
        
        if not okul or not sinif:
            return jsonify({"success": False, "hata": "Okul veya sınıf bilgisi eksik."})

        global users
        sinif_listesi = []
        for student_no, user_data in users.items():
            if user_data.get('school_name') == okul and user_data.get('class') == sinif:
                sinif_listesi.append({
                    "no": student_no,
                    "ad_soyad": f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip(),
                    "secili": False # Başlangıçta seçili değil
                })
        
        if not sinif_listesi:
            return jsonify({"success": True, "sinif_listesi": [], "mesaj": "Seçilen sınıf ve okul için kayıtlı öğrenci bulunamadı."})
            
        return jsonify({"success": True, "sinif_listesi": sinif_listesi})

    except Exception as e:
        print(f"Sınıf listesi çekme hatası: {e}")
        return jsonify({"success": False, "hata": str(e)})

@app.route('/yarisma-secim')
def yarisma_secim_page():
    print("Yarışma seçim sayfasına erişim sağlandı")
    return render_template('yarisma_secim.html')

# --- Bireysel Yarışma Rotaları (YENİ) ---

@app.route('/bireysel-yarisma')
def bireysel_yarisma_page():
    print("Bireysel Yarışma sayfasına erişim sağlandı")
    # Artık boş değil, gerçek oyun arayüzünü (V6) render ediyoruz
    return render_template('bireysel_yarisma.html')

@app.route('/api/bireysel/basla', methods=['POST'])
def bireysel_basla():
    """ 
    Öğrenci durumunu kontrol eder. 
    EĞER ÖNCEKİ OYUN BİTMİŞSE (Skor >= 10) OTOMATİK SIFIRLAR.
    """
    try:
        data = request.get_json()
        student_no = data.get('student_no')
        if not student_no:
            return jsonify({'success': False, 'mesaj': 'Öğrenci numarası eksik.'})

        # 1. Mevcut durumu çek
        durum_response = by_v6.get_ogrenci_durumu(student_no)
        
        # --- DÜZELTME BAŞLANGICI: Otomatik Sıfırlama ---
        # Eğer durum başarılıysa ve öğrenci 10 soruyu tamamlamışsa, yeni oyun için sıfırla
        if durum_response.get('success') and durum_response.get('durum'):
            mevcut_dogru = durum_response['durum'].get('dogru_soru_sayisi', 0)
            
            if mevcut_dogru >= 10:
                print(f"🔄 KULLANICI {student_no} OYUNU BİTİRMİŞ. VERİLER SIFIRLANIYOR...")
                
                # Veritabanında puanı ve süreyi sıfırla
                conn = db_helper.get_db_connection()
                cur = conn.cursor()
                
                # Puanı sıfırla
                cur.execute("""
                    UPDATE bireysel_skorlar 
                    SET dogru_soru_sayisi = 0, toplam_sure_saniye = 0, updated_at = CURRENT_TIMESTAMP 
                    WHERE student_no = %s
                """, (student_no,))
                
                # Rozetleri sil (Yeni oyun için)
                cur.execute("DELETE FROM ogrenci_rozetler WHERE student_no = %s", (student_no,))
                
                conn.commit()
                cur.close()
                conn.close()
                
                # Sıfırlama sonrası durumu tekrar taze çek
                durum_response = by_v6.get_ogrenci_durumu(student_no)
        # --- DÜZELTME BİTİŞİ ---
        return jsonify(durum_response)
        
    except Exception as e:
        print(f"Bireysel başla API hatası: {e}")
        return jsonify({'success': False, 'mesaj': str(e)})

@app.route('/api/bireysel/yeni_soru', methods=['POST'])
def bireysel_yeni_soru():
    """ 
    (SÜRÜM 8) Artık Gemini'yi çağırmaz.
    Hafızadan (veya gerekirse Bankadan) sıradaki soruyu çeker.
    """
    try:
        # --- GÜNCELLENDİ: 'gemini_model' parametresi kaldırıldı ---
        data = request.get_json()
        student_no = data.get('student_no')
        if not student_no:
            return jsonify({"success": False, "data": {"metin": "Öğrenci No eksik."}})
            
        # Model parametresi olmadan çağırıyoruz
        soru_response = by_v6.get_yeni_soru_from_gemini(None, student_no)
        return jsonify(soru_response)
        
    except Exception as e:
        print(f"Bireysel yeni soru API hatası: {e}")
        return jsonify({'success': False, 'data': {"metin": str(e)}})

@app.route('/api/bireysel/kaydet_dogru', methods=['POST'])
def bireysel_kaydet_dogru():
    """ Bir soruyu (metni) doğru tamamladığında skoru kaydeder """
    try:
        data = request.get_json()
        student_no = data.get('student_no')
        soru_suresi_saniye = data.get('soru_suresi_saniye', 60) # Süre gelmezse 60 say
        
        if not student_no:
            return jsonify({'success': False, 'mesaj': 'Öğrenci numarası eksik.'})
            
        kayit_response = by_v6.kaydet_soru_sonucu(student_no, soru_suresi_saniye)
        return jsonify(kayit_response)
        
    except Exception as e:
        print(f"Bireysel doğru kaydet API hatası: {e}")
        return jsonify({'success': False, 'mesaj': str(e)})

@app.route('/api/bireysel/kaydet_elenme', methods=['POST'])
def bireysel_kaydet_elenme():
    """ Elendiğinde süreyi kaydeder """
    try:
        data = request.get_json()
        student_no = data.get('student_no')
        harcanan_sure_saniye = data.get('harcanan_sure_saniye', 60)
        
        if not student_no:
            return jsonify({'success': False, 'mesaj': 'Öğrenci numarası eksik.'})
        
        kayit_response = by_v6.kaydet_elenme_sonucu(student_no, harcanan_sure_saniye)
        return jsonify(kayit_response)
        
    except Exception as e:
        print(f"Bireysel elenme kaydet API hatası: {e}")
        return jsonify({'success': False, 'mesaj': str(e)})

# --- Liderlik Tablosu Rotaları (YENİ) ---
@app.route('/leaderboard')
def leaderboard_page():
    print("Liderlik Tablosu sayfasına erişim sağlandı")
    return render_template('leaderboard.html')

@app.route('/api/get_leaderboard', methods=['GET'])
def api_get_leaderboard():
    """ 
    İki veritabanını birleştirip sıralı listeyi döner.
    Eğer '?class=SINIF' parametresi varsa, o sınıfa göre filtreler 
    ve 'top_5' olarak döndürür (İstek 3).
    """
    try:
        # --- YENİ (AŞAMA 4.2): Sınıf filtresini al ---
        sinif_filtresi = request.args.get('class', None)

        # 'users' (ana db) ve 'bireysel_yaris' modülünü kullan
        # by_v6.get_leaderboard fonksiyonu artık 'sinif_filtresi' parametresini de alacak
        leaderboard_data = by_v6.get_leaderboard(users, sinif_filtresi)

        if sinif_filtresi:
            # Öğretmen, kendi sınıfını istedi. 'top_5' olarak döndür.
            # (by_v6.get_leaderboard bu filtrelemeyi ve sıralamayı zaten yapacak)
            return jsonify({'success': True, 'top_5': leaderboard_data})
        else:
            # Öğrenci veya genel bakış, tüm listeyi 'leaderboard' olarak döndür.
            return jsonify({'success': True, 'leaderboard': leaderboard_data})
        # --- BİTTİ ---

    except Exception as e:
        print(f"Liderlik tablosu API hatası: {e}")
        return jsonify({'success': False, 'message': str(e)})

# --- Takım Yarışması Rotaları (Hala Placeholder) ---

@app.route('/takim-yarisma')
def takim_yarisma_page():
    print("Takım Yarışması sayfasına erişim sağlandı")
    return render_template('takim_kurulum.html')
# TODO: /api/takim/create, /api/takim/join, /api/takim/cevap_ver vb. API rotaları buraya eklenecek.

# ########## BİTTİ ##########


# --- YÖNETİCİ API ROTALARI ---
# --- YENİ YÖNETİCİ ROTALARI (AŞAMA 2.5) ---

@app.route('/get_all_users', methods=['GET'])
def get_all_users():
    """Tüm kullanıcıları ve ÇEVRİMİÇİ durumlarını döndürür."""
    try:
        users_data = users if users is not None else {}
        
        current_time = time.time()
        
        # Veritabanındaki her kullanıcıyı kontrol et
        for user_id, user_data in users_data.items():
            
            # --- KRİTİK DÜZELTME BURADA ---
            # Sorun: user_id bazen "469_OkulAdi", ama ping sadece "469" geliyor.
            # Çözüm: user_id'ye değil, user_data içindeki 'student_no'ya bakacağız.
            
            # 1. Öğrenci numarasını verinin içinden al. Yoksa ID'yi kullan.
            # (String'e çeviriyoruz ki garanti olsun)
            ogrenci_no = str(user_data.get('student_no', user_id))
            
            # 2. Online listesinde BU numarayı ara
            last_seen = online_users.get(ogrenci_no, 0)
            
            # 3. Son 15 saniye içinde sinyal geldiyse çevrimiçi say (Süreyi biraz artırdım)
            if current_time - last_seen < 15:
                user_data['is_online'] = True
            else:
                user_data['is_online'] = False
        # ----------------------------------------

        return jsonify({'success': True, 'users': users_data})
    except Exception as e:
        print(f"Kullanıcı listesi alma hatası: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/delete_user', methods=['POST'])
def delete_user():
    """Herhangi bir kullanıcıyı ID'sine göre siler."""
    try:
        data = request.get_json()
        # JavaScript artık 'user_id' yolluyor
        user_id = data.get('user_id') 

        if user_id in users:
            del users[user_id]
            print(f"Kullanıcı silindi: {user_id}")
            return jsonify({'success': True, 'message': 'Kullanıcı silindi!'})
        else:
            return jsonify({'success': False, 'message': 'Kullanıcı bulunamadı!'})
    except Exception as e:
        print(f"Kullanıcı silme hatası: {e}")
        return jsonify({'success': False, 'message': str(e)})

# --- YÖNETİCİ ROTALARI GÜNCELLENDİ ---

@app.route('/delete_student_bulk', methods=['POST'])
def delete_student_bulk():
    try:
        import db_helper
        conn = db_helper.get_db_connection()
        cur = conn.cursor()
        
        data = request.get_json()
        student_ids = data.get('student_ids', [])
        
        if not student_ids:
            return jsonify({'success': False, 'message': 'Silinecek öğrenci seçilmedi.'})
            
        # SQL'den sil
        # student_ids listesini tuple'a çevirip SQL'e veriyoruz
        cur.execute("DELETE FROM users WHERE user_id = ANY(%s)", (student_ids,))
        deleted_count = cur.rowcount
        
        conn.commit()
        cur.close()
        conn.close()
        
        # RAM'den de temizle
        for sid in student_ids:
            if sid in users:
                del users[sid]
        
        return jsonify({'success': True, 'message': f'{deleted_count} öğrenci veritabanından silindi!'})
    except Exception as e:
        print(f"Toplu silme hatası: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/update_student_bulk', methods=['POST'])
def update_student_bulk():
    try:
        import db_helper # Veritabanı bağlantısı
        
        data = request.get_json()
        student_ids = data.get('student_ids', [])
        actions = data.get('actions', {})
        
        updated_count = 0
        
        # Seçili öğrencileri güncelle
        for student_no in student_ids:
            # RAM'de var mı kontrol et (veya doğrudan DB'ye de bakılabilir)
            if student_no in users:
                user_data = users[student_no] # Mevcut veriyi al
                updated = False
                
                # Okul Güncelle
                if actions.get('school'):
                    user_data['school_name'] = actions['school']
                    updated = True
                
                # Sınıf Güncelle
                if actions.get('class'):
                    user_data['class'] = actions['class']
                    updated = True
                
                # Şifre Sıfırla
                if actions.get('set_password_to_lastname'):
                    last_name = user_data.get('last_name', '')
                    if last_name:
                        user_data['password'] = last_name
                        updated = True
                        
                # Rol Değişimi (Güvenlikli)
                if actions.get('role') == 'student':
                    if user_data.get('role') not in ['teacher', 'admin']:
                        user_data['role'] = 'student'
                        updated = True
                
                # Eğer değişiklik varsa VERİTABANINA YAZ
                if updated:
                    # RAM'i güncelle
                    users[student_no] = user_data
                    # SQL'i güncelle
                    db_helper.save_user(student_no, user_data)
                    updated_count += 1
        
        return jsonify({'success': True, 'message': f'{updated_count} öğrenci veritabanında güncellendi!'})
    except Exception as e:
        print(f"Toplu güncelleme hatası: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/upload_excel', methods=['POST'])
def upload_excel():
    global users # <--- BU SATIRI EN BAŞA ALDIK (Düzeltme Burada)
    try:
        import db_helper
        
        if 'excelFile' not in request.files:
            return jsonify({'success': False, 'message': 'Dosya bulunamadı'})
            
        file = request.files['excelFile']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'Dosya seçilmedi'})

        # Dosyayı oku
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(file.read().decode('utf-8-sig')), dtype=str)
            df.rename(columns={'NO': 'Öğrenci No', 'ADI': 'Adı', 'SOYADI': 'Soyadı', 'SINIF': 'Sınıf', 'OKUL': 'Okul'}, inplace=True)
        else:
            df = pd.read_excel(file, dtype=str)
            df.rename(columns={'NO': 'Öğrenci No', 'ADI': 'Adı', 'SOYADI': 'Soyadı', 'SINIF': 'Sınıf', 'OKUL': 'Okul'}, inplace=True)

        required_columns = ['Öğrenci No', 'Adı', 'Soyadı']
        if not all(col in df.columns for col in required_columns):
            return jsonify({'success': False, 'message': 'Excel dosyasında "Öğrenci No", "Adı", "Soyadı" sütunları mutlaka olmalı.'})

        count = 0
        for index, row in df.iterrows():
            student_no = str(row['Öğrenci No']).strip()
            
            user_data = {
                'role': 'student',
                'student_no': student_no,
                'first_name': str(row['Adı']).strip(),
                'last_name': str(row['Soyadı']).strip(),
                'password': '',
                'class': str(row['Sınıf']).strip() if 'Sınıf' in df.columns and pd.notna(row['Sınıf']) else '',
                'school_name': str(row['Okul']).strip() if 'Okul' in df.columns and pd.notna(row['Okul']) else ''
            }

            # 1. RAM'i güncelle
            users[student_no] = user_data
            
            # 2. VERİTABANINI GÜNCELLE
            db_helper.save_user(student_no, user_data)
            count += 1
        
        # Hafızayı veritabanından tazele (Reassign yapıldığı için global şarttı)
        users = db_helper.load_users()
        
        print(f"✅ {count} öğrenci veritabanına başarıyla kaydedildi.")
        return jsonify({'success': True, 'message': f'{count} öğrenci veritabanına yüklendi!'})

    except Exception as e:
        print(f"Excel yükleme hatası: {e}")
        return jsonify({'success': False, 'message': f"Hata: {str(e)}"})
# ########## BİTTİ ##########
# (Burası sosyallab.py dosyanızın sonu olmalı)
# ... (Mevcut en son kodunuz, muhtemelen /upload_excel rotası) ...

# ########## YENİ EKLENDİ: PODCAST OLUŞTURMA ROTALARI ##########
# (podcast_dinle.py içeriği) 

# --- 'static' KLASÖRÜNÜN VARLIĞINDAN EMİN OLUN ---
if not os.path.exists('static'):
    os.makedirs('static')

# BU KODU app.py DOSYASINDAKİ "def seyret_bul_ogrenci_page():" YERİNE YAPIŞTIRIN

# ==========================================
# SEYRET BUL (ORİJİNAL SOL MENÜLÜ TASARIM)
# ==========================================

@app.route('/seyret-bul-liste')
def seyret_bul_liste_page():
    user_role = session.get('role', 'student')
    try:
        surecler_dict = seyret_bul.tum_surecleri_getir()
        unite_yapisi = seyret_bul.UNITE_YAPISI
        return render_template(
            'seyret_bul.html',
            role=user_role,
            surecler_sozlugu=surecler_dict,
            unite_yapisi=unite_yapisi
        )
    except Exception as e:
        print(f"Hata: {e}")
        return f"Hata: {str(e)}"


@app.route('/api/seyret-bul/surecler')
def api_get_surecler():
    """Tüm süreç bileşenlerini döndürür"""
    try:
        surecler_dict = seyret_bul.tum_surecleri_getir()
        surecler_listesi = [{"kod": kod, "aciklama": aciklama} for kod, aciklama in surecler_dict.items()]
        return jsonify({"success": True, "surecler": surecler_listesi})
    except Exception as e:
        return jsonify({"success": False, "hata": str(e)})

@app.route('/api/seyret-bul/videolar')
def api_get_videolar_by_surec():
    """
    Belirli bir süreç bileşeni koduna ait videoları listeler.
    (JavaScript'in 2. dropdown'u doldurması için)
    """
    try:
        surec_kodu = request.args.get('kod')
        if not surec_kodu:
            return jsonify({"success": False, "hata": "Süreç kodu eksik."})
        # seyret_bul.py'deki fonksiyonu çağır
        videolar = seyret_bul.surece_gore_videolari_getir(surec_kodu)
        return jsonify({"success": True, "videolar": videolar})
    except Exception as e:
        print(f"Videoları getir API hatası: {e}")
        return jsonify({"success": False, "hata": str(e)})

@app.route('/seyret-bul/izle/<string:video_id>')
def seyret_bul_izle_page(video_id):
    """Video izleme sayfası"""
    return render_template('seyret_bul_izle.html', video_id=video_id)

@app.route('/api/seyret-bul/video-detay/<string:video_id>')
def api_video_detay(video_id):
    """Video detaylarını ve sorularını döndürür"""
    video = seyret_bul.video_detay_getir(video_id)
    if video:
        return jsonify({"success": True, "video": video})
    return jsonify({"success": False, "mesaj": "Video bulunamadı"})


# Kullanıcının sağladığı 5. Sınıf müfredat verisi
PODCAST_CURRICULUM_DATA = """
Süreç Bileşenleri:
SB.5.1.1. Dâhil olduğu gruplar ve bu gruplardaki rolleri arasındaki ilişkileri çözümleyebilme
SB.5.1.2. Kültürel özelliklere saygı duymanın birlikte yaşamaya etkisini yorumlayabilme
SB.5.1.3. Toplumsal birliği sürdürmeye yönelik yardımlaşma ve dayanışma faaliyetlerine katkı sağlayabilme
SB.5.2.1. Yaşadığı ilin göreceli konum özelliklerini belirleyebilme
SB.5.2.2. Yaşadığı ilde doğal ve beşerî çevredeki değişimi neden ve sonuçlarıyla yorumlayabilme
SB.5.2.3. Yaşadığı ilde meydana gelebilecek afetlerin etkilerini azaltmaya yönelik farkındalık etkinlikleri düzenleyebilme
SB.5.2.4. Ülkemize komşu devletler hakkında bilgi toplayabilme
SB.5.3.1. Yaşadığı ildeki ortak miras ögelerine ilişkin oluşturduğu ürünü paylaşabilme
SB.5.3.2. Anadolu’da ilk yerleşimleri kuran toplumların sosyal hayatlarına yönelik bakış açısı geliştirebilme
SB.5.3.3. Mezopotamya ve Anadolu medeniyetlerinin ortak mirasa katkılarını karşılaştırabilme
SB.5.4.1. Demokrasi ve cumhuriyet kavramları arasındaki ilişkiyi çözümleyebilme
SB.5.4.2. Toplum düzenine etkisi bakımından etkin vatandaş olmanın önemine yönelik çıkarımda bulunabilme
SB.5.4.3. Temel insan hak ve sorumluluklarının önemini sorgulayabilme
SB.5.4.4. Bir ihtiyaç hâlinde veya sorun karşısında başvuru yapılabilecek kurumlar hakkında başvuru yapılabilecek kurumlar hakkında bilgi toplayabilme
SB.5.5.1. Kaynakları verimli kullanmanın doğa ve insanlar üzerindeki etkisini yorumlayabilme
SB.5.5.2. İhtiyaç ve isteklerini karşılamak için gerekli bütçeyi planlayabilme
SB.5.5.3. Yaşadığı ildeki ekonomik faaliyetleri özetleyebilme
SB.5.6.1.Teknolojik gelişmelerin toplum hayatına etkilerini tartışabilme
SB.5.6.2. Teknolojik ürünlerin bilinçli kullanımının önemine ilişkin ürün oluşturabilme

Öğrenme Alanları (Konular):
1. ÖĞRENME ALANI: BİRLİKTE YAŞAMAK (Gruplar, roller, haklar, sorumluluklar, kültür, yardımlaşma)
2. ÖĞRENME ALANI: EVİMİZ DÜNYA (Konum, doğal ve beşerî çevre, afetler, komşu devletler)
3. ÖĞRENME ALANI: ORTAK MİRASIMIZ (Ortak miras, Anadolu ve Mezopotamya medeniyetleri)
4. ÖĞRENME ALANI: YAŞAYAN DEMOKRASİMİZ (Demokrasi, cumhuriyet, etkin vatandaş, hak ve sorumluluklar, kurumlar)
5. ÖĞRENME ALANI: HAYATIMIZDAKİ EKONOMİ (Kaynak verimliliği, bütçe, ekonomik faaliyetler)
6. ÖĞRENME ALANI: TEKNOLOJİ ve SOSYAL BİLİMLER (Teknolojik gelişmelerin etkileri, bilinçli kullanım)
"""

def _create_podcast_validation_prompt(user_text):
    """Podcast metninin uygunluğunu denetlemek için Gemini prompt'u hazırlar (v2 - Bileşen listesi ister)."""
    return f"""
    Görevin, bir 5. Sınıf Sosyal Bilgiler müfredat uzmanı olarak, bir metnin bu müfredatla ne kadar ilgili olduğunu analiz etmektir.

    AŞAĞIDAKİ MÜFREDAT BİLGİSİNİ KULLAN:
    ---
    {PODCAST_CURRICULUM_DATA}
    ---

    ANALİZ EDİLECEK METİN:
    ---
    {user_text}
    ---

    GÖREV:
    1.  Metnin, sağlanan 5. Sınıf Sosyal Bilgiler müfredatıyla (hem süreç bileşenleri hem de öğrenme alanları) ne kadar ilgili olduğunu 0 ile 100 arasında bir yüzde ile derecelendir.
    2.  Eğer uygunluk %70'in altındaysa:
        - "aciklama" alanına neden 5. sınıf Sosyal Bilgiler konusuyla ilgisiz olduğuna dair KISA bir açıklama yap.
        - "uyumlu_bilesenler" alanını boş bir dizi [] olarak bırak.
    3.  Eğer uygunluk %70 veya üzerindeyse:
        - "aciklama" alanına "Metin 5. Sınıf Sosyal Bilgiler müfredatıyla uyumludur." yaz.
        - "uyumlu_bilesenler" alanına, metnin DOĞRUDAN ilgili olduğu süreç bileşeni KODLARINI (örn: "SB.5.1.1") içeren bir dizi (array) ekle.
    4.  Yanıtını SADECE aşağıdaki JSON formatında ver, başka HİÇBİR ŞEY yazma.

    JSON FORMATI (Başarılıysa):
    {{
      "uygunluk_yuzdesi": 85,
      "aciklama": "Metin 5. Sınıf Sosyal Bilgiler müfredatıyla uyumludur.",
      "uyumlu_bilesenler": ["SB.5.3.2", "SB.5.3.3"]
    }}
    
    JSON FORMATI (Başarısızsa):
    {{
      "uygunluk_yuzdesi": 30,
      "aciklama": "Bu metin daha çok Fen Bilimleri konusudur.",
      "uyumlu_bilesenler": []
    }}
    ---
    JSON ÇIKTIN:
    """

def validate_text_relevance(user_text, model):
    """Metnin müfredata uygunluğunu Gemini ile kontrol eder (v2 - Bileşen listesi alır)."""
    try:
        prompt = _create_podcast_validation_prompt(user_text)
        # DÜZELTME: Python dict'i tek parantez olmalı
        response = model.generate_content(prompt, request_options={'timeout': 45}) 
        
        # JSON'u ayrıştır
        try:
            # DÜZELTME: re.search tek parantez olmalı
            match = re.search(r"```json\s*(\{.*\})\s*```", response.text, re.DOTALL)
            if match:
                json_text = match.group(1)
            else:
                json_text = response.text.strip()
            gemini_json = json.loads(json_text)
        except Exception as json_err:
            # DÜZELTME: f-string tek parantez olmalı
            print(f"Podcast JSON Ayrıştırma Hatası: {json_err} - Yanıt: {response.text}")
            # DÜZELTME: return dict tek parantez olmalı
            return {"success": False, "error": f"Gemini'den gelen analiz yanıtı işlenemedi."}

        yuzde = gemini_json.get("uygunluk_yuzdesi")
        aciklama = gemini_json.get("aciklama")
        bilesenler_listesi = gemini_json.get("uyumlu_bilesenler", []) 
        
        if yuzde is None or aciklama is None:
            # DÜZELTME: return dict tek parantez olmalı
            return {"success": False, "error": "Gemini analizinden eksik veri ('uygunluk_yuzdesi' veya 'aciklama') alındı."}
        
        # DÜZELTME: return dict tek parantez olmalı
        return {
            "success": True, 
            "uygunluk_yuzdesi": int(yuzde), 
            "aciklama": aciklama,
            "uyumlu_bilesenler": bilesenler_listesi
        }

    except Exception as e:
        hata_mesaji = str(e)
        # DÜZELTME: f-string tek parantez olmalı
        print(f"Podcast validasyon API hatası: {hata_mesaji}")
        # DÜZELTME: return dict tek parantez olmalı
        return {"success": False, "error": f"Gemini analiz API'sinde hata: {hata_mesaji}"}

# --- Podcast Konu Kontrolü Bitişi ---

# ==========================================
# PODCAST SİSTEMİ (EKSİK ROTALAR)
# ==========================================
# ==========================================
# PODCAST PANELİ (ORİJİNAL SOL MENÜLÜ TASARIM)
# ==========================================
@app.route('/podcast_paneli')
def podcast_paneli():
    """Podcast Panel - Rol bazlı"""
    user_role = session.get('role', 'student')
    return render_template('podcast.html', role=user_role)

@app.route('/generate-podcast', methods=['POST'])
def handle_generation():
    data = request.get_json()
    user_text = data.get('text')
    student_no = data.get('student_no')  # student_no'yu en başta alalım
    
    if not user_text:
        return jsonify({"success": False, "error": "Metin boş olamaz."}), 400

    try:
        # --- 1. Metin Uygunluğunu Kontrol Et ---
        print("🔵 1. Metnin müfredata uygunluğu kontrol ediliyor...")
        global gemini_model
        validation_result = validate_text_relevance(user_text, gemini_model)
        
        if not validation_result.get("success"):
            return jsonify(validation_result), 500

        uygunluk_yuzdesi = validation_result.get("uygunluk_yuzdesi", 0)
        aciklama = validation_result.get("aciklama", "Açıklama yok.")

        if uygunluk_yuzdesi < 70:
            print(f"❌ Metin reddedildi. Uygunluk: {uygunluk_yuzdesi}%")
            return jsonify({
                "success": False,
                "error": f"Metin Reddedildi (Uygunluk: {uygunluk_yuzdesi}%). \n\nAçıklama: {aciklama}"
            }), 400
        
        print(f"✅ Metin onaylandı. (Uygunluk: {uygunluk_yuzdesi}%)")

        # --- 2. Gemini ile podcast metni oluştur ---
        print("🔵 2. Gemini ile podcast metni oluşturuluyor...")
        podcast_text = podcast_creator.generate_podcast_content(user_text, gemini_model)
        
        if not podcast_text:
            return jsonify({"success": False, "error": "Gemini'den boş yanıt alındı."}), 500
        
        print(f"✅ Podcast metni oluşturuldu: {podcast_text[:100]}...")
        
        # --- 3. Piper ile ses dosyası oluştur ---
        print("🔵 3. Piper ile ses dosyası oluşturuluyor...")
        audio_url = podcast_creator.convert_text_to_speech(podcast_text, app.static_folder)
        
        if not audio_url:
            return jsonify({"success": False, "error": "Piper TTS ses oluşturamadı."}), 500
        
        print(f"✅ Ses URL: {audio_url}")
        
        # YENİ: RAPORLAMAYA EKLE - Podcast başarıyla oluşturulduysa
        if student_no:
            db_helper.kaydet_kullanim(student_no, "Podcast Yap", "Podcast oluşturuldu")
            print(f"🔍 DEBUG: student_no = {student_no} - Raporlamaya eklendi")

        return jsonify({
            "success": True,
            "audio_url": audio_url,
            "validation_data": validation_result
        })

    except Exception as e:
        print(f"❌ HATA: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

def degerlendirme_promptu_olustur(soru_metni, kullanici_cevabi):
    """Kısa cevabı değerlendirmek için Gemini prompt'u hazırlar (JSON - Puanlama v2)."""
    return f"""
    Bir 5. Sınıf Sosyal Bilgiler öğretmenisin. Görevin, bir soruya verilen öğrenci cevabını 1 (çok yetersiz) ile 5 (tamamen doğru) arasında puanlamak ve yapıcı geri bildirim vermektir.

    KURALLAR:
    1.  Cevabı anlamsal doğruluğuna göre değerlendir. Birebir aynı kelimeler gerekmez.
    2.  Puanlama 1-5 arası olmalıdır.
    3.  Geri bildirimin, öğrencinin 5/5 alması için neyi eksik yaptığını açıklamalıdır.
    4.  Yanıtını SADECE aşağıdaki JSON formatında ver, başka HİÇBİR ŞEY yazma:

    {{
      "skor": <1-5 arası bir tamsayı>,
      "geri_bildirim": "<Öğrenciye verilecek yapıcı geri bildirim metni>"
    }}

    ÖRNEK ÇIKTILAR:
    - Tam doğruysa: {{ "skor": 5, "geri_bildirim": "Tebrikler, cevabın anlamsal olarak tam ve doğru." }}
    - Kısmen doğruysa: {{ "skor": 3, "geri_bildirim": "Cevabın doğru yolda, ancak 'x' konusundan da bahsetseydin daha net olacaktı." }}
    - Yanlışsa: {{ "skor": 1, "geri_bildirim": "Cevabın sorunun ana noktasıyla ilgisiz görünüyor. Metindeki 'y' konusuna tekrar odaklanmalısın." }}

    ---
    SORU:
    "{soru_metni}"

    ÖĞRENCİ CEVABI:
    "{kullanici_cevabi}"
    ---

    JSON ÇIKTIN:
    """
    
def kisa_cevabi_degerlendir(soru_metni, kullanici_cevabi, model):
    """Kısa cevabı Gemini ile değerlendirir (JSON - Puanlama v2)."""
    if not model:
        return {"success": False, "hata": "Değerlendirme modeli yüklenemedi."}
        
    if not kullanici_cevabi or kullanici_cevabi.strip() == "":
        return {"success": False, "hata": "Cevap boş bırakılamaz."}

    try:
        # Adım 1: Yeni prompt'u (yukarıdaki fonksiyonu) çağır
        prompt = degerlendirme_promptu_olustur(soru_metni, kullanici_cevabi)
        
        # API çağrısı
        response = model.generate_content(prompt, request_options={'timeout': 30})
        
        # Adım 2: Gelen yanıtı JSON olarak ayrıştır
        try:
            # Önce ```json ... ``` bloğunu arayalım
            # Not: json_parse_et fonksiyonu seyret_bul.py'de kaldı, o yüzden burada manuel ayrıştırma yapacağız.
            
            # JSON'u ayıklamak için re (regex) import etmeniz gerekebilir. 
            # sosyallab_fixed.py'nin en üstüne 'import re' ve 'import json' eklediğinizden emin olun.
            match = re.search(r"```json\s*(\{.*\})\s*```", response.text, re.DOTALL)
            if match:
                json_text = match.group(1)
            else:
                json_text = response.text.strip()

            gemini_json = json.loads(json_text)

        except Exception as json_err:
            print(f"JSON Ayrıştırma Hatası: {json_err} - Yanıt: {response.text}")
            return {"success": False, "hata": f"Gemini'den gelen yanıt işlenemedi. Yanıt: {response.text}"}

        # Adım 3: JSON'dan skor ve geri bildirimi al
        skor = gemini_json.get("skor")
        geri_bildirim = gemini_json.get("geri_bildirim")

        if skor is not None and geri_bildirim is not None:
            # JavaScript'e (checkCevap fonksiyonuna) beklediği formatı gönder
            return {
                "success": True, 
                "skor": skor, 
                "geri_bildirim": geri_bildirim
            }
        else:
            return {"success": False, "hata": "Gemini yanıtında 'skor' veya 'geri_bildirim' alanları eksik."}

    except Exception as e:
        hata_mesaji = str(e)
        if "DeadlineExceeded" in hata_mesaji:
            hata_mesaji = "Gemini değerlendirmesi zaman aşımına uğradı."
        elif "response.prompt_feedback" in hata_mesaji:
            hata_mesaji = "Gemini güvenlik filtrelerine takıldı. Cevabınızı değiştirin."
            
        print(f"Kısa cevap değerlendirme hatası: {hata_mesaji}")
        return {"success": False, "hata": f"Değerlendirme sırasında API hatası: {hata_mesaji}"}

# --- YENİ EKLENDİ: VİDEO İSTEK ROTALARI ---
@app.route('/video-istegi')
def video_istegi_page():
    """Video isteği gönderme sayfasını sunar."""
    print("Video İstek sayfasına erişim sağlandı")
    return render_template('video_istek.html')

@app.route('/api/video-istegi-gonder', methods=['POST'])
def video_istegi_gonder():
    """Öğretmenden gelen video isteğini PostgreSQL veritabanına kaydeder."""
    try:
        data = request.get_json()
        
        istek_metni = data.get('istek_metni')
        isteyen_kullanici = data.get('isteyen_ogretmen', 'Bilinmiyor')
        kullanici_rol = data.get('kullanici_rol', 'Bilinmiyor')
        kullanici_no = data.get('kullanici_no')
        kullanici_okul = data.get('kullanici_okul')
        kullanici_sinif = data.get('kullanici_sinif')
        
        if not istek_metni:
            return jsonify({"success": False, "hata": "İstek metni boş olamaz."})
        
        # Yeni isteği oluştur (Sözlük yapısı db_helper ile uyumlu)
        yeni_istek = {
            "id": f"istek_{int(pd.Timestamp.now().timestamp())}",
            "tarih": pd.Timestamp.now().isoformat(), # db_helper timestamp bekliyorsa str gönderiyoruz, SQL çevirir
            "ogretmen": isteyen_kullanici,
            "metin": istek_metni,
            "durum": "Yeni",
            "rol": kullanici_rol,
            "okul": kullanici_okul,
            "sinif": kullanici_sinif,
            "no": kullanici_no
        }
        
        # --- LİSTEYE DEĞİL, DOĞRUDAN DB'YE KAYIT ---
        basarili = db_helper.save_video_istek(yeni_istek)
        
        if basarili:
            return jsonify({"success": True, "mesaj": "İstek veritabanına kaydedildi."})
        else:
            return jsonify({"success": False, "hata": "Veritabanı kayıt hatası."})
        
    except Exception as e:
        print(f"Video isteği API hatası: {e}")
        return jsonify({"success": False, "hata": str(e)})

# --- VİDEO İSTEK ROTALARI BİTTİ ---
# --- YENİ EKLENDİ: VİDEO İSTEKLERİNİ ÇEKME ROTASI ---
@app.route('/api/get-video-istekleri', methods=['GET'])
def api_get_video_istekleri():
    """Tüm video isteklerini PostgreSQL veritabanından çeker."""
    try:
        # --- DEĞİŞİKLİK BURADA: Global liste yerine DB'den çek ---
        istekler = db_helper.get_all_video_istekleri()
        return jsonify({"success": True, "istekler": istekler})
    except Exception as e:
        print(f"Video istekleri çekme API hatası: {e}")
        return jsonify({"success": False, "hata": str(e)})
# --- BİTTİ ---

# --- YENİ EKLENDİ: VİDEO İSTEĞİ SİLME ROTASI (3. İsteğiniz) ---
@app.route('/api/delete-video-istek', methods=['POST'])
def api_delete_video_istek():
    """Bir video isteğini ID'sine göre PostgreSQL veritabanından siler."""
    try:
        data = request.get_json()
        istek_id = data.get('istek_id')
        
        if not istek_id:
            return jsonify({"success": False, "hata": "İstek ID'si eksik."})

        # --- DEĞİŞİKLİK BURADA: Listeden arama yok, direkt DB'den sil ---
        basarili = db_helper.delete_video_istek(istek_id)
        
        if basarili:
            return jsonify({"success": True, "mesaj": "İstek veritabanından silindi."})
        else:
            return jsonify({"success": False, "hata": "Silme işlemi başarısız (veya kayıt bulunamadı)."})
            
    except Exception as e:
        print(f"Video isteği silme API hatası: {e}")
        return jsonify({"success": False, "hata": str(e)})
# --- BİTTİ ---

@app.route('/api/seyret-bul/admin/edit-video', methods=['POST'])
def api_admin_edit_video():
    """
    Yönetici panelinden gelen video düzenleme isteğini işler.
    (Adım 4'teki JavaScript bu rotayı çağıracak)
    """
    try:
        data = request.get_json()
        video_id = data.get('video_id')
        yeni_baslik = data.get('yeni_baslik')
        yeni_surec = data.get('yeni_surec') # Bu 'value' boş olabilir

        if not video_id or not yeni_baslik:
            return jsonify({"success": False, "hata": "Video ID veya Başlık eksik."})

        # 'seyret_bul.py' içindeki fonksiyonları çağırıyoruz
        videos_dict = seyret_bul.videolari_yukle()
        
        if video_id not in videos_dict:
            return jsonify({"success": False, "hata": "Video bulunamadı."})

        # 1. Başlığı Güncelle
        videos_dict[video_id]['baslik'] = yeni_baslik
        
        # 2. Süreç bileşenini GÜNCELLE (eğer yeni bir tane seçildiyse)
        if yeni_surec and yeni_surec != "":
            videos_dict[video_id]['surec_bileseni'] = yeni_surec
            
        # 3. Değişiklikleri JSON dosyasına kaydet
        seyret_bul.videolari_kaydet(videos_dict)
        
        print(f"Video güncellendi: {video_id} - {yeni_baslik}")
        return jsonify({"success": True, "mesaj": "Video başarıyla güncellendi."})

    except Exception as e:
        print(f"Video DÜZENLEME API hatası: {e}")
        return jsonify({"success": False, "hata": str(e)})

# ########## YENİ EKLENDİ: TAKIM YARIŞMASI OYUN API ROTALARI ##########

@app.route('/takim-oyun-ekrani/<string:yarisma_id>')
def takim_oyun_ekrani(yarisma_id):
    """Yeni oyun ekranı HTML'ini sunar."""
    if yarisma_id not in active_team_games:
        return "Yarışma bulunamadı veya zaman aşımına uğradı.", 404
    # HATA BURADAYDI, ŞİMDİ DÜZELDİ (HTML'i yukarıya eklediniz)
    return render_template('takim_oyun.html')

@app.route('/takim-liderlik-tablosu')
def takim_liderlik_tablosu_sayfasi():
    """Yeni liderlik tablosu HTML'ini sunar."""
    # HATA BURADAYDI, ŞİMDİ DÜZELDİ (HTML'i yukarıya eklediniz)
    return render_template('takim_leaderboard.html')

@app.route('/api/takim/get_leaderboard', methods=['GET'])
def api_get_takim_leaderboard():
    """Liderlik tablosu verisini JSON olarak döndürür."""
    try:
        skorlar = ty.load_takim_skorlari()
        return jsonify(skorlar)
    except Exception as e:
        return jsonify({"success": False, "hata": str(e)}), 500

@app.route('/api/takim/get_durum/<string:yarisma_id>')
def api_get_takim_durum(yarisma_id):
    """Bir yarışmanın mevcut durumunu JSON olarak döndürür."""
    
    oyun = active_team_games.get(yarisma_id)
    if not oyun:
        return jsonify({"success": False, "hata": "Yarışma bulunamadı."})

    # --- ÖĞRETMEN ZAMAN AŞIMI KONTROLÜ ---
    import time
    su_an = time.time()
    
    if not hasattr(oyun, 'son_ogretmen_sinyali'):
        oyun.son_ogretmen_sinyali = su_an
    
    is_teacher = request.args.get('ogretmen_burada') == 'evet'
    
    if is_teacher:
        oyun.son_ogretmen_sinyali = su_an
    
    if su_an - oyun.son_ogretmen_sinyali > 75:
        print(f"Zaman aşımı! {yarisma_id} siliniyor...")
        if yarisma_id in active_team_games:
            del active_team_games[yarisma_id]
        for key, val in list(game_redirects.items()):
            if val == yarisma_id:
                del game_redirects[key]
        return jsonify({"success": False, "hata": "Öğretmen ayrıldığı için yarışma sonlandırıldı."})
    # -------------------------------------

    try:
        durum_datasi = oyun.durumu_json_yap()
        
        # --- YENİ: Kaptan Çevrimiçi mi? ---
        kaptan_id = durum_datasi.get("aktif_takim_kaptani_id")
        is_online = False
        if kaptan_id:
            # Kaptan ID'sini string'e çevirip kontrol et (Veri türü hatasını önlemek için)
            last_seen = online_users.get(str(kaptan_id), 0)
            if time.time() - last_seen < 15: # 15 saniye tolerans
                is_online = True
        
        durum_datasi["kaptan_cevrimici_mi"] = is_online
        # ----------------------------------

        durum_datasi["success"] = True
        return jsonify(durum_datasi)
    except Exception as e:
        return jsonify({"success": False, "hata": str(e)})
    # -----------------------------------------------------
    
    try:
        durum_datasi = oyun.durumu_json_yap()
        durum_datasi["success"] = True
        return jsonify(durum_datasi)
    except Exception as e:
        return jsonify({"success": False, "hata": str(e)})

@app.route('/api/takim/soru_goster/<string:yarisma_id>')
def api_soru_goster(yarisma_id):
    """(SÜRÜM 8) Aktif takım için Soru Bankası'ndan sıradaki soruyu ister."""
    oyun = active_team_games.get(yarisma_id)
    if not oyun:
        return jsonify({"success": False, "hata": "Yarışma bulunamadı."})
    
    aktif_takim_id = oyun.get_aktif_takim_id()
    if not aktif_takim_id:
        return jsonify({"success": False, "hata": "Aktif takım bulunamadı."})
    
    # --- GÜNCELLENDİ: 'gemini_model' parametresi kaldırıldı ---
    # Artık 'bireysel_soru_bankasi.json' dosyasından anında çekecek
    sonuc = oyun.soru_iste(aktif_takim_id)
    return jsonify(sonuc)

@app.route('/api/takim/cevap_ver/<string:yarisma_id>', methods=['POST'])
def api_cevap_ver(yarisma_id):
    """Bir takımın cevabını işler."""
    oyun = active_team_games.get(yarisma_id)
    if not oyun:
        return jsonify({"success": False, "hata": "Yarışma bulunamadı."})
        
    data = request.get_json()
    sonuc = oyun.cevap_ver(
        takim_id=data.get('takim_id'),
        tiklanan_tip=data.get('tiklanan_tip'),
        tiklanan_cumle=data.get('tiklanan_cumle')
    )
    return jsonify(sonuc)

@app.route('/api/takim/bilgisayar_oynasin/<string:yarisma_id>', methods=['POST'])
def api_bilgisayar_oynasin(yarisma_id):
    """(Yeni Özellik) Sıradaki takım yerine bilgisayar rastgele bir hamle yapar."""
    try:
        oyun = active_team_games.get(yarisma_id)
        if not oyun:
            return jsonify({"success": False, "hata": "Oyun bulunamadı."})
        
        aktif_takim_id = oyun.get_aktif_takim_id()
        if not aktif_takim_id:
            return jsonify({"success": False, "hata": "Aktif takım yok."})
            
        # %50 Şansla Doğru veya Yanlış yap
        import random
        sans = random.random() # 0.0 ile 1.0 arası
        
        soru = oyun.mevcut_soru_verisi
        if not soru:
            return jsonify({"success": False, "hata": "Soru yok."})

        # Hangi tipi oynayacağına karar ver (Beceri bulunmadıysa Beceri, yoksa Değer)
        takim = oyun.takimlar[aktif_takim_id]
        tiklanan_tip = "beceri" if not takim["bulunan_beceri"] else "deger"
        
        if sans > 0.5:
            # DOĞRU HAMLE YAP
            tiklanan_cumle = soru["beceri_cumlesi"] if tiklanan_tip == "beceri" else soru["deger_cumlesi"]
            print(f"🤖 Bilgisayar DOĞRU oynadı ({tiklanan_tip})")
        else:
            # YANLIŞ HAMLE YAP (Rastgele bir cümle seç)
            tum_cumleler = soru["metin"].replace('!', '.').replace('?', '.').split('.')
            # Boş olmayan rastgele bir cümle seç
            adaylar = [c.strip() for c in tum_cumleler if len(c.strip()) > 5]
            if adaylar:
                tiklanan_cumle = random.choice(adaylar)
            else:
                tiklanan_cumle = "Hatalı Cümle"
            print(f"🤖 Bilgisayar YANLIŞ oynadı ({tiklanan_tip})")

        # Sanki o takım cevap vermiş gibi işlem yap
        sonuc = oyun.cevap_ver(aktif_takim_id, tiklanan_tip, tiklanan_cumle)
        
        # Bilgisayar oynadı mesajını ekle
        sonuc["mesaj"] = "🤖 Bilgisayar Oynadı: " + sonuc["mesaj"]
        
        return jsonify(sonuc)

    except Exception as e:
        print(f"Bilgisayar hamlesi hatası: {e}")
        return jsonify({"success": False, "hata": str(e)})

@app.route('/api/takim/siradaki_takim/<string:yarisma_id>')
def api_siradaki_takim(yarisma_id):
    """Sırayı bir sonraki takıma geçirir."""
    oyun = active_team_games.get(yarisma_id)
    if not oyun:
        return jsonify({"success": False, "hata": "Yarışma bulunamadı."})
    
    oyun.siradaki_takima_gec()
    return jsonify({"success": True})

@app.route('/api/takim/bitir/<string:yarisma_id>', methods=['POST'])
def api_yarismayi_bitir_ve_kaydet(yarisma_id):
    """(Kural 36, 38) Yarışma bitince skoru kaydeder. (Otomatik Kazanan Bulma Eklendi)"""
    oyun = active_team_games.get(yarisma_id)
    if not oyun:
        return jsonify({"success": False, "hata": "Yarışma bulunamadı."})
    
    kazanan_id = oyun.kazanan_takim_id
    
    # --- DÜZELTME: Eğer sistem bir kazanan belirlemediyse, ayakta kalan son takımı bul ---
    if not kazanan_id:
        # Elenmemiş (aktif) takımları bul
        elenmeyenler = [tid for tid, takim in oyun.takimlar.items() if not takim.get('elendi', False)]
        
        # Eğer sadece 1 takım kaldıysa, o kazanmıştır
        if len(elenmeyenler) == 1:
            kazanan_id = elenmeyenler[0]
            print(f"🏆 Oyun Bitti: Otomatik Kazanan Belirlendi -> {oyun.takimlar[kazanan_id]['isim']}")
    # -------------------------------------------------------------------------------------
    
    # Eğer bir kazanan varsa (veya şimdi bulduysak) kaydet
    if kazanan_id:
        kazanan_takim = oyun.takimlar[kazanan_id]
        
        try:
            ty.kaydet_yarışma_sonucu(
                takim_adi=kazanan_takim["isim"],
                rozet=kazanan_takim["rozet"],
                soru_sayisi=kazanan_takim["puan"],
                toplam_sure=kazanan_takim["toplam_sure_saniye"],
                okul=oyun.okul,
                sinif=oyun.sinif
            )
            print(f"✅ Skor Kaydedildi: {kazanan_takim['isim']}")
            return jsonify({"success": True, "mesaj": "Skor başarıyla kaydedildi."})
        except Exception as e:
            print(f"❌ Skor Kaydetme Hatası: {e}")
            return jsonify({"success": False, "hata": str(e)})
    
    # Gerçekten kimse kalmadıysa
    return jsonify({"success": True, "mesaj": "Herkes elendi, skor kaydedilmedi."})
    
    # Kazanan yoksa (herkes elendiyse)
    return jsonify({"success": True, "mesaj": "Herkes elendi, skor kaydedilmedi."})
    
    # NOT: Oyunu buradan 'del' ile silmiyoruz! 
    # Öğrenciler son durumu görüp yönlensin diye oyun hafızada kalıyor.
    # 75 saniyelik "Öğretmen Zaman Aşımı" oyunu temizleyecektir.
    
# --- VERİTABANI TAMİR FONKSİYONU ---
def veritabani_tamir_et_v2():
    """Eksik 'student_no' alanlarını ID'den kopyalar."""
    try:
        degisiklik = False
        if os.path.exists(DB_FILE):
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                db = json.load(f)
            
            for uid, data in db.items():
                # Eğer rolü öğrenciyse VE içinde 'student_no' yoksa
                if data.get('role') == 'student' and 'student_no' not in data:
                    data['student_no'] = uid # ID'yi içeri kopyala
                    degisiklik = True
                    print(f"🔧 DÜZELTİLDİ: {data.get('first_name')} -> No: {uid}")
            
            if degisiklik:
                with open(DB_FILE, 'w', encoding='utf-8') as f:
                    json.dump(db, f, ensure_ascii=False, indent=4)
                print("✅ Tüm öğrenci kayıtları yeni formata güncellendi.")
            else:
                print("✅ Veritabanı kontrol edildi, sorun yok.")
                
    except Exception as e:
        print(f"Tamir hatası: {e}")


# Sunucu başlarken çalıştır
veritabani_tamir_et_v2()

# ########## TAKIM YARIŞMASI OYUN API ROTALARI BİTTİ ##########
# --- DÜZELTME: Sunucuyu başlatmak için bu satırların yorumunu kaldırın ---

# === RAPORLAMA API ===
@app.route("/api/raporlar")
def api_raporlar():
    """Kullanım raporlarını döndürür"""
    okul = request.args.get("okul")
    sinif = request.args.get("sinif")
    baslangic = request.args.get("baslangic")
    bitis = request.args.get("bitis")
    
    raporlar = db_helper.get_kullanim_raporu(okul, sinif, baslangic, bitis)
    return jsonify({"success": True, "data": raporlar})


@app.route("/api/raporlar/haftalik")
def api_raporlar_haftalik():
    """Haftalık kullanım raporları"""
    okul = request.args.get("okul")
    sinif = request.args.get("sinif")
    ay = request.args.get("ay")  # Format: 2025-11
    
    if not okul or not sinif or not ay:
        return jsonify({"success": False, "error": "Okul, sınıf ve ay gerekli"})
    
    raporlar = db_helper.get_haftalik_rapor(okul, sinif, ay)
    return jsonify({"success": True, "data": raporlar})
@app.route("/raporlar")
def raporlar_sayfa():
    """Öğretmen/Yönetici rapor sayfası"""
    user_role = session.get("role", "guest")
    user_school = session.get("school_name", "")
    user_class = session.get("class", "")
    return render_template("raporlar.html", role=user_role, school=user_school, sinif=user_class)
    return render_template("raporlar.html")


# === EKSİK OLAN RAPORLAMA API'LARI ===

# ESKİ HATALI KOD DEVRE DIŞI
# @app.route("/api/okul_sinif_listesi")
def api_okul_sinif_listesi():
    """Okul ve sınıf listelerini PostgreSQL'den döndürür"""
    try:
        # db_helper üzerinden PostgreSQL bağlantısını al
        conn = db_helper.get_db_connection()
        cur = conn.cursor()
        
        # Okulları getir
        cur.execute("SELECT DISTINCT school_name FROM users WHERE school_name IS NOT NULL AND school_name != '' ORDER BY school_name")
        okullar = [row[0] for row in cur.fetchall()]
        
        # Sınıfları getir
        cur.execute("SELECT DISTINCT class FROM users WHERE class IS NOT NULL AND class != '' ORDER BY class")
        siniflar = [row[0] for row in cur.fetchall()]
        
        cur.close()
        conn.close()
        
        return jsonify({"success": True, "okullar": okullar, "siniflar": siniflar})
    except Exception as e:
        print(f"API HATA: {e}")
        return jsonify({"success": False, "error": str(e), "okullar": [], "siniflar": []})

@app.route("/api/raporlar/excel")
def api_raporlar_excel():
    """Raporları Excel olarak indir"""
    try:
        import pandas as pd
        from io import BytesIO
        from flask import send_file
        
        # Parametreleri al
        okul = request.args.get("okul")
        sinif = request.args.get("sinif")
        baslangic = request.args.get("baslangic")
        bitis = request.args.get("bitis")
        
        # db_helper fonksiyonunu çağır (Bu da Postgres kullanmalı)
        raporlar = db_helper.get_kullanim_raporu(okul, sinif, baslangic, bitis)
        
        # DataFrame oluştur
        df = pd.DataFrame(raporlar)
        
        # Excel'e yaz
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Kullanım Raporu')
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='kullanim_raporu.xlsx'
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# --- SUNUCU BAŞLATMA (EN SONDA OLMALI) ---


@app.route("/api/benim_sonuclarim", methods=["GET"])
def api_benim_sonuclarim():
    """Öğrencinin kendi bireysel sonuçlarını döndürür"""
    student_no = request.args.get("student_no")
    if not student_no:
        return jsonify({"success": False, "message": "student_no gerekli"})
    
    # Öğrenci bilgisini al
    conn = db_helper.get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT first_name, last_name, school_name, class FROM users WHERE user_no = %s", (student_no,))
    user = cur.fetchone()
    
    if not user:
        cur.close()
        conn.close()
        return jsonify({"success": False, "message": "Öğrenci bulunamadı"})
    
    # Skorlarını al
    cur.execute("SELECT dogru_soru_sayisi, toplam_sure_saniye FROM bireysel_skorlar WHERE student_no = %s", (student_no,))
    skor = cur.fetchone()
    
    # Rozetleri al
    cur.execute("SELECT rozet FROM ogrenci_rozetler WHERE student_no = %s", (student_no,))
    rozetler = [r[0] for r in cur.fetchall()]
    
    cur.close()
    conn.close()
    
    return jsonify({
        "success": True,
        "isim": user[0],
        "soyisim": user[1],
        "okul": user[2],
        "sinif": user[3],
        "dogru_soru": skor[0] if skor else 0,
        "toplam_sure": skor[1] if skor else 0,
        "rozetler": rozetler
    })


@app.route("/api/get_students", methods=["GET"])
def api_get_students():
    """Tüm öğrencileri döndürür"""
    try:
        conn = db_helper.get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT user_no, first_name, last_name, school_name, class FROM users WHERE role = %s ORDER BY school_name, class, first_name", ("student",))
        students = []
        for row in cur.fetchall():
            students.append({
                "student_no": row[0],
                "first_name": row[1],
                "last_name": row[2],
                "school_name": row[3],
                "class": row[4]
            })
        cur.close()
        conn.close()
        return jsonify({"success": True, "students": students})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/seyret-bul/kaydet-izleme', methods=['POST'])
def api_seyret_bul_kaydet_izleme():
    try:
        data = request.get_json()
        student_no = data.get('student_no')
        video_baslik = data.get('video_baslik')
        if not student_no: return jsonify({"success": False})
        import db_helper
        # YENİ: RAPORLAMAYA EKLE - Video izlendiyse
        db_helper.kaydet_kullanim(student_no, 'Seyret Bul', f"Video izlendi: {video_baslik}")
        return jsonify({"success": True})
    except: return jsonify({"success": False})
    
@app.route('/api/seyret-bul/admin/get-all-videos', methods=['GET'])
def api_get_all_videos():
    """Tüm videoları admin paneli için listeler"""
    try:
        videos_dict = seyret_bul.videolari_yukle()
        videolar = []
        for video_id, video_data in videos_dict.items():
            videolar.append({
                'video_id': video_id,
                'baslik': video_data.get('baslik', ''),
                'surec_bileseni': video_data.get('surec_bileseni', ''),
                'video_url': video_data.get('video_url', '')
            })
        return jsonify({"success": True, "videolar": videolar})
    except Exception as e:
        return jsonify({"success": False, "hata": str(e)})


@app.route('/api/seyret-bul/degerlendir', methods=['POST'])
def api_seyret_bul_degerlendir():
    try:
        data = request.get_json()
        soru = data.get('soru_metni')
        cevap = data.get('kullanici_cevabi')
        
        prompt = f'''Sen bir öğretmensin. Soru: "{soru}", Cevap: "{cevap}". 1-5 arası puanla ve kısa geri bildirim ver. Yanıt SADECE JSON olsun: {{"skor": 3, "geri_bildirim": "..."}}'''

        global gemini_model
        if not gemini_model: return jsonify({"success": True, "skor": 3, "geri_bildirim": "Yapay zeka yok."})

        response = gemini_model.generate_content(prompt)
        text = response.text.strip().replace("```json", "").replace("```", "")
        import json
        try:
            res = json.loads(text)
            return jsonify({"success": True, "skor": res.get('skor', 1), "geri_bildirim": res.get('geri_bildirim', '')})
        except: return jsonify({"success": True, "skor": 3, "geri_bildirim": "Otomatik puanlandı."})
    except: return jsonify({"success": True, "skor": 1, "geri_bildirim": "Hata."})

# ==========================================
# --- 1. DASHBOARD İÇİN KURTARICI KOD (JSON'DAN OKUR) ---
# ==========================================
@app.route("/api/okul_sinif_listesi")
def api_okul_sinif_listesi():
    """Dashboard'un çökmemesi için verileri users.json'dan okur"""
    try:
        global users
        okullar = set()
        siniflar = set()
        
        if users:
            for user_data in users.values():
                s_name = user_data.get('school_name')
                c_name = user_data.get('class')
                if s_name: okullar.add(s_name)
                if c_name: siniflar.add(c_name)
        
        return jsonify({
            "success": True,
            "okullar": sorted(list(okullar)),
            "siniflar": sorted(list(siniflar))
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "okullar": [], "siniflar": []})

# ==========================================
# --- 2. RAPORLAMA İÇİN FİLTRE KODLARI (JSON'DAN OKUR) ---
# ==========================================
# ==========================================
# --- 2. RAPORLAMA İÇİN FİLTRE KODLARI (SQL TABANLI - KESİN ÇÖZÜM) ---
# ==========================================

@app.route("/api/filter/get_schools")
def api_get_schools():
    """Rapor sayfası için okul listesini DOĞRUDAN SQL'den çeker"""
    try:
        import db_helper # db_helper'ın import edildiğinden emin olalım
        conn = db_helper.get_db_connection()
        cur = conn.cursor()
        
        # Sadece okulu dolu olanları getir
        cur.execute("SELECT DISTINCT school_name FROM users WHERE school_name IS NOT NULL AND school_name != '' ORDER BY school_name")
        rows = cur.fetchall()
        
        # Tuple listesini düz listeye çevir ('Okul A', 'Okul B'...)
        # rows örneği: [('Okul A',), ('Okul B',)]
        okullar = [r[0] for r in rows if r[0]]
        
        cur.close()
        conn.close()
        
        return jsonify({"success": True, "data": okullar})
    except Exception as e:
        print(f"Okul listesi SQL hatası: {e}")
        return jsonify({"success": False, "error": str(e), "data": []})


@app.route("/api/filter/get_classes")
def api_get_classes():
    """Sınıf listesini döndürür (Düzeltilmiş)"""
    try:
        okul_adi = request.args.get('school_name')
        print(f"🔍 Sınıf listesi isteniyor - Okul: '{okul_adi}'")
        
        if not okul_adi: 
            return jsonify({"success": False, "data": []})

        import db_helper
        conn = db_helper.get_db_connection()
        cur = conn.cursor()
        
        # Seçilen okula ait sınıfları getir
        cur.execute("""
            SELECT DISTINCT class FROM users 
            WHERE school_name = %s AND class IS NOT NULL AND class != '' 
            ORDER BY class
        """, (okul_adi,))
        
        rows = cur.fetchall()
        siniflar = [r[0] for r in rows if r[0]]
        
        print(f"🔍 '{okul_adi}' için bulunan sınıflar: {siniflar}")
        
        cur.close()
        conn.close()
        
        # Eğer sınıf yoksa, test sınıfları ekle
        if not siniflar:
            print("⚠️ Sınıf bulunamadı, test sınıfları ekleniyor...")
            siniflar = ['5A', '5B', '5C', '5D', '6A', '6B']
        
        return jsonify({"success": True, "data": siniflar})
    except Exception as e:
        print(f"❌ Sınıf listesi hatası: {e}")
        # Hata durumunda manuel liste döndür
        return jsonify({"success": True, "data": ['5A', '5B', '5C', '5D', '6A', '6B']})

@app.route("/api/filter/get_years")
def api_get_years():
    return jsonify({"success": True, "data": ["2024", "2025", "2026"]})

# ==========================================
# --- SUNUCU BAŞLATMA ---
# ==========================================
if __name__ == '__main__':
    print("UYGULAMA SUNUCUSU http://127.0.0.1:5002 adresinde çalışıyor...")
    print("Giriş yapmak için: http://127.0.0.1:5002")
    app.run(debug=False, host='127.0.0.1', port=5002)
