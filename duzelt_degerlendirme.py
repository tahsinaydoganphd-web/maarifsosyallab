import os

# 1. HTML'DEKI HATAYI DUZELT (Hata durumunda dogru sayma!)
html_path = 'templates/seyret_bul.html'
if os.path.exists(html_path):
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    # Hatali satiri bul ve degistir (True -> False)
    eski_kod = 'catch(e => finishFeedback(true, "Kaydedildi."));'
    yeni_kod = 'catch(e => finishFeedback(false, "Bağlantı hatası: Değerlendirilemedi."));'
    
    if eski_kod in html:
        html = html.replace(eski_kod, yeni_kod)
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print("✅ seyret_bul.html: Hata yakalama mantığı düzeltildi.")
    else:
        print("ℹ️ seyret_bul.html zaten düzeltilmiş olabilir.")

# 2. APP.PY'YE EKSIK OLAN DEGERLENDIRME ROTASINI EKLE
app_path = 'app.py'
if os.path.exists(app_path):
    with open(app_path, 'r', encoding='utf-8') as f:
        app_content = f.read()

    # Eklenecek Rota Kodu
    yeni_rota = """
@app.route('/api/seyret-bul/degerlendir', methods=['POST'])
def api_seyret_bul_degerlendir():
    try:
        data = request.get_json()
        soru = data.get('soru_metni')
        cevap = data.get('kullanici_cevabi')
        
        if not soru or not cevap:
            return jsonify({"success": False, "hata": "Eksik veri"})

        # Gemini Promptu
        prompt = f'''Sen bir 5. sınıf Sosyal Bilgiler öğretmenisin. 
        Soru: "{soru}"
        Öğrenci Cevabı: "{cevap}"
        
        Görevin:
        1. Cevabı 1 ile 5 arasında puanla.
        2. Öğrenciye kısa, yapıcı bir geri bildirim yaz.
        
        Yanıtını SADECE şu JSON formatında ver: {{"skor": 3, "geri_bildirim": "..."}}'''

        global gemini_model
        if not gemini_model:
            return jsonify({"success": True, "skor": 0, "geri_bildirim": "Yapay zeka bağlantısı yok, puanlanamadı."})

        response = gemini_model.generate_content(prompt)
        
        import json
        import re
        match = re.search(r"\{.*\}", response.text, re.DOTALL)
        json_str = match.group(0) if match else response.text
        sonuc = json.loads(json_str)
        
        return jsonify({"success": True, "skor": sonuc.get('skor'), "geri_bildirim": sonuc.get('geri_bildirim')})

    except Exception as e:
        print(f"Değerlendirme Hatası: {e}")
        return jsonify({"success": False, "hata": str(e)})
"""

    if "/api/seyret-bul/degerlendir" not in app_content:
        # if __name__ == '__main__': satırından hemen önceye ekle
        if "if __name__ == '__main__':" in app_content:
            app_content = app_content.replace("if __name__ == '__main__':", new=yeni_rota + "\n\nif __name__ == '__main__':")
            with open(app_path, 'w', encoding='utf-8') as f:
                f.write(app_content)
            print("✅ app.py: Eksik değerlendirme rotası eklendi.")
        else:
            print("⚠️ app.py içinde 'main' bloğu bulunamadı, kod eklenemedi.")
    else:
        print("ℹ️ app.py: Değerlendirme rotası zaten var.")

