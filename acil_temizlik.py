import os

app_path = 'app.py'

if os.path.exists(app_path):
    with open(app_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    skip_block = False
    
    # Silinecek rotaların tanımları
    targets = [
        "/api/seyret-bul/degerlendir",
        "/api/seyret-bul/kaydet-izleme"
    ]

    print("1. app.py taranıyor ve çift kayıtlar temizleniyor...")

    for line in lines:
        # Eğer satır, silinecek rotalardan birini içeriyorsa silme modunu aç
        if any(t in line for t in targets) and "@app.route" in line:
            skip_block = True
        
        # Silme modundaysak:
        if skip_block:
            # Eğer yeni bir rota tanımına (@app.route) veya ana bloğa (if __name__) geldiysek
            # Ve bu satır bizim sildiğimiz hedeflerden biri DEĞİLSE silme modunu kapat
            is_new_route = line.strip().startswith("@app.route")
            is_main = "if __name__" in line
            is_target_line = any(t in line for t in targets)

            if (is_new_route and not is_target_line) or is_main:
                skip_block = False
                new_lines.append(line) # Bu satırı koru
            # Aksi takdirde satırı atla (sil)
        else:
            new_lines.append(line)

    # Temizlenmiş içeriği birleştir
    content = "".join(new_lines)

    # 2. TEMİZ VE TEK VERSİYONLARI EKLE
    # (En sona, main bloğundan hemen önceye)
    
    yeni_kodlar = """
@app.route('/api/seyret-bul/kaydet-izleme', methods=['POST'])
def api_seyret_bul_kaydet_izleme():
    try:
        data = request.get_json()
        student_no = data.get('student_no')
        video_baslik = data.get('video_baslik')
        if not student_no: return jsonify({"success": False})
        import db_helper
        db_helper.kaydet_kullanim(student_no, 'Seyret Bul', f"İzlendi: {video_baslik}")
        return jsonify({"success": True})
    except: return jsonify({"success": False})

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
"""

    if "if __name__ == '__main__':" in content:
        content = content.replace("if __name__ == '__main__':", yeni_kodlar + "\n\nif __name__ == '__main__':")
    else:
        content += "\n" + yeni_kodlar

    with open(app_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print("✅ Çakışmalar giderildi. app.py artık temiz.")

else:
    print("❌ app.py bulunamadı.")
