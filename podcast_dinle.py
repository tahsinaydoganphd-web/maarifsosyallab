# Bu dosyanın adı: podcast_dinle.py
from flask import Flask, request, jsonify, render_template_string
import os
import podcast_creator
import google.generativeai as genai

app = Flask(__name__)

# Gemini API Key (SENİN KEY'İNİ BURAYA KOY!)
GEMINI_API_KEY = "BURAYA_KENDİ_GEMİNİ_API_ANAHTARINI_YAZ"
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-2.0-flash-exp')

# Static klasörü oluştur
if not os.path.exists('static'):
    os.makedirs('static')

@app.route('/podcast_paneli')
def podcast_paneli():
    """Podcast oluşturucu arayüzünü (HTML) doğrudan sunar."""
    
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
                        <img src="https://derepazari.meb.gov.tr/meb_iys_dosyalar/2019_01/04150849_photo_2019-01-04_09-30-46.jpg" alt="MEB Logo" class="w-full h-full object-cover rounded-full">
                    </div>
                </div>
                <div class="flex items-center">
                    <div id="user-avatar-initial" class="w-10 h-10 rounded-full bg-cyan-500 flex items-center justify-center text-white font-bold text-lg">K</div>
                    <div class="ml-3">
                        <span id="user-name-placeholder" class="block text-sm font-bold text-gray-800">Kullanıcı</span>
                    </div>
                </div>
            </div>
            <nav class="flex-1 overflow-y-auto p-4 space-y-2">
                <a href="/metin-analiz" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-blue-500 hover:bg-blue-600 transition-all">
                    <i class="fa-solid fa-file-pen mr-3 w-6 text-center"></i><span>Metin Analiz</span></a>
                <a href="/soru-uretim" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-green-500 hover:bg-green-600 transition-all">
                    <i class="fa-solid fa-circle-question mr-3 w-6 text-center"></i><span>Soru Üretim</span></a>
                <a href="/metin-olusturma" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-purple-500 hover:bg-purple-600 transition-all">
                    <i class="fa-solid fa-wand-magic-sparkles mr-3 w-6 text-center"></i><span>Metin Oluşturma</span></a>
                <a href="/haritada-bul" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-orange-500 hover:bg-orange-600 transition-all">
                    <i class="fa-solid fa-map-location-dot mr-3 w-6 text-center"></i><span>Haritada Bul</span></a>
                <a href="/podcast_paneli" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-red-600 ring-2 ring-red-300 transition-all">
                    <i class="fa-solid fa-microphone-lines mr-3 w-6 text-center"></i><span>Podcast Yap</span></a>
                <a href="/seyret-bul-liste" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-indigo-500 hover:bg-indigo-600 transition-all">
                    <i class="fa-solid fa-magnifying-glass-plus mr-3 w-6 text-center"></i><span>Seyret Bul</span></a>
                <a href="/yarisma-secim" class="flex items-center w-full p-3 rounded-lg text-white font-semibold bg-teal-500 hover:bg-teal-600 transition-all">
                    <i class="fa-solid fa-trophy mr-3 w-6 text-center"></i><span>Beceri/Değer Avcısı</span></a>
            </nav>
            <div class="p-4 border-t border-gray-200">
                <a href="/dashboard" class="flex items-center w-full p-3 rounded-lg text-gray-600 font-semibold bg-gray-100 hover:bg-gray-200 transition-all">
                    <i class="fa-solid fa-arrow-left mr-3 w-6 text-center"></i><span>Panele Geri Dön</span></a>
            </div>
        </aside>

                <main class="ml-72 flex-1 p-6 md:p-8 overflow-y-auto">
                <h2 class="text-3xl font-bold text-gray-800 mb-6">Podcast Oluşturucu</h2>
                
                <div class="bg-white p-6 rounded-lg shadow max-w-3xl">
                    <p class="text-gray-600 mb-4">Lütfen "sohbet podcasti" yapılacak metni (En fazla 600 kelime) aşağıya yapıştırın.</p>
                    
                    <form id="podcast-form">
                        <textarea id="text-input" name="text_content" placeholder="Metninizi buraya yapıştırın..."
                                  class="w-full h-64 p-4 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500 resize-vertical"></textarea>
                        <div id="word-count" class="text-right text-sm text-gray-500 mt-2">0 / 600 kelime</div>
                        <button id="generate-btn" type="submit"
                                class="w-full mt-4 px-6 py-3 bg-red-600 text-white font-semibold rounded-lg hover:bg-red-700 transition-all disabled:bg-gray-400">
                            Sohbet Podcasti Oluştur
                        </button>
                    </form>

                    <div id="podcast-status" class="mt-4 text-center"></div>
                    <div id="podcast-player-container" class="mt-4"></div>
                </div>
            </main>

        <script>
            // Kullanıcı adını yükle
            const userFullName = localStorage.getItem('loggedInUserName');
            if (userFullName) {
                document.getElementById('user-name-placeholder').textContent = userFullName;
                document.getElementById('user-avatar-initial').textContent = userFullName[0] ? userFullName[0].toUpperCase() : 'K';
            }

            const form = document.getElementById('podcast-form');
            const textArea = document.getElementById('text-input');
            const wordCountDisplay = document.getElementById('word-count');
            const button = document.getElementById('generate-btn');
            const status = document.getElementById('podcast-status');
            const playerContainer = document.getElementById('podcast-player-container');
            const wordLimit = 600;

            textArea.addEventListener('input', function() {
                const text = textArea.value;
                const words = text.split(/\\s+/).filter(Boolean);
                const wordCount = words.length;
                wordCountDisplay.textContent = `${wordCount} / ${wordLimit} kelime`;
                
                if (wordCount > wordLimit) {
                    wordCountDisplay.classList.add('over-limit');
                    button.disabled = true;
                } else {
                    wordCountDisplay.classList.remove('over-limit');
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

                const words = userText.split(/\\s+/).filter(Boolean);
                if (words.length > wordLimit) {
                    alert(`Metin ${wordLimit} kelimeyi geçemez. Şu anki kelime sayısı: ${words.length}`);
                    return;
                }

                button.disabled = true;
                button.textContent = "Oluşturuluyor...";
                status.textContent = "Sohbet senaryosu hazırlanıyor...";
                playerContainer.innerHTML = ""; 

                try {
                    const response = await fetch('/generate-podcast', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ text: userText }), 
                    });
                    
                    const data = await response.json();

                    if (response.ok && data.success) {
                        status.textContent = "Podcast başarıyla oluşturuldu!";
                        const audioPlayer = document.createElement('audio');
                        audioPlayer.controls = true;
                        audioPlayer.src = data.audio_url;
                        audioPlayer.autoplay = true;
                        playerContainer.appendChild(audioPlayer);
                    } else {
                        status.textContent = "Bir hata oluştu.";
                        alert("Hata: " + (data.error || "Bilinmeyen bir hata oluştu."));
                    }
                } catch (error) {
                    status.textContent = "Sunucuya bağlanırken bir hata oluştu.";
                    alert("Sunucu Hatası: " + error.message);
                } finally {
                    const currentWordCount = textArea.value.split(/\\s+/).filter(Boolean).length;
                    if (currentWordCount <= wordLimit) {
                        button.disabled = false;
                    }
                    button.textContent = "Sohbet Podcasti Oluştur";
                }
            });
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
        # Gemini modelini kontrol et
        if not gemini_model:
            return jsonify({"success": False, "error": "Gemini API bağlantısı kurulamadı. Lütfen API anahtarınızı kontrol edin."}), 500

        podcast_text = podcast_creator.generate_podcast_content(user_text, gemini_model)
        if not podcast_text:
            raise Exception("Gemini'den boş yanıt alındı.")
            
        audio_url = podcast_creator.convert_text_to_speech(podcast_text, app.static_folder)
        
        # Hata mesajı düzeltildi: Artık Piper'a atıf yapıyor.
        if not audio_url:
            raise Exception("Ses dosyası (Piper TTS) oluşturulamadı. (Piper yürütülebilir/model yolu hatası olabilir.)") 

        return jsonify({"success": True, "audio_url": audio_url})

    except Exception as e:
        print(f"İşlem sırasında hata (podcast_dinle.py): {e}")
        return jsonify({"success": False, "error": str(e)}), 500
```
**Neden Bu Düzeltme:** Bu, Piper bir hata verdiğinde tarayıcıya daha net bir hata mesajı iletilmesini sağlar.

### Düzeltme B: Çalıştırma İzni Kontrolü (Linux/macOS)

Bu, en yaygın Piper hatasıdır. Python, Piper yürütülebilir dosyasını çalıştırmak için izin alamıyor olabilir.

* Linux veya macOS kullanıyorsanız, Piper yürütülebilir dosyasına çalıştırma izni verin:
    ```bash
    chmod +x piper/piper