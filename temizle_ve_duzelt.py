import re
import os

dosya_yolu = 'app.py'

if os.path.exists(dosya_yolu):
    with open(dosya_yolu, 'r', encoding='utf-8') as f:
        icerik = f.read()

    # 1. ADIM: Mevcut (hatalı veya çift) fonksiyonların hepsini temizle
    # Regex: @app.route ile baslayip, bir sonraki @app.route veya if __name__ gorene kadar siler.
    temiz_icerik = re.sub(r"@app\.route\('/api/seyret-bul/degerlendir', methods=\['POST'\])[\s\S]*?def api_seyret_bul_degerlendir\(\):[\s\S]*?(?=@app\.route|if __name__)", "", icerik)

    # 2. ADIM: Tek ve Doğru Fonksiyonu Tanımla
    dogru_fonksiyon = """
@app.route('/api/seyret-bul/degerlendir', methods=['POST'])
def api_seyret_bul_degerlendir():
    try:
        # Global model kontrolü
        global gemini_model
        
        data = request.get_json()
        soru = data.get('soru_metni')
        cevap = data.get('kullanici_cevabi')
        
        if not soru or not cevap:
            return jsonify({"success": False, "hata": "Eksik veri"})

        # Gemini Promptu
        prompt = f'''Sen bir öğretmensin. Soru: "{soru}", Öğrenci Cevabı: "{cevap}".
        Bu cevabı 1-5 arası puanla ve geri bildirim ver.
        Yanıtın SADECE şu JSON formatında olsun: {{"skor": 3, "geri_bildirim": "..."}}'''

        if not gemini_model:
            return jsonify({"success": True, "skor": 3, "geri_bildirim": "Yapay zeka bağlantısı yok, otomatik puanlandı."})

        response = gemini_model.generate_content(prompt)
        text = response.text.strip()
        
        # Markdown temizliği
        if "```" in text:
            text = text.replace("```json", "").replace("```", "").strip()
        
        import json
        try:
            sonuc = json.loads(text)
            skor = sonuc.get('skor', 1)
            geri_bildirim = sonuc.get('geri_bildirim', 'Geri bildirim alınamadı.')
        except:
            skor = 3
            geri_bildirim = f"Yapay zeka yanıtı okunamadı."
        
        return jsonify({"success": True, "skor": skor, "geri_bildirim": geri_bildirim})

    except Exception as e:
        print(f"Değerlendirme Hatası: {e}")
        return jsonify({"success": True, "skor": 1, "geri_bildirim": "Sistem hatası."})
"""

    # 3. ADIM: Temizlenen dosyanın sonuna (main bloğundan hemen önceye) ekle
    if "if __name__ == '__main__':" in temiz_icerik:
        final_icerik = temiz_icerik.replace("if __name__ == '__main__':", dogru_fonksiyon + "\n\nif __name__ == '__main__':")
    else:
        final_icerik = temiz_icerik + "\n" + dogru_fonksiyon

    with open(dosya_yolu, 'w', encoding='utf-8') as f:
        f.write(final_icerik)
    
    print("✅ app.py içindeki çift kayıtlar temizlendi ve rota düzeltildi.")

else:
    print("❌ app.py bulunamadı.")
