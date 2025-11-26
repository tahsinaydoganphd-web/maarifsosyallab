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

# ÖNCE API anahtarını tanımla
GEMINI_API_KEY = "AIzaSyAi5gR1RQaWihbfRstFP381glOYKbMerIU"  # <-- Gerçek anahtarınız

# SONRA Flask app'i oluştur
app = Flask(__name__)

# EN SON config'e kaydet
app.config['GEMINI_API_KEY'] = GEMINI_API_KEY
app.config['SECRET_KEY'] = 'bu-cok-gizli-bir-anahtar-olmalı-321'

# --- Haritada Bul Modülünü Kaydet ---
GOOGLE_MAPS_API_KEY = ""
harita_bul.register_harita_bul_routes(app, GOOGLE_MAPS_API_KEY)


# --- Lokal Videoları (ve Arka Planı) Serve Et ---
@app.route('/videolar/<path:filename>')
def serve_video(filename):
    """Videolar klasöründeki dosyaları serve eder (maarif.png<div id="card-metin" class="card" style="background-image: url('https://source.unsplash.com/800x1000?student,writing,notebook');"> dahil)"""
    """Videolar klasöründeki dosyaları serve eder (maarif.png dahil)"""
    return send_from_directory('videolar', filename)
# --- BİTTİ ---

# --- Kalıcı Veritabanı Ayarları ---
DB_FILE = 'users.json' # Öğrenci kayıtları için

VIDEO_ISTEKLERI_DB_FILE = 'video_istekleri.json'

