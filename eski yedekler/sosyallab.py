# Import'lar
from flask import Flask, render_template_string, request, jsonify, send_from_directory, flash, redirect, url_for
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
import harita_bul
import seyret_bul
import metin_analiz
import soru_uretim

# ÖNCE API anahtarını tanımla
GEMINI_API_KEY = ""  # <-- Gerçek anahtarınız

# SONRA Flask app'i oluştur
app = Flask(__name__)

# EN SON config'e kaydet
app.config['GEMINI_API_KEY'] = GEMINI_API_KEY
app.config['SECRET_KEY'] = 'bu-cok-gizli-bir-anahtar-olmalı-321'

# --- Haritada Bul Modülünü Kaydet ---
GOOGLE_MAPS_API_KEY = "BURAYA_KENDİ_GOOGLE_MAPS_API_ANAHTARINIZI_GİRİN"
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

def load_users():
    """ Sunucu başladığında JSON dosyasından kullanıcıları yükler. """
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_users(data):
    """ Kullanıcı veritabanını JSON dosyasına kaydeder. """
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"Veritabanı '{DB_FILE}' dosyasına başarıyla kaydedildi.")
    except Exception as e:
        print(f"Veritabanı kaydetme hatası: {e}")
        
# --- Soru Üretim Limiti ---
SORU_URETIM_LIMIT_FILE = 'soru_uretim_limits.json'
HAFTALIK_LIMIT = 4

def load_soru_limits():
    if os.path.exists(SORU_URETIM_LIMIT_FILE):
        try:
            with open(SORU_URETIM_LIMIT_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_soru_limits(data):
    try:
        with open(SORU_URETIM_LIMIT_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Soru limiti kaydetme hatası: {e}")
        
# --- Video İstekleri Veritabanı ---
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
    save_soru_limits(limits)
    return {"success": True}
# --- Soru Üretim Limiti Bitişi ---

# Öğrenci veritabanını (users.json) yükle
users = load_users()

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
        save_users(users)
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
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Maarif SosyalLab</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Inter', sans-serif;
            /* Diğer sayfalarla uyumlu açık gri arka plan */
            background-color: #ffffff;
        }
        /* YENİ VİDEO STİLİ (Sığdır ve Alta Hizala) */
        #bg-video {
            position: fixed; 
            bottom: 0;
            left: 50%; /* ORTALAMA BAŞLANGICI: Ekranın tam ortasından başla */
            width: 75%; 
            height: 75%; 
            
            /* ORTALAMA SONU: Başlangıç noktasından sola doğru kendi genişliğinin yarısı kadar kaydır */
            transform: translateX(-50%); 
            
            object-fit: contain;
            object-position: center bottom; 
            z-index: -10; 
        }
        
        .hidden-screen { display: none; }

        /* 6. İSTEK: Kartlar dikey dikdörtgen */
        .card {
            position: relative;
            border-radius: 0.5rem;
            overflow: hidden;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            transition: all 0.3s ease-in-out;
            background-size: cover;
            background-position: center;
            min-height: 400px; /* Dikey olması için yüksekliği artır */
            cursor: pointer;
        }
        .card:hover {
            transform: scale(1.03);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        }
        .card-overlay {
            position: absolute;
            inset: 0;
            background-color: rgba(0, 0, 0, 0.5); 
            transition: background-color 0.3s ease;
        }
        .card:hover .card-overlay {
            background-color: rgba(0, 0, 0, 0.3); 
        }
        .card-content {
            position: relative; 
            z-index: 10;
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: flex-end; 
            padding: 1.5rem;
            color: white;
        }
        .card-title {
            font-size: 1.75rem; 
            font-weight: 800; 
            text-shadow: 0 2px 4px rgba(0, 0, 0, 0.5);
        }
        
        /* Buton Stilleri (Modernleştirildi) */
        .nav-button {
            padding: 0.5rem 1rem;
            border-radius: 0.375rem;
            font-weight: 600;
            transition: all 0.2s ease-in-out;
            border: 2px solid transparent;
            /* Hafif gölge eklendi */
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
        }
        
        /* ÖĞRENCİ BUTONU (Yeni Renk: #E2FA2A) */
        .nav-button-student { 
            background-color: #E2FA2A; 
            /* ÇOK ÖNEMLİ: Açık renk olduğu için yazı rengi koyu gri yapıldı */
            color: #374151; 
        }
        .nav-button-student:hover {
            background-color: #cddf24; /* Bir ton koyusu */
            transform: translateY(-2px);
            /* Vurguyu artırmak için daha büyük gölge */
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }
        
        /* ÖĞRETMEN BUTONU (Yeni Renk: #F56AA8) */
        .nav-button-teacher { 
            background-color: #F56AA8; 
            color: white;
        }
        .nav-button-teacher:hover {
            background-color: #d95890; /* Bir ton koyusu */
            transform: translateY(-2px);
            /* Vurguyu artırmak için daha büyük gölge */
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }
        
        /* Modal Stilleri (CSS HATASI DÜZELTİLDİ) */
        .modal-screen {
            display: none; /* JS ile açılacak */
            position: fixed;
            inset: 0;
            z-index: 50;
            /* 'display: flex;' satırı buradan SİLİNDİ (KRİTİK HATA DÜZELTMESİ) */
            align-items: center;
            justify-content: center;
            background-color: rgba(13, 32, 63, 0.6); 
            backdrop-filter: blur(5px);
            padding: 1rem;
        }
        .modal-box {
            background-color: white;
            color: #1f2937; 
            border-radius: 1rem;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
            width: 100%;
            max-width: 640px; 
            position: relative;
            overflow: hidden;
            display: flex;
        }
        .modal-close-btn {
            position: absolute;
            top: 0.75rem;
            right: 0.75rem;
            color: #9ca3af; 
            cursor: pointer;
            z-index: 20;
        }
        .modal-close-btn:hover { color: #374151; }
        
        .modal-left-panel {
            width: 40%;
            background-color: #0d203f; /* Koyu mavi (giriş pop-up'ı için) */
            color: white;
            padding: 2rem;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }
        .modal-right-panel {
            width: 60%;
            padding: 2rem;
        }
        
        /* Form elemanları */
        .form-label { display: block; margin-bottom: 0.25rem; font-size: 0.875rem; font-weight: 500; color: #4b5563; }
        .form-input { 
            width: 100%; 
            padding: 0.5rem 0.75rem; 
            border: 1px solid #d1d5db;
            border-radius: 0.375rem; 
            color: #1f2937;
        }
        .form-input:focus {
            outline: 2px solid transparent;
            outline-offset: 2px;
            border-color: #007bff;
            box-shadow: 0 0 0 2px #007bff;
        }
        .form-button {
            width: 100%;
            padding: 0.75rem;
            border-radius: 0.375rem;
            font-weight: 600;
            color: white;
            transition: background-color 0.2s;
        }
        .form-button:disabled { opacity: 0.5; cursor: not-allowed; }
        .form-link { 
            margin-top: 1rem; 
            font-size: 0.875rem; 
            color: #4b5563; 
            text-align: center;
        }
        .form-link a { color: #007bff; cursor: pointer; }
        .form-link a:hover { text-decoration: underline; }
        /* Video Düzenle Modalı için (Adım 1'de eklenen) stiller */
        /* Zaten .modal-screen, .modal-box, .form-input vb. tanımlı olduğu için */
        /* Sadece eksik olan .modal-left-panel ve .modal-right-panel stillerini ekl_İ_yoruz */
        /* Not: Bu, Adım 1'deki inline stilleri (style="...") tamamlar/genelleştirir */
        
        #edit-video-modal .modal-left-panel {
            width: 100%;
            background-color: #0d203f; /* Koyu mavi */
            color: white;
            padding: 1.5rem;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }
        #edit-video-modal .modal-right-panel {
            width: 100%;
            padding: 1.5rem;
        }
        /* --- YÖNETİCİ PANELİ SEKMELERİ İÇİN EKSİK CSS --- */
        .admin-tab {
            padding: 0.5rem 1rem;
            font-weight: 600;
            color: #4b5563; /* text-gray-600 */
            border-bottom: 3px solid transparent;
            cursor: pointer;
        }
        .admin-tab:hover {
            color: #0e7490; /* text-cyan-700 */
        }
        .admin-tab.active {
            color: #0891b2; /* text-cyan-600 */
            border-bottom-color: #0891b2;
        }
        .admin-tab-content {
            display: none; /* Varsayılan olarak tüm içerikleri GİZLE */
        }
        .admin-tab-content.active {
            display: block; /* Sadece 'active' class'ı olanı GÖSTER */
        }
        
        }
    </style>
