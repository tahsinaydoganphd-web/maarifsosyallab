# Bu dosyanın adı: podcast_dinle.py (Sizin ana flask uygulamanız)

from flask import Flask, request, jsonify, render_template_string
import os
# Yeni oluşturduğumuz modülü içe aktarıyoruz
import podcast_creator 

# --- MEVCUT FLASK UYGULAMANIZ ---
# Zaten sizde bu satırlar olmalı (veya benzerleri)
#
# ÖNEMLİ: Bu satırların uygulamanızda olduğundan emin olun!
# import google.generativeai as genai
# app = Flask(__name__)
#
# genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
# gemini_model = genai.GenerativeModel('gemini-1.5-flash') # Bu modelin adını sizdekiyle değiştirin


# --- 'static' KLASÖRÜNÜN VARLIĞINDAN EMİN OLUN ---
# app.run() demeden önce bu kontrolü ekleyin
if not os.path.exists('static'):
    os.makedirs('static')


# --- PODCAST KONULARI LİSTESİ (ARTIK GEREKLİ DEĞİL) ---
# PODCAST_KONULAR listesi bu senaryoda kaldırıldı.


# --- YENİ ROUTE 1: Podcast Panelini Gösteren Sayfa (Güncellendi) ---
# Kullanıcı artık bir konu seçmek yerine metin girecek
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
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #f0f2f5; color: #333; }}
            .podcast-container {{
                width: 90%; max-width: 700px; margin: 40px auto; padding: 30px;
                background-color: #ffffff; border-radius: 10px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05); text-align: center;
            }}
            .podcast-container h1 {{ color: #005a9c; margin-bottom: 25px; }}
            
            /* Metin alanı (textarea) için stiller */
            .podcast-container textarea {{
                width: 100%; height: 250px; padding: 12px; font-size: 15px;
                border-radius: 6px; border: 1px solid #ddd;
                margin-bottom: 10px; box-sizing: border-box; resize: vertical;
            }}
            
            /* Kelime sayacı */
            #word-count {{ 
                text-align: right; font-size: 14px; color: #666; 
                margin-bottom: 20px;
            }}
            #word-count.over-limit {{ color: red; font-weight: bold; }}

            .podcast-container button {{
                width: 100%; padding: 12px; font-size: 16px;
                background-color: #007bff; color: white; font-weight: bold;
                cursor: pointer; border: none; border-radius: 6px;
            }}
            .podcast-container button:disabled {{ background-color: #ccc; }}
            #podcast-status {{ font-style: italic; color: #555; margin-top: 15px; }}
            #podcast-player-container audio {{ width: 100%; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="podcast-container">
            <h1>Podcast Oluşturucu</h1>
            <p>Lütfen "sohbet podcasti" yapılacak metni (En fazla 600 kelime) aşağıya yapıştırın.</p>
            
            <form id="podcast-form">
                <textarea id="text-input" 
                          name="text_content"
                          placeholder="Metninizi buraya yapıştırın..."></textarea>
                
                <div id="word-count">0 / 600 kelime</div>

                <button id="generate-btn" type="submit">Sohbet Podcasti Oluştur</button>
            </form>

            <div id="podcast-status"></div>
            <div id="podcast-player-container"></div>
        </div>

        <script>
            (function() {{
                const form = document.getElementById('podcast-form');
                if (form) {{
                    const textArea = document.getElementById('text-input');
                    const wordCountDisplay = document.getElementById('word-count');
                    const button = document.getElementById('generate-btn');
                    const status = document.getElementById('podcast-status');
                    const playerContainer = document.getElementById('podcast-player-container');
                    const wordLimit = 600;

                    // Kelime sayacı
                    textArea.addEventListener('input', function() {{
                        const text = textArea.value;
                        const words = text.split(/\\s+/).filter(Boolean); // Boşluklara göre ayır
                        const wordCount = words.length;

                        wordCountDisplay.textContent = `${{wordCount}} / ${{wordLimit}} kelime`;
                        
                        if (wordCount > wordLimit) {{
                            wordCountDisplay.classList.add('over-limit');
                            button.disabled = true;
                        }} else {{
                            wordCountDisplay.classList.remove('over-limit');
                            button.disabled = false;
                        }}
                    }});

                    form.addEventListener('submit', async function(event) {{
                        event.preventDefault();
                        const userText = textArea.value.trim();
                        
                        if (!userText) {{
                            alert("Lütfen bir metin girin.");
                            return;
                        }}

                        // Kelime sayısını tekrar kontrol et
                        const words = userText.split(/\\s+/).filter(Boolean);
                        if (words.length > wordLimit) {{
                            alert(`Metin ${{wordLimit}} kelimeyi geçemez. Şu anki kelime sayısı: ${{words.length}}`);
                            return;
                        }}

                        button.disabled = true;
                        button.textContent = "Oluşturuluyor...";
                        status.textContent = "Sohbet senaryosu hazırlanıyor...";
                        playerContainer.innerHTML = ""; 

                        try {{
                            const response = await fetch('/generate-podcast', {{
                                method: 'POST',
                                headers: {{ 'Content-Type': 'application/json' }},
                                // Sunucuya 'topic' yerine 'text' gönderiyoruz
                                body: JSON.stringify({{ text: userText }}), 
                            }});
                            
                            const data = await response.json();

                            if (response.ok && data.success) {{
                                status.textContent = "Podcast başarıyla oluşturuldu!";
                                const audioPlayer = document.createElement('audio');
                                audioPlayer.controls = true;
                                audioPlayer.src = data.audio_url; // gTTS'ten gelen dosya yolu
                                audioPlayer.autoplay = true;
                                playerContainer.appendChild(audioPlayer);
                            }} else {{
                                status.textContent = "Bir hata oluştu.";
                                alert("Hata: " + (data.error || "Bilinmeyen bir hata oluştu."));
                            }}
                        }} catch (error) {{
                            status.textContent = "Sunucuya bağlanırken bir hata oluştu.";
                            alert("Sunucu Hatası: " + error.message);
                        }} finally {{
                            // Butonu tekrar aktif et (kelime limiti aşılmamışsa)
                            const currentWordCount = textArea.value.split(/\\s+/).filter(Boolean).length;
                            if (currentWordCount <= wordLimit) {{
                                button.disabled = false;
                            }}
                            button.textContent = "Sohbet Podcasti Oluştur";
                        }}
                    }});
                }}
            }})();
        </script>
    </body>
    </html>
    """
    # HTML içeriğini Flask'in render_template_string fonksiyonu ile döndür
    # Bu, 'app' değişkeninizin Flask(__name__) ile tanımlandığını varsayar.
    return render_template_string(html_content)


# --- YENİ ROUTE 2: Podcast'i Oluşturan API (Güncellendi) ---
# Artık 'topic' yerine 'text' alacak
@app.route('/generate-podcast', methods=['POST'])
def handle_generation():
    """
    Arka planda çalışan podcast oluşturma isteğini alır.
    """
    data = request.get_json()
    user_text = data.get('text') # 'topic' yerine 'text' al
    
    if not user_text:
        return jsonify({"success": False, "error": "Metin boş olamaz."}), 400

    try:
        # 1. Metni oluştur (Gemini'ye metni ve modeli gönder)
        # BURASI ÖNEMLİ: 'gemini_model' sizin sosyallab.py'de 
        # başlattığınız model değişkeninin adıdır.
        podcast_text = podcast_creator.generate_podcast_content(user_text, gemini_model)
        if not podcast_text:
            raise Exception("Gemini'den boş yanıt alındı.")
            
        # 2. Metni sese dönüştür
        # 'app.static_folder' Flask uygulamasının 'static' klasörünün yolunu verir.
        audio_url = podcast_creator.convert_text_to_speech(podcast_text, app.static_folder)
        if not audio_url:
            raise Exception("Ses dosyası (gTTS) oluşturulamadı.")

        # 3. Başarılı yanıtı ve ses dosyasının yolunu döndür
        return jsonify({"success": True, "audio_url": audio_url})

    except Exception as e:
        print(f"İşlem sırasında hata (podcast_dinle.py): {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# --- MEVCUT app.run() ---
# Bu satır zaten dosyanızın en altında olmalı
# if __name__ == '__main__':
#     # 'app' değişkeninizin adının 'app' olduğunu varsayıyorum
#     app.run(debug=True)