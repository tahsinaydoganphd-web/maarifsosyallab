import os
import shutil

# --- 1. EKLENECEK YENİ PYTHON KODLARI (APP.PY İÇİN) ---
NEW_API_CODE = """
# ==========================================
# --- OTOMATİK EKLENEN RAPORLAMA API'LARI ---
# ==========================================

@app.route("/api/filter/get_schools")
def api_get_schools():
    \"\"\"Sadece okul listesini döndürür.\"\"\"
    try:
        conn = db_helper.get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT school_name FROM users WHERE school_name IS NOT NULL AND school_name != '' ORDER BY school_name")
        okullar = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()
        return jsonify({"success": True, "data": okullar})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/filter/get_classes")
def api_get_classes():
    \"\"\"Seçilen okula ait sınıfları döndürür.\"\"\"
    try:
        okul_adi = request.args.get('school_name')
        if not okul_adi:
            return jsonify({"success": False, "data": []})

        conn = db_helper.get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT class FROM users WHERE school_name = %s AND class IS NOT NULL AND class != '' ORDER BY class", (okul_adi,))
        siniflar = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()
        return jsonify({"success": True, "data": siniflar})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/filter/get_years")
def api_get_years():
    \"\"\"Raporlama için yılları döndürür.\"\"\"
    return jsonify({"success": True, "data": ["2024", "2025", "2026"]})

# ==========================================
"""