</head>
        <body class="min-h-screen text-gray-800">
        <video id="bg-video" autoplay muted>
        <source src="/videolar/maarif.mp4" type="video/mp4">
        Tarayıcınız video etiketini desteklemiyor.
        </video>
                
    <!-- 2. İSTEK: Üst Bar Turkuaz/Mavi, 4. İSTEK: Sadece 2 Buton -->
    <div class="container mx-auto pt-20"> 
        <div class="flex justify-center items-center">
            
            <div class="flex items-center mx-auto w-fit p-4 rounded-xl shadow-lg" style="background-color: #34ACD9;">
                
                <h1 class="text-3xl font-extrabold text-white mr-64" style="font-family: 'Inter', sans-serif;">
                    Maarif SosyalLab'la Her Yerde Eğitim
                </h1>
                
                <nav class="flex space-x-3"> 
                    <button id="show-student-login" class="nav-button nav-button-student">
                        <i class="fa-solid fa-user mr-1"></i>
                        Öğrenci Girişi
                    </button>
                    <button id="show-teacher-login" class="nav-button nav-button-teacher">
                        <i class="fa-solid fa-user-tie mr-1"></i>
                        Öğretmen Girişi
                    </button>
                </nav>
            </div>
            
        </div>
    </div>

    <div id="welcome-screen" class="container mx-auto p-0 h-0"></div>

    <!-- ANA EKRAN (WELCOME-SCREEN) -->
   
            
    <!-- === GİZLİ POP-UP MODALLAR BÖLÜMÜ === -->
    
    <!-- 1. ÖĞRENCİ GİRİŞ MODAL'I -->
    <div id="login-screen-student" class="modal-screen">
        <div class="modal-box">
            <div class="modal-left-panel">
                <img src="/videolar/maarif.png" alt="Logo" class="w-32 h-auto rounded-lg mb-4">
                <h3 class="text-2xl font-bold text-center">Maarif SosyalLab</h3>
                <p class="text-center text-gray-300 mt-2">Öğrenci Girişi</p>
            </div>
            <div class="modal-right-panel">
                <button class="modal-close-btn" data-modal-id="login-screen-student"><i class="fa-solid fa-times fa-xl"></i></button>
                <h2 class="text-2xl font-bold text-gray-800 mb-6">Hoş Geldiniz!</h2>
                
                <div id="login-message-student" class="mb-4 text-sm text-red-500"></div>
                
                <form id="login-form-student">
                    <div class="mb-4">
                        <label for="login-student-no" class="form-label">Öğrenci No</label>
                        <input type="text" id="login-student-no" class="form-input" required>
                    </div>
                    <div class="mb-6">
                        <label for="login-student-password" class="form-label">Şifre</label>
                        <input type="password" id="login-student-password" class="form-input" required>
                    </div>
                    <button type="submit" class="form-button nav-button-student">Giriş Yap</button>
                </form>
                
                <div class="form-link">
                    Hesabın yok mu? <a id="show-student-register" data-modal-id="register-screen-student">Kayıt Ol</a>
                </div>
            </div>
        </div>
    </div>
    
    <!-- 2. ÖĞRETMEN GİRİŞ MODAL'I -->
    <div id="login-screen-teacher" class="modal-screen">
        <div class="modal-box">
            <div class="modal-left-panel">
                <img src="/videolar/maarif.png" alt="Logo" class="w-32 h-auto rounded-lg mb-4">
                <h3 class="text-2xl font-bold text-center">Maarif SosyalLab</h3>
                <p class="text-center text-gray-300 mt-2">Öğretmen Girişi</p>
            </div>
            <div class="modal-right-panel">
                <button class="modal-close-btn" data-modal-id="login-screen-teacher"><i class="fa-solid fa-times fa-xl"></i></button>
                <h2 class="text-2xl font-bold text-gray-800 mb-6">Değerli Öğretmenimiz,</h2>
                
                <div id="login-message-teacher" class="mb-4 text-sm text-red-500"></div>
                
                <form id="login-form-teacher">
                    <div class="mb-4">
                        <label for="login-teacher-lastname" class="form-label">Soyadınız</label>
                        <input type="text" id="login-teacher-lastname" class="form-input" required>
                    </div>
                    <div class="mb-6">
                        <label for="login-teacher-password" class="form-label">Şifre</label>
                        <input type="password" id="login-teacher-password" class="form-input" required>
                    </div>
                    <button type="submit" class="form-button nav-button-teacher">Giriş Yap</button>
                </form>
                
                <div class="form-link">
                    Hesabın yok mu? <a id="show-teacher-register" data-modal-id="register-screen-teacher">Kayıt Ol</a>
                </div>
            </div>
        </div>
    </div>

    <!-- 3. YÖNETİCİ GİRİŞ MODAL'I (Gizli) -->
    <div id="login-screen-admin" class="modal-screen">
        <div class="modal-box">
            <div class="modal-left-panel">
                <img src="/videolar/maarif.png" alt="Logo" class="w-32 h-auto rounded-lg mb-4">
                <h3 class="text-2xl font-bold text-center">Maarif SosyalLab</h3>
                <p class="text-center text-gray-300 mt-2">Süper Yönetici Girişi</p>
            </div>
            <div class="modal-right-panel">
                <button class="modal-close-btn" data-modal-id="login-screen-admin"><i class="fa-solid fa-times fa-xl"></i></button>
                <h2 class="text-2xl font-bold text-gray-800 mb-6">Yönetici Paneli</h2>
                <div id="login-message-admin" class="mb-4 text-sm text-red-500"></div>
                <form id="login-form-admin">
                    <div class="mb-4">
                        <label for="login-admin-username" class="form-label">Yönetici Adı (Soyadı)</label>
                        <input type="text" id="login-admin-username" class="form-input" required>
                    </div>
                    <div class="mb-6">
                        <label for="login-admin-password" class="form-label">Şifre</label>
                        <input type="password" id="login-admin-password" class="form-input" required>
                    </div>
                    <button type="submit" class="form-button" style="background-color: #dc3545;">Giriş Yap</button>
                </form>
                <div class="form-link">
                    Yönetici hesabı gerekiyor mu? <a id="show-admin-register" data-modal-id="register-screen-admin">Yeni Yönetici Kaydı</a>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Kayıt Modalları (Değişmedi) -->
    <div id="register-screen-student" class="modal-screen">
        <div class="modal-box">
            <div class="modal-left-panel">
                <img src="/videolar/maarif.png" alt="Logo" class="w-32 h-auto rounded-lg mb-4">
                <h3 class="text-2xl font-bold text-center">Öğrenci Kayıt</h3>
            </div>
            <div class="modal-right-panel" style="max-height: 80vh; overflow-y: auto;">
                <button class="modal-close-btn" data-modal-id="register-screen-student"><i class="fa-solid fa-times fa-xl"></i></button>
                <h2 class="text-2xl font-bold text-gray-800 mb-6">Yeni Hesap Oluştur</h2>
                <div id="register-message-student" class="mb-4 text-sm text-red-500"></div>
                <form id="register-form-student">
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div class="mb-3">
                            <label for="reg-student-school" class="form-label">Okul Adı</label>
                            <select id="reg-student-school" class="form-input" required>
                                <option value="">Okul Seçiniz...</option>
                                <option value="Sezi Eratik Ortaokulu">Sezi Eratik Ortaokulu</option>
                                <option value="TOKİ Demokrasi Ortaokulu">TOKİ Demokrasi Ortaokulu</option>
                            </select>
                        </div>
                        <div class="mb-3">
                            <label for="reg-student-class" class="form-label">Sınıf</label>
                            <select id="reg-student-class" class="form-input" required>
                                <option value="">Sınıf Seçiniz...</option>
                                <option value="5A">5A</option><option value="5B">5B</option><option value="5C">5C</option>
                                <option value="5D">5D</option><option value="5E">5E</option><option value="5F">5F</option>
                                <option value="5G">5G</option><option value="5H">5H</option>
                            </select>
                        </div>
                        <div class="mb-3">
                            <label for="reg-student-firstname" class="form-label">Adı</label>
                            <input type="text" id="reg-student-firstname" class="form-input" required>
                        </div>
                        <div class="mb-3">
                            <label for="reg-student-lastname" class="form-label">Soyadı</label>
                            <input type="text" id="reg-student-lastname" class="form-input" required>
                        </div>
                        <div class="mb-3">
                            <label for="reg-student-no" class="form-label">Okul Numarası</label>
                            <input type="text" id="reg-student-no" class="form-input" required>
                        </div>
                        <div class="mb-3">
                            <label for="reg-student-password" class="form-label">Şifre</label>
                            <input type="password" id="reg-student-password" class="form-input" required>
                        </div>
                    </div>
                    <button type="submit" class="form-button nav-button-student mt-4">Kayıt Ol</button>
                </form>
                <div class="form-link">
                    Zaten hesabın var mı? <a class="back-to-login" data-modal-id="login-screen-student">Giriş Yap</a>
                </div>
            </div>
        </div>
    </div>
    
    <div id="register-screen-teacher" class="modal-screen">
        <div class="modal-box">
             <div class="modal-left-panel">
                <img src="/videolar/maarif.png" alt="Logo" class="w-32 h-auto rounded-lg mb-4">
                <h3 class="text-2xl font-bold text-center">Öğretmen Kayıt</h3>
            </div>
            <div class="modal-right-panel" style="max-height: 80vh; overflow-y: auto;">
                <button class="modal-close-btn" data-modal-id="register-screen-teacher"><i class="fa-solid fa-times fa-xl"></i></button>
                <h2 class="text-2xl font-bold text-gray-800 mb-6">Öğretmen Hesabı Oluştur</h2>
                <div id="register-message-teacher" class="mb-4 text-sm text-red-500"></div>
                <form id="register-form-teacher">
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div class="mb-3">
                            <label for="reg-teacher-school" class="form-label">Okul Adı</label>
                            <select id="reg-teacher-school" class="form-input" required>
                                <option value="">Okul Seçiniz...</option>
                                <option value="Sezi Eratik Ortaokulu">Sezi Eratik Ortaokulu</option>
                                <option value="TOKİ Demokrasi Ortaokulu">TOKİ Demokrasi Ortaokulu</option>
                            </select>
                        </div>
                        <div class="mb-3">
                            <label for="reg-teacher-class" class="form-label">Sorumlu Olduğunuz Sınıf</label>
                            <select id="reg-teacher-class" class="form-input" required>
                                <option value="">Sınıf Seçiniz...</option>
                                <option value="5A">5A</option><option value="5B">5B</option><option value="5C">5C</option>
                                <option value="5D">5D</option><option value="5E">5E</option><option value="5F">5F</option>
                                <option value="5G">5G</option><option value="5H">5H</option>
                            </select>
                        </div>
                        <div class="mb-3">
                            <label for="reg-teacher-firstname" class="form-label">Adı</label>
                            <input type="text" id="reg-teacher-firstname" class="form-input" required>
                        </div>
                        <div class="mb-3">
                            <label for="reg-teacher-lastname" class="form-label">Soyadı</label>
                            <input type="text" id="reg-teacher-lastname" class="form-input" required>
                        </div>
                        <div class="col-span-2 mb-3">
                            <label for="reg-teacher-password" class="form-label">Giriş Şifresi</label>
                            <input type="password" id="reg-teacher-password" class="form-input" required>
                            <p class="text-xs text-gray-500 mt-1">Not: Giriş yaparken Soyadınızı ve bu şifreyi kullanacaksınız.</p>
                        </div>
                    </div>
                    <button type="submit" class="form-button nav-button-teacher mt-4">Kayıt Ol</button>
                </form>
                <div class="form-link">
                    Zaten hesabın var mı? <a class="back-to-login" data-modal-id="login-screen-teacher">Giriş Yap</a>
                </div>
            </div>
        </div>
    </div>
    
    <div id="register-screen-admin" class="modal-screen">
        <div class="modal-box">
            <div class="modal-left-panel">
                <img src="/videolar/maarif.png" alt="Logo" class="w-32 h-auto rounded-lg mb-4">
                <h3 class="text-2xl font-bold text-center">Yönetici Kayıt</h3>
            </div>
            <div class="modal-right-panel" style="max-height: 80vh; overflow-y: auto;">
                <button class="modal-close-btn" data-modal-id="register-screen-admin"><i class="fa-solid fa-times fa-xl"></i></button>
                <h2 class="text-2xl font-bold text-gray-800 mb-6">Yeni Yönetici Hesabı</h2>
                <div id="register-message-admin" class="mb-4 text-sm text-red-500"></div>
                <form id="register-form-admin">
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div class="mb-3">
                            <label for="reg-admin-firstname" class="form-label">Adı</label>
                            <input type="text" id="reg-admin-firstname" class="form-input" required>
                        </div>
                        <div class="mb-3">
                            <label for="reg-admin-lastname" class="form-label">Soyadı (Kullanıcı Adınız)</label>
                            <input type="text" id="reg-admin-lastname" class="form-input" required>
                        </div>
                         <div class="mb-3">
                            <label for="reg-admin-school" class="form-label">Okul Adı</label>
                            <input type="text" id="reg-admin-school" class="form-input" placeholder="Örn: İlçe Milli Eğitim" required>
                        </div>
                        <div class="mb-3">
                            <label for="reg-admin-title" class="form-label">Unvanı</label>
                            <input type="text" id="reg-admin-title" class="form-input" placeholder="Örn: Bilişim Sorumlusu" required>
                        </div>
                        <div class="col-span-2 mb-3">
                            <label for="reg-admin-password" class="form-label">Giriş Şifresi</label>
                            <input type="password" id="reg-admin-password" class="form-input" required>
                        </div>
                    </div>
                    <button type="submit" class="form-button" style="background-color: #dc3545;">Yönetici Olarak Kayıt Ol</button>
                </form>
                <div class="form-link">
                    Zaten hesabın var mı? <a class="back-to-login" data-modal-id="login-screen-admin">Giriş Yap</a>
                </div>
            </div>
        </div>
    </div>


    <!-- Yönetici Paneli (Gizli Modal) -->
    <div id="admin-panel-screen" class="modal-screen" style="max-width: 90vw; margin: auto; display: none;"> <!-- display: none eklendi -->
        <div class="bg-white text-gray-800 p-4 md:p-8 rounded-2xl shadow-xl w-full max-w-6xl relative" style="max-height: 90vh; display: flex; flex-direction: column;">
            
            <button class="modal-close-btn" data-modal-id="admin-panel-screen"><i class="fa-solid fa-times fa-xl"></i></button>
            
            <div class="flex justify-between items-center mb-4 border-b pb-3">
                <h2 class="text-3xl font-bold text-cyan-600">Süper Yönetici Paneli</h2>
            </div>
            
            <!-- (Admin panelinin geri kalanı değişmedi, içeriği aynı) -->
            <div class="border-b border-gray-200 mb-4">
                <nav class="flex space-x-4" aria-label="Tabs">
                    <button id="tab-student-list" class="admin-tab active" onclick="showAdminTab('student-list')">Öğrenci Listesi</button>
                    <button id="tab-bulk-upload" class="admin-tab" onclick="showAdminTab('bulk-upload')">Toplu Öğrenci Yükle</button>
                    <button id="tab-seyret-bul" class="admin-tab" onclick="showAdminTab('seyret-bul')">Seyret Bul Video Ekle</button>   
                    <button id="tab-seyret-bul-lokal" class="admin-tab" onclick="showAdminTab('seyret-bul-lokal')">Lokal Video Yükle</button>
                    <button id="tab-video-sil" class="admin-tab" onclick="showAdminTab('video-sil')">Video Listesi / Sil</button>
                    <button id="tab-video-istekleri" class="admin-tab" onclick="showAdminTab('video-istekleri')">Video İstekleri</button>
                </nav>
            </div>
            <div class="flex-1 overflow-y-auto">
                <div id="content-student-list" class="admin-tab-content active">
                <div class="flex items-center gap-4 mb-4 p-4 bg-gray-50 rounded-lg border">
                        <label for="filter-school" class="form-label mb-0 text-sm font-semibold">Okula Göre Filtrele:</label>
                        <select id="filter-school" class="form-input py-1 text-sm w-auto">
                            <option value="">Tüm Okullar</option>
                            <option value="Sezi Eratik Ortaokulu">Sezi Eratik Ortaokulu</option>
                            <option value="TOKİ Demokrasi Ortaokulu">TOKİ Demokrasi Ortaokulu</option>
                        </select>
                        <label for="filter-class" class="form-label mb-0 text-sm font-semibold">Sınıfa Göre Filtrele:</label>
                        <select id="filter-class" class="form-input py-1 text-sm w-auto">
                            <option value="">Tüm Sınıflar</option>
                            <option value="atanmadi">--- Sınıfı Atanmamışlar ---</option> <option value="5A">5A</option><option value="5B">5B</option><option value="5C">5C</option>
                            <option value="5D">5D</option><option value="5E">5E</option><option value="5F">5F</option>
                            <option value="5G">5G</option><option value="5H">5H</option>
                        </select>
                    </div>
                    <!-- (Admin paneli içeriği değişmedi, sizin dosyanızdan kopyalandı) -->
                    <div class="bg-gray-50 p-4 rounded-lg border border-gray-200 mb-4 flex flex-wrap items-center gap-4">
                        <span class="text-sm font-semibold text-gray-700">Seçililerle:</span>
                        <select id="bulk-school-select" class="text-sm rounded-lg border-gray-300 focus:ring-cyan-500">
                            <option value="">Toplu Okul Ata...</option>
                            <option value="Sezi Eratik Ortaokulu">Sezi Eratik Ortaokulu</option>
                            <option value="TOKİ Demokrasi Ortaokulu">TOKİ Demokrasi Ortaokulu</option>
                        </select>
                        <select id="bulk-class-select" class="text-sm rounded-lg border-gray-300 focus:ring-cyan-500">
                            <option value="">Toplu Sınıf Ata...</option>
                            <option value="5A">5A</option><option value="5B">5B</option><option value="5C">5C</option>
                            <option value="5D">5D</option><option value="5E">5E</option><option value="5F">5F</option>
                            <option value="5G">5G</option><option value="5H">5H</option>
                        </select>
                        </button>
                        <button id="bulk-role-student-btn" class="text-sm bg-green-500 text-white font-semibold py-2 px-3 rounded-lg hover:bg-green-600">
                            Rolü "Öğrenci" Yap
                        </button>
                        <button id="bulk-update-btn" class="text-sm bg-blue-500 text-white font-semibold py-2 px-3 rounded-lg hover:bg-blue-600">
                            Toplu Güncelle
                        </button>
                        <button id="bulk-delete-btn" class="text-sm bg-red-500 text-white font-semibold py-2 px-3 rounded-lg hover:bg-red-600 ml-auto">
                            Seçilileri Sil
                        </button>
                    </div>
                    <div class="overflow-x-auto max-h-96">
                        <table class="w-full min-w-max text-sm text-left">
                            <thead class="bg-gray-100 sticky top-0">
                                <tr>
                                    <th class="p-2 w-10"><input type="checkbox" id="select-all-students" /></th>
                                    <th class="p-2">Öğrenci No / ID</th>
                                    <th class="p-2">Adı</th>
                                    <th class="p-2">Soyadı</th>
                                    <th class="p-2">Rol</th>
                                    <th class="p-2">Okul</th>
                                    <th class="p-2">Sınıf</th>
                                    <th class="p-2">Şifre (Gizli)</th>
                                    <th class="p-2">İşlemler</th>
                                </tr>
                            </thead>
                            <tbody id="student-list-tbody" class="divide-y">
                                <tr><td colspan="9" class="p-4 text-center text-gray-500">Yüklenecek kullanıcı verisi yok.</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
               <div id="content-bulk-upload" class="admin-tab-content p-4">
                        <h3 class="text-lg font-semibold mb-2">Toplu Öğrenci Yükle (.xlsx, .csv)</h3>
                        <p class="text-sm text-gray-600 mb-4">Sadece "Öğrenci No", "Adı", "Soyadı" sütunlarını içeren bir dosya seçin. Diğer bilgiler (okul, sınıf, şifre) daha sonra "Öğrenci Listesi" sekmesinden toplu olarak atanabilir.</p>
                        <input type="file" id="excelFile" accept=".xlsx, .csv" class="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"/>
                        <button id="uploadExcelBtn" class="mt-4 bg-blue-500 text-white font-semibold py-2 px-4 rounded-lg hover:bg-blue-600">Excel/CSV Yükle</button>
                        <div id="uploadExcelMessage" class="mt-2 text-sm"></div>
                    </div>

                    <div id="content-seyret-bul" class="admin-tab-content p-4">
                        <h3 class="text-lg font-semibold mb-2">Seyret Bul (YouTube) Video Ekle</h3>
                        <p class="text-sm text-gray-600 mb-4">Bu form, bir YouTube linki ve video metni kullanarak Gemini'ye 9 adet soru ürettirir ve sisteme ekler.</p>
                        <form id="seyret-bul-form-admin" class="space-y-4">
                            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label for="sb-admin-baslik" class="form-label">Video Başlığı</label>
                                    <input type="text" id="sb-admin-baslik" class="form-input" required>
                                </div>
                                <div>
                                    <label for="sb-admin-url" class="form-label">YouTube Video Linki (örn: https://www.youtube.com/watch?v=...)</label>
                                    <input type="url" id="sb-admin-url" class="form-input" required>
                                </div>
                            </div>
                            <div>
                                <label for="sb-admin-surec" class="form-label">Süreç Bileşeni (Kazanım)</label>
                                <select id="sb-admin-surec" class="form-input" required>
                                    <option value="">Yükleniyor...</option>
                                </select>
                            </div>
                            <div>
                                <label for="sb-admin-metin" class="form-label">Video Metni (Transkript)</label>
                                <textarea id="sb-admin-metin" rows="8" class="form-input" placeholder="Sorular bu metne göre üretilecek..."></textarea>
                            </div>
                            <div>
                                <label for="sb-admin-sifre" class="form-label">Admin Şifresi</label>
                                <input type="password" id="sb-admin-sifre" class="form-input w-auto" required>
                            </div>
                            <button type="submit" id="sb-admin-gonder-btn" class="bg-green-500 text-white font-semibold py-2 px-4 rounded-lg hover:bg-green-600">Soruları Üret ve Videoyu Ekle</button>
                            <div id="sb-admin-mesaj" class="mt-2 text-sm"></div>
                        </form>
                    </div>

                    <div id="content-seyret-bul-lokal" class="admin-tab-content p-4">
                        <h3 class="text-lg font-semibold mb-2">Seyret Bul (Lokal Video) Yükle</h3>
                        <p class="text-sm text-gray-600 mb-4">Bu form, bilgisayarınızdan bir video dosyası (.mp4) yükler ve metne göre Gemini'ye 9 adet soru ürettirir.</p>
                        <form id="seyret-bul-form-lokal" class="space-y-4">
                            <div>
                                <label for="sb-lokal-baslik" class="form-label">Video Başlığı</label>
                                <input type="text" id="sb-lokal-baslik" class="form-input" required>
                            </div>
                            <div>
                                <label for="sb-lokal-dosya" class="form-label">Video Dosyası (.mp4)</label>
                                <input type="file" id="sb-lokal-dosya" accept=".mp4" class="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100" required>
                            </div>
                            <div>
                                <label for="sb-lokal-surec" class="form-label">Süreç Bileşeni (Kazanım)</label>
                                <select id="sb-lokal-surec" class="form-input" required>
                                    <option value="">Yükleniyor...</option>
                                </select>
                            </div>
                            <div>
                                <label for="sb-lokal-metin" class="form-label">Video Metni (Transkript)</label>
                                <textarea id="sb-lokal-metin" rows="8" class="form-input" placeholder="Sorular bu metne göre üretilecek..."></textarea>
                            </div>
                            <div>
                                <label for="sb-lokal-sifre" class="form-label">Admin Şifresi</label>
                                <input type="password" id="sb-lokal-sifre" class="form-input w-auto" required>
                            </div>
                            <button type="submit" id="sb-lokal-gonder-btn" class="bg-purple-500 text-white font-semibold py-2 px-4 rounded-lg hover:bg-purple-600">Lokal Videoyu Yükle ve Soruları Üret</button>
                            <div id="sb-lokal-mesaj" class="mt-2 text-sm"></div>
                        </form>
                    </div> 

                    <div id="content-video-sil" class="admin-tab-content p-4">
                        <div class="flex justify-between items-center mb-4">
                            <h3 class="text-lg font-semibold">Video Listesi / Sil</h3>
                            <button id="refreshVideoListBtn" class="bg-gray-500 text-white font-semibold py-2 px-4 rounded-lg hover:bg-gray-600">
                                <i class="fa-solid fa-sync mr-1"></i> Listeyi Yenile
                            </button>
                        </div>
                        <div id="videoSilMesaj" class="text-sm mb-2"></div>
                        <div class="overflow-x-auto max-h-96">
                            <table class="w-full min-w-max text-sm text-left">
                                <thead class="bg-gray-100 sticky top-0">
                                    <tr>
                                        <th class="p-2">Video Başlığı</th>
                                        <th class="p-2">Kazanım (Süreç)</th>
                                        <th class="p-2">URL / Dosya</th>
                                        <th class="p-2">Soru Sayısı</th>
                                        <th class="p-2">Video ID</th>
                                        <th class="p-2">İşlemler</th>
                                    </tr>
                                </thead>
                                <tbody id="video-list-tbody" class="divide-y">
                                    <tr><td colspan="6" class="p-4 text-center text-gray-500">Video listesini görmek için "Listeyi Yenile" butonuna basın.</td></tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                    <!-- Video İstekleri Paneli -->
                    <div id="content-video-istekleri" class="admin-tab-content p-4">
                        <h3 class="text-lg font-semibold mb-4">Video İstekleri</h3>
                        <p class="text-sm text-gray-600 mb-4">Öğretmen ve öğrencilerden gelen video istekleri.</p>
                        
                        <div class="overflow-x-auto">
                            <table class="w-full bg-white shadow-md rounded-lg text-sm">
                                <thead class="bg-gray-100">
                                    <tr>
                                        <th class="p-3 text-left">Tarih</th>
                                        <th class="p-3 text-left">Gönderen</th> <th class="p-3 text-left">Rol</th>    <th class="p-3 text-left">Okul</th>
                                        <th class="p-3 text-left">Sınıf / No</th>
                                        <th class="p-3 text-left w-1/2">İstek Metni</th>
                                        <th class="p-3 text-left">Durum</th>
                                        <th class="p-3 text-left">İşlemler</th>
                                    </tr>
                                </thead>
                                <tbody id="video-istekleri-tbody">
                                    <tr><td colspan="8" class="p-4 text-center text-gray-500">İstekler yükleniyor...</td></tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
                <!-- ========== VİDEO DÜZENLEME MODAL POP-UP ========== -->
    <div id="edit-video-modal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 9999; justify-content: center; align-items: center;">
        <div style="background: white; padding: 24px; border-radius: 8px; width: 90%; max-width: 600px; max-height: 90vh; overflow-y: auto;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                <h3 style="font-size: 20px; font-weight: bold;">Video Düzenle</h3>
                <button class="modal-close-btn" style="font-size: 24px; cursor: pointer; background: none; border: none;">&times;</button>
            </div>
            
            <form id="edit-video-form">
                <input type="hidden" id="edit-video-id">
                
                <div style="margin-bottom: 16px;">
                    <label style="display: block; margin-bottom: 8px; font-weight: 600;">Video Başlığı:</label>
                    <input type="text" id="edit-video-baslik" required style="width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px;">
                </div>
                
                <div style="margin-bottom: 16px;">
                    <label style="display: block; margin-bottom: 8px; font-weight: 600;">Mevcut Kazanım:</label>
                    <input type="text" id="edit-video-surec-mevcut" readonly style="width: 100%; padding: 8px; border: 1px solid #e0e0e0; border-radius: 4px; background: #f5f5f5;">
                </div>
                
                <div style="margin-bottom: 16px;">
                    <label style="display: block; margin-bottom: 8px; font-weight: 600;">Yeni Kazanım (opsiyonel):</label>
                    <select id="edit-video-surec-yeni" style="width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px;">
                        <option value="">Değiştirme (Mevcut kalsın)</option>
                    </select>
                </div>
                
                <button type="submit" style="background: #3b82f6; color: white; padding: 10px 20px; border-radius: 4px; border: none; cursor: pointer; font-weight: 600;">Kaydet</button>
                <div id="edit-video-mesaj" style="margin-top: 12px; font-size: 14px;"></div>
            </form>
        </div>
    </div>
    
    <!-- GÜNCELLENMİŞ JAVASCRIPT (AŞAMA 5 - Ctrl+Alt+A Gizli Giriş Eklendi) -->
    <!-- HATA DÜZELTMESİ: f-string { } hatası olmaması için normal JS {} kullanıldı -->
    <script>
        // Global değişkenler
        let refreshVideoListBtn, videoListTbody, videoSilMesaj;

        document.addEventListener('DOMContentLoaded', () => {
        
            // --- EKRANLARI VE MODALLARI SEÇ ---
            const welcomeScreen = document.getElementById('welcome-screen');
            const studentLoginModal = document.getElementById('login-screen-student');
            const teacherLoginModal = document.getElementById('login-screen-teacher');
            const adminLoginModal = document.getElementById('login-screen-admin');
            const studentRegisterModal = document.getElementById('register-screen-student');
            const teacherRegisterModal = document.getElementById('register-screen-teacher');
            const adminRegisterModal = document.getElementById('register-screen-admin');
            const adminPanelScreen = document.getElementById('admin-panel-screen');

            // --- HEADER BUTONLARINI SEÇ ---
            const showStudentLoginBtn = document.getElementById('show-student-login');
            const showTeacherLoginBtn = document.getElementById('show-teacher-login');
            
            
            // --- YARDIMCI MODAL GÖSTERME FONKSİYONU ---
            function showModal(modalElement) {
                [studentLoginModal, teacherLoginModal, adminLoginModal, 
                 studentRegisterModal, teacherRegisterModal, adminRegisterModal, 
                 adminPanelScreen
                ].forEach(modal => {
                    if (modal) modal.style.display = 'none';
                });
                if (modalElement) modalElement.style.display = 'flex';
            }
            
            function closeModal(modalElement) {
                if (modalElement) modalElement.style.display = 'none';
            }

            // --- TIKLAMA OLAYLARI (HEADER) ---
            showStudentLoginBtn.addEventListener('click', () => showModal(studentLoginModal));
            showTeacherLoginBtn.addEventListener('click', () => showModal(teacherLoginModal));

            // --- 7. İSTEK: GİZLİ YÖNETİCİ GİRİŞİ (Ctrl + Alt + A) ---
            document.addEventListener('keydown', (e) => {
                if (e.ctrlKey && e.altKey && e.key === 'm') {
                    e.preventDefault();
                    console.log("Gizli Yönetici Girişi Kısayolu Algılandı!");
                    showModal(adminLoginModal);
                }
            });

                       
            // --- TIKLAMA OLAYLARI (MODAL İÇİ LİNKLER VE KAPATMA BUTONLARI) ---
            const showStudentRegisterBtn = document.getElementById('show-student-register');
            const showTeacherRegisterBtn = document.getElementById('show-teacher-register');
            const showAdminRegisterBtn = document.getElementById('show-admin-register');
            
            // Kayıt butonlarını etkinleştir (Önce girişi kapat, sonra kaydı aç)
            if(showStudentRegisterBtn) showStudentRegisterBtn.addEventListener('click', () => { 
                closeModal(studentLoginModal); 
                showModal(studentRegisterModal); 
            });
            if(showTeacherRegisterBtn) showTeacherRegisterBtn.addEventListener('click', () => { 
                closeModal(teacherLoginModal); 
                showModal(teacherRegisterModal); 
            });
            // Admin butonu (gerekirse)
            if(showAdminRegisterBtn) showAdminRegisterBtn.addEventListener('click', () => { 
                closeModal(adminLoginModal); 
                showModal(adminRegisterModal); 
            });

            // Girişe Geri Dön linklerini etkinleştir (Kayıt modalını kapatıp Giriş modalını aç)
            document.querySelectorAll('.back-to-login').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    // Kayıt modalını kapat
                    e.target.closest('.modal-screen').style.display = 'none'; 
                    
                    const modalId = e.target.getAttribute('data-modal-id');
                    const modalToShow = document.getElementById(modalId);
                    if (modalToShow) showModal(modalToShow);
                });
            });
            
            // X Kapatma İşlemi (e.target.closest ile çarpıya tıklamayı garantiler)
            document.querySelectorAll('.modal-close-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    // Olayın nereden başladığı fark etmeksizin, üstteki modal-close-btn'i bul
                    const targetBtn = e.target.closest('.modal-close-btn'); 
                    if (targetBtn) {
                        const modalId = targetBtn.getAttribute('data-modal-id');
                        const modalToClose = document.getElementById(modalId);
                        if (modalToClose) closeModal(modalToClose);
                    }
                });
            });
            
            // --- GİRİŞ FORMLARI (Fetch API - Değişiklik yok) ---
            
            // 1. ÖĞRENCİ GİRİŞ
            const loginFormStudent = document.getElementById('login-form-student');
            const loginMessageStudent = document.getElementById('login-message-student');
            if (loginFormStudent) {
                loginFormStudent.addEventListener('submit', async (e) => {
                    e.preventDefault(); 
                    const studentNo = document.getElementById('login-student-no').value;
                    const password = document.getElementById('login-student-password').value; 
                    loginMessageStudent.textContent = 'Giriş yapılıyor...';
                    try {
                        const response = await fetch('/login-student', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ student_no: studentNo, password: password })
                        });
                        const result = await response.json();
                       if (result.success) {
                            localStorage.setItem('loggedInUserName', result.name); 
                            localStorage.setItem('loggedInUserId', result.user_id); // Benzersiz ID (100_TOKİ...)
                            localStorage.setItem('loggedInUserRole', 'student'); 
                            localStorage.setItem('loggedInUserNo', result.user_no); // <-- DÜZELTME BURADA (Artık "100"ü kaydeder)
                            localStorage.setItem('loggedInUserSchool', result.school_name); 
                            localStorage.setItem('loggedInUserClass', result.class);     
                            window.location.href = '/dashboard';
                        } else {
                            loginMessageStudent.textContent = result.message || 'Giriş başarısız!';
                        }
                    } catch (error) {
                        loginMessageStudent.textContent = 'Sunucuyla iletişim kurulamadı.';
                    }
                });
            }
            
            // 2. ÖĞRETMEN GİRİŞ
            const loginFormTeacher = document.getElementById('login-form-teacher');
            const loginMessageTeacher = document.getElementById('login-message-teacher');
            if (loginFormTeacher) {
                loginFormTeacher.addEventListener('submit', async (e) => {
                    e.preventDefault();
                    const lastname = document.getElementById('login-teacher-lastname').value;
                    const password = document.getElementById('login-teacher-password').value;
                    loginMessageTeacher.textContent = 'Giriş yapılıyor...';
                    try {
                        const response = await fetch('/login-teacher', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ lastname: lastname, password: password })
                        });
                        const result = await response.json();
                        if (result.success) {
                            localStorage.setItem('loggedInUserName', result.name); 
                            localStorage.setItem('loggedInUserId', result.user_id); 
                            localStorage.setItem('loggedInUserRole', 'teacher'); 
                            localStorage.setItem('loggedInUserSchool', result.school_name);
                            localStorage.setItem('loggedInUserClass', result.class);
                            window.location.href = '/dashboard'; 
                        } else {
                            loginMessageTeacher.textContent = result.message || 'Giriş başarısız!';
                        }
                    } catch (error) {
                        loginMessageTeacher.textContent = 'Sunucuyla iletişim kurulamadı.';
                    }
                });
            }

            // 3. YÖNETİCİ GİRİŞ
            const loginFormAdmin = document.getElementById('login-form-admin');
            const loginMessageAdmin = document.getElementById('login-message-admin');
            if (loginFormAdmin) {
                loginFormAdmin.addEventListener('submit', async (e) => {
                    e.preventDefault();
                    const username = document.getElementById('login-admin-username').value;
                    const password = document.getElementById('login-admin-password').value;
                    loginMessageAdmin.textContent = 'Giriş yapılıyor...';
                    try {
                        const response = await fetch('/login-admin', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ username: username, password: password })
                        });
                        const result = await response.json();
                        if (result.success) {
                            localStorage.setItem('loggedInUserName', result.name); 
                            localStorage.setItem('loggedInUserId', result.user_id); 
                            localStorage.setItem('loggedInUserRole', 'admin');
                            loginMessageAdmin.textContent = 'Giriş başarılı! Panel açılıyor...';
                            showModal(adminPanelScreen); 
                            loadStudentList(); 
                        } else {
                            loginMessageAdmin.textContent = result.message || 'Giriş başarısız!';
                        }
                    } catch (e) {
                        loginMessageAdmin.textContent = 'Sunucuyla iletişim kurulamadı.';
                    }
                });
            }
            
            
            // --- KAYIT FORMLARI (Fetch API - Değişiklik yok) ---
            
            // 1. ÖĞRENCİ KAYIT
            const registerFormStudent = document.getElementById('register-form-student');
            const registerMessageStudent = document.getElementById('register-message-student');
            if (registerFormStudent) {
                registerFormStudent.addEventListener('submit', async (e) => {
                    e.preventDefault();
                    const formData = {
                        school_name: document.getElementById('reg-student-school').value,
                        class: document.getElementById('reg-student-class').value,
                        first_name: document.getElementById('reg-student-firstname').value,
                        last_name: document.getElementById('reg-student-lastname').value,
                        student_no: document.getElementById('reg-student-no').value,
                        password: document.getElementById('reg-student-password').value
                    };
                    registerMessageStudent.textContent = 'Kayıt yapılıyor...';
                    try {
                        const response = await fetch('/register-student', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(formData)
                        });
                        const result = await response.json();
                        if (result.success) {
                            registerMessageStudent.textContent = 'Kayıt başarılı! Giriş ekranına yönlendiriliyorsunuz...';
                            registerMessageStudent.style.color = 'green';
                            setTimeout(() => showModal(studentLoginModal), 2000);
                        } else {
                            registerMessageStudent.textContent = result.message || 'Kayıt başarısız!';
                            registerMessageStudent.style.color = 'red';
                        }
                    } catch (e) {
                        registerMessageStudent.textContent = 'Sunucuyla iletişim kurulamadı.';
                    }
                });
            }
            
            // 2. ÖĞRETMEN KAYIT
            const registerFormTeacher = document.getElementById('register-form-teacher');
            const registerMessageTeacher = document.getElementById('register-message-teacher');
            if (registerFormTeacher) {
                registerFormTeacher.addEventListener('submit', async (e) => {
                    e.preventDefault();
                     const formData = {
                        school_name: document.getElementById('reg-teacher-school').value,
                        class: document.getElementById('reg-teacher-class').value,
                        first_name: document.getElementById('reg-teacher-firstname').value,
                        last_name: document.getElementById('reg-teacher-lastname').value,
                        password: document.getElementById('reg-teacher-password').value
                    };
                    registerMessageTeacher.textContent = 'Kayıt yapılıyor...';
                    try {
                        const response = await fetch('/register-teacher', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(formData)
                        });
                        const result = await response.json();
                        if (result.success) {
                            registerMessageTeacher.textContent = 'Kayıt başarılı! Giriş ekranına yönlendiriliyorsunuz...';
                            registerMessageTeacher.style.color = 'green';
                            setTimeout(() => showModal(teacherLoginModal), 2000);
                        } else {
                            registerMessageTeacher.textContent = result.message || 'Kayıt başarısız!';
                            registerMessageTeacher.style.color = 'red';
                        }
                    } catch (e) {
                        registerMessageTeacher.textContent = 'Sunucuyla iletişim kurulamadı.';
                    }
                });
            }
            
            // 3. YÖNETİCİ KAYIT
            const registerFormAdmin = document.getElementById('register-form-admin');
            const registerMessageAdmin = document.getElementById('register-message-admin');
            if (registerFormAdmin) {
                registerFormAdmin.addEventListener('submit', async (e) => {
                    e.preventDefault();
                    const formData = {
                        school_name: document.getElementById('reg-admin-school').value,
                        title: document.getElementById('reg-admin-title').value,
                        first_name: document.getElementById('reg-admin-firstname').value,
                        last_name: document.getElementById('reg-admin-lastname').value,
                        password: document.getElementById('reg-admin-password').value
                    };
                    registerMessageAdmin.textContent = 'Kayıt yapılıyor...';
                     try {
                        const response = await fetch('/register-admin', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(formData)
                        });
                        const result = await response.json();
                        if (result.success) {
                            registerMessageAdmin.textContent = 'Kayıt başarılı! Giriş ekranına yönlendiriliyorsunuz...';
                            registerMessageAdmin.style.color = 'green';
                            setTimeout(() => showModal(adminLoginModal), 2000);
                        } else {
                            registerMessageAdmin.textContent = result.message || 'Kayıt başarısız!';
                            registerMessageAdmin.style.color = 'red';
                        }
                    } catch (e) {
                        registerMessageAdmin.textContent = 'Sunucuyla iletişim kurulamadı.';
                    }
                });
            }


            // --- SÜPER YÖNETİCİ PANELİ JS (Rotalar Aşama 2.5'te güncellenmişti) ---
            
            window.showAdminTab = function(tabName) {
                // ... (Bu fonksiyon değişmedi) ...
                document.getElementById('content-student-list').style.display = 'none';
                document.getElementById('content-bulk-upload').style.display = 'none';
                document.getElementById('content-seyret-bul').style.display = 'none'; 
                document.getElementById('content-seyret-bul-lokal').style.display = 'none';
                document.getElementById('content-video-sil').style.display = 'none'; 
                document.getElementById('tab-student-list').classList.remove('active');
                document.getElementById('tab-bulk-upload').classList.remove('active');
                document.getElementById('tab-seyret-bul').classList.remove('active'); 
                document.getElementById('tab-seyret-bul-lokal').classList.remove('active');
                document.getElementById('tab-video-sil').classList.remove('active'); 
                document.getElementById('content-' + tabName).style.display = 'block';
                document.getElementById('tab-' + tabName).classList.add('active');
            }
            
        // ===================================================================
            // === NİHAİ YÖNETİCİ PANELİ JAVASCRIPT (TAM DÜZELTME) ===
            // ===================================================================

            // --- Global Değişkenler ---
            let g_surecListesi = [];
            let g_videoListesi = []; 

            // --- 1. ÖĞRENCİ LİSTESİ FONKSİYONLARI ---
            
            async function loadStudentList() {
                const studentListBody = document.getElementById('student-list-tbody');
                if (!studentListBody) return;
                console.log("Kullanıcı listesi çekiliyor...");
                try {
                    const response = await fetch('/get_all_users'); 
                    const result = await response.json();
                    if (result.success && result.users) { 
                        studentListBody.innerHTML = ''; 
                        const users = result.users; 
                        if (Object.keys(users).length === 0) {
                            studentListBody.innerHTML = `<tr><td colspan="9" class="p-4 text-center text-gray-500">Kayıtlı kullanıcı bulunamadı.</td></tr>`;
                            return;
                        }
                        const schoolFilter = document.getElementById('filter-school').value;
                        const classFilter = document.getElementById('filter-class').value;
                        for (const userId in users) { 
                            const user = users[userId];
                            if (schoolFilter && user.school_name !== schoolFilter) continue;
                            if (classFilter) {
                                if (classFilter === "atanmadi") {
                                    if (user.class && user.class !== "") continue; // Sınıfı OLANI atla
                                } else {
                                    if (user.class !== classFilter) continue; 
                                }
                            }
                            let rol = '---';
                            if (istek.rol === 'student') rol = 'Öğrenci'; // <-- BURASI DOĞRU
                            else if (istek.rol === 'teacher') rol = 'Öğretmen';
                            else if (istek.rol === 'admin') rol = 'Yönetici';
                            else if (istek.rol) rol = istek.rol;
                            const displayId = user.role === 'student' ? (user.student_no || userId) : userId;
                            const row = `
                                <tr class="border-b hover:bg-gray-50">
                                    <td class="p-2"><input type="checkbox" class="student-checkbox" data-user-id="${userId}" /></td>
                                    <td class="p-2">${displayId}</td>
                                    <td class="p-2">${user.first_name || ''}</td>
                                    <td class="p-2">${user.last_name || ''}</td>
                                    <td class="p-2 ${roleClass}">${userRole}</td>
                                    <td class="p-2">${user.school_name || '<i>Atanmadı</i>'}</td>
                                    <td class="p-2">${user.class || '<i>Atanmadı</i>'}</td>
                                    <td class="p-2">${user.password ? '***' : '<i>Yok</i>'}</td>
                                    <td class="p-2">
                                        <button onclick="deleteUser('${userId}')" class="text-red-500 hover:underline text-xs">Sil</button>
                                    </td>
                                </tr>`;
                            studentListBody.innerHTML += row;
                        }
                    } else {
                        studentListBody.innerHTML = `<tr><td colspan="9" class="p-4 text-center text-red-500">Kullanıcılar yüklenemedi.</td></tr>`;
                    }
                } catch (error) {
                    console.error("loadStudentList hatası:", error);
                    studentListBody.innerHTML = `<tr><td colspan="9" class="p-4 text-center text-red-500">Bir hata oluştu.</td></tr>`;
                }
            }
            window.loadStudentList = loadStudentList; 

            // Filtrelerin ve Hepsini Seç'in Çalışmasını Sağlama
            const filterSchool = document.getElementById('filter-school');
            const filterClass = document.getElementById('filter-class');
            const selectAllCheckbox = document.getElementById('select-all-students');
            if (filterSchool) filterSchool.addEventListener('change', loadStudentList);
            if (filterClass) filterClass.addEventListener('change', loadStudentList);
            if (selectAllCheckbox) {
                selectAllCheckbox.addEventListener('change', (e) => {
                    const visibleCheckboxes = document.querySelectorAll('#student-list-tbody .student-checkbox');
                    visibleCheckboxes.forEach(cb => { cb.checked = e.target.checked; });
                });
            }

            // YARDIMCI: Seçili kullanıcı ID'lerini alır
            function getSelectedUserIds() {
                const checkboxes = document.querySelectorAll('.student-checkbox:checked');
                const ids = [];
                checkboxes.forEach(cb => { ids.push(cb.getAttribute('data-user-id')); });
                return ids;
            }

            // Toplu Rol Atama Butonu
            const bulkRoleStudentBtn = document.getElementById('bulk-role-student-btn');
            if (bulkRoleStudentBtn) {
                bulkRoleStudentBtn.addEventListener('click', async () => {
                    const selectedIds = getSelectedUserIds();
                    if (selectedIds.length === 0) return alert('Önce en az bir öğrenci seçmelisiniz.');
                    if (!confirm(`${selectedIds.length} adet seçili kullanıcının rolünü "öğrenci" olarak atamak istediğinizden emin misiniz?`)) return;
                    try {
                        await fetch('/update_student_bulk', {
                            method: 'POST', headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ student_ids: selectedIds, actions: { role: 'student' } })
                        });
                        alert('Roller başarıyla "öğrenci" olarak atandı!');
                        loadStudentList(); 
                    } catch (error) { console.error("Toplu rol atama hatası:", error); alert('Bir hata oluştu.'); }
                });
            }
            
            // Toplu Silme Butonu
            const bulkDeleteBtn = document.getElementById('bulk-delete-btn');
            if (bulkDeleteBtn) {
                bulkDeleteBtn.addEventListener('click', async () => {
                    const selectedIds = getSelectedUserIds();
                    if (selectedIds.length === 0) return alert('Önce en az bir öğrenci seçmelisiniz.');
                    if (!confirm(`${selectedIds.length} adet seçili kullanıcıyı kalıcı olarak silmek istediğinizden emin misiniz?`)) return;
                    try {
                        await fetch('/delete_student_bulk', {
                            method: 'POST', headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ student_ids: selectedIds })
                        });
                        alert(`${selectedIds.length} kullanıcı başarıyla silindi.`);
                        loadStudentList();
                    } catch (error) { console.error("Toplu silme hatası:", error); alert('Bir hata oluştu.'); }
                });
            }

            // Birleştirilmiş Toplu Güncelleme Butonu
            const bulkUpdateBtn = document.getElementById('bulk-update-btn');
            if (bulkUpdateBtn) {
                bulkUpdateBtn.addEventListener('click', async () => {
                    const selectedIds = getSelectedUserIds();
                    if (selectedIds.length === 0) return alert('Önce en az bir öğrenci seçmelisiniz.');
                    const school = document.getElementById('bulk-school-select').value;
                    const sClass = document.getElementById('bulk-class-select').value;
                    if (!school && !sClass) return alert('Lütfen atanacak bir Okul veya Sınıf seçin.');
                    const actions = { set_password_to_lastname: true };
                    if (school) actions.school = school;
                    if (sClass) actions.class = sClass;
                    if (!confirm(`${selectedIds.length} adet seçili kullanıcıya şu işlemleri uygulamak istediğinizden emin misiniz?\n\n- Okul: ${school || 'Değişmeyecek'}\n- Sınıf: ${sClass || 'Değişmeyecek'}\n- Şifre: Öğrencinin Soyadı Olarak Ayarlanacak`)) return;
                    try {
                        await fetch('/update_student_bulk', {
                            method: 'POST', headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ student_ids: selectedIds, actions: actions })
                        });
                        alert('Seçili öğrenciler başarıyla güncellendi (Okul, Sınıf ve Şifre ayarlandı).');
                        loadStudentList();
                    } catch (error) { console.error("Toplu güncelleme hatası:", error); alert('Bir hata oluştu.'); }
                });
            }

            // Kullanıcı Silme Fonksiyonu
            window.deleteUser = async function(userId) { 
                if (!confirm(`${userId} ID'li kullanıcıyı silmek istediğinizden emin misiniz?`)) return;
                try {
                    await fetch('/delete_user', { 
                        method: 'POST', headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ user_id: userId }) 
                    });
                    loadStudentList(); 
                } catch (error) { console.error("deleteUser hatası:", error); }
            }
            
            // --- 2. EXCEL YÜKLEME FONKSİYONLARI ---
            const uploadExcelBtn = document.getElementById('uploadExcelBtn');
            const excelFile = document.getElementById('excelFile');
            const uploadExcelMessage = document.getElementById('uploadExcelMessage');
            
            if (uploadExcelBtn) {
                uploadExcelBtn.addEventListener('click', async () => {
                    if (!excelFile.files || excelFile.files.length === 0) {
                        uploadExcelMessage.textContent = 'Lütfen bir dosya seçin.';
                        uploadExcelMessage.style.color = 'red';
                        return;
                    }
                    const file = excelFile.files[0];
                    const formData = new FormData();
                    formData.append('excelFile', file);
                    
                    uploadExcelMessage.textContent = 'Yükleniyor...';
                    uploadExcelMessage.style.color = 'blue';
                    try {
                        const response = await fetch('/upload_excel', { method: 'POST', body: formData });
                        const result = await response.json();
                        if (result.success) {
                            uploadExcelMessage.textContent = result.message;
                            uploadExcelMessage.style.color = 'green';
                            loadStudentList(); // Listeyi yenile
                        } else {
                            uploadExcelMessage.textContent = `Hata: ${result.message}`;
                            uploadExcelMessage.style.color = 'red';
                        }
                    } catch (error) {
                        uploadExcelMessage.textContent = `Sunucu hatası: ${error}`;
                        uploadExcelMessage.style.color = 'red';
                    }
                });
            }

            // --- 3. VİDEO YÖNETİMİ FONKSİYONLARI ---

            // YARDIMCI: Süreç bileşenlerini (kazanımları) API'den çeker
            async function loadSurecBilesenleri() {
                if (g_surecListesi.length > 0) return; // Zaten yüklendiyse tekrar çekme
                
                // Elementleri güvenli bir şekilde al
                const selectMenu1 = document.getElementById('sb-admin-surec'); 
                const selectMenu2 = document.getElementById('sb-lokal-surec'); 
                const selectMenu3 = document.getElementById('edit-video-surec-yeni'); 

                if (!selectMenu1 && !selectMenu2 && !selectMenu3) {
                     // Eğer menülerin hiçbiri DOM'da değilse (hata vermemek için) dur.
                    console.warn("DEBUG JS: Süreç menüleri (sb-admin, sb-lokal, edit-video) DOM'da bulunamadı.");
                    return; 
                }

                try {
                    const response = await fetch('/api/seyret_bul/get_surecler');
                    const data = await response.json();
                    if (data.success) {
                        g_surecListesi = data.surecler; // Global değişkene kaydet
                        
                        g_surecListesi.forEach(surec => {
                            const option = `<option value="${surec.kod}" title="${surec.aciklama}">${surec.kod} - ${surec.aciklama.substring(0, 70)}...</option>`;
                            
                            // 1. YouTube Ekleme Menüsü
                            if(selectMenu1) {
                                if(selectMenu1.innerHTML === '<option value="">Kazanım Seçin...</option>') selectMenu1.innerHTML = '';
                                selectMenu1.innerHTML += option;
                            }
                            // 2. Lokal Video Ekleme Menüsü
                            if(selectMenu2) {
                                if(selectMenu2.innerHTML === '<option value="">Kazanım Seçin...</option>') selectMenu2.innerHTML = '';
                                selectMenu2.innerHTML += option;
                            }
                            // 3. Video Düzenleme Menüsü
                            if(selectMenu3) {
                                // Sadece ilk yüklemede varsayılan seçeneği bırakır
                                if(selectMenu3.innerHTML.indexOf('Değiştirme') === -1) {
                                     selectMenu3.innerHTML = '<option value="">Değiştirme (Mevcut kalsın)</option>';
                                }
                                selectMenu3.innerHTML += option;
                            }
                        });
                        
                        // Menülerin varsayılan başlıklarını ayarla (tekrar kontrol eklendi)
                        if(selectMenu1 && selectMenu1.innerHTML === '') selectMenu1.innerHTML = '<option value="">Kazanım Seçin...</option>';
                        if(selectMenu2 && selectMenu2.innerHTML === '') selectMenu2.innerHTML = '<option value="">Kazanım Seçin...</option>';

                    } else {
                        console.error("Süreç bileşenleri API'den alınamadı:", data.hata);
                    }
                } catch (error) { 
                    console.error("Süreç bileşenleri yüklenemedi:", error); 
                }
            }

            // YARDIMCI: Mevcut videoları API'den çeker ve tabloyu doldurur
            const videoListTbody = document.getElementById('video-list-tbody');
            const videoSilMesaj = document.getElementById('videoSilMesaj');
            
            async function loadVideoList() {
                if (!videoListTbody) return;
                videoListTbody.innerHTML = `<tr><td colspan="6" class="p-4 text-center text-gray-500">Video listesi yükleniyor...</td></tr>`;
                videoSilMesaj.textContent = '';
                try {
                    const response = await fetch('/api/seyret-bul/admin/get-all-videos');
                    const data = await response.json();
                    if (data.success && data.videolar.length > 0) {
                        videoListTbody.innerHTML = '';
                        g_videoListesi = data.videolar; // Global listeyi güncelle
                        
                        data.videolar.forEach(video => {
                            const row = document.createElement('tr');
                            row.className = 'border-b hover:bg-gray-50';
                            
                            // Verileri güvenli bir şekilde ekle
                            row.innerHTML = `
                                <td class="p-2 font-semibold">${video.baslik || ''}</td>
                                <td class="p-2">${video.surec_bileseni || ''}</td>
                                <td class="p-2 text-xs truncate" style="max-width: 150px;" title="${video.url || ''}">${video.url || ''}</td>
                                <td class="p-2 text-center">${video.sorular ? video.sorular.length : 0}</td>
                                <td class="p-2 text-xs">${video.video_id}</td>
                                <td class="p-2 space-x-2"></td>`; // 6. index (İşlemler)
                            
                            videoListTbody.appendChild(row); // Önce satırı tabloya ekle
                            
                            // --- BUTONLARI OLUŞTURMA VE EKLEME ---
                            const actionCell = row.cells[5]; // 6. hücreyi (İşlemler) seç
                            
                            // 1. Düzenle Butonu
                            const editBtn = document.createElement('button');
                            editBtn.textContent = 'Düzenle';
                            editBtn.className = 'text-blue-500 hover:underline text-xs';
                            editBtn.onclick = () => { // Güvenli onclick ataması
                                editVideo(video.video_id);
                            };
                            
                            // 2. Sil Butonu
                            const deleteBtn = document.createElement('button');
                            deleteBtn.textContent = 'Sil';
                            deleteBtn.className = 'text-red-500 hover:underline text-xs';
                            deleteBtn.onclick = () => { // Güvenli onclick ataması
                                deleteVideo(video.video_id, video.baslik);
                            };

                            // Butonları hücreye ekle
                            actionCell.appendChild(editBtn);
                            actionCell.appendChild(deleteBtn);
                            
                        });
                    } else {
                        videoListTbody.innerHTML = `<tr><td colspan="6" class="p-4 text-center text-gray-500">Kayıtlı video bulunamadı.</td></tr>`;
                    }
                } catch (error) { console.error("Video listesi yüklenemedi:", error); }
            }
            
            // "Listeyi Yenile" butonuna işlev ekle
            const refreshVideoListBtn = document.getElementById('refreshVideoListBtn');
            if (refreshVideoListBtn) {
                refreshVideoListBtn.addEventListener('click', loadVideoList);
            }

            // Sekme değiştirildiğinde doğru verileri yükle
            window.showAdminTab = function(tabName) {
                document.querySelectorAll('.admin-tab').forEach(tab => tab.classList.remove('active'));
                document.querySelectorAll('.admin-tab-content').forEach(content => content.style.display = 'none');
                document.getElementById('tab-' + tabName).classList.add('active');
                document.getElementById('content-' + tabName).style.display = 'block';
                
                if (tabName === 'seyret-bul' || tabName === 'seyret-bul-lokal' || tabName === 'video-sil') {
                    loadSurecBilesenleri();
                }
                if (tabName === 'video-sil') {
                    loadVideoList();
                }
                // --- YENİ EKLENDİ ---
                if (tabName === 'video-istekleri') {
                    loadVideoIstekleri();
                }
                // --- BİTTİ ---
            }

            // LOKAL VİDEO YÜKLEME FORMU
            const lokalVideoForm = document.getElementById('seyret-bul-form-lokal');
            const lokalVideoMesaj = document.getElementById('sb-lokal-mesaj');
            const lokalVideoBtn = document.getElementById('sb-lokal-gonder-btn');
            
            if (lokalVideoForm) {
                lokalVideoForm.addEventListener('submit', async (e) => {
                    e.preventDefault();
                    lokalVideoBtn.disabled = true;
                    lokalVideoMesaj.textContent = 'Video yükleniyor ve sorular üretiliyor... Bu işlem videonun boyutuna göre 1-2 dakika sürebilir...';
                    lokalVideoMesaj.style.color = 'blue';
                    const formData = new FormData();
                    formData.append('baslik', document.getElementById('sb-lokal-baslik').value);
                    formData.append('video_dosya', document.getElementById('sb-lokal-dosya').files[0]);
                    formData.append('surec_bileseni', document.getElementById('sb-lokal-surec').value);
                    formData.append('video_metni', document.getElementById('sb-lokal-metin').value);
                    formData.append('admin_sifre', document.getElementById('sb-lokal-sifre').value);
                    try {
                        const response = await fetch('/api/seyret-bul/admin/lokal-video-yukle', { method: 'POST', body: formData });
                        const result = await response.json();
                        if (result.success) {
                            lokalVideoMesaj.textContent = `Başarılı! Video eklendi: ${result.video_id}`;
                            lokalVideoMesaj.style.color = 'green';
                            lokalVideoForm.reset();
                        } else {
                            lokalVideoMesaj.textContent = `Hata: ${result.mesaj}`;
                            lokalVideoMesaj.style.color = 'red';
                        }
                    } catch (error) {
                        lokalVideoMesaj.textContent = `Sunucu hatası: ${error}`;
                        lokalVideoMesaj.style.color = 'red';
                    } finally {
                        lokalVideoBtn.disabled = false;
                    }
                });
            }

            // YOUTUBE VİDEO EKLEME FORMU
            const youtubeVideoForm = document.getElementById('seyret-bul-form-admin');
            const youtubeVideoMesaj = document.getElementById('sb-admin-mesaj');
            const youtubeVideoBtn = document.getElementById('sb-admin-gonder-btn');
            
            if (youtubeVideoForm) {
                youtubeVideoForm.addEventListener('submit', async (e) => {
                    e.preventDefault();
                    youtubeVideoBtn.disabled = true;
                    youtubeVideoMesaj.textContent = 'Sorular üretiliyor... Bu işlem 30-60 saniye sürebilir...';
                    youtubeVideoMesaj.style.color = 'blue';
                    const data = {
                        baslik: document.getElementById('sb-admin-baslik').value,
                        video_url: document.getElementById('sb-admin-url').value,
                        surec_bileseni: document.getElementById('sb-admin-surec').value,
                        video_metni: document.getElementById('sb-admin-metin').value,
                        admin_sifre: document.getElementById('sb-admin-sifre').value,
                        video_sure_saniye: 0
                    };
                    try {
                        const response = await fetch('/api/seyret-bul/admin/soru-uret', {
                            method: 'POST', headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(data)
                        });
                        const result = await response.json();
                        if (result.success) {
                            youtubeVideoMesaj.textContent = `Başarılı! Video eklendi: ${result.video_id}`;
                            youtubeVideoMesaj.style.color = 'green';
                            youtubeVideoForm.reset();
                        } else {
                            youtubeVideoMesaj.textContent = `Hata: ${result.mesaj}`;
                            youtubeVideoMesaj.style.color = 'red';
                        }
                    } catch (error) {
                        youtubeVideoMesaj.textContent = `Sunucu hatası: ${error}`;
                        youtubeVideoMesaj.style.color = 'red';
                    } finally {
                        youtubeVideoBtn.disabled = false;
                    }
                });
            }
            
            // VİDEO SİLME FONKSİYONU
            window.deleteVideo = async function(videoId, videoBaslik) {
                if (!confirm(`'${videoBaslik}' başlıklı videoyu silmek istediğinizden emin misiniz?`)) return;
                const adminSifre = prompt("Lütfen admin şifresini girin:");
                if (!adminSifre) return;
                videoSilMesaj.textContent = `${videoId} siliniyor...`;
                videoSilMesaj.style.color = 'blue';
                try {
                    const response = await fetch('/api/seyret-bul/admin/sil-video', {
                        method: 'POST', headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ video_id: videoId, admin_sifre: adminSifre })
                    });
                    const result = await response.json();
                    if (result.success) {
                        videoSilMesaj.textContent = `Video başarıyla silindi: ${videoId}`;
                        videoSilMesaj.style.color = 'green';
                        loadVideoList(); // Listeyi yenile
                    } else {
                        videoSilMesaj.textContent = `Hata: ${result.hata}`;
                        videoSilMesaj.style.color = 'red';
                    }
                } catch (error) {
                    videoSilMesaj.textContent = `Sunucu hatası: ${error}`;
                    videoSilMesaj.style.color = 'red';
                }
            }
            // ========== GÜNCELLENDİ: VİDEO İSTEKLERİ YÜKLEME FONKSİYONU (YENİ ROL SÜTUNU) ==========
            async function loadVideoIstekleri() {
                const tbody = document.getElementById('video-istekleri-tbody');
                if (!tbody) return;

                // Colspan 8 olarak güncellendi
                tbody.innerHTML = `<tr><td colspan="8" class="p-4 text-center text-gray-500">İstekler yükleniyor...</td></tr>`;
                
                try {
                    const response = await fetch('/api/get-video-istekleri');
                    const data = await response.json();
                    
                    if (data.success && data.istekler.length > 0) {
                        tbody.innerHTML = ''; // Listeyi temizle
                        data.istekler.forEach(istek => {
                            // Tarihi formatla
                            const tarih = new Date(istek.tarih).toLocaleString('tr-TR', { 
                                day: '2-digit', month: '2-digit', year: 'numeric', 
                                hour: '2-digit', minute: '2-digit' 
                            });
                            
                            // --- GÜNCELLENDİ (İsteğiniz): Verileri ayır ---
                            const gonderen = `${istek.ogretmen || 'Bilinmiyor'}`;
                            const okul = istek.okul || '---';
                            
                            // Rolü çevir (student -> Öğrenci)
                            let rol = '---';
                            if (istek.rol === 'student') rol = 'Öğrenci';
                            else if (istek.rol === 'teacher') rol = 'Öğretmen';
                            else if (istek.rol === 'admin') rol = 'Yönetici';
                            else if (istek.rol) rol = istek.rol;
                            
                            // Sınıf/No
                            let sinifVeyaNo = '---';
                            if (istek.rol === 'student') {
                                sinifVeyaNo = `${istek.sinif || 'Sınıfsız'} / ${istek.no || 'No Yok'}`;
                            } else if (istek.rol === 'teacher') {
                                sinifVeyaNo = `Sorumlu Sınıf: ${istek.sinif || 'Yok'}`;
                            }
                            // --- BİTTİ ---

                            const row = `
                                <tr class="border-b hover:bg-gray-50">
                                    <td class="p-3 text-gray-700">${tarih}</td>
                                    <td class="p-3 font-semibold">${gonderen}</td>
                                    <td class="p-3 text-gray-700 font-medium">${rol}</td> <td class="p-3 text-gray-700">${okul}</td>
                                    <td class="p-3 text-gray-700">${sinifVeyaNo}</td>
                                    <td class="p-3 text-gray-800" style="white-space: pre-wrap; word-break: break-word;">${istek.metin}</td>
                                    <td class="p-3 text-blue-600 font-semibold">${istek.durum || 'Yeni'}</td>
                                    <td class="p-3">
                                        <button onclick="deleteVideoIstek('${istek.id}')" class="text-red-500 hover:underline text-xs font-semibold">
                                            Sil
                                        </button>
                                    </td>
                                </tr>`;
                            tbody.innerHTML += row;
                        });
                    } else if (data.success && data.istekler.length === 0) {
                        // Colspan 8 olarak güncellendi
                        tbody.innerHTML = `<tr><td colspan="8" class="p-4 text-center text-gray-500">Gösterilecek video isteği bulunamadı.</td></tr>`;
                    } else {
                        // Colspan 8 olarak güncellendi
                        tbody.innerHTML = `<tr><td colspan="8" class="p-4 text-center text-red-500">İstekler yüklenemedi: ${data.hata}</td></tr>`;
                    }
                } catch (error) {
                    console.error("Video istekleri yüklenemedi:", error);
                    // Colspan 8 olarak güncellendi
                    tbody.innerHTML = `<tr><td colspan="8" class="p-4 text-center text-red-500">Sunucu hatası: ${error.message}</td></tr>`;
                }
            }
            // ========== BİTTİ ==========

            // ========== YENİ EKLENDİ: VİDEO İSTEĞİ SİLME FONKSİYONU (3. İsteğiniz) ==========
            window.deleteVideoIstek = async function(istekId) {
                if (!istekId) {
                    alert('Hata: Silinecek istek IDsi bulunamadı.');
                    return;
                }
                
                if (!confirm('Bu video isteğini kalıcı olarak silmek istediğinizden emin misiniz?')) {
                    return;
                }

                try {
                    const response = await fetch('/api/delete-video-istek', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ istek_id: istekId })
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        alert('İstek başarıyla silindi.');
                        loadVideoIstekleri(); // Listeyi yenile
                    } else {
                        alert(`Hata: ${result.hata || 'Bilinmeyen bir sorun oluştu.'}`);
                    }
                } catch (error) {
                    alert(`Sunucu hatası: ${error.message}`);
                }
            }
            // ========== BİTTİ ==========
            // ========== MODAL ELEMENTLERİNİ TANIMLA ==========
            const editModal = document.getElementById('edit-video-modal');
            const editForm = document.getElementById('edit-video-form');
            const editVideoId = document.getElementById('edit-video-id');
            const editVideoBaslik = document.getElementById('edit-video-baslik');
            const editVideoSurecMevcut = document.getElementById('edit-video-surec-mevcut');
            const editVideoSurecYeni = document.getElementById('edit-video-surec-yeni');
            const editVideoMesaj = document.getElementById('edit-video-mesaj');
            
            
            // Düzenle butonuna tıklanınca çalışacak fonksiyon
            window.editVideo = function(videoId) {
                console.log("✏️ Video düzenleme açılıyor:", videoId);
                
                if (!editModal) {
                    console.error("❌ Modal bulunamadı!");
                    alert("Modal açılamadı. Sayfayı yenileyin.");
                    return;
                }
                
                // Videoyu global listeden bul
                const videoObject = g_videoListesi.find(v => v.video_id === videoId);
                if (!videoObject) {
                    alert('Hata: Video verisi bulunamadı.');
                    return;
                }
                
                // Önce süreç listesini yükle (yoksa)
                if (g_surecListesi.length === 0) {
                    loadSurecBilesenleri();
                }
                
                // Formu doldur
                editVideoId.value = videoObject.video_id;
                editVideoBaslik.value = videoObject.baslik;
                
                // Mevcut süreci göster
                const mevcutSurecKod = videoObject.surec_bileseni;
                const mevcutSurec = g_surecListesi.find(s => s.kod === mevcutSurecKod); 
                
                editVideoSurecMevcut.value = mevcutSurec ? `${mevcutSurec.kod} - ${mevcutSurec.aciklama.substring(0,40)}...` : mevcutSurecKod;
                
                editVideoSurecYeni.value = "";
                editVideoMesaj.textContent = "";
                
                // Pop-up'ı aç
                editModal.style.display = 'flex';
                console.log("✅ Modal açıldı");
            }
            
            
            // Modal kapatma butonu
            const editModalCloseBtn = editModal?.querySelector('.modal-close-btn');
            if(editModalCloseBtn) {
                editModalCloseBtn.addEventListener('click', () => {
                    editModal.style.display = 'none';
                });
            }
            
            // Modal dışına tıklayarak kapatma
            if (editModal) {
                editModal.addEventListener('click', (e) => {
                    if (e.target === editModal) {
                        editModal.style.display = 'none';
                    }
                });
            }
            
            // Düzenleme Formunu Gönderme
            if (editForm) {
                editForm.addEventListener('submit', async (e) => {
                    e.preventDefault();
                    editVideoMesaj.textContent = "Kaydediliyor...";
                    editVideoMesaj.style.color = 'blue';

                    const data = {
                        video_id: editVideoId.value,
                        yeni_baslik: editVideoBaslik.value,
                        yeni_surec: editVideoSurecYeni.value || ''
                    };

                    try {
                        const response = await fetch('/api/seyret-bul/admin/edit-video', {
                            method: 'POST', 
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(data)
                        });
                        const result = await response.json();
                        if (result.success) {
                            editVideoMesaj.textContent = "Başarıyla güncellendi!";
                            editVideoMesaj.style.color = 'green';
                            loadVideoList();
                            setTimeout(() => { 
                                editModal.style.display = 'none'; 
                            }, 1000);
                        } else {
                            editVideoMesaj.textContent = `Hata: ${result.hata || result.mesaj || 'Bilinmeyen hata'}`;
                            editVideoMesaj.style.color = 'red';
                        }
                    } catch (error) {
                        editVideoMesaj.textContent = `Sunucu hatası: ${error}`;
                        editVideoMesaj.style.color = 'red';
                    }
                });
            }
            
            // ... (Dosyanızdaki diğer tüm admin panel JS kodları (Excel, Video vb.)
            // buraya kopyalanmalı, ancak değişiklik gerektirmiyorlar.)
            // (Bu kodlar sizde zaten olduğu ve değişmediği için eklemiyorum, 
            // sadece loadStudentList ve deleteUser güncellendi)

        }); // DOMContentLoaded Bitişi
    </script>
