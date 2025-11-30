# Bu dosyanın adı: podcast_dinle.py
from flask import Flask, request, jsonify, render_template_string, session
import os
import podcast_creator
import google.generativeai as genai
import db_helper

app = Flask(__name__)

def api_yapilandir(api_key):
    """Gemini API'yi yapılandırır"""
    guvenli_anahtar = os.getenv('GOOGLE_API_KEY')
    if guvenli_anahtar:
        genai.configure(api_key=guvenli_anahtar)
        return genai.GenerativeModel('models/gemini-pro')
    return None

if not os.path.exists('static'):
    os.makedirs('static')

@app.route('/podcast_paneli')
def podcast_paneli():
    """Podcast oluşturucu arayüzünü (HTML) doğrudan sunar."""
    
    # --- HARİTA BUL GİBİ SESSION VERİLERİNİ AL ---
    user_name = session.get('name', 'Kullanıcı')
    user_role = session.get('role', 'student')
    user_no = session.get('user_no', '') 
    
    html_content = """
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
        body { font-family: 'Inter', sans-serif; background-color: #f3f4f6; }
        #word-count.over-limit { color: red; font-weight: bold; }
        .no-bounce { overscroll-behavior: none; }
        </style>
    </head>
    <body class="flex h-screen">
        
        <aside class="w-72 bg-white text-gray-800 shadow-lg flex flex-col fixed h-full">
            <div class="px-6 py-4 border-b border-gray-200">
                <h1 class="text-2xl font-extrabold text-blue-600 text-center tracking-wide mb-4">
                    Maarif SosyalLab
                </h1>
                <div class="mb-4">
                    <div class="w-20 h-20 rounded-full mx-auto bg-white p-1 shadow-md flex items-center justify-center overflow-hidden">
                        <img src="/videolar/maarif.png" alt="Logo" class="w-full h-full object-contain rounded-full">
                    </div>
                </div>
                <div class="flex items-center">
                    <div class="w-10 h-10 rounded-full bg-cyan-500 flex items-center justify-center text-white font-bold text-lg">
                        {{ user_name[0] if user_name else 'K' }}
                    </div>
                    <div class="ml-3">
                        <span class="block text-sm font-bold text-gray-800">{{ user_name }}</span>
                    </div>
                </div>
            </div>
            
            <nav class="flex-1 overflow-y-auto p-4 space-y-2 no-bounce">
                {% if role == 'student' %}
                <a href="/metin-analiz" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-blue-500 hover:bg-blue-600 transition-all"><i class="fa-solid fa-file-pen mr-3 w-6 text-center"></i><span>Metin Analiz</span></a>
                <a href="/soru-uretim" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-green-500 hover:bg-green-600 transition-all"><i class="fa-solid fa-circle-question mr-3 w-6 text-center"></i><span>Soru Üretim</span></a>
                <a href="/haritada-bul" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-orange-500 hover:bg-orange-600 transition-all"><i class="fa-solid fa-map-location-dot mr-3 w-6 text-center"></i><span>Haritada Bul</span></a>
                <a href="/podcast_paneli" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-red-600 ring-4 ring-red-200 shadow-lg transition-all"><i class="fa-solid fa-microphone-lines mr-3 w-6 text-center"></i><span>Podcast Yap</span></a>
                <a href="/seyret-bul-liste" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-indigo-500 hover:bg-indigo-600 transition-all"><i class="fa-solid fa-magnifying-glass-plus mr-3 w-6 text-center"></i><span>Seyret Bul</span></a>
                <a href="/yarisma-secim" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-teal-500 hover:bg-teal-600 transition-all"><i class="fa-solid fa-trophy mr-3 w-6 text-center"></i><span>Beceri/Değer Avcısı</span></a>
                <a href="/video-istegi" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-pink-500 hover:bg-pink-600 transition-all"><i class="fa-solid fa-video mr-3 w-6 text-center"></i><span>Video İsteği</span></a>
                {% else %}
                <a href="/soru-uretim" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-green-500 hover:bg-green-600 transition-all"><i class="fa-solid fa-circle-question mr-3 w-6 text-center"></i><span>Soru Üretim</span></a>
                <a href="/metin-olusturma" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-purple-500 hover:bg-purple-600 transition-all"><i class="fa-solid fa-wand-magic-sparkles mr-3 w-6 text-center"></i><span>Metin Oluşturma</span></a>
                {% endif %}
            </nav>
            
            <div class="p-4 border-t border-gray-200">
                <a href="/dashboard" class="flex items-center w-full p-3 rounded-lg text-gray-600 font-semibold bg-gray-100 hover:bg-gray-200 transition-all">
                    <i class="fa-solid fa-arrow-left mr-3 w-6 text-center"></i><span>Panele Geri Dön</span></a>
            </div>
        </aside>

        <main class="ml-72 flex-1 p-6 md:p-8 overflow-y-auto no-bounce">
            <div class="bg-white p-6 rounded-lg shadow max-w-3xl">
                <h2 class="text-3xl font-bold text-gray-800 mb-6">Podcast Oluşturucu</h2>
                <p class="text-gray-600 mb-4">Lütfen "sohbet podcasti" yapılacak metni (En fazla 330 kelime) aşağıya yapıştırın.</p>
                
                <form id="podcast-form">
                    <textarea id="text-input" name="text_content" placeholder="Metninizi buraya yapıştırın..."
                              class="w-full h-64 p-4 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500 resize-vertical"></textarea>
                    <div id="word-count" class="text-right text-sm text-gray-500 mt-2">0 / 330 kelime</div>
                    <button id="generate-btn" type="submit"
                            class="w-full mt-4 px-6 py-3 bg-red-600 text-white font-semibold rounded-lg hover:bg-red-700 transition-all disabled:bg-gray-400">
                        <i class="fa-solid fa-microphone mr-2"></i> Sohbet Podcasti Oluştur
                    </button>
                </form>

                <div id="podcast-status" class="mt-4 text-center font-semibold text-gray-700"></div>
                
                <div id="podcast-player-container" class="mt-4 hidden p-4 bg-gray-50 rounded-lg border border-gray-200">
                    <p class="text-sm text-gray-500 mb-2">Ses dosyanız hazır:</p>
                    <audio id="audio-player" controls class="w-full"></audio>
                </div>
            </div>
        </main>

        <script>
            // --- HARİTA BUL MANTIĞI: Veriyi Python'dan (Jinja2) al ---
            const loggedInUserNo = "{{ user_no }}"; 

            const form = document.getElementById('podcast-form');
            const textArea = document.getElementById('text-input');
            const wordCountDisplay = document.getElementById('word-count');
            const button = document.getElementById('generate-btn');
            const status = document.getElementById('podcast-status');
            const playerContainer = document.getElementById('podcast-player-container');
            const audioPlayer = document.getElementById('audio-player');
            const wordLimit = 330;

            textArea.addEventListener('input', function() {
                const text = textArea.value;
                const words = text.split(/\\s+/).filter(Boolean);
                const wordCount = words.length;
                wordCountDisplay.textContent = `${wordCount} / ${wordLimit} kelime`;
                
                if (wordCount > wordLimit) {
                    wordCountDisplay.classList.add('over-limit', 'text-red-500');
                    button.disabled = true;
                } else {
                    wordCountDisplay.classList.remove('over-limit', 'text-red-500');
                    button.disabled = false;
                }
            });

            form.addEventListener('submit', async function(event) {
                event.preventDefault();
                const userText = textArea.value.trim();
                
                if (!userText) {
                    alert("Lütfen bir metin girin.");
                    return;
                }

                button.disabled = true;
                button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Oluşturuluyor...';
                status.textContent = "Yapay zeka metni sese çeviriyor, lütfen bekleyin...";
                playerContainer.classList.add('hidden');

                try {
                    const response = await fetch('/generate-podcast', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ 
                            text: userText,
                            student_no: loggedInUserNo // <-- ARTIK GARANTİ OLAN BU DEĞİŞKENİ GÖNDER
                        }), 
                    });
                    
                    const data = await response.json();

                    if (response.ok && data.success) {
                        status.innerHTML = '<span class="text-green-600"><i class="fa-solid fa-check-circle"></i> Başarıyla oluşturuldu!</span>';
                        playerContainer.classList.remove('hidden');
                        audioPlayer.src = data.audio_url;
                        audioPlayer.play();
                    } else {
                        status.textContent = "Hata oluştu.";
                        alert("Hata: " + (data.error || "Bilinmeyen bir hata oluştu."));
                    }
                } catch (error) {
                    status.textContent = "Bağlantı hatası.";
                    alert("Sunucu Hatası: " + error.message);
                } finally {
                    button.disabled = false;
                    button.innerHTML = '<i class="fa-solid fa-microphone mr-2"></i> Sohbet Podcasti Oluştur';
                }
            });
        </script>
    </body>
    </html>
    """
    
    # HTML'i Render Et ve Değişkenleri Gönder (Harita Bul gibi)
    return render_template_string(html_content, user_name=user_name, role=user_role, user_no=user_no)