def load_video_istekleri():
    """ Sunucu başladığında JSON dosyasından video isteklerini yükler. """
    if os.path.exists(VIDEO_ISTEKLERI_DB_FILE):
        try:
            with open(VIDEO_ISTEKLERI_DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return [] # Liste olarak başlat
    return []

def save_video_istekleri(data):
    """ Video isteklerini JSON dosyasına kaydeder. """
    try:
        with open(VIDEO_ISTEKLERI_DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"Video istekleri '{VIDEO_ISTEKLERI_DB_FILE}' dosyasına başarıyla kaydedildi.")
    except Exception as e:
        print(f"Video istekleri kaydetme hatası: {e}")

# Video isteklerini yükle
video_istekleri = load_video_istekleri()
# --- Video İstekleri Bitişi ---

def check_and_update_soru_limit(student_no):
    from datetime import datetime, timedelta
    limits = load_soru_limits()
    today = datetime.now().date()
    user_data = limits.get(student_no, {"count": 0, "reset_date": str(today)})
    reset_date = datetime.strptime(user_data["reset_date"], "%Y-%m-%d").date()
    if today >= reset_date:
        user_data["count"] = 0
        user_data["reset_date"] = str(today + timedelta(days=7))
    if user_data["count"] >= HAFTALIK_LIMIT:
        kalan_gun = (reset_date - today).days
        return {
            "success": False, 
            "hata": f"Haftalık soru üretim limitiniz ({HAFTALIK_LIMIT}) dolmuştur. Lütfen {kalan_gun} gün sonra tekrar deneyin."
        }
    user_data["count"] += 1
    limits[student_no] = user_data
    db_helper.save_soru_limits(limits)
    return {"success": True}
# --- Soru Üretim Limiti Bitişi ---

# Öğrenci veritabanını (users.json) yükle
users = db_helper.load_users()

# --- YENİ EKLENECEK TAMİR KODU BAŞLANGICI ---
def veritabani_tamir_et():
    """Eksik öğrenci numaralarını anahtardan (key) alıp içeri kopyalar."""
    duzeltilen_sayisi = 0
    degisiklik_var = False
    
    for user_id, data in users.items():
        # Sadece öğrenciler için işlem yap
        if data.get('role') == 'student':
            # Eğer 'student_no' alanı yoksa veya boşsa
            if 'student_no' not in data or not data['student_no']:
                data['student_no'] = user_id  # Anahtarı (user_id) içeri kopyala
                duzeltilen_sayisi += 1
                degisiklik_var = True
    
    if degisiklik_var:
        print(f"✅ OTOMATİK DÜZELTME: {duzeltilen_sayisi} öğrenci kaydı onarıldı ve kaydedildi.")
    else:
        print("✅ Veritabanı kontrol edildi, eksik kayıt yok.")

# Fonksiyonu hemen çalıştır
veritabani_tamir_et()
# --- YENİ EKLENECEK TAMİR KODU BİTİŞİ ---

# --- Gemini Modelini Yükle ---
gemini_model = None 
try:
    if GEMINI_API_KEY and GEMINI_API_KEY != "":
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel('models/gemini-pro-latest')
        print("Gemini API modeli başarıyla yüklendi.")
    else:
        print("UYARI: Gemini API Anahtarı girilmemiş. Metin üretme, Analiz ve Bireysel Yarışma özellikleri çalışmayacak.")
except Exception as e:
    print(f"Gemini API yüklenirken HATA oluştu: {e}")
# --- BİTTİ ---

# Aktif Takım Yarışmaları
active_team_games = {}
# Otomatik Yönlendirme Kaydı
game_redirects = {}
# --- YENİ EKLENDİ: Çevrimiçi Kullanıcı Takibi ---
online_users = {} # Format: {'ogrenci_no': timestamp}

# --- GİRİŞ/KAYIT SAYFASI HTML KODU (AŞAMA 5 - HATALAR DÜZELTİLDİ) ---

# (Base64 fonksiyonları kaldırıldı)

# HATA DÜZELTMESİ: f-string kaldırıldı, normal string (f"" -> """) kullanıldı.
# Bu, JavaScript'teki { } karakterlerinin SyntaxError vermesini engeller.
# HTML_CONTENT -> templates/login.html konumuna taşındı.
# --- GİRİŞ/KAYIT HTML KODU BİTTİ ---

# ###############################################################
# --- PANEL (DASHBOARD) SAYFASI ---
# ###############################################################
# DASHBOARD_HTML_CONTENT -> templates/dashboard.html konumuna taşındı.
# --- PANEL HTML KODU BİTTİ ---

# ########## YENİ EKLENDİ (Daha önce silinmişti): METİN ÜRETİM SAYFASI HTML ##########
# METIN_URETIM_PAGE_HTML -> templates/metin_uretim.html konumuna taşındı.

# ########## METİN ANALİZ HTML KODU BİTTİ ##########

# --- METİN ÜRETİM HTML KODU BİTTİ ---
# ########## YENİ EKLENDİ: METİN ANALİZ SAYFASI HTML ##########
# METIN_ANALIZ_PAGE_HTML -> templates/metin_analiz.html konumuna taşındı.
# ########## METİN ANALİZ HTML KODU BİTTİ ##########


# ########## YENİ EKLENDİ: SORU ÜRETİM SAYFASI HTML ##########
# SORU_URETIM_PAGE_HTML -> templates/soru_uretim.html konumuna taşındı.

# --- YARIŞMA SEÇİM SAYFASI HTML ---
# YARISMA_SECIM_PAGE_HTML -> templates/yarisma_secim.html konumuna taşındı.
# --- YARIŞMA SEÇİM HTML KODU BİTTİ ---


# --- Bireysel Yarışma Sayfası (Dinamik) ---
# BIREYSEL_YARISMA_HTML -> templates/bireysel_yarisma.html konumuna taşındı.
# --- BİREYSEL YARIŞMA HTML KODU BİTTİ ---
# ########## YENİ EKLENDİ: TAKIM YARIŞMASI HTML (GELİŞMİŞ KURULUM) ##########
# ########## YENİ EKLENDİ: TAKIM YARIŞMASI HTML (GELİŞMİŞ KURULUM - DÜZELTİLDİ) ##########
# TAKIM_YARISMA_HTML -> templates/takim_kurulum.html konumuna taşındı.

# --- TAKIM YARIŞMA HTML KODU BİTTİ ---


# --- Liderlik Tablosu Sayfası HTML ---
# LEADERBOARD_PAGE_HTML -> templates/leaderboard.html konumuna taşındı.
# --- LİDERLİK TABLOSU HTML KODU BİTTİ ---
# ########## YENİ EKLENDİ: TAKIM YARIŞMASI OYUN EKRANI ##########
# ########## YENİ EKLENDİ: TAKIM YARIŞMASI OYUN EKRANI (GÜNCELLENDİ V3) ##########
# TAKIM_OYUN_EKRANI_HTML -> templates/takim_oyun.html konumuna taşındı.

# ########## YENİ EKLENDİ: TAKIM YARIŞMASI LİDERLİK TABLOSU ##########
# TAKIM_LIDERLIK_TABLOSU_HTML -> templates/takim_leaderboard.html konumuna taşındı.

# ########## YENİ EKLENDİ: TAKIM YARIŞMASI LİDERLİK TABLOSU ##########
# TAKIM_LIDERLIK_TABLOSU_HTML -> templates/takim_leaderboard.html konumuna taşındı.

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
        
        print(f"Metin üretme isteği: {bilesen_kodu}, {metin_tipi_adi}")
        
        # Parametre kontrolü
        if not bilesen_kodu or not metin_tipi_adi:
             return jsonify({"success": False, "metin": "Eksik parametre: Süreç Bileşeni veya Metin Tipi seçilmedi."})
        
        # metin_uretim.py'daki fonksiyonu çağır
        result = metin_uretim.metin_uret(bilesen_kodu, metin_tipi_adi, gemini_model)
        
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
    """AJAX isteği ile soru üretir. (Haftalık Limit Kontrollü)"""
    try:
        global gemini_model
        if not gemini_model:
            return jsonify({"success": False, "metin": "Sunucuda Gemini API Anahtarı yapılandırılmamış!"})

        data = request.get_json()
        bilesen_kodu = data.get('bilesen_kodu')
        soru_tipi_adi = data.get('soru_tipi_adi')
        student_no = data.get('student_no') # YENİ

        if not bilesen_kodu or not soru_tipi_adi:
             return jsonify({"success": False, "metin": "Eksik parametre: Süreç Bileşeni veya Soru Tipi."})
        
        if not student_no:
             return jsonify({"success": False, "metin": "Hata: Kullanıcı ID'si alınamadı. Lütfen tekrar giriş yapın."})

        # --- YENİ ADIM: LİMİT KONTROLÜ ---
        limit_result = check_and_update_soru_limit(student_no)
        if not limit_result["success"]:
            # Limit aşıldıysa, hata mesajını Gemini'den gelmiş gibi döndür
            return jsonify({"success": False, "metin": limit_result["hata"]})
        # --- LİMİT KONTROLÜ BİTTİ ---

        # soru_uretim.py'deki ana fonksiyonu çağırıyoruz
        result = soru_uretim.soru_uret(bilesen_kodu, soru_tipi_adi, gemini_model)

        # JSON olarak tüm detayları gönder
        return jsonify({
            "success": result.get("success", False),
            "metin": result.get("metin", "Hata oluştu."),
            "rubrik_cevap": result.get("rubrik_cevap"), # YENİ
            "is_mcq": result.get("is_mcq", False),     # YENİ
            "kelime_sayisi": result.get("kelime_sayisi", 0)
        })

    except Exception as e:
        print(f"Soru üretme API hatası: {e}")
        if "API_KEY_INVALID" in str(e):
             return jsonify({"success": False, "metin": "Geçersiz Gemini API Anahtarı!"})
        return jsonify({"success": False, "metin": f"Sunucu hatası: {str(e)}"})
        
# ########## SORU ÜRETİM ROTALARI BİTTİ ##########
@app.route('/api/seyret_bul/get_surecler', methods=['GET'])
def api_get_seyret_bul_surecler():
    """
    Yönetici panelindeki 'Seyret Bul' formunun açılır menüsünü
    doldurmak için süreç bileşenlerini LİSTE olarak döndürür.
    """
    try:
        # seyret_bul.py'den SÖZLÜK olarak al
        surecler_dict = seyret_bul.tum_surecleri_getir() 
        # JavaScript için LİSTE'ye çevir
        surecler_listesi = [{"kod": kod, "aciklama": aciklama} for kod, aciklama in surecler_dict.items()]
        return jsonify({"success": True, "surecler": surecler_listesi})
    except Exception as e:
        return jsonify({"success": False, "hata": str(e)})
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
    (SÜRÜM 8) Öğrenci durumunu ve yasakları kontrol eder.
    Artık Gemini'yi çağırmaz.
    """
    try:
        data = request.get_json()
        student_no = data.get('student_no')
        if not student_no:
            return jsonify({'success': False, 'mesaj': 'Öğrenci numarası eksik.'})
            
        # --- GÜNCELLENDİ: 'gemini_model' parametresi kaldırıldı ---
        durum_response = by_v6.get_ogrenci_durumu(student_no)
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
        data = request.get_json()
        student_ids = data.get('student_ids', [])
        
        deleted_count = 0
        for student_no in student_ids:
            if student_no in users:
                del users[student_no]
                deleted_count += 1
        
        if deleted_count > 0:
            print(f"{deleted_count} öğrenci toplu olarak silindi.")
        
        return jsonify({'success': True, 'message': f'{deleted_count} öğrenci silindi!'})
    except Exception as e:
        print(f"Toplu öğrenci silme hatası: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/update_student_bulk', methods=['POST'])
def update_student_bulk():
    try:
        data = request.get_json()
        student_ids = data.get('student_ids', [])
        actions = data.get('actions', {})
        
        updated_count = 0
        for student_no in student_ids:
            if student_no in users:
                updated = False
                
                if actions.get('school'):
                    users[student_no]['school_name'] = actions['school']
                    updated = True
                
                if actions.get('class'):
                    users[student_no]['class'] = actions['class']
                    updated = True
                
                if actions.get('set_password_to_lastname'):
                    last_name = users[student_no].get('last_name')
                    if last_name: 
                        users[student_no]['password'] = last_name
                        updated = True
                        
                # --- YENİ EKLENDİ: Rol Atama Güvenlik Kilidi ---
                if actions.get('role') == 'student': # Eğer istek "student" rolü atamaksa...
                    # Mevcut rolün ne olduğunu KONTROL ET
                    current_role = users[student_no].get('role')
                    
                    # Sadece 'teacher' veya 'admin' DEĞİLSE bu değişikliği yap.
                    if current_role not in ['teacher', 'admin']:
                        users[student_no]['role'] = 'student'
                        updated = True
                    # (Eğer 'teacher' veya 'admin' ise, hiçbir şey yapma, koru)
                        
                elif actions.get('role'):
                    # Gelecekte 'admin' yapmak gibi başka bir rol eklerseniz burası çalışır
                    users[student_no]['role'] = actions.get('role')
                    updated = True
                # --- Güvenlik Kilidi Bitişi ---
                
                if updated:
                    updated_count += 1
        
        if updated_count > 0:
            print(f"{updated_count} öğrenci toplu olarak güncellendi.")
        
        return jsonify({'success': True, 'message': f'{updated_count} öğrenci güncellendi!'})
    except Exception as e:
        print(f"Toplu öğrenci güncelleme hatası: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/upload_excel', methods=['POST'])
def upload_excel():
    try:
        if 'excelFile' not in request.files:
            return jsonify({'success': False, 'message': 'Dosya bulunamadı'})
            
        file = request.files['excelFile']
        
        if file.filename == '':
            return jsonify({'success': False, 'message': 'Dosya seçilmedi'})

        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(file.read().decode('utf-8-sig')), dtype=str)
            df.rename(columns={'NO': 'Öğrenci No', 'ADI': 'Adı', 'SOYADI': 'Soyadı'}, inplace=True)
        else:
            df = pd.read_excel(file, dtype=str) 

        required_columns = ['Öğrenci No', 'Adı', 'Soyadı']
        if not all(col in df.columns for col in required_columns):
            return jsonify({'success': False, 'message': 'Excel/CSV dosyasında "Öğrenci No", "Adı", "Soyadı" sütunları bulunmalı!'})

        for index, row in df.iterrows():
            student_no = str(row['Öğrenci No'])
            if student_no not in users:
                    users[student_no] = {
                        'role': 'student',
                        'student_no': student_no, # <--- BU SATIRI MUTLAKA EKLEYİN
                        'first_name': str(row['Adı']),
                        'last_name': str(row['Soyadı']),
                        'class': '',       
                        'password': '',    
                        'school_name': ''  
                    }
        
        print(f"{len(df)} öğrenci Excel/CSV'den yüklendi/güncellendi.")
        return jsonify({'success': True, 'message': f'{len(df)} öğrenci başarıyla yüklendi!'})

    except Exception as e:
        print(f"Excel yükleme hatası: {e}")
        if "Missing optional dependency" in str(e):
             return jsonify({'success': False, 'message': f'Hata: {e}. Gerekli kütüphaneyi kurun (örn: pip install openpyxl)'})
        return jsonify({'success': False, 'message': str(e)})

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
    """
    seyret_bul.py'deki verileri kullanarak
    Süreç Bileşenlerine göre video listesini gösterir.
    (Düzeltilmiş ve çalışan versiyon)
    """
    try:
        # 1. seyret_bul.py'den SÖZLÜK olarak süreçleri al (Artık doğru çalışıyor)
        surecler_dict = seyret_bul.tum_surecleri_getir()
        
        # 2. JavaScript'in kullanabilmesi için LİSTE formatına çevir
        surecler_listesi = [{"kod": kod, "aciklama": aciklama} for kod, aciklama in surecler_dict.items()]
        
        # Debug removed

        # 3. HTML içeriğini oluştur
        html_content = """
        <!DOCTYPE html>
        <html lang="tr">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Seyret Bul</title>
            <script src="https://cdn.tailwindcss.com"></script>
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
            <style> 
                body { font-family: 'Inter', sans-serif; background-color: #f3f4f6; } 
                select:disabled { background-color: #f3f4f6; cursor: not-allowed; }
            </style>
        </head>
        <body class="flex h-screen">
            
            <aside class="w-72 bg-white text-gray-800 shadow-lg flex flex-col fixed h-full">
                <div class="px-6 py-4 border-b border-gray-200">
                    <h1 class="text-2xl font-extrabold text-blue-600 text-center tracking-wide mb-4">
                        Maarif SosyalLab
                    </h1>
                    <div class="mb-4">
                <div class="w-full p-2 flex items-center justify-center overflow-hidden">
                    <img src="/videolar/maarif.png"  
                         alt="Maarif Logo" 
                         class="w-auto h-auto max-w-full max-h-24 object-contain rounded-lg">
                    </div>
                </div>

                <div class="flex items-center">
                    <div id="user-avatar-initial" class="w-10 h-10 rounded-full bg-cyan-500 flex items-center justify-center text-white font-bold text-lg">K</div>
                        <div class="ml-3">
                            <span id="user-name-placeholder" class="block text-sm font-bold text-gray-800">Kullanıcı</span>
                        </div>
                    </div>
                </div>
                <nav class="flex-1 overflow-y-auto p-2 space-y-1 no-bounce">

            <a id="link-metin-analiz" href="/metin-analiz"
                class="flex items-center mx-2 p-2 rounded-lg text-white font-semibold bg-blue-500 hover:bg-blue-600 transition-all">
                <i class="fa-solid fa-file-pen mr-3 w-6 text-center"></i>
                <span>Metin Analiz</span>
            </a>
            <a id="link-soru-uretim" href="/soru-uretim"
                class="flex items-center mx-2 p-2 rounded-lg text-white font-semibold bg-green-500 hover:bg-green-600 transition-all">
                <i class="fa-solid fa-circle-question mr-3 w-6 text-center"></i>
                <span>Soru Üretim</span>
            </a>
            <a id="link-haritada-bul" href="/haritada-bul"
                class="flex items-center mx-2 p-2 rounded-lg text-white font-semibold bg-orange-500 hover:bg-orange-600 transition-all">
                <i class="fa-solid fa-map-location-dot mr-3 w-6 text-center"></i>
                <span>Haritada Bul</span>
            </a>
            <a id="link-podcast" href="/podcast_paneli"
                class="flex items-center mx-2 p-2 rounded-lg text-white font-semibold bg-red-500 hover:bg-red-600 transition-all">
                <i class="fa-solid fa-microphone-lines mr-3 w-6 text-center"></i>
                <span>Podcast Yap</span>
            </a>
            <a id="link-seyret-bul" href="/seyret-bul-liste"
                class="flex items-center mx-2 p-2 rounded-lg text-white font-semibold bg-indigo-500 hover:bg-indigo-600 transition-all">
                <i class="fa-solid fa-magnifying-glass-plus mr-3 w-6 text-center"></i>
                <span>Seyret Bul</span>
            </a>
            <a id="link-yarisma" href="/yarisma-secim"
                class="flex items-center mx-2 p-2 rounded-lg text-white font-semibold bg-teal-500 hover:bg-teal-600 transition-all">
                <i class="fa-solid fa-trophy mr-3 w-6 text-center"></i>
                <span>Beceri/Değer Avcısı</span>
            </a>
            <a id="link-video-istegi" href="/video-istegi"
                class="flex items-center mx-2 p-2 rounded-lg text-white font-semibold bg-pink-500 hover:bg-pink-600 transition-all">
                <i class="fa-solid fa-video mr-3 w-6 text-center"></i>
                <span>Video İsteği</span>
            </a>
            
        </nav>
                <div class="p-4 border-t border-gray-200">
                    <a href="/dashboard" class="flex items-center w-full p-3 rounded-lg text-gray-600 font-semibold bg-gray-100 hover:bg-gray-200 transition-all">
                        <i class="fa-solid fa-arrow-left mr-3 w-6 text-center"></i><span>Panele Geri Dön</span></a>
                </div>
            </aside>
            
            <main class="ml-72 flex-1 p-6 md:p-8 overflow-y-auto no-bounce">
                
                <h2 id="main-title" class="text-3xl font-bold text-gray-800 mb-6 cursor-pointer select-none">Seyret Bul</h2>
                
                <div id="student-view" class="bg-white p-6 rounded-lg shadow max-w-8xl mx-auto">
    
                <div class="flex flex-col md:flex-row space-y-4 md:space-y-0 md:space-x-2 justify-center mb-4 mx-auto max-w-5xl">
                    
                    <div class="w-full"> 
                        <label for="bilesen-kodu" class="block text-sm font-medium text-gray-700 mb-1">1. Süreç Bileşeni (Kazanım) Seçin:</label>
                        <select id="bilesen-kodu" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white" required>
                            <option value="">Lütfen bir süreç bileşeni seçin...</option>
                        </select>
                    </div>
                    
                    <div class="w-full">
                        <label for="video-listesi" class="block text-sm font-medium text-gray-700 mb-1">2. Videoyu Seçin:</label>
                        <select id="video-listesi" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white" required disabled>
                            <option value="">Önce Süreç Bileşeni Seçin...</option>
                        </select>
                    </div>
                    
                </div> <div class="mt-4 flex justify-center"> <button id="izle-btn" class="w-1/2 bg-indigo-500 text-white font-bold py-3 px-6 rounded-lg text-lg shadow-lg hover:bg-indigo-600 transition-all duration-300" disabled>
                        Videoyu İzle
                    </button>
                </div>

                </div>
                
                </button>
                    
                    <!-- VIDEO PLAYER (Gizli) -->
                    <div id="videoContainer" class="hidden mt-6 bg-gray-50 p-6 rounded-lg">
                        
                        <div id="player" class="mb-1 w-full max-w-4xl mx-auto"></div> 
                        
                        <div id="timeline" class="w-full max-w-2xl mx-auto mb-4 bg-gray-200 rounded-full relative hidden" style="height: 2px;">
                            <div id="progress" class="bg-indigo-500 rounded-full absolute left-0 top-0" style="width: 0%; height: 2px;"></div>
                            <div id="markers"></div>
                        </div>
                    </div>
                
                <!-- SORU MODAL (Pop-up) -->
                <div id="soruModal" class="hidden fixed inset-0 bg-black bg-opacity-75 z-50 flex items-center justify-center p-4">
                    <div class="bg-white rounded-lg max-w-2xl w-full p-8 shadow-2xl">
                        <h4 id="soruMetni" class="text-2xl font-bold mb-6 text-gray-800"></h4>
                        <div id="cevaplar" class="space-y-3"></div>
                    </div>
                </div>
                
            </main>

            <script>
               // --- Python'dan Gelen Veri (Bu satır Python tarafından doldurulacak) ---
               var sureclerListesi = [];
                
                let titleClickCount = 0; 

                document.addEventListener('DOMContentLoaded', () => {
                    // --- DOM Elementleri ---
                    const bilesenSelect = document.getElementById('bilesen-kodu');
                    const videoSelect = document.getElementById('video-listesi');
                    const izleBtn = document.getElementById('izle-btn');
                    const mainTitle = document.getElementById('main-title'); 
                    
                    // --- Kullanıcı Adı Yükleme ---
                    try {{
                        const userFullName = localStorage.getItem('loggedInUserName');
                        const userRole = localStorage.getItem('loggedInUserRole'); // Rolü al

                        if (userFullName) {{
                            document.getElementById('user-name-placeholder').textContent = userFullName;
                            document.getElementById('user-avatar-initial').textContent = userFullName[0] ? userFullName[0].toUpperCase() : 'K';
                        }}
                        
                        // --- YAN MENÜ ROL KONTROLÜ (NİHAİ DOĞRU VERSİYON) ---
                        const linkMetinAnaliz = document.getElementById('link-metin-analiz');
                        const linkSoruUretim = document.getElementById('link-soru-uretim');
                        const linkMetinOlusturma = document.getElementById('link-metin-olusturma');
                        const linkHaritadaBul = document.getElementById('link-haritada-bul');
                        const linkPodcast = document.getElementById('link-podcast');
                        const linkSeyretBul = document.getElementById('link-seyret-bul');
                        const linkYarisma = document.getElementById('link-yarisma');
                        const linkVideoIstegi = document.getElementById('link-video-istegi');

                        if (userRole === 'teacher') {{
                            // --- ÖĞRETMEN GÖRÜNÜMÜ ---
                            if (linkMetinAnaliz) linkMetinAnaliz.style.display = 'none';
                            if (linkSeyretBul) linkSeyretBul.style.display = 'none';
                            if (linkHaritadaBul) linkHaritadaBul.style.display = 'none'; 
                        }} else {{
                            // --- ÖĞRENCİ GÖRÜNÜMÜ ---
                            if (linkMetinOlusturma) linkMetinOlusturma.style.display = 'none';
                        }}
                        // --- ROL KONTROLÜ BİTTİ ---

                    }} catch (e) {{ console.error("Kullanıcı adı veya rol yüklenemedi:", e); }}

                    // --- 1. Süreç Bileşeni Menüsünü Doldur ---
                    try {
                        console.log("DEBUG JS: Süreç Listesi Alındı, Boyut:", sureclerListesi.length);
                        
                        if (bilesenSelect && sureclerListesi.length > 0) {
                            
                            // Öğrenci menüsü
                            sureclerListesi.forEach(surec => {
                                const kisaAciklama = surec.aciklama.substring(0, 70) + '...';
                                const optionText = `${surec.kod} - ${kisaAciklama}`;
                                
                                const optionOgrenci = document.createElement('option');
                                optionOgrenci.value = surec.kod;
                                optionOgrenci.textContent = optionText;
                                optionOgrenci.title = surec.aciklama;
                                bilesenSelect.appendChild(optionOgrenci);
                            });
                            
                        } else if (sureclerListesi.length === 0) {
                             console.warn("DEBUG JS: 'sureclerListesi' değişkeni boş!");
                        }
                    } catch (e) {
                        console.error("Süreç bileşeni menüsü doldurulurken hata:", e);
                    }
                                      
                    // --- 2. Süreç Bileşeni değiştiğinde Videoları API'den çek ---
                    if (bilesenSelect) {
                        bilesenSelect.addEventListener('change', async () => {
                            const selectedBilesenKodu = bilesenSelect.value;
                            videoSelect.innerHTML = '<option value="">Videolar yükleniyor...</option>';
                            videoSelect.disabled = true;
                            izleBtn.disabled = true;
                            
                            if (!selectedBilesenKodu) {
                                videoSelect.innerHTML = '<option value="">Önce Süreç Bileşeni Seçin...</option>';
                                return;
                            }
                            
                            try {
                                const response = await fetch(`/api/seyret-bul/videolar?kod=${selectedBilesenKodu}`);
                                const data = await response.json();
                            
                                if (data.success && data.videolar.length > 0) {
                                    videoSelect.innerHTML = '<option value="">Lütfen bir video seçin...</option>';
                                    data.videolar.forEach(video => {
                                        const option = document.createElement('option');
                                        option.value = video.video_id;
                                        option.textContent = video.baslik;
                                        videoSelect.appendChild(option);
                                    });
                                    videoSelect.disabled = false;
                                } else {
                                    videoSelect.innerHTML = '<option value="">Bu kazanım için video bulunamadı.</option>';
                                }
                            } catch (error) {
                                console.error("Video listesi çekilirken hata:", error);
                                videoSelect.innerHTML = '<option value="">Videolar yüklenemedi (Hata).</option>';
                            }
                        });
                    }
                    
                    // --- 3. Video Seçimi değiştiğinde İzle Butonunu Aktif Et ---
                    if (videoSelect) {
                        videoSelect.addEventListener('change', () => {
                            if (videoSelect.value) {
                                izleBtn.disabled = false;
                            } else {
                                izleBtn.disabled = true;
                            }
                        });
                    }
                        
                    // --- 4. İzle Butonu ---
                    if (izleBtn) {
                        izleBtn.addEventListener('click', () => {
                            const videoId = videoSelect.value;
                            if(videoId) {
                                openVideoModal(videoId);
                            }
                        });
                    }
                    
                    // --- 5. Gizli Admin Paneli Tıklaması (ARTIK ÇALIŞMIYOR) ---
                    // (Bu kodu silebiliriz bile, çünkü adminPanel elementi artık burada yok)
                    if (mainTitle) {
                        mainTitle.addEventListener('click', () => {
                            titleClickCount++;
                            if (titleClickCount >= 3) {
                                titleClickCount = 0;
                                // 'adminPanel' elementi artık burada olmadığı için
                                // bu kod hiçbir şey yapmayacak.
                                alert('Yönetim paneli artık ana giriş ekranında.');
                            }
                        });
                    }
                });
                
                // --- VIDEO MODAL FONKSİYONLARI ---
                    function openVideoModal(videoId) {
                        // Adım 1: Kullanıcı ID'sini ve video ID'sini al
                        const studentNo = localStorage.getItem('loggedInUserNo');
                        if (!studentNo) {
                            alert("Hata: Öğrenci girişi bulunamadı. Lütfen tekrar giriş yapın.");
                            return;
                        }

                        fetch(`/api/seyret-bul/video-detay/${videoId}`)
                            .then(r => r.json())
                            .then(data => {
                                if (!data.success) {
                                    alert("Video detayları yüklenemedi.");
                                    return;
                                }
                                
                                videoData = data.video;
                                const allQuestions = videoData.sorular || []; // Videonun tüm (9) sorusu
                                if (allQuestions.length === 0) {
                                    alert("Bu video için henüz soru eklenmemiş.");
                                    return;
                                }

                                // --- YENİ SEÇİM SİSTEMİ (1-1-1 KURALI) ---
                                
                                // Adım 2: "Görülmüş Sorular" veritabanını localStorage'dan yükle
                                let seenQuestionsDB = JSON.parse(localStorage.getItem('seyretBulSeenDB')) || {};
                                const dbKey = `${studentNo}_${videoId}`;
                                let seenQuestionsForThisVideo = seenQuestionsDB[dbKey] || [];

                                // Adım 3: Görülmemiş soruları tiplerine göre ayır
                                const unseenQuestions = allQuestions.filter(q => !seenQuestionsForThisVideo.includes(q.id));
                                let unseen_CS = unseenQuestions.filter(q => q.tip === 'CoktanSecmeli');
                                let unseen_BD = unseenQuestions.filter(q => q.tip === 'BoslukDoldurma');
                                let unseen_KC = unseenQuestions.filter(q => q.tip === 'KisaCevap');

                                // Adım 4: Havuz Kuralı (Kural 4 - Tekrar Görme)
                                // Eğer 1-1-1 setini oluşturmak için *herhangi* bir tipin havuzu boşsa,
                                // tüm havuzu sıfırla ve *tüm* sorulardan seç.
                                let pool_CS, pool_BD, pool_KC;
                                let poolSifirlandi = false;

                                if (unseen_CS.length === 0 || unseen_BD.length === 0 || unseen_KC.length === 0) {
                                    console.log("DEBUG JS: Havuz sıfırlanıyor (1-1-1 için yeterli tip yok).");
                                    poolSifirlandi = true;
                                    seenQuestionsForThisVideo = []; // Görülmüş listesini sıfırla
                                    
                                    // Havuzları tüm sorularla doldur
                                    pool_CS = allQuestions.filter(q => q.tip === 'CoktanSecmeli');
                                    pool_BD = allQuestions.filter(q => q.tip === 'BoslukDoldurma');
                                    pool_KC = allQuestions.filter(q => q.tip === 'KisaCevap');
                                } else {
                                    // Havuzları görülmemiş sorularla doldur
                                    pool_CS = unseen_CS;
                                    pool_BD = unseen_BD;
                                    pool_KC = unseen_KC;
                                }

                                // Adım 5: Her havuzdan rastgele 1 soru seç
                                // (Eğer bir tipte hiç soru yoksa hata vermemesi için kontrol ekle)
                                const q_CS = pool_CS.length > 0 ? pool_CS[Math.floor(Math.random() * pool_CS.length)] : null;
                                const q_BD = pool_BD.length > 0 ? pool_BD[Math.floor(Math.random() * pool_BD.length)] : null;
                                const q_KC = pool_KC.length > 0 ? pool_KC[Math.floor(Math.random() * pool_KC.length)] : null;
                                
                                // Seçilen 3 soruyu birleştir (null olanları filtrele)
                                const selectedQuestions = [q_CS, q_BD, q_KC].filter(q => q !== null);
                                
                                if (selectedQuestions.length < 3) {
                                    alert("Hata: Bu video 1-1-1 kuralı için yeterli soru tipine sahip değil. Lütfen videoyu (veya 'seyret_bul_videos.json' dosyasını) kontrol edin.");
                                    return;
                                }

                                // Adım 6: Seçilen soruları "görülmüş" olarak işaretle ve kaydet
                                const newSeenIDs = selectedQuestions.map(q => q.id);
                                
                                if (poolSifirlandi) {
                                    seenQuestionsForThisVideo = newSeenIDs; // Liste sıfırlandı, sadece yenileri ekle
                                } else {
                                    // Liste sıfırlanmadı, mevcut listeye yenileri ekle
                                    newSeenIDs.forEach(id => {
                                        if (!seenQuestionsForThisVideo.includes(id)) {
                                            seenQuestionsForThisVideo.push(id);
                                        }
                                    });
                                }
                                
                                seenQuestionsDB[dbKey] = seenQuestionsForThisVideo;
                                localStorage.setItem('seyretBulSeenDB', JSON.stringify(seenQuestionsDB));
                                
                                // --- YENİ SEÇİM SİSTEMİ BİTTİ ---

                                // Adım 7: Seçilen 3 soruyu global `sorular` değişkenine ata ve oyunu başlat
                                sorular = selectedQuestions; // Bu artık 1-1-1 seti
                                sorular.sort((a,b) => a.duraklatma_saniyesi - b.duraklatma_saniyesi); // Duraklatma saniyesine göre sırala
                                currentSoruIndex = 0;
                                
                                document.getElementById('videoContainer').classList.remove('hidden');
                                loadYouTubeAPI();
                            });
                    }
                    
                    function loadYouTubeAPI() {
                        if (!window.YT) {
                            const tag = document.createElement('script');
                            tag.src = "https://www.youtube.com/iframe_api";
                            document.head.appendChild(tag);
                            window.onYouTubeIframeAPIReady = createPlayer;
                        } else {
                            createPlayer();
                        }
                    }
                    
                    function createPlayer() {
                    const playerDiv = document.getElementById('player');
                    
                    // Video tipi kontrolü: YouTube mu, lokal mu?
                    if (videoData.url.includes('youtube.com') || videoData.url.includes('youtu.be')) {
                        // YouTube video
                        const ytId = videoData.url.match(/[?&]v=([^&]+)/)[1];
                        player = new YT.Player('player', {
                            height: '480',
                            width: '100%',
                            videoId: ytId,
                            events: { 'onStateChange': onPlayerStateChange }
                        });
                    } else {
                        // Lokal video - HTML5 player
                        playerDiv.innerHTML = `
                            <video id="html5-player" controls style="width: 100%; max-width: 100%;">
                                <source src="${videoData.url}" type="video/mp4">
                            </video>
                        `;
                        player = document.getElementById('html5-player');
                        player.addEventListener('play', () => {
                            if (currentSoruIndex < sorular.length) checkTime();
                        });
                    }
                    
                    // Timeline'ı göster ve marker'ları ekle
                    const timeline = document.getElementById('timeline');
                    const markers = document.getElementById('markers');
                    timeline.classList.remove('hidden');
                    markers.innerHTML = '';
                    
                    sorular.forEach(soru => {
                        const marker = document.createElement('div');
                        const pozisyon = (soru.duraklatma_saniyesi / videoData.sure_saniye) * 100;
                        marker.className = 'absolute w-3 h-3 bg-red-500 rounded-full border-2 border-white shadow'; 
                        marker.style.left = `${pozisyon}%`;
                        // Yeni 2px'lik çizgiye ortalamak için (12px daire - 2px çizgi) / 2 = 5px yukarı kaydır
                        marker.style.top = '-5px'; 
                        marker.style.transform = 'translateX(-50%)';
                        marker.title = `Soru: ${soru.duraklatma_saniyesi}s`;
                        markers.appendChild(marker);
                        });
                    }

                    function onPlayerStateChange(event) {
                        if(event.data == YT.PlayerState.PLAYING && currentSoruIndex < sorular.length) {
                            checkTime();
                        }
                    }
                    
                    function checkTime() {
                        const interval = setInterval(() => {
                            if(currentSoruIndex >= sorular.length || !player) {
                                clearInterval(interval);
                                return;
                            }
                            // YouTube veya HTML5 için farklı API
                            const currentTime = player.getCurrentTime ? player.getCurrentTime() : player.currentTime;
                            const soruZamani = sorular[currentSoruIndex].duraklatma_saniyesi;
                            
                            // --- GÜNCELLEME (Gecikmeyi düzelt) ---
                            // 0.3 saniye önce durdur komutu gönder
                            const buffer = 0.3; 
                            
                            if(currentTime >= (soruZamani - buffer)) { // <--- DÜZELTME BURADA
                                
                                // --- DÜZELTME: YouTube veya HTML5 için farklı duraklatma komutu ---
                                if (player.pauseVideo) {
                                    player.pauseVideo(); // YouTube API
                                } else {
                                    player.pause(); // HTML5 Video
                                }
                                // --- DÜZELTME BİTTİ ---

                                showSoru(sorular[currentSoruIndex]);
                                clearInterval(interval);
                            }
                        }, 100); // <-- 100 olduğundan emin olun
                    }
                    
                    function showSoru(soru) {
                    if (!soru.tip && soru.cevaplar && Array.isArray(soru.cevaplar)) {
                        soru.tip = 'CoktanSecmeli'; 
                        console.log('DEBUG JS: Eksik "tip" alanı algılandı, CoktanSecmeli olarak ayarlandı.');
                    }
                    document.getElementById('soruMetni').textContent = soru.soru;
                    const cevaplarDiv = document.getElementById('cevaplar');
                    cevaplarDiv.innerHTML = ''; // Modalın içini temizle

                    // Soru tipine göre modal içeriğini oluştur
                    if (soru.tip === 'CoktanSecmeli') {
                        // --- Tip 1: Çoktan Seçmeli ---
                        const harfler = ['A', 'B', 'C', 'D'];
                        soru.cevaplar.forEach((cevap, i) => {
                            const btn = document.createElement('button');
                            btn.className = 'w-full p-3 bg-indigo-500 text-white rounded-lg hover:bg-indigo-600 transition-all';
                            btn.textContent = `${harfler[i]}) ${cevap}`;
                            // checkCevap fonksiyonuna tüm 'soru' objesini ve 'A' gibi seçimi gönder
                            btn.onclick = () => checkCevap(soru, harfler[i]);
                            cevaplarDiv.appendChild(btn);
                        });

                    } 
                    else if (soru.tip === 'BoslukDoldurma') {
                        // --- Tip 2: Boşluk Doldurma ---
                        
                        // Input alanı
                        const input = document.createElement('input');
                        input.id = 'cevap-input';
                        input.type = 'text';
                        input.className = 'w-full px-4 py-2 border border-gray-300 rounded-lg mb-3';
                        input.placeholder = 'Cevabınızı buraya yazın...';
                        cevaplarDiv.appendChild(input);

                        // Cevapla butonu
                        const btn = document.createElement('button');
                        btn.className = 'w-full p-3 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-all';
                        btn.textContent = 'Cevapla';
                        btn.onclick = () => {
                            const kullaniciCevabi = document.getElementById('cevap-input').value;
                            checkCevap(soru, kullaniciCevabi);
                        };
                        cevaplarDiv.appendChild(btn);

                    } 
                    else if (soru.tip === 'KisaCevap') {
                        // --- Tip 3: Kısa Cevap (Doğru <textarea> elementi ile) ---
                        
                        // Textarea alanı (cümle yazmak için DOĞRU ELEMENT)
                        const textarea = document.createElement('textarea');
                        textarea.id = 'cevap-textarea'; // DOĞRU ID
                        textarea.className = 'w-full p-3 border-2 border-gray-300 rounded-lg mb-3';
                        textarea.placeholder = '3-4 kelimelik cevabınızı yazın...';
                        textarea.rows = 3; // 3 satır yüksekliğinde
                        cevaplarDiv.appendChild(textarea);

                        // Cevapla butonu
                        const btn = document.createElement('button');
                        btn.className = 'w-full p-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-all';
                        btn.textContent = 'Cevabı Gönder';
                        btn.onclick = () => {
                            // Doğru ID'den oku
                            const kullaniciCevabi = document.getElementById('cevap-textarea').value; 
                            checkCevap(soru, kullaniciCevabi);
                        };
                        cevaplarDiv.appendChild(btn);
                    }

                    document.getElementById('soruModal').classList.remove('hidden');
                }
                    
                    function checkCevap(soru, kullaniciCevabi) {
                    let dogruMu = false;
                    let dogruCevapMetni = '';

                    // Modalı kilitle ve "Değerlendiriliyor" yazısını göster
                    const cevaplarDiv = document.getElementById('cevaplar');
                    cevaplarDiv.innerHTML = '<p class="text-center font-semibold text-blue-600">Cevabınız değerlendiriliyor... Lütfen bekleyin.</p>';

                    // --- GÖRSEL GERİ BİLDİRİM İÇİN YARDIMCI FONKSİYON ---
                    // Bu fonksiyon, alert() yerine sonucu modal'ın içine yazar.
                    const showVisualFeedback = (baslikHtml, aciklamaHtml) => {
                        const cevaplarDiv = document.getElementById('cevaplar');
                        cevaplarDiv.innerHTML = ''; // "Değerlendiriliyor..." yazısını sil

                        // "Devam Et" butonu oluştur
                        const devamBtn = document.createElement('button');
                        devamBtn.className = 'w-full p-3 bg-indigo-500 text-white rounded-lg hover:bg-indigo-600 transition-all mt-6';
                        devamBtn.textContent = 'Videoya Devam Et';
                        devamBtn.onclick = videoyaDevamEt; // Tıklayınca videoya devam et

                        // Modal'ın içini doldur
                        cevaplarDiv.innerHTML = baslikHtml + aciklamaHtml;
                        cevaplarDiv.appendChild(devamBtn);
                    };
                    // ---------------------------------------------------

                    if (soru.tip === 'CoktanSecmeli') {
                        dogruCevapMetni = soru.dogru_cevap;
                        if (kullaniciCevabi === dogruCevapMetni) {
                            dogruMu = true;
                        }
                        
                        let baslikHtml, aciklamaHtml;
                        if (dogruMu) {
                            baslikHtml = '<h3 class="text-2xl font-bold text-green-600 mb-4">DOĞRU!</h3>';
                            aciklamaHtml = '<p class="text-gray-700 italic bg-gray-50 p-3 rounded-lg">Tebrikler, doğru şıkkı seçtiniz.</p>';
                        } else {
                            baslikHtml = '<h3 class="text-2xl font-bold text-red-600 mb-4">YANLIŞ</h3>';
                            aciklamaHtml = `<p class="text-gray-700 text-lg"><b>Doğru Cevap:</b> ${dogruCevapMetni}</p>`;
                        }
                        // Not: Hızlı çalıştığı için "Değerlendiriliyor" yazısı görünmeyebilir, 
                        // bu yüzden sonucu 100 milisaniye sonra göstermek daha akıcı olur.
                        setTimeout(() => showVisualFeedback(baslikHtml, aciklamaHtml), 100);

                    } 
                    else if (soru.tip === 'BoslukDoldurma') {
                        dogruCevapMetni = soru.dogru_cevap;
                        // Büyük/küçük harf duyarsız ve boşlukları temizleyerek kontrol et
                        if (kullaniciCevabi.trim().toLowerCase() === dogruCevapMetni.trim().toLowerCase()) {
                            dogruMu = true;
                        }

                        let baslikHtml, aciklamaHtml;
                        if (dogruMu) {
                            baslikHtml = '<h3 class="text-2xl font-bold text-green-600 mb-4">DOĞRU!</h3>';
                            aciklamaHtml = `<p class="text-gray-700 italic bg-gray-50 p-3 rounded-lg">Tebrikler, cevabınız: ${dogruCevapMetni}</p>`;
                        } else {
                            baslikHtml = '<h3 class="text-2xl font-bold text-red-600 mb-4">YANLIŞ</h3>';
                            aciklamaHtml = `<p class="text-gray-700 text-lg"><b>Doğru Cevap:</b> ${dogruCevapMetni}</p>
                                            <p class="text-gray-500 mt-2">Sizin cevabınız: ${kullaniciCevabi}</p>`;
                        }
                        setTimeout(() => showVisualFeedback(baslikHtml, aciklamaHtml), 100);
                    } 
                    
                    else if (soru.tip === 'KisaCevap') {
                        // Gemini API'yi çağır
                        fetch('/api/seyret-bul/degerlendir', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                soru_metni: soru.soru,
                                kullanici_cevabi: kullaniciCevabi
                            })
                        })
                        .then(response => response.json())
                        .then(data => {
                            let baslikHtml = '';
                            let aciklamaHtml = '';

                            if (data.success && data.skor !== undefined) {
                                const baslikRenk = (data.skor == 5) ? 'text-green-600' : 'text-blue-600';
                                baslikHtml = `<h3 class="text-2xl font-bold ${baslikRenk} mb-4">PUANINIZ: ${data.skor} / 5</h3>`;
                                aciklamaHtml = `<p class="text-gray-700 text-lg"><b>Gemini Değerlendirmesi:</b></p>
                                                <p class="text-gray-700 italic bg-gray-50 p-3 rounded-lg">${data.geri_bildirim}</p>`;
                            } else {
                                baslikHtml = '<h3 class="text-2xl font-bold text-red-600 mb-4">Değerlendirme Hatası</h3>';
                                aciklamaHtml = `<p class="text-gray-700">${data.hata || 'Bilinmeyen format'}</p>`;
                            }
                            showVisualFeedback(baslikHtml, aciklamaHtml); // Yardımcı fonksiyonu çağır
                        })
                        .catch(err => {
                            const baslikHtml = '<h3 class="text-2xl font-bold text-red-600 mb-4">Sunucu Hatası</h3>';
                            const aciklamaHtml = `<p class="text-gray-700">${err.message}</p>`;
                            showVisualFeedback(baslikHtml, aciklamaHtml); // Yardımcı fonksiyonu çağır
                        });
                    }
                }

                // --- YARDIMCI FONKSİYONLAR (Yeni Eklendi) ---

                function videoyaDevamEt() {
                    // --- Modal'ı kapat ve videoya devam et ---
                    document.getElementById('soruModal').classList.add('hidden');
                    currentSoruIndex++;
                    
                    // YouTube veya HTML5 için farklı play
                    if (player.playVideo) {
                        player.playVideo();  // YouTube
                    } else {
                        player.play();  // HTML5
                    }
                    
                    if (currentSoruIndex < sorular.length) {
                        checkTime();
                    }
                }
                    
                    document.getElementById('closeVideo').addEventListener('click', () => {
                    document.getElementById('videoContainer').classList.add('hidden');
                    if(player) player.destroy();
                    document.getElementById('player').innerHTML = '';
                });
            </script>
        </body>
        </html>
        """
        
        # --- 4. JSON Verisini HTML'e Enjekte Etme ---
        try:
            surecler_json = json.dumps(surecler_listesi)
        except Exception as json_err:
            print(f"JSON Dumps Hatası: {json_err}")
            surecler_json = "[]" # Hata olursa boş liste gönder
            
        # JavaScript'teki 'var sureclerListesi = [];' satırını dolduruyoruz
        html_content = html_content.replace('var sureclerListesi = [];', f'var sureclerListesi = {surecler_json};')

        # 5. Tamamlanmış HTML'i döndür
        return html_content
        
    except Exception as e:
        print(f"Seyret Bul liste hatası: {e}")
        return f"Bir hata oluştu: {str(e)}"
    
# ########## YENİ EKLENDİ: SEYRET BUL API ROTALARI ##########
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
    """Podcast Panel - Soru Üretim HTML Yapısıyla Birebir Aynı."""

    html_content = f"""
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Podcast Oluşturucu</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
        <style>
            body {{ 
                font-family: 'Inter', sans-serif;
                background-color: #f3f4f6;
            }}
            /* Soru Üretim sayfasındaki aynı no-bounce sınıfı */
            .no-bounce {{ overscroll-behavior: none; }}
            
            /* Scrollbar Gizleme (Ekstra) */
            .no-scrollbar::-webkit-scrollbar {{ display: none; }}
            .no-scrollbar {{ -ms-overflow-style: none; scrollbar-width: none; }}
        </style>
    </head>
    <body class="flex h-screen">

        <aside class="w-72 bg-white text-gray-800 shadow-lg flex flex-col fixed h-full z-50">
            <div class="px-6 py-4 border-b border-gray-200">
                <h1 class="text-2xl font-extrabold text-blue-600 text-center tracking-wide mb-4">
                    Maarif SosyalLab
                </h1>
                <div class="mb-4">
                    <div class="w-full p-2 flex items-center justify-center overflow-hidden">
                        <img src="/videolar/maarif.png" alt="Maarif Logo" class="w-auto h-auto max-w-full max-h-24 object-contain rounded-lg">
                    </div>
                </div>
                <div class="flex items-center">
                    <div id="user-avatar-initial" class="w-10 h-10 rounded-full bg-cyan-500 flex items-center justify-center text-white font-bold text-lg">K</div>
                    <div class="ml-3">
                        <span id="user-name-placeholder" class="block text-sm font-bold text-gray-800">Kullanıcı</span>
                    </div>
                </div>
            </div>
            <nav class="flex-1 overflow-y-auto p-2 space-y-1 no-bounce">

            <a id="link-soru-uretim" href="/soru-uretim"
                class="flex items-center mx-2 p-2 rounded-lg text-white font-semibold bg-green-500 hover:bg-green-600 transition-all">
                <i class="fa-solid fa-circle-question mr-3 w-6 text-center"></i>
                <span>Soru Üretim</span>
            </a>
            <a id="link-metin-olusturma" href="/metin-olusturma"
                class="flex items-center mx-2 p-2 rounded-lg text-white font-semibold bg-purple-500 hover:bg-purple-600 transition-all">
                <i class="fa-solid fa-wand-magic-sparkles mr-3 w-6 text-center"></i>
                <span>Metin Oluşturma</span>
            </a>
            <a id="link-podcast" href="/podcast_paneli"
                class="flex items-center mx-2 p-2 rounded-lg text-white font-semibold bg-red-500 hover:bg-red-600 transition-all">
                <i class="fa-solid fa-microphone-lines mr-3 w-6 text-center"></i>
                <span>Podcast Yap</span>
            </a>
            <a id="link-yarisma" href="/yarisma-secim"
                class="flex items-center mx-2 p-2 rounded-lg text-white font-semibold bg-teal-500 hover:bg-teal-600 transition-all">
                <i class="fa-solid fa-trophy mr-3 w-6 text-center"></i>
                <span>Beceri/Değer Avcısı</span>
            </a>
            <a id="link-video-istegi" href="/video-istegi"
                class="flex items-center mx-2 p-2 rounded-lg text-white font-semibold bg-pink-500 hover:bg-pink-600 transition-all">
                <i class="fa-solid fa-video mr-3 w-6 text-center"></i>
                <span>Video İsteği</span>
            </a>
            
        </nav>
            <div class="p-4 border-t border-gray-200">
                <a href="/dashboard" class="flex items-center mx-2 p-2 rounded-lg text-gray-600 font-semibold bg-gray-100 hover:bg-gray-200 transition-all">
                    <i class="fa-solid fa-arrow-left mr-3 w-6 text-center"></i><span>Panele Geri Dön</span>
                </a>
            </div>
        </aside>

        <main class="ml-72 flex-1 p-6 md:p-8 overflow-y-auto no-bounce">
            
            <header class="md:hidden flex items-center justify-between mb-6">
                <h1 class="text-xl font-bold text-blue-600">SosyalLab Podcast</h1>
                <a href="/dashboard" class="text-gray-500"><i class="fa-solid fa-arrow-right-from-bracket"></i></a>
            </header>

            <h2 class="text-3xl font-bold text-gray-800 mb-6">Podcast Oluşturucu</h2>
            
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div class="bg-white p-6 rounded-lg shadow">
                    <p class="text-gray-600 mb-4">Lütfen "sohbet podcasti" yapılacak metni (En fazla 600 kelime) aşağıya yapıştırın.</p>

                    <form id="podcast-form">
                        <textarea id="text-input" 
                                  name="text_content"
                                  class="w-full h-48 p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:outline-none resize-none text-gray-700"
                                  placeholder="Metninizi buraya yapıştırın..."></textarea>

                        <div id="word-count" class="text-right text-sm text-gray-500 mt-1">0 / 600 kelime</div>

                        <button id="generate-btn" type="submit" class="w-full mt-4 bg-red-500 text-white font-bold py-3 px-6 rounded-lg text-lg shadow-lg hover:bg-red-600 transition-all duration-300 flex items-center justify-center">
                            <i class="fa-solid fa-microphone mr-2"></i> Sohbet Podcasti Oluştur
                        </button>
                    </form>

                    <div id="podcast-status" class="mt-4 font-semibold text-gray-700 text-center"></div>
                </div>

                <div class="bg-white p-6 rounded-lg shadow flex flex-col justify-center items-center text-center min-h-[300px]">
                    <h3 class="text-xl font-semibold text-gray-800 mb-4 w-full text-left">Podcast Oynatıcı</h3>
                    
                    <div id="podcast-player-container" class="mt-4 p-4 w-full" style="display: none;">
                        <p class="text-sm text-gray-500 mb-3">Ses dosyası hazır!</p>
                        <audio id="audio-player" controls class="w-full"></audio>
                    </div>

                    <div id="player-placeholder" class="p-4">
                        <div class="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4 text-gray-400">
                             <i class="fa-solid fa-microphone-lines text-3xl"></i>
                        </div>
                        <p class="text-gray-400">Podcast oluşturulduktan sonra<br>burada dinleyebilirsiniz.</p>
                    </div>
                </div>
            </div>
        </main>
      
        <script>
            (function() {{
                // --- Kullanıcı Adı Yükleme (Soru Üretim'deki kodun aynısı) ---
                try {{
                    const userFullName = localStorage.getItem('loggedInUserName');
                    const userRole = localStorage.getItem('loggedInUserRole');

                    if (userFullName) {{
                        document.getElementById('user-name-placeholder').textContent = userFullName;
                        document.getElementById('user-avatar-initial').textContent = userFullName[0] ? userFullName[0].toUpperCase() : 'K';
                    }}
                }} catch (e) {{ console.error("Kullanıcı bilgisi hatası:", e); }}

                // --- Podcast Mantığı ---
                const form = document.getElementById('podcast-form');
                const textArea = document.getElementById('text-input');
                const wordCountDisplay = document.getElementById('word-count');
                const button = document.getElementById('generate-btn');
                const status = document.getElementById('podcast-status');
                const playerContainer = document.getElementById('podcast-player-container');
                const placeholder = document.getElementById('player-placeholder');
                let audioPlayer = document.getElementById('audio-player');
                
                const wordLimit = 600;

                textArea.addEventListener('input', function() {{
                    const text = textArea.value;
                    const words = text.split(/\\s+/).filter(Boolean);
                    const wordCount = words.length;
                    wordCountDisplay.textContent = `${{wordCount}} / ${{wordLimit}} kelime`;

                    if (wordCount > wordLimit || wordCount === 0) {{
                        wordCountDisplay.classList.add('text-red-500', 'font-bold');
                        button.disabled = true;
                        button.classList.add('opacity-50', 'cursor-not-allowed');
                    }} else {{
                        wordCountDisplay.classList.remove('text-red-500', 'font-bold');
                        button.disabled = false;
                        button.classList.remove('opacity-50', 'cursor-not-allowed');
                    }}
                }}); 

                form.addEventListener('submit', async function(event) {{
                    event.preventDefault();
                    const userText = textArea.value.trim();
                    if (!userText) return;

                    button.disabled = true;
                    button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Hazırlanıyor...';
                    status.textContent = "Lütfen bekleyin...";
                    
                    try {{
                        const response = await fetch('/generate-podcast', {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify({{ text: userText, student_no: localStorage.getItem('user_no') }}), 
                        }});

                        const data = await response.json();

                        if (response.ok && data.success) {{
                            placeholder.style.display = 'none';
                            playerContainer.style.display = 'block';
                            audioPlayer.src = data.audio_url + '?' + new Date().getTime();
                            audioPlayer.play();
                            status.innerHTML = '<span class="text-green-600"><i class="fa-solid fa-check-circle"></i> Başarıyla oluşturuldu!</span>';
                        }} else {{
                            status.innerHTML = '<span class="text-red-600">Hata: ' + (data.error || "Bilinmeyen hata") + '</span>';
                        }}
                    }} catch (error) {{
                        status.innerHTML = '<span class="text-red-600">Bağlantı Hatası</span>';
                    }} finally {{
                        button.disabled = false;
                        button.innerHTML = '<i class="fa-solid fa-microphone mr-2"></i> Sohbet Podcasti Oluştur';
                    }}
                }});

            }})();
        </script>
    </body>
    </html>
    """
    # F-String kullandığımız için veri zaten içeriye gömüldü.
    # Ekstra işlem yapmaya gerek yok, sadece döndür.
    return render_template_string(html_content)

@app.route('/generate-podcast', methods=['POST'])
def handle_generation():
    data = request.get_json()
    user_text = data.get('text')
    
    if not user_text:
        return jsonify({"success": False, "error": "Metin boş olamaz."}), 400

    try:
        # --- 1. Metin Uygunluğunu Kontrol Et ---
        print("🔵 1. Metnin müfredata uygunluğu kontrol ediliyor...")
        global gemini_model # Modeli globalden al
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
        
        # Kullanım kaydı
        student_no = data.get("student_no")
        if student_no:
            db_helper.kaydet_kullanim(student_no, "podcast", "Podcast oluşturuldu")
        print(f"🔍 DEBUG: student_no = {student_no}")

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
    """Öğretmenden gelen video isteğini 'video_istekleri.json' dosyasına kaydeder."""
    try:
        data = request.get_json()
        
        # --- GÜNCELLENDİ: Tüm veriyi al ---
        istek_metni = data.get('istek_metni')
        isteyen_kullanici = data.get('isteyen_ogretmen', 'Bilinmiyor') # Bu 'isim' alanı
        kullanici_rol = data.get('kullanici_rol', 'Bilinmiyor')
        kullanici_no = data.get('kullanici_no')
        kullanici_okul = data.get('kullanici_okul')
        kullanici_sinif = data.get('kullanici_sinif')
        # --- BİTTİ ---
        
        if not istek_metni:
            return jsonify({"success": False, "hata": "İstek metni boş olamaz."})
        
        # Yeni isteği oluştur (Genişletilmiş)
        yeni_istek = {
            "id": f"istek_{int(pd.Timestamp.now().timestamp())}",
            "tarih": pd.Timestamp.now().isoformat(),
            "ogretmen": isteyen_kullanici, # Bu alanı 'isim' olarak tutuyoruz
            "metin": istek_metni,
            "durum": "Yeni",
            # --- YENİ ALANLAR ---
            "rol": kullanici_rol,
            "okul": kullanici_okul,
            "sinif": kullanici_sinif,
            "no": kullanici_no
            # --- BİTTİ ---
        }
        
        # Veritabanına ekle ve kaydet
        video_istekleri.insert(0, yeni_istek) # En yeni isteği en üste ekle
        save_video_istekleri(video_istekleri)
        
        return jsonify({"success": True, "mesaj": "İstek kaydedildi."})
        
    except Exception as e:
        print(f"Video isteği API hatası: {e}")
        return jsonify({"success": False, "hata": str(e)})

# --- VİDEO İSTEK ROTALARI BİTTİ ---
# --- YENİ EKLENDİ: VİDEO İSTEKLERİNİ ÇEKME ROTASI ---
@app.route('/api/get-video-istekleri', methods=['GET'])
def api_get_video_istekleri():
    """Tüm video isteklerini (video_istekleri global değişkeninden) JSON olarak döndürür."""
    global video_istekleri
    try:
        # 'video_istekleri' listesi zaten dosyanın başında yükleniyor.
        return jsonify({"success": True, "istekler": video_istekleri})
    except Exception as e:
        print(f"Video istekleri çekme API hatası: {e}")
        return jsonify({"success": False, "hata": str(e)})
# --- BİTTİ ---

# --- YENİ EKLENDİ: VİDEO İSTEĞİ SİLME ROTASI (3. İsteğiniz) ---
@app.route('/api/delete-video-istek', methods=['POST'])
def api_delete_video_istek():
    """Bir video isteğini ID'sine göre bulur ve 'video_istekleri.json' dosyasından siler."""
    global video_istekleri
    try:
        data = request.get_json()
        istek_id = data.get('istek_id')
        
        if not istek_id:
            return jsonify({"success": False, "hata": "İstek ID'si eksik."})

        # İsteği ID'ye göre bul
        istek_to_delete = next((istek for istek in video_istekleri if istek.get('id') == istek_id), None)
        
        if istek_to_delete:
            video_istekleri.remove(istek_to_delete) # Listeden kaldır
            save_video_istekleri(video_istekleri)   # Değişikliği dosyaya kaydet
            return jsonify({"success": True, "mesaj": "İstek silindi."})
        else:
            return jsonify({"success": False, "hata": "Silinecek istek bulunamadı."})
            
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

@app.route("/api/okul_sinif_listesi")
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
if __name__ == '__main__':
    print("UYGULAMA SUNUCUSU http://127.0.0.1:5002 adresinde çalışıyor...")
    print("Giriş yapmak için: http://127.0.0.1:5002")
    print("Dashboard'a doğrudan erişim: http://127.0.0.1:5002/dashboard")
    app.run(debug=False, host='127.0.0.1', port=5002)

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

if __name__ == '__main__':
    print("UYGULAMA SUNUCUSU http://127.0.0.1:5002 adresinde çalışıyor...")
    print("Giriş yapmak için: http://127.0.0.1:5002")
    print("Dashboard'a doğrudan erişim: http://127.0.0.1:5002/dashboard")
    app.run(debug=False, host='127.0.0.1', port=5002)