</body>
</html>
"""
# --- GİRİŞ/KAYIT HTML KODU BİTTİ ---

# ###############################################################
# --- PANEL (DASHBOARD) SAYFASI ---
# ###############################################################
DASHBOARD_HTML_CONTENT = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Maarif Model Paneli</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
       body { 
            font-family: 'Inter', sans-serif;
            background-color: #f3f4f6;
        }
        /* YENİ EKLENDİ: macOS "esneme" (bounce) efektini kapat */
        .no-bounce {
            overscroll-behavior: none;
        }
    </style>
</head>
<body class="flex h-screen">
    
    <!-- Sol Dikey Menü -->
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
                <div id="user-avatar-initial" class="w-10 h-10 rounded-full bg-cyan-500 flex items-center justify-center text-white font-bold text-lg">
                    K
                </div>
                <div class="ml-3">
                    <!-- ########## GÜNCELLEME: Sadece Soyisim ########## -->
                    <span id="user-name-placeholder" class="block text-sm font-bold text-gray-800">Kullanıcı</span>
                    <!-- ########## GÜNCELLEME: Dropdown kaldırıldı ########## -->
                </div>
            </div>
        </div>
        
        <nav class="flex-1 overflow-y-auto p-4 space-y-2 no-bounce">

            <a id="link-metin-analiz" href="/metin-analiz" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-blue-500 hover:bg-blue-600 transition-all">
                <i class="fa-solid fa-file-pen mr-3 w-6 text-center"></i>
                <span>Metin Analiz</span>
            </a>
            <a id="link-soru-uretim" href="/soru-uretim" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-green-500 hover:bg-green-600 transition-all">
                <i class="fa-solid fa-circle-question mr-3 w-6 text-center"></i>
                <span>Soru Üretim</span>
            </a>
            <a id="link-metin-olusturma" href="/metin-olusturma" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-purple-500 hover:bg-purple-600 transition-all">
                <i class="fa-solid fa-wand-magic-sparkles mr-3 w-6 text-center"></i>
                <span>Metin Oluşturma</span>
            </a>
            <a id="link-haritada-bul" href="/haritada-bul" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-orange-500 hover:bg-orange-600 transition-all">
                <i class="fa-solid fa-map-location-dot mr-3 w-6 text-center"></i>
                <span>Haritada Bul</span>
            </a>
            <a id="link-podcast" href="/podcast_paneli" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-red-500 hover:bg-red-600 transition-all">
                <i class="fa-solid fa-microphone-lines mr-3 w-6 text-center"></i>
                <span>Podcast Yap</span>
            </a>
            <a id="link-seyret-bul" href="/seyret-bul-liste" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-indigo-500 hover:bg-indigo-600 transition-all">
                <i class="fa-solid fa-magnifying-glass-plus mr-3 w-6 text-center"></i>
                <span>Seyret Bul</span>
            </a>
            <a id="link-yarisma" href="/yarisma-secim" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-teal-500 hover:bg-teal-600 transition-all">
                <i class="fa-solid fa-trophy mr-3 w-6 text-center"></i>
                <span>Beceri/Değer Avcısı</span>
            </a>
            <a id="link-video-istegi" href="/video-istegi" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-pink-500 hover:bg-pink-600 transition-all">
                <i class="fa-solid fa-video mr-3 w-6 text-center"></i>
                <span>Video İsteği</span>
            </a>

        </nav>
        
        <!-- Çıkış Butonu -->
        <div class="p-4 border-t border-gray-200">
            <a href="/" class="flex items-center w-full p-3 rounded-lg text-red-600 font-semibold bg-gray-100 hover:bg-red-100 hover:text-red-700 transition-all">
                <i class="fa-solid fa-right-from-bracket mr-3 w-6 text-center"></i>
                <span>Çıkış</span>
            </a>
        </div>
    </aside>

    <!-- Ana İçerik Alanı -->
    <main class="ml-72 flex-1 p-6 md:p-8 overflow-y-auto no-bounce">
        
        <div class="bg-white p-6 rounded-lg shadow">
            <h2 class="text-3xl font-bold text-gray-800">Hoş Geldiniz!</h2>
            <p class="text-gray-600 mt-2">
                Lütfen sol menüden bir araç seçerek başlayın.
            </p>
        </div>

    </main>
    
    <script>
        document.addEventListener('DOMContentLoaded', () => {
            // 1. Kullanıcı Bilgilerini Yükle
            const userFullName = localStorage.getItem('loggedInUserName'); 
            const userRole = localStorage.getItem('loggedInUserRole'); 
            const userNo = localStorage.getItem('loggedInUserNo');
            const userSchool = localStorage.getItem('loggedInUserSchool');
            const userClass = localStorage.getItem('loggedInUserClass');

            // 2. İsim ve Avatarı Ayarla
            if (userFullName) {
                const namePlaceholder = document.getElementById('user-name-placeholder');
                const avatarInitial = document.getElementById('user-avatar-initial');
                if (namePlaceholder) namePlaceholder.textContent = userFullName;
                if (avatarInitial) avatarInitial.textContent = userFullName[0] ? userFullName[0].toUpperCase() : 'K';
            }

            // 3. Menü Rol Kontrolü (Öğretmen/Öğrenci Farkı)
            const linkMetinAnaliz = document.getElementById('link-metin-analiz');
            const linkSoruUretim = document.getElementById('link-soru-uretim');
            const linkMetinOlusturma = document.getElementById('link-metin-olusturma');
            const linkHaritadaBul = document.getElementById('link-haritada-bul');
            const linkPodcast = document.getElementById('link-podcast');
            const linkSeyretBul = document.getElementById('link-seyret-bul');
            const linkYarisma = document.getElementById('link-yarisma');
            const linkVideoIstegi = document.getElementById('link-video-istegi');

            if (userRole === 'teacher') {
                // ÖĞRETMEN: Öğrenci araçlarını gizle
                if (linkMetinAnaliz) linkMetinAnaliz.style.display = 'none';
                if (linkSeyretBul) linkSeyretBul.style.display = 'none';
                if (linkHaritadaBul) linkHaritadaBul.style.display = 'none'; 
                
                // Ekstra butonlar varsa gizle
                const btnBireyselYarisma = document.getElementById('btn-bireysel-yarisma');
                if (btnBireyselYarisma) btnBireyselYarisma.style.display = 'none'; 
                const btnBireyselSonuclar = document.getElementById('btn-bireysel-sonuclar');
                if (btnBireyselSonuclar) btnBireyselSonuclar.style.display = 'none';

            } else {
                // ÖĞRENCİ: Öğretmen araçlarını gizle
                if (linkMetinOlusturma) linkMetinOlusturma.style.display = 'none';
                
                const btnTakimYarisma = document.getElementById('btn-takim-yarisma');
                if (btnTakimYarisma) btnTakimYarisma.style.display = 'none';

                // ============================================================
                // 👇👇👇 GİRİŞ ANINDA PING VE OTO-GİRİŞ SİSTEMİ 👇👇👇
                // ============================================================
                if (userNo) {
                    
                    // A. PING AT (Öğretmen beni yeşil görsün)
                    function sendPing() {
                        fetch('/api/ping', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ student_no: userNo })
                        }).catch(err => console.error("Ping hatası:", err));
                    }

                    // B. OYUN KONTROL ET (Başlamış oyun varsa ışınlan)
                    function checkForGame() {
                        if (!userSchool || !userClass) return;
                        
                        fetch('/api/check_for_game', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ okul: userSchool, sinif: userClass })
                        })
                        .then(res => res.json())
                        .then(data => {
                            if (data.found && data.yarisma_id) {
                                console.log("🟢 OYUN BULUNDU! Yönlendiriliyor...");
                                window.location.href = `/takim-oyun-ekrani/${data.yarisma_id}`;
                            }
                        })
                        .catch(err => console.error("Oyun kontrol hatası:", err));
                    }

                    // Sisteme girer girmez başlat
                    sendPing();
                    checkForGame();
                    
                    // Arka planda devam et (3 saniyede bir)
                    setInterval(() => {
                        sendPing();
                        checkForGame();
                    }, 3000);
                }
                // ============================================================
            }
        });
    </script>

</body>
</html>
"""
# --- PANEL HTML KODU BİTTİ ---

# ########## YENİ EKLENDİ (Daha önce silinmişti): METİN ÜRETİM SAYFASI HTML ##########
METIN_URETIM_PAGE_HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Metin Üretim Aracı</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        body { 
            font-family: 'Inter', sans-serif;
            background-color: #f3f4f6;
        }
        .spinner {
            border: 4px solid rgba(0, 0, 0, .1);
            border-left-color: #a855f7; /* purple-500 */
            border-radius: 50%;
            width: 24px;
            height: 24px;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        select:disabled {
            background-color: #f3f4f6;
            cursor: not-allowed;
        }
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

        <nav class="flex-1 overflow-y-auto p-4 space-y-2 no-bounce">

            <a id="link-metin-analiz" href="/metin-analiz" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-blue-500 hover:bg-blue-600 transition-all">
                <i class="fa-solid fa-file-pen mr-3 w-6 text-center"></i>
                <span>Metin Analiz</span>
            </a>
            <a id="link-soru-uretim" href="/soru-uretim" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-green-500 hover:bg-green-600 transition-all">
                <i class="fa-solid fa-circle-question mr-3 w-6 text-center"></i>
                <span>Soru Üretim</span>
            </a>
            <a id="link-metin-olusturma" href="/metin-olusturma" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-purple-600 ring-2 ring-purple-300 transition-all">
                <i class="fa-solid fa-wand-magic-sparkles mr-3 w-6 text-center"></i>
                <span>Metin Oluşturma</span>
            </a>
            <a id="link-haritada-bul" href="/haritada-bul" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-orange-500 hover:bg-orange-600 transition-all">
                <i class="fa-solid fa-map-location-dot mr-3 w-6 text-center"></i>
                <span>Haritada Bul</span>
            </a>
            <a id="link-podcast" href="/podcast_paneli" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-red-500 hover:bg-red-600 transition-all">
                <i class="fa-solid fa-microphone-lines mr-3 w-6 text-center"></i>
                <span>Podcast Yap</span>
            </a>
            <a id="link-seyret-bul" href="/seyret-bul-liste" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-indigo-500 hover:bg-indigo-600 transition-all">
                <i class="fa-solid fa-magnifying-glass-plus mr-3 w-6 text-center"></i>
                <span>Seyret Bul</span>
            </a>
            <a id="link-yarisma" href="/yarisma-secim" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-teal-500 hover:bg-teal-600 transition-all">
                <i class="fa-solid fa-trophy mr-3 w-6 text-center"></i>
                <span>Beceri/Değer Avcısı</span>
            </a>
            <a id="link-video-istegi" href="/video-istegi" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-pink-500 hover:bg-pink-600 transition-all">
                <i class="fa-solid fa-video mr-3 w-6 text-center"></i>
                <span>Video İsteği</span>
            </a>

        </nav>

        <div class="p-4 border-t border-gray-200">
            <a href="/dashboard" class="flex items-center w-full p-3 rounded-lg text-gray-600 font-semibold bg-gray-100 hover:bg-gray-200 transition-all">
                <i class="fa-solid fa-arrow-left mr-3 w-6 text-center"></i>
                <span>Panele Geri Dön</span>
            </a>
        </div>
    </aside>

    <main class="ml-72 flex-1 p-6 md:p-8 overflow-y-auto no-bounce">
        <h2 class="text-3xl font-bold text-gray-800 mb-6">Metin Üretim Aracı</h2>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">

            <div class="lg:col-span-1 bg-white p-6 rounded-lg shadow">
                <form id="metin-form">

                    <div class="mb-4">
                        <label for="bilesen-kodu" class="block text-sm font-medium text-gray-700 mb-1">Süreç Bileşeni</label>
                        <select id="bilesen-kodu" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white" required>
                            <option value="">Lütfen bir süreç bileşeni seçin...</option>
                            </select>
                    </div>

                    <div class="mb-4">
                        <label for="metin-tipi" class="block text-sm font-medium text-gray-700 mb-1">Metin Tipi</label>
                        <select id="metin-tipi" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white" required disabled>
                            <option value="">Önce Süreç Bileşeni Seçin...</option>
                            </select>
                    </div>

                    <button type="submit" id="generate-btn" class="w-full bg-purple-500 text-white font-bold py-3 px-6 rounded-lg text-lg shadow-lg hover:bg-purple-600 transition-all duration-300 flex items-center justify-center">
                        <i class="fa-solid fa-wand-magic-sparkles mr-2"></i>
                        <span>Metin Üret</span>
                    </button>
                    <div id="loading-spinner" class="hidden flex items-center justify-center w-full bg-purple-300 text-purple-800 font-bold py-3 px-6 rounded-lg text-lg">
                        <div class="spinner mr-3"></div>
                        <span>Üretiliyor...</span>
                    </div>
                </form>
            </div>

            <div class="lg:col-span-2 bg-white p-6 rounded-lg shadow">
                <div class="flex justify-between items-center mb-4">
                    <h3 class="text-xl font-semibold text-gray-800">Üretilen Metin</h3>
                    <div class="flex space-x-2">
                        <button id="copy-btn" title="Metni kopyala" class="text-gray-500 hover:text-blue-600"><i class="fa-solid fa-copy"></i></button>
                        <button id="save-btn" title="Metni kaydet (.txt)" class="text-gray-500 hover:text-green-600"><i class="fa-solid fa-save"></i></button>
                    </div>
                </div>

                <div id="result-message" class="mb-4"></div>

                <textarea id="result-text" class="w-full h-96 p-4 border border-gray-200 rounded-lg bg-gray-50 overflow-y-auto text-gray-700" placeholder="Üretilen metin burada görünecektir..."></textarea>

                <div class="text-sm text-gray-600 mt-2 flex justify-between">
                    <span>Kelime Sayısı: <span id="word-count" class="font-bold">0</span></span>
                    <span id="word-warning" class="text-yellow-600 font-semibold"></span>
                </div>
            </div>

        </div>
    </main>

    <script>
        // Python'dan gelen ana veri yapısı (metin_uretim.PROMPT_SABLONLARI)
        const promptSablonlari = {{ prompt_sablonlari | tojson }};

        // DOM Elementleri
        const bilesenSelect = document.getElementById('bilesen-kodu');
        const metinTipiSelect = document.getElementById('metin-tipi');

        const metinForm = document.getElementById('metin-form');
        const generateBtn = document.getElementById('generate-btn');
        const loadingSpinner = document.getElementById('loading-spinner');
        const resultText = document.getElementById('result-text');
        const resultMessage = document.getElementById('result-message');

        const wordCountSpan = document.getElementById('word-count');
        const wordWarningSpan = document.getElementById('word-warning');
        const copyBtn = document.getElementById('copy-btn');
        const saveBtn = document.getElementById('save-btn');

        document.addEventListener('DOMContentLoaded', () => {
            // --- Kullanıcı Adı Yükleme ---
            const userFullName = localStorage.getItem('loggedInUserName');
            const userRole = localStorage.getItem('loggedInUserRole'); // Rolü al

            if (userFullName) {
                document.getElementById('user-name-placeholder').textContent = userFullName;
                document.getElementById('user-avatar-initial').textContent = userFullName[0] ? userFullName[0].toUpperCase() : 'K';
            }
            
            // --- YENİ EKLENDİ: ROL KONTROLÜ ---
            const linkMetinAnaliz = document.getElementById('link-metin-analiz');
            const linkSoruUretim = document.getElementById('link-soru-uretim');
            const linkMetinOlusturma = document.getElementById('link-metin-olusturma');
            const linkHaritadaBul = document.getElementById('link-haritada-bul');
            const linkPodcast = document.getElementById('link-podcast');
            const linkSeyretBul = document.getElementById('link-seyret-bul');
            const linkYarisma = document.getElementById('link-yarisma');
            const linkVideoIstegi = document.getElementById('link-video-istegi');

            if (userRole === 'teacher') {
                // --- ÖĞRETMEN GÖRÜNÜMÜ ---
                // Öğrenci butonlarını gizle
                if (linkMetinAnaliz) linkMetinAnaliz.style.display = 'none';
                if (linkSeyretBul) linkSeyretBul.style.display = 'none';
                if (linkHaritadaBul) linkHaritadaBul.style.display = 'none'; 
                
                // Öğretmen butonları görünür kalsın (Zaten varsayılan 'flex')

            } else {
                // --- ÖĞRENCİ GÖRÜNÜMÜ ---
                // Öğretmen butonlarını gizle
                if (linkMetinOlusturma) linkMetinOlusturma.style.display = 'none';
                if (linkVideoIstegi) linkVideoIstegi.style.display = 'none';
            }
            // --- ROL KONTROLÜ BİTTİ ---


            // 1. Süreç Bileşeni Menüsünü Doldur
            for (const kod in promptSablonlari) {
                const data = promptSablonlari[kod];
                const option = document.createElement('option');
                option.value = kod;
                const kisaAciklama = data.aciklama.substring(0, 60) + '...';
                option.textContent = `${kod} - ${kisaAciklama}`;
                option.title = data.aciklama; // Tam açıklamayı başlık olarak ekle
                bilesenSelect.appendChild(option);
            }

            // 2. Süreç Bileşeni değiştiğinde Metin Tipi menüsünü güncelle
            bilesenSelect.addEventListener('change', () => {
                const selectedBilesenKodu = bilesenSelect.value;

                metinTipiSelect.innerHTML = '<option value="">Lütfen bir metin tipi seçin...</option>';

                if (selectedBilesenKodu && promptSablonlari[selectedBilesenKodu]) {
                    const metinTipleri = promptSablonlari[selectedBilesenKodu].metin_tipleri;

                    for (const tipAdi in metinTipleri) {
                        const option = document.createElement('option');
                        option.value = tipAdi;
                        option.textContent = tipAdi;
                        metinTipiSelect.appendChild(option);
                    }
                    metinTipiSelect.disabled = false;
                } else {
                    metinTipiSelect.disabled = true;
                    metinTipiSelect.innerHTML = '<option value="">Önce Süreç Bileşeni Seçin...</option>';
                }
            });

            // 3. Form Gönderme (Fetch API)
            metinForm.addEventListener('submit', async (e) => {
                e.preventDefault();

                const bilesenKodu = bilesenSelect.value;
                const metinTipiAdi = metinTipiSelect.value;

                console.log("Metin üretme isteği:", { bilesenKodu, metinTipiAdi });

                generateBtn.style.display = 'none';
                loadingSpinner.style.display = 'flex';
                resultText.value = 'Metniniz Üretiliyor, bu işlem biraz zaman alabilir...';
                resultMessage.innerHTML = '';

                try {
                    const response = await fetch('/api/generate-text', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            bilesen_kodu: bilesenKodu,
                            metin_tipi_adi: metinTipiAdi
                        })
                    });

                    const result = await response.json();

                    if (result.success) {
                        resultText.value = result.metin;
                        wordCountSpan.textContent = result.kelime_sayisi;
                        wordWarningSpan.textContent = result.uyari;
                        if(result.uyari) wordWarningSpan.classList.add('font-bold');
                        else wordWarningSpan.classList.remove('font-bold');

                        resultMessage.innerHTML = `<div class="p-3 rounded-lg bg-green-100 text-green-800 text-sm">Metin başarıyla üretildi.</div>`;
                    } else {
                        resultText.value = '';
                        wordCountSpan.textContent = 0;
                        wordWarningSpan.textContent = '';
                        resultMessage.innerHTML = `<div class="p-3 rounded-lg bg-red-100 text-red-800 text-sm">Hata: ${result.metin}</div>`;
                    }

                } catch (error) {
                    console.error("Metin üretme hatası:", error);
                    resultText.value = '';
                    wordCountSpan.textContent = 0;
                    wordWarningSpan.textContent = '';
                    resultMessage.innerHTML = `<div class="p-3 rounded-lg bg-red-100 text-red-800 text-sm">Sunucuyla iletişim kurulamadı: Failed to fetch. API anahtarınızı kontrol edin.</div>`;
                } finally {
                    generateBtn.style.display = 'flex';
                    loadingSpinner.style.display = 'none';
                }
            });

            // 4. Yardımcı Butonlar (Kopyala, Kaydet)
            copyBtn.addEventListener('click', () => {
                resultText.select();
                document.execCommand('copy');
                resultMessage.innerHTML = `<div class="p-3 rounded-lg bg-blue-100 text-blue-800 text-sm">Metin panoya kopyalandı!</div>`;
                setTimeout(() => resultMessage.innerHTML = '', 2000);
            });

            saveBtn.addEventListener('click', () => {
                const text = resultText.value;
                const blob = new Blob([text], { type: 'text/plain' });
                const a = document.createElement('a');
                a.href = URL.createObjectURL(blob);
                a.download = 'uretilen_metin.txt';
                a.click();
            });
        });
    </script>
</body>
</html>
"""

# ########## METİN ANALİZ HTML KODU BİTTİ ##########

# --- METİN ÜRETİM HTML KODU BİTTİ ---
# ########## YENİ EKLENDİ: METİN ANALİZ SAYFASI HTML ##########
METIN_ANALIZ_PAGE_HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Metin Analiz Aracı</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        body { 
            font-family: 'Inter', sans-serif;
            background-color: #f3f4f6;
        }
        .spinner {
            border: 4px solid rgba(0, 0, 0, .1);
            border-left-color: #3b82f6;
            border-radius: 50%;
            width: 24px;
            height: 24px;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        /* Analiz sonucu etiketleri */
        .tag {
            display: inline-block;
            background-color: #e0f2fe; /* light-blue-100 */
            color: #0369a1; /* light-blue-700 */
            padding: 4px 10px;
            border-radius: 9999px;
            font-size: 14px;
            font-weight: 500;
            margin: 2px;
        }
        .tag.deger {
            background-color: #dcfce7; /* green-100 */
            color: #166534; /* green-700 */
        }
        .tag.beceri-kavramsal {
            background-color: #fef3c7; /* yellow-100 */
            color: #92400e; /* yellow-700 */
        }
        .tag.beceri-sosyal {
            background-color: #fce7f3; /* pink-100 */
            color: #9d174d; /* pink-700 */
        }
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

        <nav class="flex-1 overflow-y-auto p-4 space-y-2 no-bounce">>

            <a id="link-metin-analiz" href="/metin-analiz" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-blue-600 ring-2 ring-blue-300 transition-all">
                <i class="fa-solid fa-file-pen mr-3 w-6 text-center"></i>
                <span>Metin Analiz</span>
            </a>
            <a id="link-soru-uretim" href="/soru-uretim" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-green-500 hover:bg-green-600 transition-all">
                <i class="fa-solid fa-circle-question mr-3 w-6 text-center"></i>
                <span>Soru Üretim</span>
            </a>
            <a id="link-metin-olusturma" href="/metin-olusturma" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-purple-500 hover:bg-purple-600 transition-all">
                <i class="fa-solid fa-wand-magic-sparkles mr-3 w-6 text-center"></i>
                <span>Metin Oluşturma</span>
            </a>
            <a id="link-haritada-bul" href="/haritada-bul" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-orange-500 hover:bg-orange-600 transition-all">
                <i class="fa-solid fa-map-location-dot mr-3 w-6 text-center"></i>
                <span>Haritada Bul</span>
            </a>
            <a id="link-podcast" href="/podcast_paneli" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-red-500 hover:bg-red-600 transition-all">
                <i class="fa-solid fa-microphone-lines mr-3 w-6 text-center"></i>
                <span>Podcast Yap</span>
            </a>
            <a id="link-seyret-bul" href="/seyret-bul-liste" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-indigo-500 hover:bg-indigo-600 transition-all">
                <i class="fa-solid fa-magnifying-glass-plus mr-3 w-6 text-center"></i>
                <span>Seyret Bul</span>
            </a>
            <a id="link-yarisma" href="/yarisma-secim" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-teal-500 hover:bg-teal-600 transition-all">
                <i class="fa-solid fa-trophy mr-3 w-6 text-center"></i>
                <span>Beceri/Değer Avcısı</span>
            </a>
            <a id="link-video-istegi" href="/video-istegi" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-pink-500 hover:bg-pink-600 transition-all">
                <i class="fa-solid fa-video mr-3 w-6 text-center"></i>
                <span>Video İsteği</span>
            </a>

        </nav>

        <div class="p-4 border-t border-gray-200">
            <a href="/dashboard" class="flex items-center w-full p-3 rounded-lg text-gray-600 font-semibold bg-gray-100 hover:bg-gray-200 transition-all">
                <i class="fa-solid fa-arrow-left mr-3 w-6 text-center"></i>
                <span>Panele Geri Dön</span>
            </a>
        </div>
    </aside>

    <main class="ml-72 flex-1 p-6 md:p-8 overflow-y-auto no-bounce">
        <h2 class="text-3xl font-bold text-gray-800 mb-6">Metin Analiz Aracı</h2>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">

            <div class="lg:col-span-1 bg-white p-6 rounded-lg shadow">
                <form id="analiz-form">
                    <label for="text-input" class="block text-sm font-medium text-gray-700 mb-1">Analiz Edilecek Metin (Maksimum 250 kelime)</label>
                    <textarea id="text-input" rows="15" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="Lütfen 5. sınıf seviyesine uygun bir metni buraya yapıştırın..."></textarea>

                    <div id="word-count" class="text-sm text-gray-600 text-right mt-1">0 / 250 kelime</div>

                    <button type="submit" id="analyze-btn" class="w-full mt-4 bg-blue-500 text-white font-bold py-3 px-6 rounded-lg text-lg shadow-lg hover:bg-blue-600 transition-all duration-300 flex items-center justify-center">
                        <i class="fa-solid fa-file-pen mr-2"></i>
                        <span>Analiz Et</span>
                    </button>
                    <div id="loading-spinner" class="hidden flex items-center justify-center w-full mt-4 bg-blue-300 text-blue-800 font-bold py-3 px-6 rounded-lg text-lg">
                        <div class="spinner mr-3"></div>
                        <span>Analiz ediliyor...</span>
                    </div>
                </form>
            </div>

            <div class="lg:col-span-1 bg-white p-6 rounded-lg shadow">
                <h3 class="text-xl font-semibold text-gray-800 mb-4">Analiz Sonuçları</h3>

                <div id="result-message" class="mb-4"></div>

                <div id="result-container" class="hidden space-y-4">

                    <div>
                        <h4 class="font-semibold text-gray-700">Seviye Uygunluğu:</h4>
                        <div id="seviye-badge" class="tag"></div>
                        <p id="seviye-aciklama" class="text-sm text-gray-600 italic mt-1"></p>
                    </div>

                    <div>
                        <h4 class="font-semibold text-gray-700">Önerilen Süreç Bileşenleri:</h4>
                        <div id="surec-listesi"></div>
                    </div>

                    <div>
                        <h4 class="font-semibold text-gray-700">Önerilen Metin Tipi:</h4>
                        <div id="metin-tipi" class="tag"></div>
                    </div>

                    <div>
                        <h4 class="font-semibold text-gray-700">Tespit Edilen Değerler:</h4>
                        <div id="degerler-listesi" class="flex flex-wrap gap-1"></div>
                    </div>

                    <div>
                        <h4 class="font-semibold text-gray-700">Tespit Edilen Beceriler:</h4>
                        <div id="beceriler-alan" class="flex flex-wrap gap-1"></div>
                        <div id="beceriler-kavramsal" class="flex flex-wrap gap-1 mt-1"></div>
                        <div id="beceriler-sosyal" class="flex flex-wrap gap-1 mt-1"></div>
                    </div>

                </div>

                <div id="result-placeholder" class="text-center text-gray-500 p-8">
                    <i class="fa-solid fa-flask text-4xl mb-3"></i>
                    <p>Analiz sonuçları burada görünecektir.</p>
                </div>

            </div>
        </div>
    </main>

    <script>
        document.addEventListener('DOMContentLoaded', () => {
            // --- Kullanıcı Adı Yükleme ---
            const userFullName = localStorage.getItem('loggedInUserName');
            const studentNo = localStorage.getItem('loggedInUserNo'); // Limit sistemi için
            const userRole = localStorage.getItem('loggedInUserRole'); // Rolü al

            if (userFullName) {
                document.getElementById('user-name-placeholder').textContent = userFullName;
                document.getElementById('user-avatar-initial').textContent = userFullName[0] ? userFullName[0].toUpperCase() : 'K';
            }

            // --- YAN MENÜ ROL KONTROLÜ (Düzeltilmiş Versiyon) ---
            // (Bu kod, Adım 4'teki HTML değişikliğini yaptığınızı varsayar,
            // ama yapmadıysanız bile şimdilik bu JS'i ekleyin)
            
            const linkMetinAnaliz = document.getElementById('link-metin-analiz');
            const linkSoruUretim = document.getElementById('link-soru-uretim');
            const linkMetinOlusturma = document.getElementById('link-metin-olusturma');
            const linkHaritadaBul = document.getElementById('link-haritada-bul');
            const linkPodcast = document.getElementById('link-podcast');
            const linkSeyretBul = document.getElementById('link-seyret-bul');
            const linkYarisma = document.getElementById('link-yarisma');
            const linkVideoIstegi = document.getElementById('link-video-istegi');

            if (userRole === 'teacher') {
                // --- ÖĞRETMEN GÖRÜNÜMÜ ---
                // (Öğretmen zaten Metin Analiz'i görmemeli, ama ID'ler 
                // eski kodda (btn-metin-analiz) farklı olabilir, 
                // bu yüzden şimdilik sadece öğrenci tarafını düzeltiyoruz)
                if (linkMetinAnaliz) linkMetinAnaliz.style.display = 'none';
                if (linkSeyretBul) linkSeyretBul.style.display = 'none';
                if (linkHaritadaBul) linkHaritadaBul.style.display = 'none'; 
            } else {
                // --- ÖĞRENCİ GÖRÜNÜMÜ ---
                // Sadece öğretmene özel olan "Metin Oluşturma"yı gizle
                
                // Eski kodda ID 'btn-metin-olusturma' idi, yenisinde 'link-metin-olusturma'
                // Her ikisini de kontrol edelim:
                const btnMetinOlusturma = document.getElementById('btn-metin-olusturma');
                if (linkMetinOlusturma) linkMetinOlusturma.style.display = 'none';
                if (btnMetinOlusturma) btnMetinOlusturma.style.display = 'none';
                
                // ÖNEMLİ: Video İsteği butonu artık gizlenmiyor.
            }
            // --- ROL KONTROLÜ BİTTİ ---


            // --- DOM Elementleri ---
            const analizForm = document.getElementById('analiz-form');
            const analyzeBtn = document.getElementById('analyze-btn');
            const loadingSpinner = document.getElementById('loading-spinner');
            const textInput = document.getElementById('text-input');
            const wordCountDisplay = document.getElementById('word-count');

            const resultMessage = document.getElementById('result-message');
            const resultContainer = document.getElementById('result-container');
            const resultPlaceholder = document.getElementById('result-placeholder');
            
            // ########## YENİ EKLENEN SATIRLAR ##########
            const seviyeBadge = document.getElementById('seviye-badge');
            const seviyeAciklama = document.getElementById('seviye-aciklama');
            const surecListesi = document.getElementById('surec-listesi');
            const metinTipi = document.getElementById('metin-tipi');
            const degerlerListesi = document.getElementById('degerler-listesi');
            const becerilerAlan = document.getElementById('beceriler-alan');
            const becerilerKavramsal = document.getElementById('beceriler-kavramsal');
            const becerilerSosyal = document.getElementById('beceriler-sosyal');

            // Kelime Sayacı
            textInput.addEventListener('input', () => {
                const text = textInput.value;
                const words = text.split(/\\s+/).filter(Boolean).length; 
                wordCountDisplay.textContent = `${words} / 250 kelime`;

                if (words > 250) {
                    wordCountDisplay.classList.add('text-red-600', 'font-bold');
                    analyzeBtn.disabled = true;
                    analyzeBtn.classList.add('opacity-50', 'cursor-not-allowed');
                } else {
                    wordCountDisplay.classList.remove('text-red-600', 'font-bold');
                    analyzeBtn.disabled = false;
                    analyzeBtn.classList.remove('opacity-50', 'cursor-not-allowed');
                }
            });

            // Form Gönderme
            analizForm.addEventListener('submit', async (e) => {
                e.preventDefault();

                const metin = textInput.value.trim();
                if (!metin) {
                    alert("Lütfen bir metin girin.");
                    return;
                }
                if (!studentNo) {
                    alert("Hata: Öğrenci no bulunamadı. Lütfen tekrar giriş yapın.");
                    return;
                }

                analyzeBtn.style.display = 'none';
                loadingSpinner.style.display = 'flex';
                resultMessage.innerHTML = '';
                resultContainer.style.display = 'none';
                resultPlaceholder.style.display = 'block';

                try {
                    const response = await fetch('/api/analyze-text', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            metin: metin,
                            student_no: studentNo
                        })
                    });

                    const result = await response.json();

                    if (result.success) {
                        renderSuccess(result);
                    } else {
                        renderError(result.hata || "Bilinmeyen bir hata oluştu.");
                    }

                } catch (error) {
                    console.error("Metin analiz hatası:", error);
                    renderError("Sunucuyla iletişim kurulamadı: Failed to fetch. API anahtarınızı kontrol edin.");
                } finally {
                    analyzeBtn.style.display = 'flex';
                    loadingSpinner.style.display = 'none';
                }
            });

            function renderError(message) {
                resultPlaceholder.style.display = 'none';
                resultContainer.style.display = 'none';
                resultMessage.innerHTML = `<div class="p-3 rounded-lg bg-red-100 text-red-800 text-sm">${message}</div>`;
            }

            function renderSuccess(data) {
                resultPlaceholder.style.display = 'none';

                // Kalan hak uyarısı...

                // 1. Seviye
                if (data.seviye_uygunluk.durum) {
                    // ARTIK HATA VERMEYECEK ÇÜNKÜ DEĞİŞKENLER TANIMLI
                    seviyeBadge.textContent = `Seviye: ${data.seviye_uygunluk.durum}`;
                    seviyeAciklama.textContent = `Açıklama: ${data.seviye_uygunluk.aciklama || 'Yok'}`;
                    if(data.seviye_uygunluk.durum === 'zor') {
                        seviyeBadge.className = 'tag deger'; // Yeşil yerine kırmızı yapalım
                    } else {
                        seviyeBadge.className = 'tag';
                    }
                }
                // ... (Diğer tüm elemanlar da artık tanımlı olduğu için sorunsuzca çalışacaktır) ...

                resultContainer.style.display = 'block';
          

                // 2. Süreç Bileşenleri
                surecListesi.innerHTML = '';
                if (data.surec_bilesenleri && data.surec_bilesenleri.length > 0) {
                    data.surec_bilesenleri.forEach(s => {
                        surecListesi.innerHTML += `<div class="tag">${s.kod} (%${s.uygunluk_yuzdesi}) - ${s.aciklama}</div>`;
                    });
                } else {
                    surecListesi.innerHTML = '<span class="text-sm text-gray-500">Uygun bileşen bulunamadı.</span>';
                }

                // 3. Metin Tipi
                metinTipi.textContent = data.metin_tipi || 'Belirlenemedi';

                // 4. Değerler
                degerlerListesi.innerHTML = '';
                if (data.degerler && data.degerler.length > 0) {
                    data.degerler.forEach(d => {
                        degerlerListesi.innerHTML += `<span class="tag deger">${d}</span>`;
                    });
                } else {
                    degerlerListesi.innerHTML = '<span class="text-sm text-gray-500">Tespit edilen değer yok.</span>';
                }

                // 5. Beceriler
                becerilerAlan.innerHTML = '';
                becerilerKavramsal.innerHTML = '';
                becerilerSosyal.innerHTML = '';

                if (data.beceriler.alan && data.beceriler.alan.length > 0) {
                    data.beceriler.alan.forEach(b => {
                        becerilerAlan.innerHTML += `<span class="tag">${b}</span>`;
                    });
                }
                if (data.beceriler.kavramsal && data.beceriler.kavramsal.length > 0) {
                    data.beceriler.kavramsal.forEach(b => {
                        becerilerKavramsal.innerHTML += `<span class="tag beceri-kavramsal">${b}</span>`;
                    });
                }
                if (data.beceriler.sosyal_duygusal && data.beceriler.sosyal_duygusal.length > 0) {
                    data.beceriler.sosyal_duygusal.forEach(b => {
                        becerilerSosyal.innerHTML += `<span class="tag beceri-sosyal">${b}</span>`;
                    });
                }

                resultContainer.style.display = 'block';
            }

        });
    </script>
</body>
</html>
"""
# ########## METİN ANALİZ HTML KODU BİTTİ ##########