# --- 2. YENİ HTML KODU (TEMPLATES/RAPORLAR.HTML İÇİN) ---
NEW_HTML_CODE = """<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gelişmiş Raporlama Paneli</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style> body { font-family: 'Inter', sans-serif; background-color: #f3f4f6; } </style>
</head>
<body class="p-6">

    <div class="max-w-7xl mx-auto">
        <div class="flex justify-between items-center mb-8">
            <h1 class="text-3xl font-bold text-gray-800">
                <i class="fa-solid fa-chart-line text-blue-600 mr-2"></i>Kullanım Raporları
            </h1>
            <a href="/dashboard" class="bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700 transition">
                <i class="fa-solid fa-arrow-left mr-2"></i>Dashboard'a Dön
            </a>
        </div>

        <div class="bg-white p-6 rounded-lg shadow-md mb-8 border-l-4 border-blue-600">
            <h2 class="text-lg font-semibold text-gray-700 mb-4 border-b pb-2">Rapor Filtreleri</h2>
            
            <div class="grid grid-cols-1 md:grid-cols-5 gap-4">
                
                <div>
                    <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Okul Seçimi</label>
                    <select id="filter_okul" class="w-full p-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition">
                        <option value="">Yükleniyor...</option>
                    </select>
                </div>

                <div>
                    <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Sınıf</label>
                    <select id="filter_sinif" class="w-full p-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 bg-gray-100 cursor-not-allowed" disabled>
                        <option value="">Önce Okul Seçin</option>
                    </select>
                </div>

                <div>
                    <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Yıl</label>
                    <select id="filter_yil" class="w-full p-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 bg-gray-100 cursor-not-allowed" disabled>
                        <option value="">Önce Sınıf Seçin</option>
                    </select>
                </div>

                <div>
                    <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Ay</label>
                    <select id="filter_ay" class="w-full p-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 bg-gray-100 cursor-not-allowed" disabled>
                        <option value="">Önce Yıl Seçin</option>
                        <option value="01">Ocak</option> <option value="02">Şubat</option>
                        <option value="03">Mart</option> <option value="04">Nisan</option>
                        <option value="05">Mayıs</option> <option value="06">Haziran</option>
                        <option value="07">Temmuz</option> <option value="08">Ağustos</option>
                        <option value="09">Eylül</option> <option value="10">Ekim</option>
                        <option value="11">Kasım</option> <option value="12">Aralık</option>
                    </select>
                </div>

                <div class="flex items-end gap-2">
                    <button onclick="raporGetir()" id="btnRaporGetir" class="flex-1 bg-blue-600 text-white p-2.5 rounded-lg hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed shadow-md" disabled>
                        <i class="fa-solid fa-magnifying-glass mr-1"></i> Getir
                    </button>
                    
                    <button onclick="excelIndir()" id="btnExcel" class="bg-green-600 text-white p-2.5 rounded-lg hover:bg-green-700 transition disabled:opacity-50 disabled:cursor-not-allowed shadow-md" disabled title="Excel İndir">
                        <i class="fa-solid fa-file-excel"></i>
                    </button>
                </div>
            </div>
        </div>

        <div class="bg-white rounded-lg shadow-md overflow-hidden">
            <div class="p-4 bg-gray-50 border-b flex justify-between items-center">
                <h3 class="font-semibold text-gray-700" id="tabloBaslik">Sonuçlar Bekleniyor...</h3>
                <span class="text-xs text-gray-500" id="kayitSayisi"></span>
            </div>
            
            <div class="overflow-x-auto">
                <table class="w-full text-left text-sm text-gray-600">
                    <thead class="bg-gray-100 text-gray-700 uppercase font-bold text-xs">
                        <tr>
                            <th class="p-4">Öğrenci No</th>
                            <th class="p-4">Modül</th>
                            <th class="p-4">İşlem</th>
                            <th class="p-4">Zaman</th>
                        </tr>
                    </thead>
                    <tbody id="raporBody" class="divide-y divide-gray-200">
                        <tr>
                            <td colspan="4" class="p-8 text-center text-gray-400 italic">
                                Lütfen yukarıdan filtreleri sırasıyla seçiniz.
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        const elOkul = document.getElementById('filter_okul');
        const elSinif = document.getElementById('filter_sinif');
        const elYil = document.getElementById('filter_yil');
        const elAy = document.getElementById('filter_ay');
        const btnRapor = document.getElementById('btnRaporGetir');
        const btnExcel = document.getElementById('btnExcel');
        const tbody = document.getElementById('raporBody');
        const tabloBaslik = document.getElementById('tabloBaslik');

        // YARDIMCI: Seçenekleri Temizle
        function sifirla(element, placeholder) {
            element.innerHTML = `<option value="">${placeholder}</option>`;
            if(element.id === "filter_ay") {
                element.innerHTML = `
                    <option value="">Ay Seçiniz</option>
                    <option value="01">Ocak</option> <option value="02">Şubat</option>
                    <option value="03">Mart</option> <option value="04">Nisan</option>
                    <option value="05">Mayıs</option> <option value="06">Haziran</option>
                    <option value="07">Temmuz</option> <option value="08">Ağustos</option>
                    <option value="09">Eylül</option> <option value="10">Ekim</option>
                    <option value="11">Kasım</option> <option value="12">Aralık</option>
                `;
            }
            element.disabled = true;
            element.classList.add('bg-gray-100', 'cursor-not-allowed');
        }

        function aktifEt(element) {
            element.disabled = false;
            element.classList.remove('bg-gray-100', 'cursor-not-allowed');
        }

        // 1. SAYFA YÜKLENİRKEN OKULLARI ÇEK
        document.addEventListener('DOMContentLoaded', async () => {
            try {
                const res = await fetch('/api/filter/get_schools');
                const json = await res.json();
                elOkul.innerHTML = '<option value="">Okul Seçiniz...</option>';
                if (json.success) {
                    json.data.forEach(okul => {
                        const opt = document.createElement('option');
                        opt.value = okul;
                        opt.textContent = okul;
                        elOkul.appendChild(opt);
                    });
                }
            } catch (err) { console.error('Hata:', err); }
        });

        // 2. OKUL SEÇİLİNCE -> SINIFLARI GETİR
        elOkul.addEventListener('change', async () => {
            const okul = elOkul.value;
            sifirla(elSinif, "Sınıf Yükleniyor...");
            sifirla(elYil, "Önce Sınıf Seçin");
            sifirla(elAy, "Önce Yıl Seçin");
            btnRapor.disabled = true; btnExcel.disabled = true;

            if(!okul) { sifirla(elSinif, "Önce Okul Seçin"); return; }

            try {
                const res = await fetch(`/api/filter/get_classes?school_name=${encodeURIComponent(okul)}`);
                const json = await res.json();
                
                elSinif.innerHTML = '<option value="">Sınıf Seçiniz</option>';
                if(json.success && json.data.length > 0) {
                    json.data.forEach(sinif => {
                        const opt = document.createElement('option');
                        opt.value = sinif;
                        opt.textContent = sinif;
                        elSinif.appendChild(opt);
                    });
                    aktifEt(elSinif);
                } else {
                    elSinif.innerHTML = '<option value="">Sınıf Bulunamadı</option>';
                }
            } catch(e) { console.error(e); }
        });

        // 3. SINIF SEÇİLİNCE -> YILLARI GETİR
        elSinif.addEventListener('change', async () => {
            if(!elSinif.value) { 
                sifirla(elYil, "Önce Sınıf Seçin"); 
                sifirla(elAy, "Önce Yıl Seçin");
                return; 
            }
            
            // Yılları Çek
            try {
                const res = await fetch('/api/filter/get_years');
                const json = await res.json();
                elYil.innerHTML = '<option value="">Yıl Seçiniz</option>';
                if(json.success) {
                    json.data.forEach(yil => {
                        const opt = document.createElement('option');
                        opt.value = yil;
                        opt.textContent = yil;
                        elYil.appendChild(opt);
                    });
                    aktifEt(elYil);
                }
            } catch(e) { console.error(e); }
        });

        // 4. YIL SEÇİLİNCE -> AYI AÇ
        elYil.addEventListener('change', () => {
            if(elYil.value) { aktifEt(elAy); } 
            else { sifirla(elAy, "Önce Yıl Seçin"); }
        });

        // 5. AY SEÇİLİNCE -> BUTONLARI AÇ
        elAy.addEventListener('change', () => {
            if(elAy.value) {
                btnRapor.disabled = false;
                btnRapor.classList.remove('opacity-50', 'cursor-not-allowed');
                btnExcel.disabled = false;
                btnExcel.classList.remove('opacity-50', 'cursor-not-allowed');
            } else {
                btnRapor.disabled = true;
                btnExcel.disabled = true;
            }
        });

        // --- RAPOR GETİRME FONKSİYONU ---
        async function raporGetir() {
            const okul = elOkul.value;
            const sinif = elSinif.value;
            const tarih = `${elYil.value}-${elAy.value}`;
            
            tabloBaslik.textContent = "Veriler Yükleniyor...";
            tbody.innerHTML = '<tr><td colspan="4" class="p-8 text-center"><div class="animate-spin inline-block w-8 h-8 border-4 border-blue-500 rounded-full border-t-transparent"></div></td></tr>';

            try {
                // Burada mevcut API'nizi kullanıyoruz ama artık parametreler DOĞRU gidiyor
                const url = `/api/raporlar/haftalik?okul=${encodeURIComponent(okul)}&sinif=${encodeURIComponent(sinif)}&ay=${tarih}`;
                const res = await fetch(url);
                const json = await res.json();

                tbody.innerHTML = '';
                
                if(json.success && json.data.length > 0) {
                    tabloBaslik.textContent = `${okul} - ${sinif} (${tarih}) Raporu`;
                    document.getElementById('kayitSayisi').textContent = `${json.data.length} kayıt bulundu`;
                    
                    json.data.forEach(satir => {
                        // Veri yapısına göre burayı düzenleyebiliriz. Varsayılan tahmin:
                        const tr = document.createElement('tr');
                        tr.className = "hover:bg-blue-50 transition";
                        tr.innerHTML = `
                            <td class="p-4 font-medium text-gray-900">${satir.student_no || satir.ogrenci_no || '-'}</td>
                            <td class="p-4"><span class="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs">${satir.module || satir.modul || 'Genel'}</span></td>
                            <td class="p-4">${satir.action || satir.islem || '-'}</td>
                            <td class="p-4 text-gray-500 text-xs">${satir.timestamp || satir.tarih || '-'}</td>
                        `;
                        tbody.appendChild(tr);
                    });
                } else {
                    tabloBaslik.textContent = "Sonuç Bulunamadı";
                    tbody.innerHTML = '<tr><td colspan="4" class="p-8 text-center text-red-500">Bu kriterlere uygun kayıt bulunamadı.</td></tr>';
                }

            } catch(e) {
                console.error(e);
                tbody.innerHTML = `<tr><td colspan="4" class="p-4 text-center text-red-600">Hata oluştu: ${e}</td></tr>`;
            }
        }

        function excelIndir() {
            const okul = elOkul.value;
            const sinif = elSinif.value;
            const tarih = `${elYil.value}-${elAy.value}`;
            // Mevcut Excel API'sini çağır
            window.location.href = `/api/raporlar/excel?okul=${encodeURIComponent(okul)}&sinif=${encodeURIComponent(sinif)}&baslangic=${tarih}-01&bitis=${tarih}-31`;
        }
    </script>
</body>
</html>
"""