@app.route('/generate-podcast', methods=['POST'])
def handle_generation():
    data = request.get_json()
    user_text = data.get('text')
    
    # Öncelik Frontend'den gelen veride, yoksa Session'a bak
    student_no = data.get('student_no') or session.get('user_no')
    
    if not user_text:
        return jsonify({"success": False, "error": "Metin boş olamaz."}), 400

    try:
        # Gemini modelini yapılandır
        gemini_api_key = os.getenv('GOOGLE_API_KEY')
        if gemini_api_key:
            genai.configure(api_key=gemini_api_key)
            gemini_model = genai.GenerativeModel('models/gemini-pro')
        else:
            return jsonify({"success": False, "error": "Gemini API bağlantısı kurulamadı."}), 500

        # Podcast metnini oluştur
        podcast_text = podcast_creator.generate_podcast_content(user_text, gemini_model)
        if not podcast_text:
            raise Exception("Gemini'den boş yanıt alındı.")
            
        # Sesi oluştur (Static Folder'a erişmek için)
        # Eğer 'app' global değilse current_app kullanılabilir, 
        # ama bu dosyada Flask instance'ı 'app' olarak tanımlı.
        audio_url = podcast_creator.convert_text_to_speech(podcast_text, 'static')
        
        if not audio_url:
            raise Exception("Ses dosyası oluşturulamadı.") 

        # --- RAPORLAMA ---
        if student_no:
            try:
                db_helper.kaydet_kullanim(student_no, "Podcast Yap", "Podcast oluşturuldu")
                print(f"✅ Rapor Eklendi: Öğrenci {student_no}")
            except Exception as db_err:
                print(f"⚠️ Raporlama Hatası: {db_err}")

        return jsonify({"success": True, "audio_url": audio_url})

    except Exception as e:
        print(f"İşlem sırasında hata (podcast_dinle.py): {e}")
        return jsonify({"success": False, "error": str(e)}), 500