# ########## YENİ EKLENDİ: SORU ÜRETİM SAYFASI HTML ##########
SORU_URETIM_PAGE_HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Soru Üretim Aracı</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        body { 
            font-family: 'Inter', sans-serif;
            background-color: #f3f4f6;
        }
        .spinner {
            border: 4px solid rgba(0, 0, 0, .1);
            border-left-color: #10b981; /* green-500 */
            border-radius: 50%;
            width: 24px;
            height: 24px;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        select:disabled {
            background-color: #f3f4f6;
            cursor: not-allowed;
            .answer-key {
            color: #2563eb; /* Tailwind blue-600 */
            font-weight: 600; /* Kalın yazı */
        }
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

        <nav class="flex-1 overflow-y-auto p-4 space-y-2 no-bounce">

            <a id="link-metin-analiz" href="/metin-analiz" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-blue-500 hover:bg-blue-600 transition-all">
                <i class="fa-solid fa-file-pen mr-3 w-6 text-center"></i>
                <span>Metin Analiz</span>
            </a>
            <a id="link-soru-uretim" href="/soru-uretim" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-green-600 ring-2 ring-green-300 transition-all">
                <i class="fa-solid fa-circle-question mr-3 w-6 text-center"></i>
                <span>Soru Üretim</span>
            </a>
            <a id="link-metin-olusturma" href="/metin-olusturma" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-purple-500 hover:bg-purple-600 transition-all">
                <i class="fa-solid fa-wand-magic-sparkles mr-3 w-6 text-center"></i>
                <span>Metin Oluşturma</span>
            </a>
            <a id="link-haritada-bul" href="/haritada-bul" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-orange-500 hover:bg-orange-600 transition-all">
                <i class="fa-solid fa-map-location-dot mr-3 w-6 text-center"></i>
                <span>Haritada Bul</span>
            </a>
            <a id="link-podcast" href="/podcast_paneli" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-red-500 hover:bg-red-600 transition-all">
                <i class="fa-solid fa-microphone-lines mr-3 w-6 text-center"></i>
                <span>Podcast Yap</span>
            </a>
            <a id="link-seyret-bul" href="/seyret-bul-liste" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-indigo-500 hover:bg-indigo-600 transition-all">
                <i class="fa-solid fa-magnifying-glass-plus mr-3 w-6 text-center"></i>
                <span>Seyret Bul</span>
            </a>
            <a id="link-yarisma" href="/yarisma-secim" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-teal-500 hover:bg-teal-600 transition-all">
                <i class="fa-solid fa-trophy mr-3 w-6 text-center"></i>
                <span>Beceri/Değer Avcısı</span>
            </a>
            <a id="link-video-istegi" href="/video-istegi" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-pink-500 hover:bg-pink-600 transition-all">
                <i class="fa-solid fa-video mr-3 w-6 text-center"></i>
                <span>Video İsteği</span>
            </a>

        </nav>

        <div class="p-4 border-t border-gray-200">
            <a href="/dashboard" class="flex items-center w-full p-3 rounded-lg text-gray-600 font-semibold bg-gray-100 hover:bg-gray-200 transition-all">
                <i class="fa-solid fa-arrow-left mr-3 w-6 text-center"></i>
                <span>Panele Geri Dön</span>
            </a>
        </div>
    </aside>

    <main class="ml-72 flex-1 p-6 md:p-8 overflow-y-auto no-bounce">
        <h2 class="text-3xl font-bold text-gray-800 mb-6">Soru Üretim Aracı</h2>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">

            <div class="lg:col-span-1 bg-white p-6 rounded-lg shadow">
                <form id="soru-form">

                    <div class="mb-4">
                        <label for="bilesen-kodu" class="block text-sm font-medium text-gray-700 mb-1">Süreç Bileşeni</label>
                        <select id="bilesen-kodu" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 bg-white" required>
                            <option value="">Lütfen bir süreç bileşeni seçin...</option>
                            </select>
                    </div>

                    <div class="mb-4">
                        <label for="soru-tipi" class="block text-sm font-medium text-gray-700 mb-1">Soru Tipi</label>
                        <select id="soru-tipi" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 bg-white" required disabled>
                            <option value="">Önce Süreç Bileşeni Seçin...</option>
                            </select>
                    </div>

                    <button type="submit" id="generate-btn" class="w-full bg-green-500 text-white font-bold py-3 px-6 rounded-lg text-lg shadow-lg hover:bg-green-600 transition-all duration-300 flex items-center justify-center">
                        <i class="fa-solid fa-circle-question mr-2"></i>
                        <span>Soru Üret</span>
                    </button>
                    <div id="loading-spinner" class="hidden flex items-center justify-center w-full bg-green-300 text-green-800 font-bold py-3 px-6 rounded-lg text-lg">
                        <div class="spinner mr-3"></div>
                        <span>Üretiliyor...</span>
                    </div>
                </form>
            </div>

            <div class="lg:col-span-2 bg-white p-6 rounded-lg shadow">
                <div class="flex justify-between items-center mb-4">
                    <h3 class="text-xl font-semibold text-gray-800">Üretilen Soru</h3>
                    <div class="flex space-x-2">
                        <button id="copy-btn" title="Soruyu kopyala" class="text-gray-500 hover:text-blue-600"><i class="fa-solid fa-copy"></i></button>
                    </div>
                </div>

                <div id="result-message" class="mb-4"></div>

                <textarea id="result-text" readonly class="w-full h-96 p-4 border border-gray-200 rounded-lg bg-gray-50 overflow-y-auto text-gray-700" placeholder="Soru üretmek için lütfen soldaki formu doldurun..."></textarea>
                
                <div class="mt-4 border-t pt-4">
                    <button id="show-answer-btn" class="bg-gray-500 text-white font-bold py-2 px-4 rounded-lg hover:bg-gray-600 transition-all" disabled>
                        Cevabı Göster (Puanlama Anahtarı)
                    </button>
                    <div id="rubrik-container" class="mt-3 p-4 border border-gray-200 rounded-lg bg-gray-50 text-gray-800 font-medium hidden">
                        <h4 class="font-bold mb-2">💎 Puanlama Anahtarı (10 Puan Üzerinden)</h4>
                        <p id="rubrik-content" style="white-space: pre-wrap;"></p>
                    </div>
                </div>
                </div>

    <script>
        // Python'dan gelen ana veri yapısı (soru_uretim.SORU_SABLONLARI)
        const soruSablonlari = {{ soru_sablonlari | tojson }};

        document.addEventListener('DOMContentLoaded', () => {
            
            // --- DOM Elementleri ---
            const bilesenSelect = document.getElementById('bilesen-kodu');
            const soruTipiSelect = document.getElementById('soru-tipi');
            const soruForm = document.getElementById('soru-form');
            const generateBtn = document.getElementById('generate-btn');
            const loadingSpinner = document.getElementById('loading-spinner');
            const resultText = document.getElementById('result-text');
            const resultMessage = document.getElementById('result-message');
            const copyBtn = document.getElementById('copy-btn');
            
            // --- Rubrik (Cevap Anahtarı) için YENİ elementler ---
            const showAnswerBtn = document.getElementById('show-answer-btn');
            const rubrikContainer = document.getElementById('rubrik-container');
            const rubrikContent = document.getElementById('rubrik-content');
            let currentRubrik = ''; // API'den gelen rubriği saklamak için

            // --- Kullanıcı Adı ve Rol Yükleme ---
            const userFullName = localStorage.getItem('loggedInUserName');
            const studentNo = localStorage.getItem('loggedInUserNo'); // Limit için
            const userRole = localStorage.getItem('loggedInUserRole'); 

            if (userFullName) {
                document.getElementById('user-name-placeholder').textContent = userFullName;
                document.getElementById('user-avatar-initial').textContent = userFullName[0] ? userFullName[0].toUpperCase() : 'K';
            }
            
            // --- Yan Menü Rol Kontrolü ---
            const linkMetinAnaliz = document.getElementById('link-metin-analiz');
            const linkSoruUretim = document.getElementById('link-soru-uretim');
            const linkMetinOlusturma = document.getElementById('link-metin-olusturma');
            const linkHaritadaBul = document.getElementById('link-haritada-bul');
            const linkPodcast = document.getElementById('link-podcast');
            const linkSeyretBul = document.getElementById('link-seyret-bul');
            const linkYarisma = document.getElementById('link-yarisma');
            const linkVideoIstegi = document.getElementById('link-video-istegi');

            if (userRole === 'teacher') {
                if (linkMetinAnaliz) linkMetinAnaliz.style.display = 'none';
                if (linkSeyretBul) linkSeyretBul.style.display = 'none';
                if (linkHaritadaBul) linkHaritadaBul.style.display = 'none'; 
            } else {
                if (linkMetinOlusturma) linkMetinOlusturma.style.display = 'none';
            }
            // --- Rol Kontrolü Bitti ---

            // 1. Süreç Bileşeni Menüsünü Doldur (Artık çalışacak)
            for (const kod in soruSablonlari) {
                const data = soruSablonlari[kod];
                const option = document.createElement('option');
                option.value = kod;
                const kisaAciklama = data.aciklama.substring(0, 60) + '...';
                option.textContent = `${kod} - ${kisaAciklama}`;
                option.title = data.aciklama; 
                bilesenSelect.appendChild(option);
            }

            // 2. Süreç Bileşeni değiştiğinde Soru Tipi menüsünü güncelle (Artık çalışacak)
            bilesenSelect.addEventListener('change', () => {
                const selectedBilesenKodu = bilesenSelect.value;
                soruTipiSelect.innerHTML = '<option value="">Lütfen bir soru tipi seçin...</option>';

                if (selectedBilesenKodu && soruSablonlari[selectedBilesenKodu]) {
                    const soruTipleri = soruSablonlari[selectedBilesenKodu].soru_tipleri;
                    for (const tipAdi in soruTipleri) {
                        const option = document.createElement('option');
                        option.value = tipAdi;
                        option.textContent = tipAdi;
                        soruTipiSelect.appendChild(option);
                    }
                    
                    const ayirici = document.createElement('option');
                    ayirici.disabled = true;
                    ayirici.textContent = '--- Genel Tipler ---';
                    soruTipiSelect.appendChild(ayirici);

                    const optionMC = document.createElement('option');
                    optionMC.value = "GENEL_COKTAN_SECME"; 
                    optionMC.textContent = "(Genel) Çoktan Seçmeli Soru";
                    soruTipiSelect.appendChild(optionMC);

                    const optionMetin = document.createElement('option');
                    optionMetin.value = "GENEL_METIN_YORUM";
                    optionMetin.textContent = "(Genel) Metne Dayalı Yorum Sorusu";
                    soruTipiSelect.appendChild(optionMetin);

                    soruTipiSelect.disabled = false;
                } else {
                    soruTipiSelect.disabled = true;
                    soruTipiSelect.innerHTML = '<option value="">Önce Süreç Bileşeni Seçin...</option>';
                }
            });
           
            // 3. Form Gönderme (YENİ - Rubrik destekli)
            soruForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const bilesenKodu = bilesenSelect.value;
                const soruTipiAdi = soruTipiSelect.value;
                
                if (!studentNo) {
                    resultMessage.innerHTML = `<div class="p-3 rounded-lg bg-red-100 text-red-800 text-sm">Hata: Kullanıcı ID'si bulunamadı. Lütfen tekrar giriş yapın.</div>`;
                    return;
                }

                generateBtn.style.display = 'none';
                loadingSpinner.style.display = 'flex';
                resultText.value = 'Sorunuz üretiliyor, bu işlem biraz zaman alabilir...'; 
                resultMessage.innerHTML = '';
                rubrikContainer.classList.add('hidden'); // Rubriği gizle
                showAnswerBtn.disabled = true; // Butonu kilitle

                try {
                    const response = await fetch('/api/generate-question', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            bilesen_kodu: bilesenKodu,
                            soru_tipi_adi: soruTipiAdi,
                            student_no: studentNo 
                        })
                    });
                    const result = await response.json();

                    // --- BU BLOK TAMAMEN YENİLENDİ ---
                    if (result.success) {
                        resultText.value = result.metin; // Sadece soruyu göster
                        currentRubrik = result.rubrik_cevap; // Rubriği hafızaya al
                        rubrikContainer.classList.add('hidden'); // Rubriği gizle

                        if (result.is_mcq) {
                            // Soru çoktan seçmeliyse, cevap zaten metnin içinde.
                            showAnswerBtn.disabled = true;
                            showAnswerBtn.textContent = "Cevap metne dahildir";
                        } else {
                            // Soru açık uçluysa, rubrik butonunu aç
                            showAnswerBtn.disabled = false;
                            showAnswerBtn.textContent = "Cevabı Göster (Puanlama Anahtarı)";
                        }
                        
                        resultMessage.innerHTML = `<div class="p-3 rounded-lg bg-green-100 text-green-800 text-sm">Soru başarıyla üretildi. (Limitiniz güncellendi)</div>`;
                    
                    } else {
                        resultText.value = 'Soru üretilemedi.';
                        currentRubrik = '';
                        rubrikContainer.classList.add('hidden');
                        showAnswerBtn.disabled = true;
                        showAnswerBtn.textContent = "Cevabı Göster (Puanlama Anahtarı)";
                        resultMessage.innerHTML = `<div class="p-3 rounded-lg bg-red-100 text-red-800 text-sm">Hata: ${result.metin}</div>`;
                    }
                    // --- YENİ BLOK BİTTİ ---

                } catch (error) {
                    console.error("Soru üretme hatası:", error);
                    resultText.value = 'Soru üretilemedi.';
                    resultMessage.innerHTML = `<div class="p-3 rounded-lg bg-red-100 text-red-800 text-sm">Sunucuyla iletişim kurulamadı: Failed to fetch. API anahtarınızı kontrol edin.</div>`;
                } finally {
                    generateBtn.style.display = 'flex';
                    loadingSpinner.style.display = 'none';
                }
            });
            
            // 4. Kopyala Butonu
            copyBtn.addEventListener('click', () => {
                resultText.select(); 
                try {
                    document.execCommand('copy'); 
                    resultMessage.innerHTML = `<div class="p-3 rounded-lg bg-blue-100 text-blue-800 text-sm">Soru panoya kopyalandı!</div>`;
                } catch (err) {
                    resultMessage.innerHTML = `<div class="p-3 rounded-lg bg-red-100 text-red-800 text-sm">Kopyalama başarısız.</div>`;
                }
                setTimeout(() => { resultMessage.innerHTML = '' }, 2000);
            });

            // 5. YENİ - Cevabı Göster Butonu
            if (showAnswerBtn) {
                showAnswerBtn.addEventListener('click', () => {
                    if (currentRubrik) {
                        rubrikContent.innerHTML = currentRubrik; // <-- DÜZELTİLDİ: .innerHTML
                        rubrikContainer.classList.remove('hidden');
                    } else {
                        rubrikContent.innerHTML = "Rubrik (Cevap Anahtarı) yüklenemedi."; // <-- DÜZELTİLDİ: .innerHTML
                        rubrikContainer.classList.remove('hidden');
                    }
                    showAnswerBtn.disabled = true;
                });
            }
            
        });
    </script>
</body>
</html>
"""

# --- YARIŞMA SEÇİM SAYFASI HTML ---
YARISMA_SECIM_PAGE_HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Yarışma Seçim</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        body { 
            font-family: 'Inter', sans-serif;
            background-color: #f3f4f6;
        }
    </style>
</head>
<body class="flex h-screen">
    
    <!-- Sol Dikey Menü -->
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
                    <!-- Dropdown kaldırıldı -->
                </div>
            </div>
        </div>
        
<nav class="flex-1 overflow-y-auto p-4 space-y-2 no-bounce">

            <a id="link-metin-analiz" href="/metin-analiz" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-blue-500 hover:bg-blue-600 transition-all">
                <i class="fa-solid fa-file-pen mr-3 w-6 text-center"></i>
                <span>Metin Analiz</span>
            </a>
            <a id="link-soru-uretim" href="/soru-uretim" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-green-500 hover:bg-green-600 transition-all">
                <i class="fa-solid fa-circle-question mr-3 w-6 text-center"></i>
                <span>Soru Üretim</span>
            </a>
            <a id="link-metin-olusturma" href="/metin-olusturma" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-purple-500 hover:bg-purple-600 transition-all">
                <i class="fa-solid fa-wand-magic-sparkles mr-3 w-6 text-center"></i>
                <span>Metin Oluşturma</span>
            </a>
            <a id="link-haritada-bul" href="/haritada-bul" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-orange-500 hover:bg-orange-600 transition-all">
                <i class="fa-solid fa-map-location-dot mr-3 w-6 text-center"></i>
                <span>Haritada Bul</span>
            </a>
            <a id="link-podcast" href="/podcast_paneli" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-red-500 hover:bg-red-600 transition-all">
                <i class="fa-solid fa-microphone-lines mr-3 w-6 text-center"></i>
                <span>Podcast Yap</span>
            </a>
            <a id="link-seyret-bul" href="/seyret-bul-liste" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-indigo-500 hover:bg-indigo-600 transition-all">
                <i class="fa-solid fa-magnifying-glass-plus mr-3 w-6 text-center"></i>
                <span>Seyret Bul</span>
            </a>
            <a id="link-yarisma" href="/yarisma-secim" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-teal-600 ring-2 ring-teal-300 transition-all">
                <i class="fa-solid fa-trophy mr-3 w-6 text-center"></i>
                <span>Beceri/Değer Avcısı</span>
            </a>
            <a id="link-video-istegi" href="/video-istegi" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-pink-500 hover:bg-pink-600 transition-all">
                <i class="fa-solid fa-video mr-3 w-6 text-center"></i>
                <span>Video İsteği</span>
            </a>

        </nav>
        
        <div class="p-4 border-t border-gray-200">
            <!-- Geri Dön Butonu -->
            <a href="/dashboard" class="flex items-center w-full p-3 rounded-lg text-gray-600 font-semibold bg-gray-100 hover:bg-gray-200 transition-all">
                <i class="fa-solid fa-arrow-left mr-3 w-6 text-center"></i>
                <span>Panele Geri Dön</span>
            </a>
        </div>
    </aside>

    <!-- Ana İçerik Alanı -->
    <main class="ml-72 flex-1 p-2 overflow-y-auto">
        <h2 class="text-3xl font-bold text-gray-800 mb-6">Beceri/Değer Avcısı</h2>
        <p class="text-gray-600 mb-6">Lütfen katılmak istediğiniz yarışma türünü seçin.</p>
        
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">

            <a id="btn-bireysel-yarisma" href="/bireysel-yarisma" class="block bg-white p-8 rounded-lg shadow-lg hover:shadow-xl transition-shadow duration-300 text-center">
                <i class="fa-solid fa-user text-6xl text-cyan-500 mb-4"></i>
                <h3 class="text-2xl font-bold text-gray-800 mb-2">Bireysel Yarışma</h3>
                <p class="text-gray-600">Tek başınıza yarışın, becerilerinizi test edin ve rozetler kazanın!</p>
            </a>

            <a id="btn-takim-yarisma" href="/takim-yarisma" class="block bg-white p-8 rounded-lg shadow-lg hover:shadow-xl transition-shadow duration-300 text-center">
                <i class="fa-solid fa-users text-6xl text-teal-500 mb-4"></i>
                <h3 class="text-2xl font-bold text-gray-800 mb-2">Takım Yarışması Kurulumu</h3>
                <p class="text-gray-600">Sınıfınızla takım kurun, birlikte yarışın ve zafere ulaşın!</p>
            </a>
            
            <a id="btn-takim-sonuclar" href="/takim-liderlik-tablosu" class="block bg-white p-8 rounded-lg shadow-lg hover:shadow-xl transition-shadow duration-300 text-center">
                <i class="fa-solid fa-clipboard-list text-6xl text-purple-500 mb-4"></i>
                <h3 class="text-2xl font-bold text-gray-800 mb-2">Takım Yarışma Tablosu</h3>
                <p class="text-gray-600">Okuldaki en iyi 10 takımın skorlarını görün.</p>
            </a>
            
            <a id="btn-bireysel-sonuclar" href="/leaderboard" class="block bg-white p-8 rounded-lg shadow-lg hover:shadow-xl transition-shadow duration-300 text-center">
                <i class="fa-solid fa-ranking-star text-6xl text-yellow-500 mb-4"></i>
                <h3 class="text-2xl font-bold text-gray-800 mb-2">Bireysel Sonuçlarım</h3>
                <p class="text-gray-600">Sınıfınızın rozetlerini ve en iyi 5 öğrencisini görün.</p>
            </a>

        </div>
    </main>
    
       <script>
        document.addEventListener('DOMContentLoaded', () => {
            // --- 1. Kullanıcı Bilgilerini Yükle ---
            const userFullName = localStorage.getItem('loggedInUserName'); 
            const userRole = localStorage.getItem('loggedInUserRole'); 
            const userNo = localStorage.getItem('loggedInUserNo');
            const userSchool = localStorage.getItem('loggedInUserSchool');
            const userClass = localStorage.getItem('loggedInUserClass');

            // Ad ve Avatar Ayarla
            if (userFullName) {
                const namePlaceholder = document.getElementById('user-name-placeholder');
                const avatarInitial = document.getElementById('user-avatar-initial');
                if (namePlaceholder) namePlaceholder.textContent = userFullName;
                if (avatarInitial) avatarInitial.textContent = userFullName[0] ? userFullName[0].toUpperCase() : 'K';
            }

            // --- 2. Yan Menü Rol Kontrolü ---
            const linkMetinAnaliz = document.getElementById('link-metin-analiz');
            const linkSoruUretim = document.getElementById('link-soru-uretim');
            const linkMetinOlusturma = document.getElementById('link-metin-olusturma');
            const linkHaritadaBul = document.getElementById('link-haritada-bul');
            const linkPodcast = document.getElementById('link-podcast');
            const linkSeyretBul = document.getElementById('link-seyret-bul');
            const linkYarisma = document.getElementById('link-yarisma');
            const linkVideoIstegi = document.getElementById('link-video-istegi');
      
            // --- 3. Sayfa İçi Rol Kontrolü ---
            
            if (userRole === 'teacher') {
                // --- ÖĞRETMEN GÖRÜNÜMÜ ---
                if (linkMetinAnaliz) linkMetinAnaliz.style.display = 'none';
                if (linkSeyretBul) linkSeyretBul.style.display = 'none';
                if (linkHaritadaBul) linkHaritadaBul.style.display = 'none'; 
                
                const btnBireyselYarisma = document.getElementById('btn-bireysel-yarisma');
                if (btnBireyselYarisma) btnBireyselYarisma.style.display = 'none'; 

                const btnBireyselSonuclar = document.getElementById('btn-bireysel-sonuclar');
                if (btnBireyselSonuclar) btnBireyselSonuclar.style.display = 'none';

            } else {
                // --- ÖĞRENCİ GÖRÜNÜMÜ ---
                if (linkMetinOlusturma) linkMetinOlusturma.style.display = 'none';
                
                const btnTakimYarisma = document.getElementById('btn-takim-yarisma');
                if (btnTakimYarisma) btnTakimYarisma.style.display = 'none';

                // ============================================================
                // ÖĞRENCİ ÖZEL FONKSİYONLARI (PING + OYUN KONTROLÜ)
                // ============================================================
                
                if (userNo) {
                    // A. PING ATMA (Çevrimiçi Görünmek İçin)
                    function sendPing() {
                        fetch('/api/ping', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ student_no: userNo })
                        })
                        // .then(res => res.json()).then(data => console.log("Ping:", userNo)) // Log kirliliği olmasın diye kapattım
                        .catch(err => console.error("Ping hatası:", err));
                    }
                    sendPing(); // Hemen gönder
                    setInterval(sendPing, 5000); // 5 saniyede bir tekrarla

                    // B. OYUN KONTROLÜ (Otomatik Giriş İçin)
                    if (userSchool && userClass) {
                        async function checkForGame() {
                            try {
                                const response = await fetch('/api/check_for_game', {
                                    method: 'POST',
                                    headers: { 'Content-Type': 'application/json' },
                                    body: JSON.stringify({ okul: userSchool, sinif: userClass })
                                });
                                const data = await response.json();

                                if (data.found && data.yarisma_id) {
                                    console.log("🟢 OTOMATİK BAĞLANTI: Yönlendiriliyor...");
                                    window.location.href = `/takim-oyun-ekrani/${data.yarisma_id}`;
                                }
                            } catch (err) {
                                console.error("Oyun kontrol hatası:", err);
                            }
                        }
                        // 3 saniyede bir oyun var mı diye bak
                        setInterval(checkForGame, 3000);
                    }
                }
                // ============================================================
            }
        });
    </script>
</body>
</html>
"""
# --- YARIŞMA SEÇİM HTML KODU BİTTİ ---