def patch_app_py():
    """app.py dosyasına yeni API'ları ekler."""
    if not os.path.exists("app.py"):
        print("HATA: app.py bulunamadı!")
        return

    # Yedek al
    shutil.copy("app.py", "app.py.bak")
    print("Yedek alındı: app.py.bak")

    with open("app.py", "r", encoding="utf-8") as f:
        content = f.read()

    # Çift eklemeyi önle
    if "api_get_schools" in content:
        print("UYARI: API'lar zaten ekli görünüyor. app.py değiştirilmedi.")
    else:
        # Eski hatalı route'u bulup comment'e al (Basit bir replace ile)
        if '@app.route("/api/okul_sinif_listesi")' in content:
            content = content.replace('@app.route("/api/okul_sinif_listesi")', '# ESKİ HATALI KOD DEVRE DIŞI\n# @app.route("/api/okul_sinif_listesi")')
            print("Eski hatalı API rotası devre dışı bırakıldı.")

        # Yeni kodları dosyanın sonuna (main bloğundan hemen önceye) ekle
        if "if __name__ == '__main__':" in content:
            parts = content.split("if __name__ == '__main__':")
            new_content = parts[0] + NEW_API_CODE + "\nif __name__ == '__main__':" + parts[1]
        else:
            new_content = content + NEW_API_CODE

        with open("app.py", "w", encoding="utf-8") as f:
            f.write(new_content)
        print("BAŞARILI: app.py dosyasına yeni filtreleme API'ları eklendi.")

def create_raporlar_html():
    """raporlar.html dosyasını yeniden yazar."""
    templates_dir = "templates"
    if not os.path.exists(templates_dir):
        os.makedirs(templates_dir)
    
    file_path = os.path.join(templates_dir, "raporlar.html")
    
    # Dosyayı sıfırdan yaz
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(NEW_HTML_CODE)
    print("BAŞARILI: templates/raporlar.html dosyası çalışan versiyonla yenilendi.")

if __name__ == "__main__":
    print("--- SOSYALLAB RAPORLAMA TAMİR SİSTEMİ ---")
    patch_app_py()
    create_raporlar_html()
    print("\nİŞLEM TAMAMLANDI!")
    print("Lütfen sunucuyu durdurup yeniden başlatın: python app.py")