# --- Bireysel Yarışma Sayfası (Dinamik) ---
BIREYSEL_YARISMA_HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bireysel Yarışma</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style> 
        body { font-family: 'Inter', sans-serif; background-color: #f3f4f6; } 
        /* Tıklanabilir cümle stili */
        .sentence {
            cursor: pointer;
            padding: 4px;
            margin: 2px 0;
            border-radius: 6px;
            transition: all 0.2s ease-in-out;
            border: 2px solid transparent;
        }
        .sentence:hover {
            background-color: #f0f9ff; /* light-blue-50 */
            border-color: #38bdf8; /* light-blue-400 */
        }
        /* Tıklanmış/Kullanılmış cümle */
        .sentence.clicked {
            background-color: #fef9c3; /* yellow-100 */
            border-color: #facc15; /* yellow-400 */
            cursor: not-allowed;
        }
        /* Doğru bulunan cümle */
        .sentence.correct-beceri {
            background-color: #cffafe; /* cyan-100 */
            border-color: #06b6d4; /* cyan-500 */
            cursor: not-allowed;
            font-weight: 600;
        }
        .sentence.correct-deger {
            background-color: #dcfce7; /* green-100 */
            border-color: #22c55e; /* green-500 */
            cursor: not-allowed;
            font-weight: 600;
        }
        /* Yanlış tıklanan ve hakkı düşüren cümle */
        .sentence.wrong {
            background-color: #fee2e2; /* red-100 */
            border-color: #ef4444; /* red-500 */
            cursor: not-allowed;
            opacity: 0.7;
        }
        
        /* Aktif buton stili */
        .control-btn.active {
            transform: scale(1.05);
            box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.8), 0 0 0 6px #3b82f6;
        }
        .control-btn[disabled] {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .timer-bar {
            height: 6px;
            background-color: #3b82f6;
            border-radius: 3px;
            transition: width 1s linear;
        }
    </style>
</head>
<body class="flex h-screen">
    
    <!-- Sol Dikey Menü -->
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
                    <!-- Dropdown kaldırıldı -->
                </div>
            </div>
        </div>
        <nav class="flex-1 overflow-y-auto p-4 space-y-2 no-bounce">
            
            <a href="/metin-analiz" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-blue-500 hover:bg-blue-600 transition-all">
                <i class="fa-solid fa-file-pen mr-3 w-6 text-center"></i>
                <span>Metin Analiz</span>
            </a>
            <a href="/soru-uretim" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-green-500 hover:bg-green-600 transition-all">
                <i class="fa-solid fa-circle-question mr-3 w-6 text-center"></i>
                <span>Soru Üretim</span>
            </a>
            <a href="/metin-olusturma" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-purple-500 hover:bg-purple-600 transition-all">
                <i class="fa-solid fa-wand-magic-sparkles mr-3 w-6 text-center"></i>
                <span>Metin Oluşturma</span>
            </a>
            <a href="/haritada-bul" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-orange-500 hover:bg-orange-600 transition-all">
                <i class="fa-solid fa-map-location-dot mr-3 w-6 text-center"></i>
                <span>Haritada Bul</span>
            </a>
            <a href="/podcast_paneli" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-red-500 hover:bg-red-600 transition-all">
                <i class="fa-solid fa-microphone-lines mr-3 w-6 text-center"></i>
                <span>Podcast Yap</span>
            </a>
            <a href="/seyret-bul-liste" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-indigo-500 hover:bg-indigo-600 transition-all">
                <i class="fa-solid fa-magnifying-glass-plus mr-3 w-6 text-center"></i>
                <span>Seyret Bul</span>
            </a>
            <a href="/yarisma-secim" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-teal-600 ring-2 ring-teal-300 transition-all">
                <i class="fa-solid fa-trophy mr-3 w-6 text-center"></i>
                <span>Beceri/Değer Avcısı</span>
            </a>
            <a href="/video-istegi" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-pink-500 hover:bg-pink-600 transition-all">
                <i class="fa-solid fa-video mr-3 w-6 text-center"></i>
                <span>Video İsteği</span>
            </a>
            
        </nav>
        <div class="p-4 border-t border-gray-200">
            <a href="/dashboard" class="flex items-center w-full p-3 rounded-lg text-gray-600 font-semibold bg-gray-100 hover:bg-gray-200 transition-all">
                <i class="fa-solid fa-arrow-left mr-3 w-6 text-center"></i>
                <span>Panele Geri Dön</span>
            </a>
        </div>
    </aside>

    <!-- Ana İçerik Alanı -->
    <main class="ml-72 flex-1 p-6 md:p-8 overflow-y-auto relative">
        <div id="game-container">
            <div class="flex justify-between items-center">
                <h2 class="text-3xl font-bold text-gray-800">Beceri/Değer Avcısı (Bireysel)</h2>
                <!-- ########## GÜNCELLEME: Liderlik Tablosu Butonu Buraya Eklendi ########## -->
                <a href="/leaderboard" class="flex items-center p-3 rounded-lg text-white font-semibold bg-yellow-500 hover:bg-yellow-600 transition-all">
                    <i class="fa-solid fa-ranking-star mr-2"></i>
                    <span>Liderlik Tablosu</span>
                </a>
            </div>
            
            <!-- Skor ve Durum Alanı -->
            <div class="flex flex-wrap justify-between items-center bg-white p-4 rounded-lg shadow mt-4 gap-4">
                <div>
                    <span class="text-sm text-gray-500">Mevcut Soru</span>
                    <p id="soru-sayisi-text" class="text-2xl font-bold text-gray-800">Soru 1 / 10</p>
                </div>
                <div>
                    <span class="text-sm text-gray-500">Kalan Hak (Bu Soru İçin)</span>
                    <p id="kalan-hak-text" class="text-2xl font-bold text-red-500">3</p>
                </div>
                <div class="flex-1 min-w-[150px]">
                    <span class="text-sm text-gray-500">Kalan Süre (60sn)</span>
                    <div class="w-full bg-gray-200 rounded-full h-[6px] mt-2">
                        <div id="timer-bar" class="timer-bar" style="width: 100%;"></div>
                    </div>
                </div>
                <div id="rozetler-container" class="flex space-x-2">
                    <!-- Rozetler JS ile eklenecek -->
                </div>
            </div>
            
            <!-- Mesaj Alanı (Tebrikler, Elendiniz vb.) -->
            <div id="game-message" class="mt-4 text-center"></div>

            <!-- Oyun Alanı -->
            <div class="mt-6 max-w-4xl mx-auto"> <div>
                    <h3 class="text-lg font-semibold text-gray-700 mb-3 text-center">1. Bulunacak Tipi Seçin:</h3>
                    <div class="flex flex-col md:flex-row md:space-x-4 space-y-4 md:space-y-0 justify-center">
                        <button id="btn-beceri" data-type="beceri" class="control-btn w-full md:w-1/2 p-3 rounded-lg shadow-md font-bold text-white bg-blue-500 hover:bg-blue-600 transition-all">
                            </button>
                        <button id="btn-deger" data-type="deger" class="control-btn w-full md:w-1/2 p-3 rounded-lg shadow-md font-bold text-white bg-green-500 hover:bg-green-600 transition-all">
                            </button>
                    </div>
                </div>
                
                <div class="mt-8"> <h3 class="text-lg font-semibold text-gray-700 mb-2 text-center">2. Metinden Cümleyi Tıklayın:</h3>
                    <div id="metin-container" class="bg-white p-6 rounded-lg shadow min-h-[200px] text-lg leading-relaxed">
                        </div>
                </div>

            </div>
            
            <!-- Overlay'ler (Yükleme, Elenme, Yasak) -->
            <div id="overlay-container" class="hidden absolute inset-0 bg-white/80 flex-col items-center justify-center rounded-lg p-8 text-center z-10">
                <!-- İçerik JS ile doldurulacak -->
            </div>
        </div>
    </main>
    
    <script>
        // ########## YENİ OYUN MANTIĞI (V6 - GEMINI) ##########
        
        // --- Global Değişkenler ---
        let studentNo = localStorage.getItem('loggedInUserNo');
        let userSoyad = localStorage.getItem('loggedInUserName') || 'Kullanıcı';
        
        let kalanHak = 3;
        let soruSayisi = 0;
        let rozetler = [];
        let toplamSure = 0;
        
        let timerInterval = null;
        let saniyeBasinaDusenWidth = 100 / 60;
        let mevcutSaniye = 60;
        
        let aktifButonTipi = null; // 'beceri' veya 'deger'
        let cevapAnahtari = {
            beceri_cumlesi: "",
            deger_cumlesi: ""
        };
        let bulundu = {
            beceri: false,
            deger: false
        };
        let tiklananCumleler = []; // Aynı cümleye tekrar tıklamayı engelle

        // --- DOM Elementleri ---
        const gameContainer = document.getElementById('game-container');
        const kalanHakText = document.getElementById('kalan-hak-text');
        const soruSayisiText = document.getElementById('soru-sayisi-text');
        const rozetlerContainer = document.getElementById('rozetler-container');
        const gameMessage = document.getElementById('game-message');
        const btnBeceri = document.getElementById('btn-beceri');
        const btnDeger = document.getElementById('btn-deger');
        const metinContainer = document.getElementById('metin-container');
        const timerBar = document.getElementById('timer-bar');
        const overlayContainer = document.getElementById('overlay-container');

        // --- Paneldeki Kullanıcı Adını Yükleme ---
    document.addEventListener('DOMContentLoaded', () => {
        // --- GÜNCELLEME: Değişken adı "userSoyad" -> "userFullName" oldu ---
        // 'userSoyad' değişkeni zaten script'in en başında tanımlı (localStorage'dan alınıyor)
        // Sadece o değişkenin adını en başta değiştirmek yerine, burada yeni bir değişken oluşturuyoruz.
        const userFullName = localStorage.getItem('loggedInUserName'); 
        const namePlaceholder = document.getElementById('user-name-placeholder');
        const avatarInitial = document.getElementById('user-avatar-initial');

        if (namePlaceholder && userFullName) {
            namePlaceholder.textContent = userFullName; // Değişti
        }
        if (avatarInitial && userFullName) {
            // İlk harfi al (Adın ilk harfi)
            avatarInitial.textContent = userFullName[0] ? userFullName[0].toUpperCase() : 'K'; // Değişti
        }
        // --- GÜNCELLEME BİTTİ ---

        if (!studentNo) {
                gameContainer.innerHTML = '<h2 class="text-2xl font-bold text-red-600">Hata: Giriş yapılmamış!</h2><p>Lütfen önce ana sayfadan giriş yapın.</p>';
                return;
            }
            
            // Oyunu Başlat
            oyunuBaslat();
        });

        // --- Oyun Fonksiyonları ---

        async function oyunuBaslat() {
            // 1. Öğrenci durumunu kontrol et (Yasaklı mı?)
            try {
                const response = await fetch('/api/bireysel/basla', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ student_no: studentNo })
                });
                const result = await response.json();
                
                if (!result.success && result.giris_yasakli) {
                    // YASAKLI EKRANI
                    showOverlay('yasak', result.mesaj);
                    return;
                }
                
                // 2. Durumu ve skoru güncelle
                soruSayisi = result.durum.dogru_soru_sayisi;
                rozetler = result.durum.rozetler;
                toplamSure = result.durum.toplam_sure_saniye;
                guncelleSkorboard();

                // 3. İlk soruyu yükle
                yeniSoruGetir();
                
            } catch (e) {
                showGameMessage('Hata: Sunucuyla bağlantı kurulamadı.', 'red');
            }
        }

        async function yeniSoruGetir() {
            showOverlay('loading');
            stopTimer();
            
            try {
                const response = await fetch('/api/bireysel/yeni_soru', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ student_no: studentNo })
                });
                const result = await response.json();
                
                if (result.success) {
                    const data = result.data;
                    
                    cevapAnahtari.beceri_cumlesi = data.beceri_cumlesi.trim();
                    cevapAnahtari.deger_cumlesi = data.deger_cumlesi.trim();
                    btnBeceri.textContent = data.beceri_adi + " Becerisi";
                    btnDeger.textContent = data.deger_adi + " Değeri";
                    
                    metinContainer.innerHTML = '';
                    const sentences = data.metin.match(/[^.!?]+[.!?]+/g) || [data.metin];
                    
                    sentences.forEach((sentenceText, index) => {
                        const span = document.createElement('span');
                        span.textContent = sentenceText.trim() + ' ';
                        span.className = 'sentence';
                        span.dataset.id = `s-${index}`;
                        span.onclick = () => cumleTikla(span);
                        metinContainer.appendChild(span);
                    });
                    
                    resetSoruDurumu();
                } else {
                    // ########## GÜNCELLEME: API Hata Düzeltmesi ##########
                    // Metin gelmeme hatası (API Key eksikse)
                    showOverlay('api_error', result.metin || 'Hata: Yeni soru yüklenemedi.');
                }
            } catch (e) {
                showOverlay('api_error', 'Sunucuyla iletişim kurulamadı. Lütfen API anahtarınızı kontrol edin.');
            } finally {
                // Not: Başarılı olursa 'loading' overlay'i resetSoruDurumu() kaldırır
                // Başarısız olursa 'api_error' overlay'i kalır.
            }
        }
        
        function resetSoruDurumu() {
            kalanHak = 3;
            aktifButonTipi = null;
            bulundu = { beceri: false, deger: false };
            tiklananCumleler = [];
            
            kalanHakText.textContent = kalanHak;
            kalanHakText.className = "text-2xl font-bold text-red-500";
            
            btnBeceri.disabled = false;
            btnDeger.disabled = false;
            btnBeceri.classList.remove('active', 'opacity-50');
            btnDeger.classList.remove('active', 'opacity-50');
            
            showGameMessage('Lütfen önce bir buton seçin (Beceri veya Değer), sonra metinden ilgili cümleyi bulun.', 'blue');
            
            showOverlay('none'); // Yükleme ekranını gizle
            startTimer();
        }

        // Kontrol Butonları (Beceri / Değer)
        btnBeceri.onclick = () => setAktifButon('beceri');
        btnDeger.onclick = () => setAktifButon('deger');

        function setAktifButon(tip) {
            if ( (tip === 'beceri' && bulundu.beceri) || (tip === 'deger' && bulundu.deger) ) {
                return; // Zaten bulunduysa bu butonu seçme
            }

            // --- YENİ EKLENDİ (İsteğiniz) ---
            // Yeni bir buton seçildiğinde, önceki denemedeki
            // 'wrong' (kırmızı) işaretlerini temizle.
            document.querySelectorAll('.sentence.wrong').forEach(span => {
                span.classList.remove('wrong');
            });
            // --- BİTTİ ---

            aktifButonTipi = tip;
            
            if (tip === 'beceri') {
                btnBeceri.classList.add('active');
                btnDeger.classList.remove('active');
            } else {
                btnDeger.classList.add('active');
                btnBeceri.classList.remove('active');
            }
            showGameMessage(`"${tip === 'beceri' ? btnBeceri.textContent : btnDeger.textContent}" cümlesini metinde bulun.`, 'blue');
        }

        // Cümleye Tıklama Mantığı
        function cumleTikla(spanElement) {
            const cumleMetni = spanElement.textContent.trim();
            
            // 1. Kontroller
            if (kalanHak <= 0 || (bulundu.beceri && bulundu.deger)) return;
            if (!aktifButonTipi) {
                showGameMessage('Lütfen önce "Beceri" veya "Değer" butonlarından birini seçin!', 'red');
                return;
            }
            
            // 'tiklananCumleler.includes' KONTROLÜ ARTIK YOK

            // 2. Tıklanana Ekle
            // 'tiklananCumleler.push' ARTIK YOK

            let dogruMu = false;
            // ... (kodun geri kalanı)

            // 3. Cevap Kontrolü
            if (aktifButonTipi === 'beceri' && cumleMetni === cevapAnahtari.beceri_cumlesi) {
                bulundu.beceri = true;
                dogruMu = true;
                spanElement.className = 'sentence correct-beceri'; // Mavi
                btnBeceri.disabled = true;
                btnBeceri.classList.add('opacity-50');
                btnBeceri.classList.remove('active');
                showGameMessage('Beceri cümlesi DOĞRU! Şimdi Değer cümlesini bulun.', 'green');
                aktifButonTipi = null; 
            } 
            else if (aktifButonTipi === 'deger' && cumleMetni === cevapAnahtari.deger_cumlesi) {
                bulundu.deger = true;
                dogruMu = true;
                spanElement.className = 'sentence correct-deger'; // Yeşil
                btnDeger.disabled = true;
                btnDeger.classList.add('opacity-50');
                btnDeger.classList.remove('active');
                showGameMessage('Değer cümlesi DOĞRU! Şimdi Beceri cümlesini bulun.', 'green');
                aktifButonTipi = null; 
            }
            
            // 4. Yanlış Cevap (Hakkı SADECE BURADA DÜŞÜR)
            if (!dogruMu) {
                kalanHak--; // <-- YERİ DEĞİŞTİ
                kalanHakText.textContent = kalanHak; // <-- YERİ DEĞİŞTİ
                spanElement.className = 'sentence wrong';
                showGameMessage(`YANLIŞ! Kalan hak: ${kalanHak}`, 'red');
            }

            // 5. Durum Kontrolü (Kazandı mı? Elendi mi?)
            checkGameStatus();
        }
        
        async function checkGameStatus() {
            // KAZANDI (İkisini de buldu)
            if (bulundu.beceri && bulundu.deger) {
                stopTimer();
                let harcananSure = 60 - mevcutSaniye;
                
                showGameMessage('TEBRİKLER! Her ikisini de buldunuz. Yeni soru yükleniyor...', 'green', false);
                
                // Skoru sunucuya kaydet
                const response = await fetch('/api/bireysel/kaydet_dogru', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        student_no: studentNo,
                        soru_suresi_saniye: harcananSure
                    })
                });
                const result = await response.json();

                // Rozet kazandıysa özel mesajı göster
                if(result.rozet_sonucu && result.rozet_sonucu.yeni_rozet) {
                    showGameMessage(result.rozet_sonucu.mesaj, 'green', false);
                }

                // Puanı ve rozetleri yenile
                soruSayisi = result.yeni_dogru_sayisi;
                rozetler = result.rozet_sonucu.yeni_durum.rozetler || rozetler;
                guncelleSkorboard();
                
                // 10 soruyu da bitirdi mi?
                if (soruSayisi >= 10) {
                    // Altın rozet yasağı zaten sunucuda (kaydet_dogru) ayarlandı.
                    setTimeout(() => {
                        showOverlay('final', result.rozet_sonucu.mesaj);
                    }, 3000);
                } else {
                    setTimeout(yeniSoruGetir, 3000); // 3 saniye sonra yeni soru
                }
            }
            // ELENDİ (Hak bitti)
            else if (kalanHak <= 0) {
                stopTimer();
                let harcananSure = 60 - mevcutSaniye;
                kalanHakText.className = "text-2xl font-bold text-gray-400";
                
                // Sunucuya elenme süresini kaydet
                await fetch('/api/bireysel/kaydet_elenme', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        student_no: studentNo,
                        harcanan_sure_saniye: harcananSure
                    })
                });
                
                // 10 saniyelik teselli mesajı
                showOverlay('elendin', 'Hakkınız bitti, bu turda elendiniz. 10 saniye sonra yarışma seçim ekranına yönlendirileceksiniz...');
                
                setTimeout(() => {
                    window.location.href = '/yarisma-secim';
                }, 10000); // 10 saniye sonra yönlendir
            }
        }
        
        function guncelleSkorboard() {
            soruSayisiText.textContent = `Soru ${soruSayisi + 1} / 10`;
            
            rozetlerContainer.innerHTML = ''; // Temizle
            if (rozetler.includes('bronz')) {
                rozetlerContainer.innerHTML += '<i class="fa-solid fa-medal text-3xl text-yellow-600" title="Bronz Rozet"></i>';
            }
            if (rozetler.includes('gumus')) {
                rozetlerContainer.innerHTML += '<i class="fa-solid fa-medal text-3xl text-gray-400" title="Gümüş Rozet"></i>';
            }
            if (rozetler.includes('altin')) {
                rozetlerContainer.innerHTML += '<i class="fa-solid fa-medal text-3xl text-yellow-400" title="Altın Rozet"></i>';
            }
        }

        // --- Zamanlayıcı (Timer) Fonksiyonları ---
        function startTimer() {
            mevcutSaniye = 60;
            timerBar.style.width = '100%';
            timerBar.classList.remove('bg-red-500');
            timerBar.classList.add('bg-blue-500');
            
            stopTimer(); // Önceki timer'ı durdur
            
            timerInterval = setInterval(() => {
                mevcutSaniye--;
                let widthPercent = (mevcutSaniye / 60) * 100;
                timerBar.style.width = `${widthPercent}%`;
                
                if (mevcutSaniye <= 10) {
                    timerBar.classList.remove('bg-blue-500');
                    timerBar.classList.add('bg-red-500');
                }
                
                if (mevcutSaniye <= 0) {
                    stopTimer();
                    sureDoldu();
                }
            }, 1000);
        }
        
        function stopTimer() {
            clearInterval(timerInterval);
        }

        async function sureDoldu() {
            let harcananSure = 60;
            
            // Sunucuya elenme süresini kaydet
            await fetch('/api/bireysel/kaydet_elenme', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    student_no: studentNo,
                    harcanan_sure_saniye: harcananSure
                })
            });
            
            // 10 saniyelik teselli mesajı
            showOverlay('elendin', 'Süreniz doldu, bu turda elendiniz. 10 saniye sonra yarışma seçim ekranına yönlendirileceksiniz...');
            
            setTimeout(() => {
                window.location.href = '/yarisma-secim';
            }, 10000); // 10 saniye sonra yönlendir
        }
        
        // --- Yardımcı Fonksiyonlar ---
        
        function showGameMessage(message, type = 'blue', autoClear = true) {
            let colorClasses = 'bg-blue-100 text-blue-800'; // default
            if (type === 'red') colorClasses = 'bg-red-100 text-red-800';
            if (type === 'green') colorClasses = 'bg-green-100 text-green-800';
            if (type === 'yellow') colorClasses = 'bg-yellow-100 text-yellow-800';
            
            gameMessage.innerHTML = `<div class="p-3 rounded-lg ${colorClasses} font-semibold">${message}</div>`;
            
            if (autoClear) {
                setTimeout(() => {
                    if (gameMessage.innerHTML.includes(message)) {
                        gameMessage.innerHTML = '';
                    }
                }, 3000);
            }
        }
        
        function showOverlay(type, message = '') {
            if (type === 'none') {
                overlayContainer.style.display = 'none';
                return;
            }
            
            let content = '';
            if (type === 'loading') {
                content = `
                    <div class="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                    <p class="mt-4 text-lg font-semibold text-gray-700">Yeni soru hazırlanıyor...</p>
                `;
            } else if (type === 'yasak') {
                content = `
                    <i class="fa-solid fa-gavel text-6xl text-red-500 mb-4"></i>
                    <h2 class="text-3xl font-bold text-red-700">Yarışma Yasağı</h2>
                    <p class="text-gray-700 mt-2 text-lg">${message}</p>
                    <a href="/dashboard" class="mt-6 bg-blue-500 text-white font-semibold py-2 px-4 rounded-lg hover:bg-blue-600">Panele Dön</a>
                `;
            } else if (type === 'elendin') {
                content = `
                    <i class="fa-solid fa-face-sad-tear text-6xl text-blue-500 mb-4"></i>
                    <h2 class="text-3xl font-bold text-blue-700">Oyun Bitti</h2>
                    <p class="text-gray-700 mt-2 text-lg">${message}</p>
                `;
            } else if (type === 'final') {
                content = `
                    <i class="fa-solid fa-trophy text-6xl text-yellow-500 mb-4"></i>
                    <h2 class="text-3xl font-bold text-yellow-700">Yarışma Bitti!</h2>
                    <p class="text-gray-700 mt-2 text-lg">${message}</p>
                    <a href="/leaderboard" class="mt-6 bg-green-500 text-white font-semibold py-2 px-4 rounded-lg hover:bg-green-600">Liderlik Tablosunu Gör</a>
                `;
            } else if (type === 'api_error') {
                 content = `
                    <i class="fa-solid fa-circle-exclamation text-6xl text-red-500 mb-4"></i>
                    <h2 class="text-3xl font-bold text-red-700">API Hatası</h2>
                    <p class="text-gray-700 mt-2 text-lg">${message}</p>
                    <p class="text-gray-500 mt-2 text-sm">Lütfen 'sosyallab.py' dosyasındaki API anahtarınızı kontrol edin.</p>
                    <a href="/dashboard" class="mt-6 bg-blue-500 text-white font-semibold py-2 px-4 rounded-lg hover:bg-blue-600">Panele Dön</a>
                `;
            }
            
            overlayContainer.innerHTML = content;
            overlayContainer.style.display = 'flex';
        }
        
    </script>
</body>
</html>
"""
# --- BİREYSEL YARIŞMA HTML KODU BİTTİ ---
# ########## YENİ EKLENDİ: TAKIM YARIŞMASI HTML (GELİŞMİŞ KURULUM) ##########
# ########## YENİ EKLENDİ: TAKIM YARIŞMASI HTML (GELİŞMİŞ KURULUM - DÜZELTİLDİ) ##########
TAKIM_YARISMA_HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Takım Yarışması Kurulumu</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style> 
        body { font-family: 'Inter', sans-serif; background-color: #f3f4f6; } 
        select:disabled { background-color: #f3f4f6; cursor: not-allowed; }
        .team-list-item { background-color: #d1fae5; padding: 4px; border-radius: 4px; margin-bottom: 4px; }
        
        /* 👇👇👇 YENİ EKLENEN STİLLER 👇👇👇 */
        .student-item { 
            padding: 6px; 
            border-radius: 4px; 
            cursor: pointer; 
            transition: background-color 0.1s;
        }
        .student-item:hover { background-color: #f0f9ff; }
        .student-item.selected { 
            background-color: #d1fae5; /* Yeşilimsi arka plan */
            font-weight: 600; 
            border: 1px solid #10b981; /* Yeşil kenarlık */
        }
        .student-item.assigned { 
            opacity: 0.6; 
            cursor: not-allowed; 
            background-color: #f3f4f6;
        }
        /* 👆👆👆 YENİ EKLENEN STİLLER BİTTİ 👆👆👆 */

        /* YENİ EKLENEN KURAL (macOS esnemesini durdurur) */
        .no-bounce {
            overscroll-behavior: none;
        }
    </style>
</head>
<body class="flex h-screen">
    
    <aside class="w-72 bg-white text-gray-800 shadow-lg flex flex-col fixed h-full">
    <div class="px-6 py-4 border-b border-gray-200">
        <h1 class="text-2xl font-extrabold text-blue-600 text-center tracking-wide mb-4">Maarif SosyalLab</h1>
        <div class="mb-4">
                <div class="w-full p-2 flex items-center justify-center overflow-hidden">
                    <img src="/videolar/maarif.png"  
                         alt="Maarif Logo" 
                         class="w-auto h-auto max-w-full max-h-24 object-contain rounded-lg">
                </div>
            </div>
        <div class="flex items-center">
            <div id="user-avatar-initial" class="w-10 h-10 rounded-full bg-cyan-500 flex items-center justify-center text-white font-bold text-lg">K</div>
            <div class="ml-3"><span id="user-name-placeholder" class="block text-sm font-bold text-gray-800">Kullanıcı</span></div>
        </div>
    </div>
        <nav class="flex-1 overflow-y-auto p-4 space-y-2 no-bounce">
        <a id="link-metin-analiz" href="/metin-analiz" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-blue-500 hover:bg-blue-600 transition-all">
            <i class="fa-solid fa-file-pen mr-3 w-6 text-center"></i><span>Metin Analiz</span></a>
        
        <a href="/soru-uretim" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-green-500 hover:bg-green-600 transition-all">
            <i class="fa-solid fa-circle-question mr-3 w-6 text-center"></i><span>Soru Üretim</span></a>
        
        <a href="/metin-olusturma" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-purple-500 hover:bg-purple-600 transition-all">
            <i class="fa-solid fa-wand-magic-sparkles mr-3 w-6 text-center"></i><span>Metin Oluşturma</span></a>
        
        <a id="link-haritada-bul" href="/haritada-bul" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-orange-500 hover:bg-orange-600 transition-all">
            <i class="fa-solid fa-map-location-dot mr-3 w-6 text-center"></i><span>Haritada Bul</span></a>
        
        <a href="/podcast_paneli" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-red-500 hover:bg-red-600 transition-all">
            <i class="fa-solid fa-microphone-lines mr-3 w-6 text-center"></i><span>Podcast Yap</span></a>
        
        <a id="link-seyret-bul" href="/seyret-bul-liste" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-indigo-500 hover:bg-indigo-600 transition-all">
            <i class="fa-solid fa-magnifying-glass-plus mr-3 w-6 text-center"></i><span>Seyret Bul</span></a>
        
        <a href="/yarisma-secim" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-teal-600 ring-2 ring-teal-300 transition-all">
            <i class="fa-solid fa-trophy mr-3 w-6 text-center"></i><span>Beceri/Değer Avcısı</span></a>
        
        <a id="link-video-istegi" href="/video-istegi" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-pink-500 hover:bg-pink-600 transition-all">
            <i class="fa-solid fa-video mr-3 w-6 text-center"></i><span>Video İsteği</span></a>
    </nav>
    <div class="p-4 border-t border-gray-200">
        <a href="/dashboard" class="flex items-center w-full p-3 rounded-lg text-gray-600 font-semibold bg-gray-100 hover:bg-gray-200 transition-all"><i class="fa-solid fa-arrow-left mr-3 w-6 text-center"></i><span>Panele Geri Dön</span></a>
    </div>
    </aside>
    
    <main class="ml-72 flex-1 p-6 md:p-8 overflow-y-auto no-bounce">
        <h2 class="text-3xl font-bold text-gray-800 mb-6">Takım Yarışması Kurulumu</h2>
        
        <div id="loading-message" class="hidden bg-yellow-100 p-4 rounded-lg shadow text-yellow-800 font-semibold">Öğrenci verileri yükleniyor...</div>
        <div id="error-message" class="hidden bg-red-100 p-4 rounded-lg shadow text-red-800 font-semibold"></div>

        <div id="step-1" class="bg-white p-6 rounded-lg shadow mt-4 grid grid-cols-1 md:grid-cols-4 gap-4">
            <div class="md:col-span-2 p-2 rounded-lg bg-blue-50 border border-blue-200">
                <h4 class="font-bold text-blue-800 mb-1">Sorumlu Sınıf</h4>
                <p id="teacher-class-info" class="text-lg font-semibold text-gray-800">Yükleniyor...</p>
                <input type="hidden" id="okul-select" value="">
                <input type="hidden" id="sinif-select" value="">
            </div>
            
            <div>
                <label for="takim-sayisi-select" class="block text-sm font-medium text-gray-700 mb-1">1. Takım Sayısı</label>
                <select id="takim-sayisi-select" class="w-full px-4 py-2 border rounded-lg bg-white" disabled>
                    <option value="">Sınıf Yükleniyor...</option>
                </select>
            </div>
            
            <div>
                <label for="kisi-sayisi-select" class="block text-sm font-medium text-gray-700 mb-1">2. Takım Başı Kişi</label>
                <select id="kisi-sayisi-select" class="w-full px-4 py-2 border rounded-lg bg-white" disabled>
                    <option value="">Sınıf Yükleniyor...</option>
                </select>
            </div>   
            <div class="col-span-4 text-center">
                <button id="sinif-listesini-getir-btn" class="mt-4 bg-teal-500 text-white font-bold py-2 px-6 rounded-lg hover:bg-teal-600 transition-all" disabled>
                    Takımları Önizle
                </button>
            </div>
        </div>
           
        <div id="step-2" class="hidden mt-6 bg-white p-6 rounded-lg shadow">
            
            <div class="grid grid-cols-1 md:grid-cols-10 gap-6 w-full"> 
                
                <div class="md:col-span-4">
                    <div class="bg-gray-50 p-4 rounded-lg shadow min-h-[400px]">
                        <div class="flex justify-between items-center mb-3">
                            <h3 class="text-xl font-semibold text-gray-800">Öğrenci Listesi (<span id="unassigned-count">0</span> Kişi)</h3>
                            <button id="select-all-btn" class="text-xs text-blue-500 hover:underline">Tümünü Seç</button>
                        </div>
                        <div id="student-list-container" class="space-y-1 max-h-96 overflow-y-auto">
                            </div>
                        <button id="otomatik-eslestir-btn" class="mt-4 w-full bg-orange-500 text-white font-bold py-2 rounded-lg hover:bg-orange-600 transition-all">
                            Otomatik Takım Oluştur
                        </button>
                    </div>
                </div>
                
                <div class="md:col-span-2 flex flex-col items-center justify-center pt-8">
                    </div>

                <div id="team-assignment-container" class="md:col-span-4 grid grid-cols-2 gap-4 max-h-[500px] overflow-y-auto">
                     </div>
                
            </div>
            
            <div class="pt-4 border-t mt-6 text-center">
                <button id="yarismayi-baslat-btn" class="bg-green-500 text-white font-bold py-3 px-10 rounded-lg text-lg shadow-lg hover:bg-green-600 transition-all disabled:opacity-50" disabled>
                    Yarışmayı Başlat
                </button>
                <div id="takim-baslatma-mesaj" class="mt-4 text-red-500 font-semibold text-center hidden"></div>
            </div>
            
        </div>
        <div id="game-screen" class="hidden mt-6">
            <h2 class="text-3xl font-bold text-gray-800 mb-6">Yarışma Başladı!</h2>
            <p class="text-gray-600">Oyun arayüzü bir sonraki adımda buraya gelecek...</p>
        </div>
        
    </main>
    <script>
        // --- Sabit Veri ---
        const SCHOOLS = [{name: "Sezi Eratik Ortaokulu"}, {name: "TOKİ Demokrasi Ortaokulu"}];
        const CLASSES = ["5A", "5B", "5C", "5D", "5E", "5F"];
        
        // --- Global State ---
        let currentStudentList = [];
        let teams = [];
        let teamCount = 0;
        let studentsPerTeam = 0;

        // --- DOM Elements ---
        const okulSelect = document.getElementById('okul-select');
        const sinifSelect = document.getElementById('sinif-select');
        const takimSayisiSelect = document.getElementById('takim-sayisi-select');
        const kisiSayisiSelect = document.getElementById('kisi-sayisi-select');
        const listeyiGetirBtn = document.getElementById('sinif-listesini-getir-btn');
        const loadingMessage = document.getElementById('loading-message');
        const step1 = document.getElementById('step-1');
        const step2 = document.getElementById('step-2');
        const studentListContainer = document.getElementById('student-list-container');
        const unassignedCountSpan = document.getElementById('unassigned-count');
        const teamAssignmentContainer = document.getElementById('team-assignment-container');
        const otomatikEslestirBtn = document.getElementById('otomatik-eslestir-btn');
        const yarismayiBaslatBtn = document.getElementById('yarismayi-baslat-btn');
        const takimBaslatmaMesaj = document.getElementById('takim-baslatma-mesaj');
        const errorMessage = document.getElementById('error-message');


        // ########## GEREKLİ TEMEL FONKSİYONLAR ##########

        function initializeSelections() {
            // (Bu fonksiyon öğretmen girişinde kullanılmıyor, yedek)
            okulSelect.innerHTML = '<option value="">Okul Seçin...</option>';
            SCHOOLS.forEach(s => {
                okulSelect.innerHTML += `<option value="${s.name}">${s.name}</option>`;
            });

            sinifSelect.innerHTML = '<option value="">Sınıf Seçin...</option>';
            CLASSES.forEach(c => {
                sinifSelect.innerHTML += `<option value="${c}">${c}</option>`;
            });
            sinifSelect.disabled = true;
        }
        
        function updateTeamSettings() {
            const totalStudents = currentStudentList.length;
            if (totalStudents < 2) { // En az 2 öğrenci lazım (1 vs 1 için)
                errorMessage.textContent = "Bu sınıfta takım oluşturmak için yeterli öğrenci yok.";
                errorMessage.style.display = 'block';
                return;
            }
            
            takimSayisiSelect.innerHTML = '<option value="">Takım Sayısı</option>';
            kisiSayisiSelect.innerHTML = '<option value="">Kişi Sayısı</option>';

            // 1. Takım Sayısı Döngüsü (En az 2 takım olmalı)
            const maxTeams = 4; 
            for (let i = 2; i <= maxTeams; i++) {
                if (totalStudents >= i) { // Toplam öğrenci sayısı takım sayısına yetiyor mu?
                    takimSayisiSelect.innerHTML += `<option value="${i}">${i}</option>`;
                }
            }

            // 2. Kişi Sayısı Döngüsü (GÜNCELLENDİ: 1'den başlıyor)
            const maxStudentsPerTeam = 5; 
            // 👇👇👇 BURASI ARTIK 1'DEN BAŞLIYOR 👇👇👇
            for (let i = 1; i <= maxStudentsPerTeam; i++) {
                // En az 2 takım kurulacağı için (i * 2) kadar öğrenci var mı diye bakıyoruz
                if (totalStudents >= (i * 2)) {
                    kisiSayisiSelect.innerHTML += `<option value="${i}">${i}</option>`;
                }
            }
            // 👆👆👆 DEĞİŞİKLİK BURADA 👆👆👆

            takimSayisiSelect.disabled = false;
            kisiSayisiSelect.disabled = false;
            listeyiGetirBtn.disabled = true; 

            takimSayisiSelect.value = ""; 
            kisiSayisiSelect.value = ""; 
            
            takimSayisiSelect.addEventListener('change', checkStep1Readiness);
            kisiSayisiSelect.addEventListener('change', checkStep1Readiness);
            
            checkStep1Readiness();
        }
        
        function checkStep1Readiness() {
            const takimSayisi = takimSayisiSelect.value;
            const kisiSayisi = kisiSayisiSelect.value;
            
            if (takimSayisi && kisiSayisi) {
                teamCount = parseInt(takimSayisi);
                studentsPerTeam = parseInt(kisiSayisi);
                createEmptyTeams(teamCount);
                step2.classList.remove('hidden');
                renderStudentList();
                renderTeamBoxes();
            } else {
                step2.classList.add('hidden');
            }
        }

        // ########## ÖĞRENCİ LİSTESİ VE TAKIM ATAMA EKRANI ##########
        
        function renderStudentList() {
            studentListContainer.innerHTML = '';
            let unassignedCount = 0;
            
            currentStudentList.forEach((student, index) => {
                const isAssigned = teams.some(team => team.uyeler.some(u => u.no === student.no));
                if (!isAssigned) unassignedCount++;
                
                const item = document.createElement('div');
                item.className = `student-item ${isAssigned ? 'assigned' : ''} ${student.selected ? 'selected' : ''}`;
                item.dataset.no = student.no;
                item.dataset.index = index;
                // --- YENİ: Çevrimiçi Durumu Göstergesi ---
                let onlineBadge = '';
                if (student.is_online) {
                    onlineBadge = ' <span class="text-green-600 font-bold text-xs animate-pulse">● Çevrimiçi</span>';
                }
                item.innerHTML = student.ad_soyad + onlineBadge;
                
                if (!isAssigned) {
                    item.onclick = () => toggleStudentSelection(index);
                }
                studentListContainer.appendChild(item);
            });
            
            unassignedCountSpan.textContent = unassignedCount;
            checkTeamCreationReadiness();
        }

        function toggleStudentSelection(index) {
            currentStudentList[index].selected = !currentStudentList[index].selected;
            renderStudentList();
        }

        function renderTeamBoxes() {
            teamAssignmentContainer.innerHTML = '';
            teams.forEach((team, teamIndex) => {
                const box = document.createElement('div');
                box.className = 'bg-gray-50 p-3 rounded-lg shadow-inner';
                
                const header = document.createElement('div');
                header.className = 'flex justify-between items-center mb-2';
                header.innerHTML = `<h4 contenteditable="true" data-index="${teamIndex}" class="font-bold text-teal-700">${team.ad}</h4>
                                    <button onclick="removeTeam(${teamIndex})" class="text-red-500 text-xs font-semibold">[Sil]</button>`;
                box.appendChild(header);
                
                const ul = document.createElement('ul');
                ul.id = `team-${teamIndex}-list`;
                team.uyeler.forEach(uye => {
                    ul.innerHTML += `<li class="team-list-item">${uye.ad_soyad} <button onclick="removeStudentFromTeam(${teamIndex}, '${uye.no}')" class="text-red-700 text-xs ml-1 font-semibold">[x]</button></li>`;
                });
                box.appendChild(ul);
                
                // DÜZELTME: Atama butonu, sadece takım dolu değilse görünür
                const assignBtn = document.createElement('button');
                const isFull = (studentsPerTeam > 0 && team.uyeler.length >= studentsPerTeam);
                
                assignBtn.className = `w-full mt-2 text-white text-sm py-1 rounded ${isFull ? 'bg-gray-400' : 'bg-blue-500 hover:bg-blue-600'}`;
                assignBtn.textContent = isFull ? 'Takım Dolu' : 'Seçilenleri Ata';
                assignBtn.disabled = isFull;
                
                assignBtn.onclick = () => assignSelectedStudentsToTeam(teamIndex);
                box.appendChild(assignBtn);
                
                box.querySelector('h4').addEventListener('blur', (e) => {
                    teams[teamIndex].ad = e.target.textContent.trim();
                });

                teamAssignmentContainer.appendChild(box);
            });
            checkTeamCreationReadiness();
        }

        function createEmptyTeams(count) {
            teams = [];
            for (let i = 1; i <= count; i++) {
                teams.push({ ad: `Takım ${i}`, uyeler: [] });
            }
        }
        
        // DÜZELTME: Takım limitini (studentsPerTeam) kontrol eder
        function assignSelectedStudentsToTeam(teamIndex) {
            const team = teams[teamIndex];
            const unassignedSelected = currentStudentList.filter(s => s.selected && !teams.some(t => t.uyeler.some(u => u.no === s.no)));
            
            if (unassignedSelected.length === 0) {
                alert("Önce öğrencileri soldan seçin.");
                return;
            }

            // DÜZELTME (Kural 2 - Doluluk): Takım kapasitesini kontrol et
            if (studentsPerTeam > 0 && (team.uyeler.length + unassignedSelected.length) > studentsPerTeam) {
                alert(`Hata: Bu takıma en fazla ${studentsPerTeam} kişi ekleyebilirsiniz. Takımda ${team.uyeler.length} kişi var, ${unassignedSelected.length} kişi daha eklenemez.`);
                return;
            }
            
            unassignedSelected.forEach(student => {
                // Sadece limit dahilindekileri ekle (Bu bir çift kontrol)
                if (team.uyeler.length < studentsPerTeam) {
                    team.uyeler.push({ no: student.no, ad_soyad: student.ad_soyad });
                    student.selected = false; // Seçimi kaldır
                }
            });
            
            renderTeamBoxes();
            renderStudentList();
        }
        
        function removeStudentFromTeam(teamIndex, studentNo) {
            const team = teams[teamIndex];
            team.uyeler = team.uyeler.filter(u => u.no !== studentNo);
            
            const studentInList = currentStudentList.find(s => s.no === studentNo);
            if (studentInList) studentInList.selected = false;
            
            renderTeamBoxes();
            renderStudentList();
        }
        
        function removeTeam(teamIndex) {
            if (confirm(`'${teams[teamIndex].ad}' takımını silmek istediğinizden emin misiniz? Takımdaki öğrenciler listeye geri dönecektir.`)) {
                teams[teamIndex].uyeler.forEach(uye => {
                    const studentInList = currentStudentList.find(s => s.no === uye.no);
                    if (studentInList) studentInList.selected = false; 
                });
                teams.splice(teamIndex, 1);
                renderTeamBoxes();
                renderStudentList();
            }
        }
        
        function checkTeamCreationReadiness() {
            otomatikEslestirBtn.disabled = !(currentStudentList.length >= (teamCount * studentsPerTeam) && teamCount > 0 && studentsPerTeam > 0);
            yarismayiBaslatBtn.disabled = !checkAllTeamsFull();
        }
        
        // DÜZELTME: 'Yarışmayı Başlat' butonunu aktifleştirme mantığı
        function checkAllTeamsFull() {
            if (teams.length === 0) return false;
            
            // 1. Takım sayısı, seçilen takım sayısıyla eşleşmeli
            if (teams.length !== teamCount) {
                takimBaslatmaMesaj.textContent = `Hata: ${teamCount} takım olmalı, şu an ${teams.length} takım var.`;
                takimBaslatmaMesaj.classList.remove('hidden');
                return false;
            }
            
            // 2. HER takımın kişi sayısı TAM OLARAK `studentsPerTeam` olmalı
            const allTeamsFull = teams.every(team => team.uyeler.length === studentsPerTeam);
            
            if (!allTeamsFull) {
                takimBaslatmaMesaj.textContent = `Devam etmek için ${teamCount} takımın her birinde tam ${studentsPerTeam} öğrenci olmalıdır.`;
                takimBaslatmaMesaj.classList.remove('hidden');
                return false;
            }

            takimBaslatmaMesaj.classList.add('hidden');
            return true; // Tüm koşullar sağlandı
        }

        // ########## OLAY DİNLEYİCİLERİ ##########

        // ########## BAŞLANGIÇ ##########
        
        document.addEventListener('DOMContentLoaded', async () => {
            const userFullName = localStorage.getItem('loggedInUserName'); 
            const userRole = localStorage.getItem('loggedInUserRole');
            const teacherClass = localStorage.getItem('loggedInUserClass'); 
            const teacherSchool = localStorage.getItem('loggedInUserSchool'); 
            
            // 1. Kullanıcı adını yükle
            if (userFullName) {
                document.getElementById('user-name-placeholder').textContent = userFullName;
                document.getElementById('user-avatar-initial').textContent = userFullName[0] ? userFullName[0].toUpperCase() : 'K';
            }
            // 2. Rol Kontrolü (Sol Menü)
            if (userRole === 'teacher') {
                const linkMetinAnaliz = document.getElementById('link-metin-analiz');
                const linkSeyretBul = document.getElementById('link-seyret-bul');
                const linkHaritadaBul = document.getElementById('link-haritada-bul');
                if (linkMetinAnaliz) linkMetinAnaliz.style.display = 'none';
                if (linkSeyretBul) linkSeyretBul.style.display = 'none';
                if (linkHaritadaBul) linkHaritadaBul.style.display = 'none';
            }
            
            if (userRole !== 'teacher') {
                errorMessage.textContent = "Bu panel sadece öğretmenler içindir.";
                errorMessage.style.display = 'block';
                return;
            }

            if (!teacherClass || !teacherSchool) {
                errorMessage.textContent = "Hata: Öğretmen kaydınızda okul veya sınıf bilgisi eksik.";
                errorMessage.style.display = 'block';
                return;
            }

            // 3. Bilgi Panelini Doldur
            document.getElementById('teacher-class-info').textContent = `${teacherSchool} - ${teacherClass}`;
            document.getElementById('okul-select').value = teacherSchool; // Gizli inputları doldur
            document.getElementById('sinif-select').value = teacherClass; // Gizli inputları doldur
            
            // 4. Sınıf listesini API'den çek
            try {
                const response = await fetch('/get_all_users');
                const data = await response.json();
                if (data.success) {
                    currentStudentList = Object.entries(data.users)
                        .filter(([id, user]) => 
                            user.role === 'student' && 
                            user.school_name === teacherSchool && 
                            user.class === teacherClass
                        )
                        .map(([id, user]) => ({
                            no: id,
                            ad_soyad: `${user.first_name} ${user.last_name}`,
                            
                            // 👇👇👇 BU SATIRI EKLEMELİSİNİZ 👇👇👇
                            is_online: user.is_online, 
                            // 👆👆👆 BURASI EKSİKTİ 👆👆👆
                            
                            selected: false
                        }));
                    
                    console.log(`✅ ${currentStudentList.length} öğrenci yüklendi.`);
                    // 5. Takım Ayarlarını Aktifleştir
                    updateTeamSettings(); 
                }
            } catch (error) {
                console.error('Öğrenci listesi yüklenemedi:', error);
                errorMessage.textContent = 'Öğrenci listesi yüklenemedi.';
                errorMessage.style.display = 'block';
            }

            // 6. Takımları Önizle butonu (DÜZELTME: Mantık değişti)
            listeyiGetirBtn.addEventListener('click', () => {
                const takimSayisi = parseInt(takimSayisiSelect.value);
                const kisiSayisi = parseInt(kisiSayisiSelect.value);
                
                // YENİ KURAL: Her iki değer de seçilmelidir.
                if (!takimSayisi || !kisiSayisi) {
                    alert("Lütfen hem Takım Sayısını hem de Kişi Sayısını seçin.");
                    return;
                }
                
                // YENİ KURAL: Toplam öğrenci yetiyor mu?
                if (takimSayisi * kisiSayisi > currentStudentList.length) {
                    alert(`Hata: ${takimSayisi} takım ve ${kisiSayisi} kişi (${takimSayisi * kisiSayisi} toplam) için yeterli öğrenci (${currentStudentList.length}) yok.`);
                    return;
                }

                // Değişkenleri global'e ata
                teamCount = takimSayisi;
                studentsPerTeam = kisiSayisi; // <-- HESAPLAMA KALDIRILDI

                createEmptyTeams(teamCount); // Boş takımları oluştur
                
                // Step 2'yi göster
                step1.style.display = 'none'; // Adım 1'i gizle
                step2.style.display = 'block'; // Adım 2'yi göster
                renderStudentList();
                renderTeamBoxes();
            });

            // "Tümünü Seç" butonu
            const selectAllBtn = document.getElementById('select-all-btn');
            if (selectAllBtn) {
                selectAllBtn.addEventListener('click', () => {
                    currentStudentList.forEach(s => {
                        if (!teams.some(t => t.uyeler.some(u => u.no === s.no))) {
                            s.selected = true;
                        }
                    });
                    renderStudentList();
                });
            }

            // "Otomatik Takım Oluştur" butonu (SADECE ÇEVRİMİÇİLER)
            if (otomatikEslestirBtn) {
                otomatikEslestirBtn.addEventListener('click', () => {
                    
                    // 1. Mevcut takımları temizle
                    teams.forEach(team => team.uyeler = []);
                    
                    // 2. SADECE ÇEVRİMİÇİ ÖĞRENCİLERİ AL (DÜZELTME BURADA)
                    // (Eski kodda offline olanları da ekliyorduk, şimdi kaldırdık)
                    const onlineStudents = currentStudentList.filter(s => s.is_online);

                    // 3. Listeyi karıştır (Rastgelelik için)
                    onlineStudents.sort(() => Math.random() - 0.5);

                    // 4. Yeterli sayı var mı kontrol et
                    const requiredStudents = teamCount * studentsPerTeam;
                    
                    if (onlineStudents.length < requiredStudents) {
                        alert(`Hata: Yeterli ÇEVRİMİÇİ öğrenci yok!\n\nİstenen: ${requiredStudents} kişi\nÇevrimiçi: ${onlineStudents.length} kişi\n\nLütfen öğrencilerin sisteme girmesini bekleyin.`);
                        return;
                    }
                    
                    // 5. Sırayla dağıt
                    let studentIndex = 0;
                    for (let t = 0; t < teamCount; t++) { 
                        for (let p = 0; p < studentsPerTeam; p++) { 
                            const student = onlineStudents[studentIndex];
                            teams[t].uyeler.push({ no: student.no, ad_soyad: student.ad_soyad });
                            student.selected = false; 
                            studentIndex++;
                        }
                    }
                    
                    renderTeamBoxes();
                    renderStudentList();
                });
            }
            
            // Yarışmayı Başlat butonu (API Çağrısı)
            if (yarismayiBaslatBtn) {
                yarismayiBaslatBtn.addEventListener('click', async () => {
                    // checkAllTeamsFull() zaten butonu etkinleştirdi, tekrar kontrol et
                    if (!checkAllTeamsFull()) {
                        takimBaslatmaMesaj.textContent = 'Tüm takımlar kurallara göre doldurulmalıdır.';
                        takimBaslatmaMesaj.classList.remove('hidden');
                        return;
                    }

                    yarismayiBaslatBtn.disabled = true;
                    takimBaslatmaMesaj.textContent = 'Yarışma sunucuda oluşturuluyor...';
                    takimBaslatmaMesaj.classList.remove('hidden', 'text-red-500');
                    takimBaslatmaMesaj.classList.add('text-blue-500');

                    const takimlarListesi = teams.map(team => ({
                        ad: team.ad,
                        uyeler: team.uyeler 
                    }));
                    
                    const okulAdi = document.getElementById('okul-select').value;
                    const sinifAdi = document.getElementById('sinif-select').value;

                    try {
                        const response = await fetch('/api/takim/basla', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ 
                                takimlarListesi: takimlarListesi,
                                okul: okulAdi,
                                sinif: sinifAdi
                            })
                        });
                        
                        const result = await response.json();
                        
                        if (result.success) {
                            takimBaslatmaMesaj.textContent = `Yarışma başarıyla oluşturuldu! ID: ${result.yarisma_id}`;
                            takimBaslatmaMesaj.classList.add('text-green-500');
                            
                            setTimeout(() => {
                                window.location.href = `/takim-oyun-ekrani/${result.yarisma_id}`;
                            }, 1000); 

                        } else {
                            takimBaslatmaMesaj.textContent = `Hata: ${result.hata}`;
                            takimBaslatmaMesaj.classList.add('text-red-500');
                            yarismayiBaslatBtn.disabled = false;
                        }
                    } catch (error) {
                        takimBaslatmaMesaj.textContent = `Sunucu hatası: ${error.message}`;
                        takimBaslatmaMesaj.classList.add('text-red-500');
                        yarismayiBaslatBtn.disabled = false;
                    }
                });
            }
            
           });
</script>
</body>
</html>
"""

# --- TAKIM YARIŞMA HTML KODU BİTTİ ---


# --- Liderlik Tablosu Sayfası HTML ---
LEADERBOARD_PAGE_HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Liderlik Tablosu</title>
    <style> 
    body { font-family: 'Inter', sans-serif; background-color: #f3f4f6; } 
    select:disabled { background-color: #f3f4f6; cursor: not-allowed; }
    #admin-panel { display: none; }

    /* YENİ EKLENEN KURAL */
    .no-bounce {
        overscroll-behavior: none;
    }
</style>
</head>
<body class="flex h-screen">
    
    <!-- Sol Dikey Menü -->
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
                    <!-- Dropdown kaldırıldı -->
                </div>
            </div>
        </div>
        <nav class="flex-1 overflow-y-auto p-4 space-y-2 no-bounce">

        <a href="/metin-analiz" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-blue-500 hover:bg-blue-600 transition-all">
            <i class="fa-solid fa-file-pen mr-3 w-6 text-center"></i>
            <span>Metin Analiz</span>
        </a>
        <a href="/soru-uretim" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-green-500 hover:bg-green-600 transition-all">
            <i class="fa-solid fa-circle-question mr-3 w-6 text-center"></i>
            <span>Soru Üretim</span>
        </a>
        <a href="/metin-olusturma" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-purple-500 hover:bg-purple-600 transition-all">
            <i class="fa-solid fa-wand-magic-sparkles mr-3 w-6 text-center"></i>
            <span>Metin Oluşturma</span>
        </a>
        <a href="/haritada-bul" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-orange-500 hover:bg-orange-600 transition-all">
            <i class="fa-solid fa-map-location-dot mr-3 w-6 text-center"></i>
            <span>Haritada Bul</span>
        </a>
        <a href="/podcast_paneli" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-red-500 hover:bg-red-600 transition-all">
            <i class="fa-solid fa-microphone-lines mr-3 w-6 text-center"></i>
            <span>Podcast Yap</span>
        </a>
        <a href="/seyret-bul-liste" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-indigo-500 hover:bg-indigo-600 transition-all">
            <i class="fa-solid fa-magnifying-glass-plus mr-3 w-6 text-center"></i>
            <span>Seyret Bul</span>
        </a>
        <a href="/yarisma-secim" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-teal-600 ring-2 ring-teal-300 transition-all">
            <i class="fa-solid fa-trophy mr-3 w-6 text-center"></i>
            <span>Beceri/Değer Avcısı</span>
        </a>

    </nav>
        <div class="p-4 border-t border-gray-200">
            <a href="/dashboard" class="flex items-center w-full p-3 rounded-lg text-gray-600 font-semibold bg-gray-100 hover:bg-gray-200 transition-all">
                <i class="fa-solid fa-arrow-left mr-3 w-6 text-center"></i>
                <span>Panele Geri Dön</span>
            </a>
        </div>
    </aside>

    <!-- Ana İçerik Alanı -->
    <main class="ml-72 flex-1 p-6 md:p-8 overflow-y-auto no-bounce">
        <h2 class="text-3xl font-bold text-gray-800 mb-6">Liderlik Tablosu (Bireysel Yarışma)</h2>
        <div class="bg-white p-6 rounded-lg shadow">
            <table class="w-full text-left">
                <thead class="bg-gray-100">
                    <tr>
                        <th class="p-3 font-semibold text-sm text-gray-600">Sıra</th>
                        <th class="p-3 font-semibold text-sm text-gray-600">Soyisim</th>
                        <th class="p-3 font-semibold text-sm text-gray-600">Okul / Şube</th>
                        <th class="p-3 font-semibold text-sm text-gray-600">Doğru Soru</th>
                        <th class="p-3 font-semibold text-sm text-gray-600">Rozetler</th>
                        <th class="p-3 font-semibold text-sm text-gray-600">Toplam Süre (sn)</th>
                    </tr>
                </thead>
                <tbody id="leaderboard-body" class="divide-y">
                    <!-- JS ile yüklenecek -->
                    <tr><td colspan="6" class="p-4 text-center text-gray-500">Yükleniyor...</td></tr>
                </tbody>
            </table>
        </div>
    </main>
    
    <script>
        // Paneldeki kullanıcı adını yükleme
        document.addEventListener('DOMContentLoaded', () => {
            // --- GÜNCELLEME: Değişken adı "userSoyad" -> "userFullName" oldu ---
            const userFullName = localStorage.getItem('loggedInUserName'); 
            if (userFullName) {
                const namePlaceholder = document.getElementById('user-name-placeholder');
                const avatarInitial = document.getElementById('user-avatar-initial');
                
                if (namePlaceholder) {
                    namePlaceholder.textContent = userFullName; // Değişti
                }
                if (avatarInitial) {
                    // İlk harfi al (Adın ilk harfi)
                    avatarInitial.textContent = userFullName[0] ? userFullName[0].toUpperCase() : 'K'; // Değişti
                }
            }
            // --- GÜNCELLEME BİTTİ ---
            
            // Liderlik tablosunu yükle
            loadLeaderboard();
        });

        async function loadLeaderboard() {
        const tbody = document.getElementById('leaderboard-body');

        // --- YENİ (AŞAMA 4.1) ---
        const userRole = localStorage.getItem('loggedInUserRole');
        const userClass = localStorage.getItem('loggedInUserClass'); // Öğretmenin sınıfını al

        let apiUrl = '/api/get_leaderboard'; // Varsayılan (herkesi göster)

        // Eğer giriş yapan öğretmense, API URL'ini değiştir
        if (userRole === 'teacher' && userClass) {
            apiUrl = `/api/get_leaderboard?class=${userClass}`;
        }
        // --- BİTTİ ---

        try {
            // API URL'i artık dinamik
            const response = await fetch(apiUrl); 
            const result = await response.json();

            if (result.success) {
                tbody.innerHTML = ''; // Temizle

                // --- YENİ (AŞAMA 4.1) ---
                // Eğer öğretmense ve 'top_5' verisi geldiyse onu göster
                if (userRole === 'teacher' && result.top_5) {
                     if (result.top_5.length === 0) {
                        tbody.innerHTML = `<tr><td colspan="6" class="p-4 text-center text-gray-500">Sınıfınızda (${userClass}) henüz kimse yarışmamış.</td></tr>`;
                        return;
                    }

                    result.top_5.forEach((entry, index) => {
                        const row = `
                            <tr class="hover:bg-gray-50">
                                <td class="p-3 font-bold">${index + 1}</td>
                                <td class="p-3">${entry.soyisim}</td>
                                <td class="p-3">${entry.okul} / ${entry.sube}</td>
                                <td class="p-3 font-semibold text-blue-600">${entry.dogru_soru}</td>
                                <td class="p-3">${entry.rozetler}</td>
                                <td class="p-3">${entry.toplam_sure} sn</td>
                            </tr>
                        `;
                        tbody.innerHTML += row;
                    });

                } 
                // Eğer öğrenciyse (veya genel) 'leaderboard' verisini göster
                else if (result.leaderboard) {
                    if (result.leaderboard.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="6" class="p-4 text-center text-gray-500">Henüz kimse yarışmamış.</td></tr>';
                        return;
                    }

                    result.leaderboard.forEach((entry, index) => {
                        const row = `
                            <tr class="hover:bg-gray-50">
                                <td class="p-3 font-bold">${index + 1}</td>
                                <td class="p-3">${entry.soyisim}</td>
                                <td class="p-3">${entry.okul} / ${entry.sube}</td>
                                <td class="p-3 font-semibold text-blue-600">${entry.dogru_soru}</td>
                                <td class="p-3">${entry.rozetler}</td>
                                <td class="p-3">${entry.toplam_sure} sn</td>
                            </tr>
                        `;
                        tbody.innerHTML += row;
                    });
                }
                // --- BİTTİ ---

            } else {
                tbody.innerHTML = `<tr><td colspan="6" class="p-4 text-center text-red-500">Hata: ${result.message}</td></tr>`;
            }
        } catch (e) {
            console.error("Liderlik tablosu hatası:", e);
            tbody.innerHTML = '<tr><td colspan="6" class="p-4 text-center text-red-500">Sunucuya bağlanılamadı.</td></tr>';
        }
    }
    </script>
</body>
</html>
"""
# --- LİDERLİK TABLOSU HTML KODU BİTTİ ---
# ########## YENİ EKLENDİ: TAKIM YARIŞMASI OYUN EKRANI ##########
# ########## YENİ EKLENDİ: TAKIM YARIŞMASI OYUN EKRANI (GÜNCELLENDİ V3) ##########
TAKIM_OYUN_EKRANI_HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Takım Yarışması - Oyun Ekranı</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; background-color: #f3f4f6; }
        .team-item { transition: all 0.3s ease; }
        .team-item.active { background-color: #eff6ff; border-color: #3b82f6; box-shadow: 0 4px 6px rgba(0,0,0,0.1); transform: scale(1.02); }
        .team-item.inactive { opacity: 0.6; background-color: #fee2e2; border-color: #ef4444; } 
        
        .sentence { cursor: default; display: inline; padding: 2px 4px; margin: 0 2px; line-height: 2.2; border-radius: 4px; transition: all 0.2s ease-in-out; border: 1px solid transparent; box-decoration-break: clone; -webkit-box-decoration-break: clone; }
        .sentence.clickable { cursor: pointer; }
        .sentence.clickable:hover { background-color: #dbeafe; border-color: #3b82f6; }
        .sentence.correct-beceri { background-color: #cffafe; border-color: #06b6d4; font-weight: 600; }
        .sentence.correct-deger { background-color: #dcfce7; border-color: #22c55e; font-weight: 600; }
        .sentence.wrong { background-color: #fee2e2; border-color: #ef4444; color: #b91c1c; font-weight: bold; opacity: 0.8; }
        
        .timer-bar-bg { height: 10px; background-color: #e5e7eb; border-radius: 5px; overflow: hidden; }
        .timer-bar { height: 100%; background-color: #22c55e; width: 100%; transition: width 1s linear; }
        .control-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .control-btn.active-beceri { box-shadow: 0 0 0 3px #bfdbfe; background-color: #2563eb; }
        .control-btn.active-deger { box-shadow: 0 0 0 3px #bbf7d0; background-color: #16a34a; }
        
        #toast-notification { position: fixed; top: -100px; left: 50%; transform: translateX(-50%); padding: 12px 24px; border-radius: 8px; color: white; font-weight: bold; z-index: 50; transition: top 0.3s ease; }
        #toast-notification.show { top: 20px; }
        #toast-notification.success { background-color: #10b981; }
        #toast-notification.error { background-color: #ef4444; }
        #toast-notification.info { background-color: #3b82f6; }
        .no-bounce { overscroll-behavior: none; }
    </style>
</head>
<body class="flex h-screen"> <div id="toast-notification"></div>

    <aside class="w-72 bg-white text-gray-800 shadow-lg flex flex-col fixed h-full">
        <div class="px-6 py-4 border-b border-gray-200">
            <h1 class="text-2xl font-extrabold text-blue-600 text-center tracking-wide mb-4">Maarif SosyalLab</h1>
            <div class="mb-4 flex justify-center"><img src="/videolar/maarif.png" class="h-24 object-contain rounded-lg"></div>
            <div class="flex items-center">
                <div id="user-avatar-initial" class="w-10 h-10 rounded-full bg-cyan-500 flex items-center justify-center text-white font-bold text-lg">K</div>
                <div class="ml-3"><span id="user-name-placeholder" class="block text-sm font-bold text-gray-800">Kullanıcı</span></div>
            </div>
        </div>
        <nav class="flex-1 overflow-y-auto p-4 space-y-2 no-bounce">
            <a href="/metin-analiz" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-blue-500 hover:bg-blue-600 transition-all"><i class="fa-solid fa-file-pen mr-3 w-6 text-center"></i><span>Metin Analiz</span></a>
            <a href="/seyret-bul-liste" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-indigo-500 hover:bg-indigo-600 transition-all"><i class="fa-solid fa-magnifying-glass-plus mr-3 w-6 text-center"></i><span>Seyret Bul</span></a>
            <a href="/yarisma-secim" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-teal-600 ring-2 ring-teal-300 transition-all"><i class="fa-solid fa-trophy mr-3 w-6 text-center"></i><span>Beceri/Değer Avcısı</span></a>
            <a href="/haritada-bul" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-orange-500 hover:bg-orange-600 transition-all"><i class="fa-solid fa-map-location-dot mr-3 w-6 text-center"></i><span>Haritada Bul</span></a>
            <a href="/podcast_paneli" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-red-500 hover:bg-red-600 transition-all"><i class="fa-solid fa-microphone-lines mr-3 w-6 text-center"></i><span>Podcast Yap</span></a>
        </nav>
        <div class="p-4 border-t border-gray-200">
            <a id="btn-exit-game" href="#" class="flex items-center w-full p-3 rounded-lg text-gray-600 font-semibold bg-gray-100 hover:bg-gray-200 transition-all"><i class="fa-solid fa-arrow-left mr-3 w-6 text-center"></i><span>Panele Geri Dön</span></a>
        </div>
    </aside>

    <main class="ml-72 flex-1 p-6 md:p-8 overflow-y-auto no-bounce">
        <div id="game-container" class="max-w-7xl mx-auto">
            <div class="flex justify-between items-center mb-4">
                <h1 class="text-3xl font-bold text-gray-800">Takım Yarışması</h1>
                <div class="w-1/3">
                    <div id="timer-text" class="text-right font-bold text-xl mb-1">60</div>
                    <div class="timer-bar-bg"><div id="timer-bar" class="timer-bar"></div></div>
                </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
                <div class="md:col-span-1 bg-white p-4 rounded-lg shadow-md">
                    <h2 class="text-lg font-semibold mb-3 border-b pb-2">Takımlar</h2>
                    <div id="team-list-container" class="space-y-3"><div class="text-center text-gray-500 p-4">Yükleniyor...</div></div>
                </div>

                <div class="md:col-span-2 bg-white p-6 rounded-lg shadow-lg">
                    <h2 id="soru-numarasi-text" class="text-xl font-bold text-center text-blue-600 mb-4">Yarışma Başlıyor...</h2>
                    <div id="metin-container" class="bg-gray-50 p-4 rounded-lg min-h-[300px] max-h-[500px] overflow-y-auto text-lg leading-relaxed border">
                        <p class="text-gray-500 text-center p-8">Sıradaki takımın soruyu görebilmesi için lütfen 'Soruyu Göster' butonuna basın.</p>
                    </div>
                </div>

                <div class="md:col-span-1 bg-white p-4 rounded-lg shadow-md">
                    <h2 class="text-lg font-semibold mb-3 border-b pb-2">Kontrol Paneli</h2>
                    <button id="soru-goster-btn" class="w-full bg-blue-500 text-white font-bold py-3 px-4 rounded-lg text-lg shadow hover:bg-blue-600 transition-all mb-2"><i class="fa-solid fa-eye mr-2"></i> Soruyu Göster</button>
                    
                    <div class="mt-4 border-t pt-4">
                        <h3 class="font-semibold mb-2 text-gray-700">Aktif Butonlar:</h3>
                        <p id="kontrol-mesaj" class="text-sm text-gray-500 mb-3">Bekleniyor...</p>
                        <button id="btn-beceri" class="control-btn w-full p-3 rounded-lg font-semibold text-white bg-blue-400 hover:bg-blue-500 transition-all mb-2" disabled>Beceri</button>
                        <button id="btn-deger" class="control-btn w-full p-3 rounded-lg font-semibold text-white bg-green-400 hover:bg-green-500 transition-all" disabled>Değer</button>
                    </div>
                </div>
            </div>
        </div>
    </main>
    
    <div id="game-over-modal" class="hidden fixed inset-0 bg-black bg-opacity-70 z-50 flex items-center justify-center p-4">
        <div class="bg-white rounded-lg max-w-lg w-full p-8 shadow-2xl text-center">
            <h2 id="tebrik-baslik" class="text-3xl font-bold text-yellow-500 mb-4">Yarışma Bitti!</h2>
            <p id="tebrik-mesaj" class="text-lg text-gray-700 mb-6">...</p>
            <p id="yonlendirme-mesaj" class="text-sm text-gray-400 mt-2">...</p>
        </div>
    </div>

    <script>
        const YARISMA_ID = window.location.pathname.split('/').pop();
        let MY_USER_ID = ''; let MY_USER_ROLE = ''; let MY_USER_NAME = '';
        let AKTIF_TAKIM_ID = null; let AKTIF_SORU_NUMARASI = 0; let SECILI_BUTON_TIPI = null;
        let TIMER_INTERVAL = null; let DURUM_GUNCELLEME_INTERVAL = null; let KalanSaniye = 60;
        let TOAST_TIMER = null; let OYUN_KILITLI = false; let soruVerisi = null;
        let LAST_EVENT_TIME = 0; 

        const teamListContainer = document.getElementById('team-list-container');
        const soruNumarasiText = document.getElementById('soru-numarasi-text');
        const metinContainer = document.getElementById('metin-container');
        const soruGosterBtn = document.getElementById('soru-goster-btn');
        const btnBeceri = document.getElementById('btn-beceri');
        const btnDeger = document.getElementById('btn-deger');
        const kontrolMesaj = document.getElementById('kontrol-mesaj');
        const timerText = document.getElementById('timer-text');
        const timerBar = document.getElementById('timer-bar');
        const gameOverModal = document.getElementById('game-over-modal');
        const exitBtn = document.getElementById('btn-exit-game');

        document.addEventListener('DOMContentLoaded', () => {
            MY_USER_NAME = localStorage.getItem('loggedInUserName') || 'Kullanıcı';
            MY_USER_ROLE = localStorage.getItem('loggedInUserRole');
            MY_USER_ID = String(localStorage.getItem('loggedInUserNo') || '').trim();

            document.getElementById('user-name-placeholder').textContent = MY_USER_NAME;
            document.getElementById('user-avatar-initial').textContent = MY_USER_NAME[0] || 'K';

            soruGosterBtn.addEventListener('click', soruGoster);
            btnBeceri.addEventListener('click', () => secimYap('beceri'));
            btnDeger.addEventListener('click', () => secimYap('deger'));
            
            if (exitBtn) {
                exitBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    if (MY_USER_ROLE === 'teacher') {
                        if (confirm("Yarışmayı sonlandırıp çıkmak istiyor musunuz?")) {
                             const data = new FormData();
                             navigator.sendBeacon(`/api/takim/bitir/${YARISMA_ID}`, data);
                             window.location.href = '/dashboard';
                        }
                    } else {
                        window.location.href = '/yarisma-secim';
                    }
                });
            }
            
            window.addEventListener('pagehide', () => {
                if (MY_USER_ROLE === 'teacher') {
                    const data = new FormData();
                    navigator.sendBeacon(`/api/takim/bitir/${YARISMA_ID}`, data);
                }
            });

            getDurum();
            DURUM_GUNCELLEME_INTERVAL = setInterval(getDurum, 3000);
        });

        async function getDurum() {
            if (OYUN_KILITLI) return;
            try {
                let url = `/api/takim/get_durum/${YARISMA_ID}`;
                if (MY_USER_ROLE === 'teacher') url += '?ogretmen_burada=evet';

                const response = await fetch(url);
                if (!response.ok) throw new Error("Oyun bulunamadı");

                const durum = await response.json();

                // Eğer oyun silindiyse
                if (!durum.success) {
                    clearInterval(DURUM_GUNCELLEME_INTERVAL);
                    showToast("Yarışma sonlandı. Yönlendiriliyorsunuz...", "error");
                    setTimeout(() => {
                        if (MY_USER_ROLE === 'student') window.location.href = '/yarisma-secim';
                        else window.location.href = '/dashboard';
                    }, 2000);
                    return;
                }

                // Eğer oyun bittiyse (10. soru veya elenme)
                if (durum.yarışma_bitti) {
                    oyunuBitir(durum);
                    return;
                }

                if (AKTIF_TAKIM_ID !== durum.aktif_takim_id) {
                    stopClientTimer();
                    resetSoruAlani();
                }

                AKTIF_TAKIM_ID = durum.aktif_takim_id;
                AKTIF_SORU_NUMARASI = durum.mevcut_soru_numarasi;
                renderTakimListesi(durum.takimlar, durum.aktif_takim_id);

                const kaptanId = String(durum.aktif_takim_kaptani_id || '').trim();
                const amICaptain = (MY_USER_ROLE === 'student' && MY_USER_ID === kaptanId);
                const isTeacher = (MY_USER_ROLE === 'teacher');
                
                // Son olay (İzleyici için)
                if (durum.son_olay && durum.son_olay.zaman > LAST_EVENT_TIME) {
                    LAST_EVENT_TIME = durum.son_olay.zaman;
                    showToast(durum.son_olay.mesaj, durum.son_olay.tur);
                    
                    const detay = durum.son_olay.detay;
                    if (detay && detay.sonuc === "yanlis" && detay.tiklanan_cumle) {
                         const yanlisEleman = document.querySelector(`.sentence[data-text="${detay.tiklanan_cumle}"]`);
                         if (yanlisEleman) {
                             yanlisEleman.classList.add('wrong');
                             setTimeout(() => yanlisEleman.classList.remove('wrong'), 2000);
                         }
                    }
                }

                if (durum.mevcut_soru_verisi) {
                    KalanSaniye = durum.kalan_saniye;
                    renderTimer(KalanSaniye);
                    soruVerisi = durum.mevcut_soru_verisi;
                    
                    const aktifTakim = durum.takimlar.find(t => t.id === durum.aktif_takim_id);
                    const beceriBulundu = aktifTakim ? aktifTakim.bulunan_beceri : false;
                    const degerBulundu = aktifTakim ? aktifTakim.bulunan_deger : false;

                    renderSoruAlani(soruVerisi.metin, soruVerisi.beceri_adi, soruVerisi.deger_adi, beceriBulundu, degerBulundu, amICaptain);

                    soruGosterBtn.disabled = true;
                    soruGosterBtn.textContent = `${AKTIF_SORU_NUMARASI}. Soru Gösterildi`;

                    btnBeceri.disabled = !amICaptain || beceriBulundu;
                    btnDeger.disabled = !amICaptain || degerBulundu;
                    
                    if (amICaptain) {
                        kontrolMesaj.textContent = "Sıra SİZDE! (Kaptan)";
                        kontrolMesaj.className = "text-sm font-bold text-green-600 mb-3 animate-pulse";
                    } else {
                        kontrolMesaj.textContent = `Sıra: ${aktifTakim ? aktifTakim.isim : '...'}`;
                        kontrolMesaj.className = "text-sm text-gray-500 mb-3";
                    }

                    if (!TIMER_INTERVAL) startClientTimer(KalanSaniye);

                } else {
                    stopClientTimer();
                    resetSoruAlani();
                    soruGosterBtn.disabled = !isTeacher;
                    soruGosterBtn.style.display = isTeacher ? 'block' : 'none';
                    soruGosterBtn.textContent = `${AKTIF_SORU_NUMARASI}. Soruyu Göster`;
                    kontrolMesaj.textContent = "Sıradaki soru bekleniyor...";
                }

            } catch (err) {
                console.error("Durum hatası:", err);
                if (err.message.includes("Oyun bulunamadı") || err.message.includes("JSON") || err.message.includes("Failed to fetch")) {
                     clearInterval(DURUM_GUNCELLEME_INTERVAL);
                     showToast("Bağlantı koptu.", "error");
                     setTimeout(() => {
                         if (typeof MY_USER_ROLE !== 'undefined' && MY_USER_ROLE === 'student') window.location.href = '/yarisma-secim';
                         else window.location.href = '/dashboard';
                     }, 2000);
                }
            }
        }

        function renderTakimListesi(takimlar, aktifTakimId) {
            teamListContainer.innerHTML = "";
            takimlar.forEach(takim => {
                const isTeamActive = takim.id === aktifTakimId;
                const isEliminated = !takim.aktif;
                const currentCaptainIndex = (takim.aktif_uye_index || 0) % takim.uyeler.length;
                
                const teamDiv = document.createElement('div');
                teamDiv.className = `team-item p-3 rounded-lg border-2 mb-3 transition-all ${isTeamActive ? 'border-blue-500 bg-blue-50 shadow-md' : 'border-gray-200 bg-white'} ${isEliminated ? 'inactive' : ''}`;
                
                let headerHtml = `
                    <div class="flex justify-between items-center mb-2 border-b pb-1">
                        <span class="font-bold text-lg ${isTeamActive ? 'text-blue-700' : 'text-gray-700'}">${takim.isim}</span>
                        <span class="font-bold text-xl ${isTeamActive ? 'text-blue-600' : 'text-gray-500'}">${takim.puan} P</span>
                    </div>
                `;

                let membersHtml = '<div class="flex flex-wrap gap-2 mb-2">';
                takim.uyeler.forEach((uye, index) => {
                    const isCaptain = (index === currentCaptainIndex);
                    const activeStyle = (isTeamActive && isCaptain) 
                        ? 'bg-green-500 text-white font-bold ring-2 ring-green-300 transform scale-105 shadow' 
                        : (isCaptain ? 'bg-gray-300 text-gray-600 font-semibold' : 'bg-gray-100 text-gray-500 text-xs');
                    
                    const kisaAd = uye.ad_soyad.split(' ')[0];
                    membersHtml += `<span class="px-2 py-1 rounded-md text-xs transition-all duration-300 ${activeStyle}">${isCaptain && isTeamActive ? '▶ ' : ''}${kisaAd}</span>`;
                });
                membersHtml += '</div>';
                
                let rozetIkon = '';
                if(takim.rozet === 'bronz') rozetIkon = '<i class="fa-solid fa-medal text-yellow-700"></i>';
                if(takim.rozet === 'gümüş') rozetIkon = '<i class="fa-solid fa-medal text-gray-400"></i>';
                if(takim.rozet === 'altin') rozetIkon = '<i class="fa-solid fa-medal text-yellow-400"></i>';

                let statusHtml = isEliminated ? '<span class="text-red-600 font-bold text-sm">ELENDİ</span>' : (isTeamActive ? '<span class="text-blue-600 font-semibold text-sm">Sıra Sizde</span>' : 'Bekliyor');

                let footerHtml = `
                    <div class="flex justify-between items-center text-sm text-gray-500">
                       <span>${statusHtml}</span>
                       <div class="text-lg">${rozetIkon}</div>
                    </div>`;

                teamDiv.innerHTML = headerHtml + membersHtml + footerHtml;
                teamListContainer.appendChild(teamDiv);
            });
        }

        function renderSoruAlani(metin, beceriAdi, degerAdi, beceriBulundu, degerBulundu, amICaptain) {
            metinContainer.innerHTML = "";
            soruNumarasiText.textContent = `${AKTIF_SORU_NUMARASI}. Soru`;
            const sentences = metin.match(/[^.!?]+[.!?]+/g) || [metin];
            
            sentences.forEach(sentenceText => {
                const cleanText = sentenceText.trim();
                const span = document.createElement('span');
                span.textContent = cleanText + ' ';
                span.className = 'sentence'; 
                
                if (amICaptain) { 
                    span.classList.add('clickable');
                    span.onclick = (e) => { e.preventDefault(); cevapVer(cleanText); }; 
                } 
                
                if (soruVerisi) { 
                    if (beceriBulundu && cleanText === soruVerisi.beceri_cumlesi) span.className = 'sentence correct-beceri';
                    if (degerBulundu && cleanText === soruVerisi.deger_cumlesi) span.className = 'sentence correct-deger';
                }
                metinContainer.appendChild(span);
            });
            btnBeceri.textContent = beceriAdi; 
            btnDeger.textContent = degerAdi;
        }

        async function cevapVer(tiklananCumleMetni) {
            if (OYUN_KILITLI || (KalanSaniye <= 0 && tiklananCumleMetni !== "SÜRE DOLDU")) return;
            if (!SECILI_BUTON_TIPI && tiklananCumleMetni !== "SÜRE DOLDU") {
                showToast("Lütfen önce bir buton seçin.", "info");
                return;
            }
            OYUN_KILITLI = true;
            btnBeceri.disabled = true; btnDeger.disabled = true;
            try {
                const response = await fetch(`/api/takim/cevap_ver/${YARISMA_ID}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        takim_id: AKTIF_TAKIM_ID, 
                        tiklanan_tip: SECILI_BUTON_TIPI, 
                        tiklanan_cumle: tiklananCumleMetni 
                    })
                });
                const result = await response.json();
                
                if (result.sonuc === "yanlis") {
                    showToast("Yanlış!", "error");
                    getDurum(); 
                } else if (result.sonuc === "dogru_parca") {
                    showToast("Doğru Parça!", "success");
                } else {
                    if (result.sonuc === "elendi") {
                        showToast(result.mesaj, "error");
                        kontrolMesaj.textContent = result.mesaj;
                        kontrolMesaj.className = "text-sm font-bold text-red-600 mb-3";
                    } else {
                        showToast(result.mesaj, "success");
                    }
                    stopClientTimer();
                    if(result.sonuc === "tur_bitti" || result.sonuc === "elendi") setTimeout(siradakiTakimaGec, 3000);
                    else if(result.sonuc === "oyun_bitti") setTimeout(getDurum, 3000);
                    else { resetSoruAlani(); } 
                }
            } catch(e) { console.error(e); }
            finally { OYUN_KILITLI = false; }
        }

        async function soruGoster() {
            soruGosterBtn.disabled = true;
            await fetch(`/api/takim/soru_goster/${YARISMA_ID}`);
            getDurum();
        }
        async function siradakiTakimaGec() {
            await fetch(`/api/takim/siradaki_takim/${YARISMA_ID}`);
            getDurum();
        }

        function resetSoruAlani() {
             metinContainer.innerHTML = '<p class="text-gray-500 text-center p-8">Sıradaki soru bekleniyor...</p>';
             btnBeceri.textContent = "Beceri"; btnDeger.textContent = "Değer";
             btnBeceri.disabled = true; btnDeger.disabled = true;
        }
        function secimYap(tip) {
            SECILI_BUTON_TIPI = tip;
            if (tip === 'beceri') { btnBeceri.classList.add('active-beceri'); btnDeger.classList.remove('active-deger'); } 
            else { btnDeger.classList.add('active-deger'); btnBeceri.classList.remove('active-beceri'); }
        }
        function startClientTimer(saniye) {
            stopClientTimer(); KalanSaniye = saniye; renderTimer(KalanSaniye);
            TIMER_INTERVAL = setInterval(() => {
                KalanSaniye--; renderTimer(KalanSaniye);
                if (KalanSaniye <= 0) { stopClientTimer(); cevapVer("SÜRE DOLDU"); }
            }, 1000);
        }
        function stopClientTimer() { clearInterval(TIMER_INTERVAL); TIMER_INTERVAL = null; }
        function renderTimer(s) { timerText.textContent = s; timerBar.style.width = `${(s/60)*100}%`; }
        function showToast(msg, type='info') {
            const t = document.getElementById('toast-notification');
            if (TOAST_TIMER) clearTimeout(TOAST_TIMER);
            t.textContent = msg; t.className = `show ${type}`;
            TOAST_TIMER = setTimeout(() => t.className = '', 3000);
        }
        
        // --- NİHAİ ÇIKIŞ MANTIĞI (10 SN KURALI DAHİL) ---
        function oyunuBitir(durum) {
            clearInterval(DURUM_GUNCELLEME_INTERVAL); 
            stopClientTimer();
            const kazanan = durum.takimlar.find(t => t.id === durum.kazanan_takim_id);
            const mesaj = kazanan ? `Kazanan: ${kazanan.isim}` : "Herkes elendi.";
            
            document.getElementById('tebrik-mesaj').textContent = mesaj;
            gameOverModal.classList.remove('hidden');
            
            // Skoru kaydet
            fetch(`/api/takim/bitir/${YARISMA_ID}`, { method: 'POST' });

            const mesajAlani = document.getElementById('yonlendirme-mesaj');
            
            if (durum.dereceye_girdi_mi) {
                mesajAlani.textContent = "Dereceye girdiniz! 3 sn sonra Liderlik Tablosu açılıyor...";
                setTimeout(() => {
                    window.location.href = '/takim-liderlik-tablosu?auto_exit=1';
                }, 3000);
            } else {
                mesajAlani.textContent = "3 sn sonra ana menüye dönülüyor...";
                setTimeout(() => {
                    if (MY_USER_ROLE === 'student') window.location.href = '/yarisma-secim';
                    else window.location.href = '/dashboard';
                }, 3000);
            }
        }
    </script>
</body>
</html>
"""

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
    <style> 
        /* GÜNCELLENDİ (İstek 4): Artık 'flex' kullanıyor */
        body { font-family: 'Inter', sans-serif; background-color: #f3f4f6; } 
    </style>
</head>
<body class="flex h-screen"> <aside class="w-72 bg-white text-gray-800 shadow-lg flex flex-col fixed h-full">
        <div class="px-6 py-4 border-b border-gray-200">
            <h1 class="text-2xl font-extrabold text-blue-600 text-center tracking-wide mb-4">Maarif SosyalLab</h1>
            <div class="mb-4">
                <div class="w-full p-2 flex items-center justify-center overflow-hidden">
                    <img src="/videolar/maarif.png" alt="Maarif Logo" class="w-auto h-auto max-w-full max-h-24 object-contain rounded-lg">
                </div>
            </div>
            <div class="flex items-center">
                <div id="user-avatar-initial" class="w-10 h-10 rounded-full bg-cyan-500 flex items-center justify-center text-white font-bold text-lg">K</div>
                <div class="ml-3"><span id="user-name-placeholder" class="block text-sm font-bold text-gray-800">Kullanıcı</span></div>
            </div>
        </div>
        <nav class="flex-1 overflow-y-auto p-4 space-y-2 no-bounce">
            <a id="link-metin-analiz" href="/metin-analiz" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-blue-500 hover:bg-blue-600 transition-all">
                <i class="fa-solid fa-file-pen mr-3 w-6 text-center"></i><span>Metin Analiz</span></a>
            <a href="/soru-uretim" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-green-500 hover:bg-green-600 transition-all">
                <i class="fa-solid fa-circle-question mr-3 w-6 text-center"></i><span>Soru Üretim</span></a>
            <a href="/metin-olusturma" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-purple-500 hover:bg-purple-600 transition-all">
                <i class="fa-solid fa-wand-magic-sparkles mr-3 w-6 text-center"></i><span>Metin Oluşturma</span></a>
            <a id="link-haritada-bul" href="/haritada-bul" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-orange-500 hover:bg-orange-600 transition-all">
                <i class="fa-solid fa-map-location-dot mr-3 w-6 text-center"></i><span>Haritada Bul</span></a>
            <a href="/podcast_paneli" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-red-500 hover:bg-red-600 transition-all">
                <i class="fa-solid fa-microphone-lines mr-3 w-6 text-center"></i><span>Podcast Yap</span></a>
            <a id="link-seyret-bul" href="/seyret-bul-liste" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-indigo-500 hover:bg-indigo-600 transition-all">
                <i class="fa-solid fa-magnifying-glass-plus mr-3 w-6 text-center"></i><span>Seyret Bul</span></a>
            <a href="/yarisma-secim" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-teal-600 ring-2 ring-teal-300 transition-all">
                <i class="fa-solid fa-trophy mr-3 w-6 text-center"></i><span>Beceri/Değer Avcısı</span></a>
            <a id="link-video-istegi" href="/video-istegi" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-pink-500 hover:bg-pink-600 transition-all">
                <i class="fa-solid fa-video mr-3 w-6 text-center"></i><span>Video İsteği</span></a>
        </nav>
        <div class="p-4 border-t border-gray-200">
            <a href="/dashboard" class="flex items-center w-full p-3 rounded-lg text-gray-600 font-semibold bg-gray-100 hover:bg-gray-200 transition-all">
                <i class="fa-solid fa-arrow-left mr-3 w-6 text-center"></i><span>Panele Geri Dön</span></a>
        </div>
    </aside>

    <main class="ml-72 flex-1 p-6 md:p-8 overflow-y-auto no-bounce">
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
    </main>

    <script>
        document.addEventListener('DOMContentLoaded', async () => {
            // GÜNCELLENDİ (İstek 4): Sol Menü için Kullanıcı Adı Yükleme
            const userFullName = localStorage.getItem('loggedInUserName');
            const userRole = localStorage.getItem('loggedInUserRole'); 

            if (userFullName) {
                document.getElementById('user-name-placeholder').textContent = userFullName;
                document.getElementById('user-avatar-initial').textContent = userFullName[0] ? userFullName[0].toUpperCase() : 'K';
            }
            // GÜNCELLENDİ (İstek 4): Sol Menü Rol Kontrolü
            const linkMetinAnaliz = document.getElementById('link-metin-analiz');
            const linkSoruUretim = document.getElementById('link-soru-uretim');
            const linkMetinOlusturma = document.getElementById('link-metin-olusturma');
            const linkHaritadaBul = document.getElementById('link-haritada-bul');
            const linkPodcast = document.getElementById('link-podcast');
            const linkSeyretBul = document.getElementById('link-seyret-bul');
            const linkYarisma = document.getElementById('link-yarisma');
            const linkVideoIstegi = document.getElementById('link-video-istegi');

            if (userRole === 'teacher') {
                if (linkMetinAnaliz) linkMetinAnaliz.style.display = 'none';
                if (linkSeyretBul) linkSeyretBul.style.display = 'none';
                if (linkHaritadaBul) linkHaritadaBul.style.display = 'none'; 
            } else {
                if (linkMetinOlusturma) linkMetinOlusturma.style.display = 'none';
            }
            // --- BİTTİ ---

            // Liderlik tablosu içeriğini yükle
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
    <style> 
        /* GÜNCELLENDİ (İstek 4): Artık 'flex' kullanıyor */
        body { font-family: 'Inter', sans-serif; background-color: #f3f4f6; } 
    </style>
</head>
<body class="flex h-screen"> <aside class="w-72 bg-white text-gray-800 shadow-lg flex flex-col fixed h-full">
        <div class="px-6 py-4 border-b border-gray-200">
            <h1 class="text-2xl font-extrabold text-blue-600 text-center tracking-wide mb-4">Maarif SosyalLab</h1>
            <div class="mb-4">
                <div class="w-full p-2 flex items-center justify-center overflow-hidden">
                    <img src="/videolar/maarif.png" alt="Maarif Logo" class="w-auto h-auto max-w-full max-h-24 object-contain rounded-lg">
                </div>
            </div>
            <div class="flex items-center">
                <div id="user-avatar-initial" class="w-10 h-10 rounded-full bg-cyan-500 flex items-center justify-center text-white font-bold text-lg">K</div>
                <div class="ml-3"><span id="user-name-placeholder" class="block text-sm font-bold text-gray-800">Kullanıcı</span></div>
            </div>
        </div>
        <nav class="flex-1 overflow-y-auto p-4 space-y-2 no-bounce">
            <a id="link-metin-analiz" href="/metin-analiz" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-blue-500 hover:bg-blue-600 transition-all">
                <i class="fa-solid fa-file-pen mr-3 w-6 text-center"></i><span>Metin Analiz</span></a>
            <a href="/soru-uretim" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-green-500 hover:bg-green-600 transition-all">
                <i class="fa-solid fa-circle-question mr-3 w-6 text-center"></i><span>Soru Üretim</span></a>
            <a href="/metin-olusturma" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-purple-500 hover:bg-purple-600 transition-all">
                <i class="fa-solid fa-wand-magic-sparkles mr-3 w-6 text-center"></i><span>Metin Oluşturma</span></a>
            <a id="link-haritada-bul" href="/haritada-bul" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-orange-500 hover:bg-orange-600 transition-all">
                <i class="fa-solid fa-map-location-dot mr-3 w-6 text-center"></i><span>Haritada Bul</span></a>
            <a href="/podcast_paneli" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-red-500 hover:bg-red-600 transition-all">
                <i class="fa-solid fa-microphone-lines mr-3 w-6 text-center"></i><span>Podcast Yap</span></a>
            <a id="link-seyret-bul" href="/seyret-bul-liste" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-indigo-500 hover:bg-indigo-600 transition-all">
                <i class="fa-solid fa-magnifying-glass-plus mr-3 w-6 text-center"></i><span>Seyret Bul</span></a>
            <a href="/yarisma-secim" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-teal-600 ring-2 ring-teal-300 transition-all">
                <i class="fa-solid fa-trophy mr-3 w-6 text-center"></i><span>Beceri/Değer Avcısı</span></a>
            <a id="link-video-istegi" href="/video-istegi" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-pink-500 hover:bg-pink-600 transition-all">
                <i class="fa-solid fa-video mr-3 w-6 text-center"></i><span>Video İsteği</span></a>
        </nav>
        <div class="p-4 border-t border-gray-200">
            <a href="/dashboard" class="flex items-center w-full p-3 rounded-lg text-gray-600 font-semibold bg-gray-100 hover:bg-gray-200 transition-all">
                <i class="fa-solid fa-arrow-left mr-3 w-6 text-center"></i><span>Panele Geri Dön</span></a>
        </div>
    </aside>

    <main class="ml-72 flex-1 p-6 md:p-8 overflow-y-auto no-bounce">
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
    </main>

    <script>
        document.addEventListener('DOMContentLoaded', async () => {
            // GÜNCELLENDİ (İstek 4): Sol Menü için Kullanıcı Adı Yükleme
            const userFullName = localStorage.getItem('loggedInUserName');
            const userRole = localStorage.getItem('loggedInUserRole'); 

            if (userFullName) {
                document.getElementById('user-name-placeholder').textContent = userFullName;
                document.getElementById('user-avatar-initial').textContent = userFullName[0] ? userFullName[0].toUpperCase() : 'K';
            }
            // GÜNCELLENDİ (İstek 4): Sol Menü Rol Kontrolü
            const linkMetinAnaliz = document.getElementById('link-metin-analiz');
            const linkSoruUretim = document.getElementById('link-soru-uretim');
            const linkMetinOlusturma = document.getElementById('link-metin-olusturma');
            const linkHaritadaBul = document.getElementById('link-haritada-bul');
            const linkPodcast = document.getElementById('link-podcast');
            const linkSeyretBul = document.getElementById('link-seyret-bul');
            const linkYarisma = document.getElementById('link-yarisma');
            const linkVideoIstegi = document.getElementById('link-video-istegi');

            if (userRole === 'teacher') {
                if (linkMetinAnaliz) linkMetinAnaliz.style.display = 'none';
                if (linkSeyretBul) linkSeyretBul.style.display = 'none';
                if (linkHaritadaBul) linkHaritadaBul.style.display = 'none'; 
            } else {
                if (linkMetinOlusturma) linkMetinOlusturma.style.display = 'none';
            }
            // --- BİTTİ ---

            // Liderlik tablosu içeriğini yükle
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
VIDEO_ISTEGI_PAGE_HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Video İstek Paneli</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style> 
    body { font-family: 'Inter', sans-serif; background-color: #f3f4f6; } 
    /* YENİ EKLENDİ: Limit aşılırsa sayacı kırmızı yapar */
    #word-count.over-limit { color: #ef4444; font-weight: 600; }
    #gonder-btn:disabled { background-color: #9ca3af; cursor: not-allowed; }

    /* YENİ EKLENEN KURAL */
    .no-bounce {
        overscroll-behavior: none;
    }
</style>
</head>
<body class="flex h-screen">
    
    <aside class="w-72 bg-white text-gray-800 shadow-lg flex flex-col fixed h-full">
        <div class="px-6 py-4 border-b border-gray-200">
            <h1 class="text-2xl font-extrabold text-blue-600 text-center tracking-wide mb-4">Maarif SosyalLab</h1>
            <div class="mb-4">
                <div class="w-full p-2 flex items-center justify-center overflow-hidden">
                    <img src="/videolar/maarif.png"  
                         alt="Maarif Logo" 
                         class="w-auto h-auto max-w-full max-h-24 object-contain rounded-lg">
                </div>
            </div>
            <div class="flex items-center">
                <div id="user-avatar-initial" class="w-10 h-10 rounded-full bg-cyan-500 flex items-center justify-center text-white font-bold text-lg">K</div>
                <div class="ml-3"><span id="user-name-placeholder" class="block text-sm font-bold text-gray-800">Kullanıcı</span></div>
            </div>
        </div>
        
       <nav class="flex-1 overflow-y-auto p-4 space-y-2 no-bounce">

            <a id="link-metin-analiz" href="/metin-analiz" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-blue-500 hover:bg-blue-600 transition-all">
                <i class="fa-solid fa-file-pen mr-3 w-6 text-center"></i>
                <span>Metin Analiz</span>
            </a>
            <a id="link-soru-uretim" href="/soru-uretim" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-green-500 hover:bg-green-600 transition-all">
                <i class="fa-solid fa-circle-question mr-3 w-6 text-center"></i>
                <span>Soru Üretim</span>
            </a>
            <a id="link-metin-olusturma" href="/metin-olusturma" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-purple-500 hover:bg-purple-600 transition-all">
                <i class="fa-solid fa-wand-magic-sparkles mr-3 w-6 text-center"></i>
                <span>Metin Oluşturma</span>
            </a>
            <a id="link-haritada-bul" href="/haritada-bul" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-orange-500 hover:bg-orange-600 transition-all">
                <i class="fa-solid fa-map-location-dot mr-3 w-6 text-center"></i>
                <span>Haritada Bul</span>
            </a>
            <a id="link-podcast" href="/podcast_paneli" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-red-500 hover:bg-red-600 transition-all">
                <i class="fa-solid fa-microphone-lines mr-3 w-6 text-center"></i>
                <span>Podcast Yap</span>
            </a>
            <a id="link-seyret-bul" href="/seyret-bul-liste" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-indigo-500 hover:bg-indigo-600 transition-all">
                <i class="fa-solid fa-magnifying-glass-plus mr-3 w-6 text-center"></i>
                <span>Seyret Bul</span>
            </a>
            <a id="link-yarisma" href="/yarisma-secim" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-teal-600 ring-2 ring-teal-300 transition-all">
                <i class="fa-solid fa-trophy mr-3 w-6 text-center"></i>
                <span>Beceri/Değer Avcısı</span>
            </a>
            <a id="link-video-istegi" href="/video-istegi" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-pink-500 hover:bg-pink-600 transition-all">
                <i class="fa-solid fa-video mr-3 w-6 text-center"></i>
                <span>Video İsteği</span>
            </a>

        </nav>
        <div class="p-4 border-t border-gray-200">
            <a href="/dashboard" class="flex items-center w-full p-3 rounded-lg text-gray-600 font-semibold bg-gray-100 hover:bg-gray-200 transition-all">
                <i class="fa-solid fa-arrow-left mr-3 w-6 text-center"></i>
                <span>Panele Geri Dön</span>
            </a>
        </div>
    </aside>

    <main class="ml-72 flex-1 p-6 md:p-8 overflow-y-auto no-bounce">
        <h2 class="text-3xl font-bold text-gray-800 mb-6">Video İstek Paneli</h2>
        
        <div class="bg-white p-6 rounded-lg shadow max-w-2xl">
            <p class="text-gray-600 mb-4">
                Oluşturulmasını istediğiniz video içeriğinin metnini veya konusunu (En fazla 800 kelime) buraya yazarak panel yöneticisine gönderebilirsiniz. 
            </p>
            
            <form id="istek-form">
                <label for="istek-metni" class="block text-sm font-medium text-gray-700 mb-2">İstek Metni:</label>
                <textarea id="istek-metni" rows="10" class="w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-pink-500" placeholder="Lütfen videonun konusunu, kazanımını ve mümkünse örnek metnini buraya yapıştırın..."></textarea>
                
                <div id="word-count" class="text-right text-sm text-gray-500 mt-1">0 / 800 kelime</div>
                
                <div id="form-mesaj" class="mt-4 text-sm font-semibold"></div>
                
                <button type="submit" id="gonder-btn" class="w-full mt-4 bg-pink-500 text-white font-bold py-3 px-6 rounded-lg text-lg shadow-lg hover:bg-pink-600 transition-all duration-300 flex items-center justify-center" disabled>
                    <i class="fa-solid fa-paper-plane mr-2"></i>
                    <span>İsteği Gönder</span>
                </button>
            </form>
        </div>
    </main>
    
    <script>
        document.addEventListener('DOMContentLoaded', () => {
            const userFullName = localStorage.getItem('loggedInUserName') || 'Öğretmen';
            const userRole = localStorage.getItem('loggedInUserRole');
            
            // --- Kullanıcı Adını Ayarla ---
            document.getElementById('user-name-placeholder').textContent = userFullName;
            document.getElementById('user-avatar-initial').textContent = userFullName[0] ? userFullName[0].toUpperCase() : 'K';
            
            // --- Rol Kontrolü (STANDART) ---
            const linkMetinAnaliz = document.getElementById('link-metin-analiz');
            const linkSoruUretim = document.getElementById('link-soru-uretim');
            const linkMetinOlusturma = document.getElementById('link-metin-olusturma');
            const linkHaritadaBul = document.getElementById('link-haritada-bul');
            const linkPodcast = document.getElementById('link-podcast');
            const linkSeyretBul = document.getElementById('link-seyret-bul');
            const linkYarisma = document.getElementById('link-yarisma');
            const linkVideoIstegi = document.getElementById('link-video-istegi');
             if (userRole === 'teacher') {
                // --- ÖĞRETMEN GÖRÜNÜMÜ ---
                if (linkMetinAnaliz) linkMetinAnaliz.style.display = 'none';
                if (linkSeyretBul) linkSeyretBul.style.display = 'none';
                if (linkHaritadaBul) linkHaritadaBul.style.display = 'none'; 
            } else {
                // --- ÖĞRENCİ GÖRÜNÜMÜ ---
                if (linkMetinOlusturma) linkMetinOlusturma.style.display = 'none';
                // HATALI SATIR BURADAN SİLİNDİ
            }

            // --- Form Gönderme ---
            const istekForm = document.getElementById('istek-form');
            const gonderBtn = document.getElementById('gonder-btn');
            const formMesaj = document.getElementById('form-mesaj');
            const istekMetni = document.getElementById('istek-metni');
            
            // --- YENİ EKLENDİ: Kelime Sayacı ve Buton Kontrolü ---
            const wordCountDisplay = document.getElementById('word-count');
            const wordLimit = 800;
            const minWordLimit = 10; // En az 10 kelime olsun

            istekMetni.addEventListener('input', () => {
                const text = istekMetni.value.trim();
                const words = text.split(/\\s+/).filter(Boolean);
                const wordCount = words.length;
                
                wordCountDisplay.textContent = `${wordCount} / ${wordLimit} kelime`;
                
                if (wordCount > wordLimit) {
                    gonderBtn.disabled = true;
                    wordCountDisplay.classList.add('over-limit');
                    formMesaj.textContent = "Hata: İstek metni 800 kelime limitini aşıyor.";
                    formMesaj.className = "mt-4 text-sm font-semibold text-red-600";
                } else if (wordCount < minWordLimit) {
                    gonderBtn.disabled = true;
                    wordCountDisplay.classList.remove('over-limit');
                    if (wordCount > 0) { // Sadece bir şey yazmaya başladıysa mesaj göster
                         formMesaj.textContent = "Lütfen en az 10 kelime girin.";
                         formMesaj.className = "mt-4 text-sm font-semibold text-yellow-600";
                    }
                } else {
                    gonderBtn.disabled = false;
                    wordCountDisplay.classList.remove('over-limit');
                    formMesaj.textContent = "";
                }
            });
            
            // Sayfa yüklendiğinde sayacı çalıştır (buton disabled başlar)
            istekMetni.dispatchEvent(new Event('input')); 
            // --- Kelime Sayacı Bitti ---

            istekForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const metin = istekMetni.value.trim();
                
                if (metin.length === 0 || gonderBtn.disabled) return;
                
                gonderBtn.disabled = true;
                gonderBtn.textContent = "Gönderiliyor...";
                
                // --- YENİ EKLENDİ: Tüm kullanıcı verisini localStorage'dan oku ---
                const gonderen_isim = localStorage.getItem('loggedInUserName') || 'Bilinmiyor';
                const gonderen_rol = localStorage.getItem('loggedInUserRole') || 'Bilinmiyor';
                const gonderen_no = localStorage.getItem('loggedInUserNo') || '';
                
                // --- GÜNCELLENDİ: Rol fark etmeksizin okul/sınıf bilgisini al ---
                // (Adım 2'de öğrenci için de kaydetmeyi eklediğimiz için bu artık çalışacak)
                let gonderen_okul = localStorage.getItem('loggedInUserSchool') || '';
                let gonderen_sinif = localStorage.getItem('loggedInUserClass') || '';
                // --- BİTTİ ---

                try {
                    const response = await fetch('/api/video-istegi-gonder', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        
                        // --- GÜNCELLENDİ: Tüm veriyi API'ye gönder ---
                        body: JSON.stringify({ 
                            istek_metni: metin,
                            isteyen_ogretmen: gonderen_isim, // Bu, 'isim' alanı için kullanılıyor
                            kullanici_rol: gonderen_rol,
                            kullanici_no: gonderen_no,
                            kullanici_okul: gonderen_okul,
                            kullanici_sinif: gonderen_sinif
                        })
                        // --- GÜNCELLEME BİTTİ ---
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        formMesaj.textContent = "İsteğiniz başarıyla yöneticiye iletildi. Teşekkür ederiz!";
                        formMesaj.className = "mt-4 text-sm font-semibold text-green-600";
                        istekMetni.value = ""; // Kutuyu temizle
                        istekMetni.dispatchEvent(new Event('input')); // Sayacı sıfırla
                    } else {
                        formMesaj.textContent = `Hata: ${result.hata || 'Bilinmeyen bir sorun oluştu.'}`;
                        formMesaj.className = "mt-4 text-sm font-semibold text-red-600";
                    }
                    
                } catch (error) {
                    formMesaj.textContent = "Sunucuyla iletişim kurulamadı.";
                    formMesaj.className = "mt-4 text-sm font-semibold text-red-600";
                } finally {
                    gonderBtn.textContent = "İsteği Gönder";
                }
            });
        });
    </script>
</body>
</html>
"""
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
            # print(f"📡 Ping alındı: {student_no}") # İsterseniz bu satırı açıp siyah ekranda takip edebilirsiniz
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
    return render_template_string(HTML_CONTENT)

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
                user_data.get('password') == password_input):
                
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
                user_data.get('password') == password):
                
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
                user_data.get('password') == password):
                
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
        save_users(users) 
        return jsonify({'success': True, 'message': 'Öğrenci kaydı başarılı! Giriş yapabilirsiniz.'})
    
    except Exception as e:
        print(f"Öğrenci kayıt hatası: {e}")
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
        save_users(users) 
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
            # Admin'in 'class' (sınıf) alanı yok
        }
        save_users(users) 
        return jsonify({'success': True, 'message': 'Yönetici kaydı başarılı! Giriş yapabilirsiniz.'})
    
    except Exception as e:
        print(f"Yönetici kayıt hatası: {e}")
        return jsonify({'success': False, 'message': str(e)})

# --- KAYIT ROTALARI BİTTİ ---

# Dashboard sayfası
@app.route('/dashboard')
def dashboard():
    print("Dashboard sayfasına erişim sağlandı")
    return render_template_string(DASHBOARD_HTML_CONTENT)

# --- Metin Oluşturma Rotaları ---
@app.route('/metin-olusturma')
def metin_olusturma_page():
    """Metin oluşturma sayfasını render eder."""
    print("Metin Oluşturma sayfasına erişim sağlandı")
    
    # Modelin yüklenip yüklenmediğini kontrol edelim (iyi bir pratiktir)
    global gemini_model
    if not gemini_model:
        try:
            # Modeli yüklemeyi dene (API anahtarı önceden ayarlanmış olmalı)
            gemini_model = metin_uretim.api_yapilandir(app.config.get('GEMINI_API_KEY', ''))
            if not gemini_model:
                print("Metin oluşturma sayfasında model yüklenemedi.")
                # 'flash' ve 'redirect' kullanabilmek için 'from flask import flash, redirect, url_for' eklediğinizden emin olun
                flash("Sunucu hatası: Gemini modeli yüklenemedi.", "danger")
                #return redirect(url_for('index')) # veya ana sayfa
        except Exception as e:
            print(f"Model yükleme hatası: {e}")
            flash(f"Sunucu hatası: {e}", "danger")
            #return redirect(url_for('index'))

    return render_template_string(
        METIN_URETIM_PAGE_HTML,
        prompt_sablonlari=metin_uretim.PROMPT_SABLONLARI,
        metin_tipleri=metin_uretim.PROMPT_SABLONLARI  # Bunu ekle
    )

@app.route('/api/generate-text', methods=['POST'])
def api_generate_text():
    """AJAX isteği ile metin üretir."""
    try:
        global gemini_model
        if not gemini_model:
            return jsonify({"success": False, "metin": "Sunucuda Gemini API Anahtarı yapılandırılmamış veya yüklenememiş!", "kelime_sayisi": 0, "uyari": ""})

        data = request.get_json()
        
        # --- YENİ YAPIYA GÖRE GÜNCELLENDİ ---
        bilesen_kodu = data.get('bilesen_kodu')
        metin_tipi_adi = data.get('metin_tipi_adi') # 'tip_adi' -> 'metin_tipi_adi' olarak değişti
        
        # 'konu_adi' kaldırıldı.
        print(f"Metin üretme isteği: {bilesen_kodu}, {metin_tipi_adi}")
        
        # Parametre kontrolü güncellendi
        if not bilesen_kodu or not metin_tipi_adi:
             return jsonify({"success": False, "metin": "Eksik parametre: Süreç Bileşeni veya Metin Tipi seçilmedi."})
        
        # metin_uretim.py'daki (yeni) fonksiyonu çağırıyoruz
        # İmza değişti: (bilesen_kodu, metin_tipi_adi, model)
        # Not: gemini_model'i ilk parametre olarak gönderen eski yapıyı düzelttim.
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
    return render_template_string(METIN_ANALIZ_PAGE_HTML)

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
    return render_template_string(
        SORU_URETIM_PAGE_HTML,
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
    return render_template_string(YARISMA_SECIM_PAGE_HTML)

# --- Bireysel Yarışma Rotaları (YENİ) ---

@app.route('/bireysel-yarisma')
def bireysel_yarisma_page():
    print("Bireysel Yarışma sayfasına erişim sağlandı")
    # Artık boş değil, gerçek oyun arayüzünü (V6) render ediyoruz
    return render_template_string(BIREYSEL_YARISMA_HTML)

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
    return render_template_string(LEADERBOARD_PAGE_HTML)

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
    return render_template_string(TAKIM_YARISMA_HTML)
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
            save_users(users) 
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
            save_users(users) 
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
            save_users(users) 
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
        
        save_users(users) 
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

@app.route('/podcast_paneli')
def podcast_paneli():
    """Podcast oluşturucu arayüzünü (HTML) doğrudan sunar."""

    # HTML, CSS ve JS kodunu tek bir f-string olarak döndür
    html_content = f"""
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Podcast Oluşturucu</title>
        <!-- Bu sayfada soldaki menüyü göstermek için bu stilleri ekliyoruz -->
        <script src="https://cdn.tailwindcss.com"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
        <style>
            body {{ 
                font-family: 'Inter', sans-serif;
                background-color: #f3f4f6;
            }}
            .podcast-container {{
                max-width: 700px; margin: 40px auto; padding: 30px;
                background-color: #ffffff; border-radius: 10px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
            }}
            .podcast-container h1 {{ color: #005a9c; margin-bottom: 25px; text-align: center; }}
            .podcast-container textarea {{
                width: 100%; height: 250px; padding: 12px; font-size: 15px;
                border-radius: 6px; border: 1px solid #ddd;
                margin-bottom: 10px; box-sizing: border-box; resize: vertical;
            }}
            .podcast-container button {{
                width: 100%; padding: 12px; font-size: 16px;
                background-color: #007bff; color: white; font-weight: bold;
                cursor: pointer; border: none; border-radius: 6px;
            }}
            #word-count.over-limit {{ color: red; font-weight: bold; }}
        </style>
    </head>
    <body class="flex h-screen">

        <!-- Sol Menü -->
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
            <nav class="flex-1 overflow-y-auto p-4 space-y-2 no-bounce">
                <a id="link-metin-analiz" href="/metin-analiz" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-blue-500 hover:bg-blue-600 transition-all">
                    <i class="fa-solid fa-file-pen mr-3 w-6 text-center"></i><span>Metin Analiz</span></a>
                <a id="link-soru-uretim" href="/soru-uretim" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-green-500 hover:bg-green-600 transition-all">
                    <i class="fa-solid fa-circle-question mr-3 w-6 text-center"></i><span>Soru Üretim</span></a>
                <a id="link-metin-olusturma" href="/metin-olusturma" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-purple-500 hover:bg-purple-600 transition-all">
                    <i class="fa-solid fa-wand-magic-sparkles mr-3 w-6 text-center"></i><span>Metin Oluşturma</span></a>
                <a id="link-haritada-bul" href="/haritada-bul" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-orange-500 hover:bg-orange-600 transition-all">
                    <i class="fa-solid fa-map-location-dot mr-3 w-6 text-center"></i><span>Haritada Bul</span></a>
                <a id="link-podcast" href="/podcast_paneli" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-red-600 ring-2 ring-red-300 transition-all">
                    <i class="fa-solid fa-microphone-lines mr-3 w-6 text-center"></i><span>Podcast Yap</span></a>
                <a id="link-seyret-bul" href="/seyret-bul-liste" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-indigo-500 hover:bg-indigo-600 transition-all">
                    <i class="fa-solid fa-magnifying-glass-plus mr-3 w-6 text-center"></i><span>Seyret Bul</span></a>
                <a id="link-yarisma" href="/yarisma-secim" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-teal-500 hover:bg-teal-600 transition-all">
                    <i class="fa-solid fa-trophy mr-3 w-6 text-center"></i><span>Beceri/Değer Avcısı</span></a>
                <a id="link-video-istegi" href="/video-istegi" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-pink-500 hover:bg-pink-600 transition-all">
                    <i class="fa-solid fa-video mr-3 w-6 text-center"></i><span>Video İsteği</span></a>
            </nav>
            <div class="p-4 border-t border-gray-200">
                <a href="/dashboard" class="flex items-center w-full p-3 rounded-lg text-gray-600 font-semibold bg-gray-100 hover:bg-gray-200 transition-all">
                    <i class="fa-solid fa-arrow-left mr-3 w-6 text-center"></i><span>Panele Geri Dön</span></a>
            </div>
        </aside>

        <!-- Ana İçerik -->
            <main class="ml-72 flex-1 p-6 md:p-8 overflow-y-auto no-bounce">
            
            <h2 class="text-3xl font-bold text-gray-800 mb-6">Podcast Oluşturucu</h2>
            
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div class="lg:col-span-1 bg-white p-6 rounded-lg shadow">
                    
                    <p class="text-gray-600 mb-4">Lütfen "sohbet podcasti" yapılacak metni (En fazla 600 kelime) aşağıya yapıştırın.</p>

                    <form id="podcast-form">
                        <textarea id="text-input" 
                                  name="text_content"
                                  class="w-full h-48 p-3 border border-gray-300 rounded-lg"
                                  placeholder="Metninizi buraya yapıştırın..."></textarea>

                        <div id="word-count" class="text-right text-sm text-gray-500 mt-1">0 / 600 kelime</div>

                        <button id="generate-btn" type="submit" class="w-full mt-4 bg-red-500 text-white font-bold py-3 px-6 rounded-lg text-lg shadow-lg hover:bg-red-600 transition-all">
                            Sohbet Podcasti Oluştur
                        </button>
                    </form>

                    <div id="podcast-status" class="mt-4 font-semibold text-gray-700"></div>
                </div>

                <div class="lg:col-span-1 bg-white p-6 rounded-lg shadow min-h-[300px]">
                    <h3 class="text-xl font-semibold text-gray-800 mb-4">Podcast Oynatıcı</h3>
                    
                    <div id="podcast-player-container" class="mt-4 p-4 border-t border-gray-200" style="display: none;">
                        <p class="text-sm text-gray-500 mb-3">Ses dosyası yüklendiğinde oynatıcı burada görünecektir.</p>
                        <audio id="audio-player" controls class="w-full"></audio>
                    </div>

                    <div id="player-placeholder" class="text-center text-gray-500 p-8">
                        <i class="fa-solid fa-microphone-lines text-4xl mb-3"></i>
                        <p>Podcast oluşturulduktan sonra burada dinleyebilirsiniz.</p>
                    </div>
                </div>
            </div>
        </main>
      
        <script>
            (function() {{
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

                // --- Podcast Mantığı ---
                const form = document.getElementById('podcast-form');
                const textArea = document.getElementById('text-input');
                const wordCountDisplay = document.getElementById('word-count');
                const button = document.getElementById('generate-btn');
                const status = document.getElementById('podcast-status');
                const playerContainer = document.getElementById('podcast-player-container');
                let audioPlayer = document.getElementById('audio-player'); // let olarak tanımla
                
                const wordLimit = 600;

                // --- 1. Kelime Sayacı ---
                textArea.addEventListener('input', function() {{
                    const text = textArea.value;
                    const words = text.split(/\\s+/).filter(Boolean);
                    const wordCount = words.length;
                    wordCountDisplay.textContent = `${{wordCount}} / ${{wordLimit}} kelime`;

                    if (wordCount > wordLimit || wordCount === 0) {{
                        wordCountDisplay.classList.add('over-limit');
                        button.disabled = true;
                    }} else {{
                        wordCountDisplay.classList.remove('over-limit');
                        button.disabled = false;
                    }}
                }});
                textArea.dispatchEvent(new Event('input')); 

                // --- 2. Form Gönderme (Piper'ı Çalıştır ve WAV Al) ---
                form.addEventListener('submit', async function(event) {{
                    event.preventDefault();
                    
                    const userText = textArea.value.trim();
                    if (!userText || textArea.value.split(/\\s+/).filter(Boolean).length > wordLimit) return;

                    button.disabled = true;
                    button.textContent = "Podcast'iniz Hazırlanıyor";
                    status.textContent = "Lütfen bekleyin, bu işlem 5-30 saniye sürebilir.";
                    playerContainer.style.display = 'none';

                    try {{
                        // API'yi çağır (Piper'ın çalıştığı yer)
                        const response = await fetch('/generate-podcast', {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify({{ text: userText }}), 
                        }});

                        const data = await response.json();

                        // Burası yapıştırılacak yerin TAMAMI (if (response.ok && data.success) {{ bloğu)
                        if (response.ok && data.success) {{
                            status.textContent = "✅ Podcast başarıyla oluşturuldu! Ses yükleniyor...";
                            
                            // -----------------------------------------------------
                            // ÇÖZÜM: Oynatıcıyı her seferinde yeniden oluştur (Flask önbellek sorununu aşmak için)
                            // Eski oynatıcıyı kaldırıyoruz
                            if (audioPlayer && audioPlayer.parentNode) {{ // Kontrol eklendi
                                audioPlayer.parentNode.removeChild(audioPlayer); 
                            }}
                            
                            // Yeni oynatıcıyı oluşturuyoruz
                            const newAudioPlayer = document.createElement('audio');
                            newAudioPlayer.id = 'audio-player';
                            newAudioPlayer.controls = true;
                            newAudioPlayer.className = 'w-full';
                            
                            // Önbellek sorununu aşmak için time stamp ekleniyor:
                            const timestampedUrl = data.audio_url + '?' + new Date().getTime();
                            newAudioPlayer.src = timestampedUrl;
                            
                            // Yeni oynatıcıyı konteynere ekle
                            playerContainer.appendChild(newAudioPlayer);
                            audioPlayer = newAudioPlayer; // <--- KRİTİK: Global değişkeni YENİ oynatıcıya atama
                            // -----------------------------------------------------
                            
                            // Yeni kodda eklenmesi gereken event listener'lar:
                            newAudioPlayer.addEventListener('loadeddata', () => {{
                            let successMsg = "✅ Podcast başarıyla oluşturuldu! Ses çalmaya hazır."; // Varsayılan mesaj
                            
                            // Adım 3'te yolladığımız 'validation_data'yı kontrol et
                            if (data.validation_data && data.validation_data.uyumlu_bilesenler && data.validation_data.uyumlu_bilesenler.length > 0) {{
                                // Bileşen kodlarını "SB.5.1.1 ve SB.5.1.2" şeklinde birleştir
                                const bilesenlerStr = data.validation_data.uyumlu_bilesenler.join(' ve ');
                                
                                // DİKKAT: JavaScript'in ${...} ifadesi de {{...}} oldu
                                successMsg = `✅ Verdiğiniz metin ${{bilesenlerStr}} süreç bileşen(ler)i ile uyumlu olduğundan podcast'iniz başarıyla oluşturuldu! Ses çalmaya hazır.`;
                            }}
                            
                            status.textContent = successMsg; // Yeni mesajı ayarla
                            newAudioPlayer.play(); // Oynatmayı dene
                        }});
                            
                            newAudioPlayer.addEventListener('error', (e) => {{
                                status.textContent = "❌ HATA: Ses dosyası yüklenemedi. (Dosya eksik veya bozuk). Konsolu kontrol edin.";
                                console.error("Ses yükleme hatası:", e); // Tarayıcı konsoluna yazılacak
                            }});
                            
                            playerContainer.style.display = 'block';
                        }} else {{
                            // Piper veya Gemini'dan gelen hata mesajını göster
                            status.textContent = `❌ Hata: ${{data.error || "Bilinmeyen bir hata oluştu."}}`;
                        }}
                    }} catch (error) {{
                        status.textContent = `❌ Sunucu Hatası: Sunucuyla iletişim kurulamadı. ${{error.message}}`;
                    }} finally {{
                        // Butonu eski haline getir
                        const currentWordCount = textArea.value.split(/\\s+/).filter(Boolean).length;
                        if (currentWordCount <= wordLimit && currentWordCount > 0) {{
                            button.disabled = false;
                        }}
                        button.textContent = "Sohbet Podcasti Oluştur";
                    }}
                }});

            }})();
        </script>
    </body>
    </html>
    """
    return render_template_string(html_content)

@app.route('/generate-podcast', methods=['POST'])
def handle_generation():
    data = request.get_json()
    user_text = data.get('text')
    
    if not user_text:
        return jsonify({"success": False, "error": "Metin boş olamaz."}), 400

    try:
        # --- YENİ ADIM 1: Metin Uygunluğunu Kontrol Et ---
        print("🔵 1. Metnin müfredata uygunluğu kontrol ediliyor...")
        global gemini_model # Modeli globalden al
        validation_result = validate_text_relevance(user_text, gemini_model)
        
        if not validation_result.get("success"):
            # Analiz API'sinde bir hata oldu
            return jsonify(validation_result), 500

        uygunluk_yuzdesi = validation_result.get("uygunluk_yuzdesi", 0)
        aciklama = validation_result.get("aciklama", "Açıklama yok.")

        if uygunluk_yuzdesi < 70:
            print(f"❌ Metin reddedildi. Uygunluk: {uygunluk_yuzdesi}%")
            # Metin uygun değil, podcast üretme.
            return jsonify({
                "success": False, 
                "error": f"Metin Reddedildi (Uygunluk: {uygunluk_yuzdesi}%). \n\nAçıklama: {aciklama}"
            }), 400 # 400 "Bad Request" (Kullanıcı hatası)
        
        print(f"✅ Metin onaylandı. (Uygunluk: {uygunluk_yuzdesi}%)")
        # --- Kontrol Bitti ---

        print("🔵 2. Gemini ile podcast metni oluşturuluyor...")
        podcast_text = podcast_creator.generate_podcast_content(user_text, gemini_model)
        
        if not podcast_text:
            return jsonify({"success": False, "error": "Gemini'den boş yanıt alındı."}), 500
        
        print(f"✅ Podcast metni oluşturuldu: {podcast_text[:100]}...")
        
        print("🔵 3. Piper ile ses dosyası oluşturuluyor...")
        audio_url = podcast_creator.convert_text_to_speech(podcast_text, app.static_folder)
        
        if not audio_url:
            return jsonify({"success": False, "error": "Piper TTS ses oluşturamadı."}), 500
        
        print(f"✅ Ses URL: {audio_url}")
        
        # YENİ: Başarılı yanıta, analiz sonucunu (validation_result) da ekliyoruz.
        return jsonify({
            "success": True, 
            "audio_url": audio_url,
            "validation_data": validation_result 
        })

    except Exception as e:
        print(f"❌ HATA: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
        
# ########## PODCAST ROTALARI BİTTİ ##########

# (Burası sosyallab.py dosyasının sonu, podcast rotalarından sonra)

# ########## SEYRET BUL ROTALARI (GÜNCELLENDİ) ##########

# LÜTFEN ESKİ @app.route('/seyret-bul-liste') BLOĞUNUN TAMAMINI SİLİP BUNU YAPIŞTIRIN

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
        
        print(f"DEBUG: Seyret Bul için {len(surecler_listesi)} süreç bileşeni yüklendi.")

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
                <nav class="flex-1 overflow-y-auto p-4 space-y-2 no-bounce">
                    <a id="link-metin-analiz" href="/metin-analiz" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-blue-500 hover:bg-blue-600 transition-all">
                        <i class="fa-solid fa-file-pen mr-3 w-6 text-center"></i><span>Metin Analiz</span></a>
                    <a id="link-soru-uretim" href="/soru-uretim" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-green-500 hover:bg-green-600 transition-all">
                        <i class="fa-solid fa-circle-question mr-3 w-6 text-center"></i><span>Soru Üretim</span></a>
                    <a id="link-metin-olusturma" href="/metin-olusturma" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-purple-500 hover:bg-purple-600 transition-all">
                        <i class="fa-solid fa-wand-magic-sparkles mr-3 w-6 text-center"></i><span>Metin Oluşturma</span></a>
                    <a id="link-haritada-bul" href="/haritada-bul" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-orange-500 hover:bg-orange-600 transition-all">
                        <i class="fa-solid fa-map-location-dot mr-3 w-6 text-center"></i><span>Haritada Bul</span></a>
                    <a id="link-podcast" href="/podcast_paneli" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-red-500 hover:bg-red-600 transition-all">
                        <i class="fa-solid fa-microphone-lines mr-3 w-6 text-center"></i><span>Podcast Yap</span></a>
                    <a id="link-seyret-bul" href="/seyret-bul-liste" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-indigo-600 ring-2 ring-indigo-300 transition-all">
                        <i class="fa-solid fa-magnifying-glass-plus mr-3 w-6 text-center"></i><span>Seyret Bul</span></a>
                    <a id="link-yarisma" href="/yarisma-secim" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-teal-500 hover:bg-teal-600 transition-all">
                        <i class="fa-solid fa-trophy mr-3 w-6 text-center"></i><span>Beceri/Değer Avcısı</span></a>
                    <a id="link-video-istegi" href="/video-istegi" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-pink-500 hover:bg-pink-600 transition-all">
                        <i class="fa-solid fa-video mr-3 w-6 text-center"></i><span>Video İsteği</span></a>
                </nav>
                <div class="p-4 border-t border-gray-200">
                    <a href="/dashboard" class="flex items-center w-full p-3 rounded-lg text-gray-600 font-semibold bg-gray-100 hover:bg-gray-200 transition-all">
                        <i class="fa-solid fa-arrow-left mr-3 w-6 text-center"></i><span>Panele Geri Dön</span></a>
                </div>
            </aside>
            
            <main class="ml-72 flex-1 p-6 md:p-8 overflow-y-auto no-bounce">
                
                <h2 id="main-title" class="text-3xl font-bold text-gray-800 mb-6 cursor-pointer select-none">Seyret Bul</h2>
                
                <div id="student-view" class="bg-white p-6 rounded-lg shadow max-w-5xl mx-auto">
    
                <div class="flex flex-col md:flex-row space-y-4 md:space-y-0 md:space-x-2 justify-center mb-4 mx-auto max-w-xl">
                    
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
                        
                        <div id="player" class="mb-1 w-full max-w-2xl mx-auto"></div> 
                        
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
    return render_template_string(SEYRET_BUL_IZLE_HTML, video_id=video_id)

@app.route('/api/seyret-bul/video-detay/<string:video_id>')
def api_video_detay(video_id):
    """Video detaylarını ve sorularını döndürür"""
    video = seyret_bul.video_detay_getir(video_id)
    if video:
        return jsonify({"success": True, "video": video})
    return jsonify({"success": False, "mesaj": "Video bulunamadı"})
    
# ########## YENİ EKLENDİ: SEYRET BUL (GEMINI ADMIN) ROTASI ##########
@app.route('/api/seyret-bul/admin/soru-uret', methods=['POST'])
def api_admin_soru_uret():
    """
    Yönetici panelinden gelen video metnini alır,
    seyret_bul.py'deki Gemini fonksiyonunu çağırır ve sonucu döndürür.
    """
    try:
        data = request.get_json()
        
        # Gerekli tüm alanları al
        surec_bileseni = data.get('surec_bileseni')
        baslik = data.get('baslik')
        video_url = data.get('video_url')
        video_metni = data.get('video_metni')
        admin_sifre = data.get('admin_sifre')
        video_sure_saniye = data.get('video_sure_saniye', 0) # Süre gelmezse 0

        if not all([surec_bileseni, baslik, video_url, video_metni, admin_sifre]):
            return jsonify({"success": False, "mesaj": "Tüm alanlar zorunludur."})
        
        # "İşçi" (seyret_bul.py) modülündeki ana Gemini fonksiyonunu çağır
        result = seyret_bul.sorular_uret_ve_kaydet(
            surec_bileseni=surec_bileseni,
            baslik=baslik,
            video_url=video_url,
            video_metni=video_metni,
            admin_sifre=admin_sifre,
           video_sure_saniye=video_sure_saniye
        )
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Gemini Soru Üretme API Hatası (sosyallab): {e}")
        return jsonify({"success": False, "mesaj": f"Sunucu Hatası (sosyallab): {str(e)}"})

@app.route('/api/seyret-bul/admin/lokal-video-yukle', methods=['POST'])
def api_lokal_video_yukle():
    """Lokal video yükleme ve soru üretme"""
    try:
        # Form verilerini al
        baslik = request.form.get('baslik')
        surec_bileseni = request.form.get('surec_bileseni')
        video_metni = request.form.get('video_metni')
        admin_sifre = request.form.get('admin_sifre')
        
        # Admin şifre kontrolü
        if admin_sifre != "97032647":
            return jsonify({"success": False, "mesaj": "Admin şifresi hatalı."})
        
        # Video dosyasını al
        video_file = request.files.get('video_dosya')
        if not video_file:
            return jsonify({"success": False, "mesaj": "Video dosyası yüklenmedi."})
        
        # Dosya adını güvenli hale getir
        import werkzeug
        filename = werkzeug.utils.secure_filename(video_file.filename)
        video_path = os.path.join('videolar', filename)
        
        # Videoyu kaydet
        video_file.save(video_path)
        
        # Video süresini hesapla
        video_sure = seyret_bul.get_video_duration(video_path)
        
        # Video URL'i (lokal)
        video_url = f"/videolar/{filename}"
        
        # Gemini ile soruları üret
        result = seyret_bul.sorular_uret_ve_kaydet(
            surec_bileseni=surec_bileseni,
            baslik=baslik,
            video_url=video_url,
            video_metni=video_metni,
            admin_sifre=admin_sifre,
            video_sure_saniye=video_sure
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"success": False, "mesaj": f"Hata: {str(e)}"})
        
@app.route('/api/seyret-bul/degerlendir', methods=['POST'])
def api_seyret_bul_degerlendir():
    """
    Kısa cevaplı soruları Gemini ile değerlendirmek için kullanılır.
    """
    try:
        # --- BU KISIMLARIN OLDUĞUNDAN EMİN OLUN ---
        data = request.get_json()
        soru_metni = data.get('soru_metni')
        kullanici_cevabi = data.get('kullanici_cevabi')

        if not soru_metni or not kullanici_cevabi:
            return jsonify({"success": False, "hata": "Soru metni veya cevap eksik."})

        # Global gemini_model'i al
        global gemini_model
        if not gemini_model:
            return jsonify({"success": False, "hata": "Sunucuda Gemini modeli yüklenemedi."})
        # --- KONTROL BİTTİ ---
            
        # Bu dosyanın (sosyallab_fixed.py) en sonundaki fonksiyonu çağır
        # Modeli bir parametre olarak iletiyoruz
        result = kisa_cevabi_degerlendir(soru_metni, kullanici_cevabi, gemini_model) # <--- SİZİN DÜZELTTİĞİNİZ SATIR (DOĞRU)
        
        return jsonify(result)

    except Exception as e:
        print(f"Kısa cevap API değerlendirme hatası: {e}")
        return jsonify({"success": False, "hata": str(e)})
      
@app.route('/api/seyret-bul/admin/get-all-videos', methods=['GET'])
def api_admin_get_all_videos():
    """
    Yönetim paneli için TÜM videoları JSON olarak döndürür.
    """
    try:
        videos = seyret_bul.videolari_yukle()
        # Sözlüğü listeye çevirip göndermek JS için daha kolay
        video_listesi = []
        for video_id, data in videos.items():
            data['video_id'] = video_id # ID'yi objenin içine ekle
            video_listesi.append(data)
        
        # En son eklenen en üste gelsin diye listeyi ters çevir
        video_listesi.reverse()
        return jsonify({"success": True, "videolar": video_listesi})
    except Exception as e:
        return jsonify({"success": False, "hata": str(e)})

@app.route('/api/seyret-bul/admin/sil-video', methods=['POST'])
def api_admin_sil_video():
    """
    Bir videoyu ID'sine göre siler.
    """
    try:
        data = request.get_json()
        video_id = data.get('video_id')
        admin_sifre = data.get('admin_sifre')

        if admin_sifre != "97032647": # (Koddaki admin şifresi)
            return jsonify({"success": False, "hata": "Admin şifresi hatalı."})
        
        if not video_id:
            return jsonify({"success": False, "hata": "Video ID eksik."})
            
        # seyret_bul.py'deki yeni helper fonksiyonumuzu çağır
        result = seyret_bul.videoyu_sil(video_id)
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Video silme API rotası hatası: {e}")
        return jsonify({"success": False, "hata": str(e)})
        
# ########## BİTTİ ##########
# ANA KAYIP FONKSİYON (sorular_uret_ve_kaydet)
# -------------------------------------------------------
from flask import current_app # Flask bağlamını kullanmak için eklenmelidir!

def sorular_uret_ve_kaydet(surec_bileseni, baslik, video_url, video_metni, admin_sifre, video_sure_saniye):
    """
    Video metnini ve bilgileri alır, Gemini ile soruları üretir ve kaydeder.
    Bu, /api/seyret-bul/admin/soru-uret rotası tarafından çağrılan eksik fonksiyondur.
    """
    
    # 1. Admin şifresi kontrolü 
    if admin_sifre != ADMIN_SIFRE:
        return {"success": False, "mesaj": "Admin şifresi hatalı."}

    # 2. Gemini modelini yapılandır
    try:
        # Flask'ın uygulamasından API key'i almayı dener.
        # Not: current_app kullanılabilmesi için 'from flask import current_app' import edilmelidir.
        gemini_api_key = os.environ.get("GEMINI_API_KEY") or current_app.config.get('GEMINI_API_KEY')
        model = api_yapilandir(gemini_api_key) 
    except Exception:
        model = api_yapilandir(os.environ.get("GEMINI_API_KEY")) 
        
    if not model:
        return {"success": False, "mesaj": "Gemini API anahtarı ayarlanmamış veya model yüklenemedi. (Lütfen anahtarınızı kontrol edin)."}
    
    # 3. Prompt oluştur
    prompt = soru_uretme_promptu_olustur(video_metni)
    
    # 4. API çağrısı ve JSON alma
    try:
        response = model.generate_content(prompt, request_options={'timeout': 90})
        soru_json = json_parse_et(response.text) 
    except Exception as e:
        hata_mesaji = str(e)
        if "response.prompt_feedback" in hata_mesaji:
            hata_mesaji = "Gemini güvenlik filtrelerine takıldı. Metni düzenleyin."
        elif "DeadlineExceeded" in hata_mesaji:
             hata_mesaji = "API isteği zaman aşımına uğradı. Tekrar deneyin."
             
        return {"success": False, "mesaj": f"Gemini API çağrısı hatası: {hata_mesaji}"}
    
    if not soru_json or 'sorular' not in soru_json or not isinstance(soru_json['sorular'], list):
        return {"success": False, "mesaj": "Gemini yanıtı işlenemedi (JSON formatı hatalı)."}

    # 5. Kayıt verisini hazırla
    video_id = video_id_olustur()
    # Thumbnail URL'sini oluştur
    thumbnail_url = video_url.replace("watch?v=", "embed/").split('&')[0].replace("youtube.com/", "img.youtube.com/vi/") + "/mqdefault.jpg"

    video_data = {
        "video_id": video_id,
        "surec_bileseni": surec_bileseni,
        "baslik": baslik,
        "url": video_url,
        "thumbnail_url": thumbnail_url,
        "sure_saniye": video_sure_saniye,
        "sorular": soru_json['sorular']
    }

    # 6. Kaydetme işlemi
    videos_dict = videolari_yukle() 
    videos_dict[video_id] = video_data

    if videolari_kaydet(videos_dict):
        return {"success": True, "mesaj": "Sorular başarıyla üretildi ve kaydedildi.", "video_id": video_id}
    else:
        return {"success": False, "mesaj": "Dosyaya yazma hatası (seyret_bul_videos.json)."}

# ########## ARTIK KULLANILMIYOR: Eski Manuel Ekleme Rotası ##########
# @app.route('/api/seyret-bul/video-ekle', methods=['POST'])
# def api_video_ekle():
#    ... (Bu rota artık yeni Gemini akışı için gerekli değil) ...
# ########## BİTTİ ##########


# ... [Geri kalan tüm rotalarınız - /api/takim/get_sinif_listesi, /upload_excel vb.] ...
# ...
# ########## SEYRET BUL İZLE SAYFASI HTML ##########
SEYRET_BUL_IZLE_HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <title>Seyret Bul - Video İzle</title>
    <style>
        body { font-family: Arial; margin: 20px; background: #f0f8ff; }
        #videoContainer { max-width: 800px; margin: 0 auto; }
        #soruModal { display: none; position: fixed; top: 50%; left: 50%; 
                     transform: translate(-50%, -50%); background: white; 
                     padding: 30px; border-radius: 10px; box-shadow: 0 0 20px rgba(0,0,0,0.3); 
                     z-index: 1000; min-width: 400px; }
        .cevap-btn { display: block; margin: 10px 0; padding: 10px; 
                     background: #007bff; color: white; border: none; 
                     border-radius: 5px; cursor: pointer; width: 100%; }
        .cevap-btn:hover { background: #0056b3; }
    </style>
</head>
<body>
    <div id="videoContainer">
        <h2 id="videoBaslik">Yükleniyor...</h2>
        <div id="player"></div>
    </div>
    
    <div id="soruModal">
        <h3 id="soruMetni"></h3>
        <div id="cevaplar"></div>
    </div>

    <script src="https://www.youtube.com/iframe_api"></script>
    <script>
        const VIDEO_ID = "{{ video_id }}";
        let player, videoData, sorular, currentSoruIndex = 0;

        fetch(`/api/seyret-bul/video-detay/${VIDEO_ID}`)
            .then(r => r.json())
            .then(data => {
                if(data.success) {
                    videoData = data.video;
                    document.getElementById('videoBaslik').textContent = videoData.baslik;
                    sorular = videoData.sorular.slice(0, 3);
                    sorular.sort((a,b) => a.duraklatma_saniyesi - b.duraklatma_saniyesi);
                    onYouTubeIframeAPIReady();
                }
            });

        function onYouTubeIframeAPIReady() {
            const ytId = videoData.url.match(/[?&]v=([^&]+)/)[1];
            player = new YT.Player('player', {
                height: '450',
                width: '800',
                videoId: ytId,
                events: { 'onStateChange': onPlayerStateChange }
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
                
                // Progress bar güncelle
                const progress = (currentTime / videoData.sure_saniye) * 100;
                document.getElementById('progress').style.width = `${progress}%`;
                
                if(currentTime >= soruZamani) {
                    // YouTube veya HTML5 için farklı pause
                    if (player.pauseVideo) {
                        player.pauseVideo();  // YouTube
                    } else {
                        player.pause();  // HTML5
                    }
                    showSoru(sorular[currentSoruIndex]);
                    clearInterval(interval);
                }
            }, 100);
        }

        function showSoru(soru) {
        // Eğer tip yoksa, default olarak çoktan seçmeli kabul et
        if (!soru.tip && soru.cevaplar && Array.isArray(soru.cevaplar)) {
            soru.tip = 'coktan_secmeli';
        }
        
        document.getElementById('soruMetni').textContent = soru.soru;
        const cevaplarDiv = document.getElementById('cevaplar');
        cevaplarDiv.innerHTML = '';
        
        // SORU TİPİNE GÖRE FARKLI UI
    if (soru.tip === 'coktan_secmeli') {
        // Çoktan seçmeli - şıklar
        const harfler = ['A', 'B', 'C', 'D'];
        soru.cevaplar.forEach((cevap, i) => {
        const btn = document.createElement('button');
        btn.className = 'w-full p-3 bg-indigo-500 text-white rounded-lg hover:bg-indigo-600 transition-all';
        btn.textContent = `${harfler[i]}) ${cevap}`;
        btn.onclick = () => checkCevap(harfler[i], soru.dogru_cevap, soru.tip);
        cevaplarDiv.appendChild(btn);
        });
    }
    else if (soru.tip === 'bosluk_doldurma') {
        // Boşluk doldurma - input + buton
        const input = document.createElement('input');
        input.type = 'text';
        input.className = 'w-full p-3 border-2 border-gray-300 rounded-lg mb-3';
        input.placeholder = 'Cevabınızı yazın...';
        input.id = 'cevap-input';
        
        const btn = document.createElement('button');
        btn.className = 'w-full p-3 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-all';
        btn.textContent = 'Cevabımı Gönder';
        btn.onclick = () => {
            const cevap = document.getElementById('cevap-input').value.trim();
            checkCevap(cevap, soru.dogru_cevap, soru.tip);
        };
        
        cevaplarDiv.appendChild(input);
        cevaplarDiv.appendChild(btn);
    }
    else if (soru.tip === 'kisa_cevap') {
        // Kısa cevap - textarea + buton
        const textarea = document.createElement('textarea');
        textarea.className = 'w-full p-3 border-2 border-gray-300 rounded-lg mb-3';
        textarea.placeholder = '3-4 kelimelik cevabınızı yazın...';
        textarea.rows = 3;
        textarea.id = 'cevap-textarea';
        
        const btn = document.createElement('button');
        btn.className = 'w-full p-3 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-all';
        btn.textContent = 'Cevabımı Gönder';
        btn.onclick = () => {
            const cevap = document.getElementById('cevap-textarea').value.trim();
            checkCevapGemini(cevap, soru.soru, soru.tip);
        };
        
        cevaplarDiv.appendChild(textarea);
        cevaplarDiv.appendChild(btn);
    }
    
    document.getElementById('soruModal').classList.remove('hidden');
    }

        function checkCevap(secilen, dogru, tip) {
            let mesaj = '';
            if(secilen === dogru || secilen.toLowerCase() === dogru.toLowerCase()) {
                mesaj = '✅ Tebrikler! Maarif SosyalLab ile Öğreniyorsun';
            } else {
                if(tip === 'bosluk_doldurma') {
                    mesaj = `❌ Üzgünüm. Doğru Cevap: ${dogru}`;
                } else {
                    mesaj = `❌ Yanlış! Doğru cevap: ${dogru}`;
                }
            }
            alert(mesaj);
            document.getElementById('soruModal').classList.add('hidden');
            currentSoruIndex++;
            
            // YouTube veya HTML5 için farklı play
            if (player.playVideo) {
                player.playVideo();
            } else {
                player.play();
            }
            
            if(currentSoruIndex < sorular.length) checkTime();
        }
        
        async function checkCevapGemini(ogrenciCevap, soru, tip) {
            if(!ogrenciCevap) {
                alert('Lütfen bir cevap yazın!');
                return;
            }
            
            try {
                const response = await fetch('/api/seyret-bul/gemini-cevap-kontrol', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        soru: soru,
                        ogrenci_cevap: ogrenciCevap
                    })
                });
                
                const result = await response.json();
                
                if(result.dogru) {
                    alert('✅ Tebrikler! Maarif SosyalLab ile Öğreniyorsun');
                } else {
                    alert(`❌ Üzgünüm. Doğru Cevap: ${result.dogru_cevap || 'Bilinmiyor'}`);
                }
                
                document.getElementById('soruModal').classList.add('hidden');
                currentSoruIndex++;
                if (player.playVideo) player.playVideo(); else player.play();
                if(currentSoruIndex < sorular.length) checkTime();
                
            } catch(e) {
                alert('Cevap kontrol edilemedi!');
            }
        }
        
    </script>
</body>
</html>
"""

# --- YENİ EKLENDİ: Podcast Konu Kontrolü ---

# --- YENİ EKLENDİ: Podcast Konu Kontrolü ---

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
    return render_template_string(VIDEO_ISTEGI_PAGE_HTML)

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
    return render_template_string(TAKIM_OYUN_EKRANI_HTML)

@app.route('/takim-liderlik-tablosu')
def takim_liderlik_tablosu_sayfasi():
    """Yeni liderlik tablosu HTML'ini sunar."""
    # HATA BURADAYDI, ŞİMDİ DÜZELDİ (HTML'i yukarıya eklediniz)
    return render_template_string(TAKIM_LIDERLIK_TABLOSU_HTML)

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
    """(Kural 36, 38) Yarışma bitince skoru kaydeder."""
    oyun = active_team_games.get(yarisma_id)
    if not oyun:
        return jsonify({"success": False, "hata": "Yarışma bulunamadı."})
    
    kazanan_id = oyun.kazanan_takim_id
    
    # Eğer kazanan varsa kaydet
    if kazanan_id:
        kazanan_takim = oyun.takimlar[kazanan_id]
        ty.kaydet_yarışma_sonucu(
            takim_adi=kazanan_takim["isim"],
            rozet=kazanan_takim["rozet"],
            soru_sayisi=kazanan_takim["puan"],
            toplam_sure=kazanan_takim["toplam_sure_saniye"],
            okul=oyun.okul,
            sinif=oyun.sinif
        )
        return jsonify({"success": True, "mesaj": "Skor kaydedildi."})
    
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
if __name__ == '__main__':
    print("UYGULAMA SUNUCUSU http://127.0.0.1:5002 adresinde çalışıyor...")
    print("Giriş yapmak için: http://127.0.0.1:5002")
    print("Dashboard'a doğrudan erişim: http://127.0.0.1:5002/dashboard")
    app.run(debug=True, host='127.0.0.1', port=5002)