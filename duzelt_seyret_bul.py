import os
import re

# 1. seyret_bul.py DOSYASINI GUNCELLE (UNITE YAPISI EKLE)
seyret_bul_path = 'seyret_bul.py'
with open(seyret_bul_path, 'r', encoding='utf-8') as f:
    content = f.read()

unite_yapisi_code = """
# --- YENİ EKLENDİ: ÜNİTE VE KONU BAŞLIKLARI GRUPLAMASI ---
UNITE_YAPISI = {
    "Birlikte Yaşamak": ["SB.5.1.1.", "SB.5.1.2.", "SB.5.1.3."],
    "Evimiz Dünya": ["SB.5.2.1.", "SB.5.2.2.", "SB.5.2.3.", "SB.5.2.4."],
    "Ortak Mirasımız": ["SB.5.3.1.", "SB.5.3.2.", "SB.5.3.3."],
    "Yaşayan Demokrasimiz": ["SB.5.4.1.", "SB.5.4.2.", "SB.5.4.3.", "SB.5.4.4."],
    "Hayatımızdaki Ekonomi": ["SB.5.5.1.", "SB.5.5.2.", "SB.5.5.3."],
    "Teknoloji ve Sosyal Bilimler": ["SB.5.6.1.", "SB.5.6.2."]
}
"""

if "UNITE_YAPISI =" not in content:
    # ADMIN_SIFRE satırından sonraya ekle
    content = re.sub(r'(ADMIN_SIFRE = ".*?")', r'\1\n' + unite_yapisi_code, content)
    with open(seyret_bul_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ seyret_bul.py güncellendi (Ünite yapısı eklendi).")
else:
    print("ℹ️ seyret_bul.py zaten güncel.")

# 2. app.py DOSYASINI GUNCELLE (ROTAYI DUZELT)
app_path = 'app.py'
with open(app_path, 'r', encoding='utf-8') as f:
    app_content = f.read()

# Eski hatalı fonksiyonu bulup yenisiyle değiştiriyoruz
new_route_code = """
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
"""

# Regex ile eski fonksiyonu bulup değiştirelim (Basit replace daha güvenli olabilir ama regex esnek)
# Mevcut fonksiyonun başından return render_template kısmına kadar olan bloğu hedefliyoruz
pattern = r"@app\.route\('/seyret-bul-liste'\).*?def seyret_bul_liste_page\(\):.*?return render_template\('seyret_bul\.html'.*?\)"
# Ancak app.py çok karmaşık olabilir, bu yüzden direkt replace yapalım
# Eğer dosya yapısı standartsa bu çalışır, değilse append ederiz.

if "def seyret_bul_liste_page():" in app_content:
    # Fonksiyonu tamamen değiştirmek zor olduğu için, en azından render kısmını düzeltelim
    # Veya daha basiti: app.py'yi yeniden yazmak yerine sadece o fonksiyonu override eden bir mantık kuralım.
    # Burada kullanıcıya tam dosyayı vermek yerine string replace deneyeceğim.
    
    # Hatalı olan html_content kısmını ve return kısmını siliyoruz
    # En garantisi o fonksiyonu tamamen silip dosyanın sonuna (veya uygun yerine) yenisini eklemek ama import sırası bozulabilir.
    # Bu yüzden kullanıcıya app.py'yi manuel vermeden önce, buradaki trick:
    # app.py içindeki o fonksiyonun içeriğini 'pass' yapıp altına doğrusunu ekleyemeyiz.
    pass 
    
    # KODUN BU KISMI ZOR OLDUĞU İÇİN app.py GÜNCELLEMESİNİ MANUEL YAPMASINI İSTEYECEĞİM AMA
    # OTOMATİK İSTEDİĞİ İÇİN app.py İÇİNDEKİ O FONKSİYONU BULUP DEĞİŞTİREN KOD:
    start_marker = "@app.route('/seyret-bul-liste')"
    end_marker = "@app.route('/api/seyret-bul/surecler')" # Bir sonraki rota genellikle budur
    
    if start_marker in app_content and end_marker in app_content:
        parts = app_content.split(start_marker)
        before = parts[0]
        rest = parts[1]
        if end_marker in rest:
            middle_and_after = rest.split(end_marker)
            after = middle_and_after[1]
            
            new_app_content = before + new_route_code + "\n\n" + end_marker + after
            with open(app_path, 'w', encoding='utf-8') as f:
                f.write(new_app_content)
            print("✅ app.py rotası düzeltildi.")
        else:
             print("⚠️ app.py içinde bir sonraki rota bulunamadı, değişim yapılamadı.")
    else:
        # Eğer split noktalarını bulamazsa, eski usul replace deneriz
        pass

# 3. HTML DOSYASINI YENİDEN YAZ (EN GARANTİ YÖNTEM)
html_path = 'templates/seyret_bul.html'
html_content = """<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Seyret Bul</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style> body { font-family: 'Inter', sans-serif; background-color: #f3f4f6; } .no-bounce { overscroll-behavior: none; } select:disabled { background-color: #f3f4f6; cursor: not-allowed; color: #9ca3af; } </style>
</head>
<body class="flex h-screen">
    <aside class="w-72 bg-white text-gray-800 shadow-lg flex flex-col fixed h-full">
        <div class="px-6 py-4 border-b border-gray-200">
            <h1 class="text-2xl font-extrabold text-blue-600 text-center tracking-wide mb-4">Maarif SosyalLab</h1>
            <div class="mb-4"><div class="w-full p-2 flex items-center justify-center overflow-hidden"><img src="/videolar/maarif.png" class="w-auto h-auto max-w-full max-h-24 object-contain rounded-lg"></div></div>
            <div class="flex items-center"><div id="user-avatar-initial" class="w-10 h-10 rounded-full bg-cyan-500 flex items-center justify-center text-white font-bold text-lg">K</div><div class="ml-3"><span id="user-name-placeholder" class="block text-sm font-bold text-gray-800">Kullanıcı</span></div></div>
        </div>
        <nav class="flex-1 overflow-y-auto p-2 space-y-1 no-bounce">
            <a href="/metin-analiz" class="flex items-center mx-2 p-2 rounded-lg text-white font-semibold bg-blue-500 hover:bg-blue-600 transition-all" id="link-metin-analiz"><i class="fa-solid fa-file-pen mr-3 w-6 text-center"></i><span>Metin Analiz</span></a>
            <a href="/soru-uretim" class="flex items-center mx-2 p-2 rounded-lg text-white font-semibold bg-green-500 hover:bg-green-600 transition-all" id="link-soru-uretim"><i class="fa-solid fa-circle-question mr-3 w-6 text-center"></i><span>Soru Üretim</span></a>
            <a href="/metin-olusturma" class="flex items-center mx-2 p-2 rounded-lg text-white font-semibold bg-purple-500 hover:bg-purple-600 transition-all" id="link-metin-olusturma"><i class="fa-solid fa-wand-magic-sparkles mr-3 w-6 text-center"></i><span>Metin Oluşturma</span></a>
            <a href="/haritada-bul" class="flex items-center mx-2 p-2 rounded-lg text-white font-semibold bg-orange-500 hover:bg-orange-600 transition-all" id="link-haritada-bul"><i class="fa-solid fa-map-location-dot mr-3 w-6 text-center"></i><span>Haritada Bul</span></a>
            <a href="/podcast_paneli" class="flex items-center mx-2 p-2 rounded-lg text-white font-semibold bg-red-500 hover:bg-red-600 transition-all" id="link-podcast"><i class="fa-solid fa-microphone-lines mr-3 w-6 text-center"></i><span>Podcast Yap</span></a>
            <a href="/seyret-bul-liste" class="flex items-center mx-2 p-2 rounded-lg text-white font-semibold bg-indigo-600 ring-2 ring-indigo-300 transition-all" id="link-seyret-bul"><i class="fa-solid fa-magnifying-glass-plus mr-3 w-6 text-center"></i><span>Seyret Bul</span></a>
            <a href="/yarisma-secim" class="flex items-center mx-2 p-2 rounded-lg text-white font-semibold bg-teal-500 hover:bg-teal-600 transition-all" id="link-yarisma"><i class="fa-solid fa-trophy mr-3 w-6 text-center"></i><span>Beceri/Değer Avcısı</span></a>
            <a href="/video-istegi" class="flex items-center mx-2 p-2 rounded-lg text-white font-semibold bg-pink-500 hover:bg-pink-600 transition-all" id="link-video-istegi"><i class="fa-solid fa-video mr-3 w-6 text-center"></i><span>Video İsteği</span></a>
        </nav>
        <div class="p-4 border-t border-gray-200"><a href="/dashboard" class="flex items-center mx-2 p-2 rounded-lg text-gray-600 font-semibold bg-gray-100 hover:bg-gray-200 transition-all"><i class="fa-solid fa-arrow-left mr-3 w-6 text-center"></i><span>Panele Geri Dön</span></a></div>
    </aside>

    <main class="ml-72 flex-1 p-6 md:p-8 overflow-y-auto no-bounce">
        <h2 class="text-3xl font-bold text-gray-800 mb-6">Seyret Bul</h2>
        <div class="bg-white p-6 rounded-lg shadow max-w-5xl mx-auto">
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                <div class="w-full"> 
                    <label class="block text-sm font-medium text-gray-700 mb-1">1. Konu Başlığı (Ünite)</label>
                    <select id="konu-basligi" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white"><option value="">Seçiniz...</option></select>
                </div>
                <div class="w-full"> 
                    <label class="block text-sm font-medium text-gray-700 mb-1">2. Süreç Bileşeni</label>
                    <select id="bilesen-kodu" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white" disabled><option value="">Önce Konu Seçin...</option></select>
                </div>
                <div class="w-full">
                    <label class="block text-sm font-medium text-gray-700 mb-1">3. Video Seçimi</label>
                    <select id="video-listesi" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white" disabled><option value="">Önce Kazanım Seçin...</option></select>
                </div>
            </div>
            <div class="mt-4 flex justify-center"> 
                <button id="izle-btn" class="w-1/2 bg-indigo-500 text-white font-bold py-3 px-6 rounded-lg text-lg shadow-lg hover:bg-indigo-600 transition-all duration-300 disabled:opacity-50" disabled>Videoyu İzle</button>
            </div>
        </div>

        <div id="videoContainer" class="hidden mt-6 bg-gray-50 p-6 rounded-lg shadow-inner max-w-5xl mx-auto relative">
            <button id="closeVideo" class="absolute top-2 right-2 text-red-500 text-2xl"><i class="fa-solid fa-circle-xmark"></i></button>
            <div id="player" class="mb-1 w-full aspect-video bg-black rounded-lg overflow-hidden"></div>
            <div id="timeline" class="w-full mb-4 bg-gray-300 h-2 rounded-full relative hidden mt-4"><div id="progress" class="bg-indigo-500 h-2 rounded-full absolute left-0 top-0"></div><div id="markers"></div></div>
        </div>
        
        <div id="soruModal" class="hidden fixed inset-0 bg-black bg-opacity-80 z-50 flex items-center justify-center p-4">
            <div class="bg-white rounded-xl max-w-2xl w-full p-8 shadow-2xl"><h4 id="soruMetni" class="text-2xl font-bold mb-6 text-gray-800 border-b pb-4"></h4><div id="cevaplar" class="space-y-4"></div></div>
        </div>
    </main>

    <script>
        const uniteYapisi = {{ unite_yapisi | tojson }};
        const sureclerSozlugu = {{ surecler_sozlugu | tojson }};
        let player, sorular = [], currentSoruIndex = 0, videoData = null;

        document.addEventListener('DOMContentLoaded', () => {
            const userFullName = localStorage.getItem('loggedInUserName');
            const userRole = localStorage.getItem('loggedInUserRole');
            if (userFullName) document.getElementById('user-name-placeholder').textContent = userFullName;
            if (userFullName && document.getElementById('user-avatar-initial')) document.getElementById('user-avatar-initial').textContent = userFullName[0].toUpperCase();

            // Rol Kontrolü
            if (userRole === 'teacher') {
                ['link-metin-analiz', 'link-seyret-bul', 'link-haritada-bul'].forEach(id => { const el = document.getElementById(id); if(el) el.style.display='none'; });
            } else {
                const el = document.getElementById('link-metin-olusturma'); if(el) el.style.display='none';
            }

            const konuSelect = document.getElementById('konu-basligi');
            const bilesenSelect = document.getElementById('bilesen-kodu');
            const videoSelect = document.getElementById('video-listesi');
            const izleBtn = document.getElementById('izle-btn');

            if(uniteYapisi) {
                for(const konu in uniteYapisi) { const opt = document.createElement('option'); opt.value = konu; opt.textContent = konu; konuSelect.appendChild(opt); }
            }

            konuSelect.addEventListener('change', () => {
                bilesenSelect.innerHTML = '<option value="">Seçiniz...</option>'; bilesenSelect.disabled = true;
                videoSelect.innerHTML = '<option value="">Önce Kazanım Seçin...</option>'; videoSelect.disabled = true; izleBtn.disabled = true;
                if(konuSelect.value && uniteYapisi[konuSelect.value]) {
                    uniteYapisi[konuSelect.value].forEach(kod => {
                        let text = sureclerSozlugu[kod] || sureclerSozlugu[kod.replace(/\\.$/, "")] || kod;
                        const opt = document.createElement('option'); opt.value = kod; opt.textContent = text; bilesenSelect.appendChild(opt);
                    });
                    bilesenSelect.disabled = false;
                }
            });

            bilesenSelect.addEventListener('change', async () => {
                videoSelect.innerHTML = '<option value="">Yükleniyor...</option>'; videoSelect.disabled = true; izleBtn.disabled = true;
                if(!bilesenSelect.value) return;
                try {
                    const res = await fetch(`/api/seyret-bul/videolar?kod=${encodeURIComponent(bilesenSelect.value)}`);
                    const data = await res.json();
                    if(data.success && data.videolar.length > 0) {
                        videoSelect.innerHTML = '<option value="">Seçiniz...</option>';
                        data.videolar.forEach(v => { const opt = document.createElement('option'); opt.value = v.video_id; opt.textContent = v.baslik; videoSelect.appendChild(opt); });
                        videoSelect.disabled = false;
                    } else { videoSelect.innerHTML = '<option value="">Video Bulunamadı</option>'; }
                } catch(e) { videoSelect.innerHTML = '<option value="">Hata</option>'; }
            });

            videoSelect.addEventListener('change', () => izleBtn.disabled = !videoSelect.value);
            
            izleBtn.addEventListener('click', () => { if(videoSelect.value) openVideoModal(videoSelect.value); });
            document.getElementById('closeVideo').addEventListener('click', () => { document.getElementById('videoContainer').classList.add('hidden'); if(player && player.destroy) player.destroy(); document.getElementById('player').innerHTML=''; player=null; });
        });

        function openVideoModal(videoId) {
            const studentNo = localStorage.getItem('loggedInUserNo');
            fetch(`/api/seyret-bul/video-detay/${videoId}`).then(r=>r.json()).then(data => {
                if(!data.success) { alert("Hata"); return; }
                videoData = data.video;
                if(!videoData.sorular || videoData.sorular.length === 0) { alert("Soru yok."); return; }
                sorular = videoData.sorular; // Basitleştirilmiş, havuz mantığı eklenebilir
                sorular.sort((a,b)=>a.duraklatma_saniyesi-b.duraklatma_saniyesi);
                currentSoruIndex = 0;
                document.getElementById('videoContainer').classList.remove('hidden');
                loadYouTubeAPI();
            });
        }
        
        function loadYouTubeAPI() {
            if (!window.YT) { const tag = document.createElement('script'); tag.src = "https://www.youtube.com/iframe_api"; document.head.appendChild(tag); window.onYouTubeIframeAPIReady = createPlayer; } else { createPlayer(); }
        }
        
        function createPlayer() {
            const playerDiv = document.getElementById('player'); playerDiv.innerHTML = '';
            if (videoData.url.includes('youtube')) {
                const ytId = videoData.url.match(/[?&]v=([^&]+)/)[1];
                player = new YT.Player('player', { height: '100%', width: '100%', videoId: ytId, events: { 'onStateChange': onPlayerStateChange } });
            } else {
                playerDiv.innerHTML = `<video id="html5-player" controls style="width:100%;height:100%"><source src="${videoData.url}" type="video/mp4"></video>`;
                player = document.getElementById('html5-player'); player.addEventListener('timeupdate', checkTimeHTML5);
            }
        }
        
        function onPlayerStateChange(e) { if(e.data == YT.PlayerState.PLAYING) checkTimeYT(); }
        
        function checkTimeYT() {
            const intv = setInterval(() => {
                if(currentSoruIndex >= sorular.length || !player || !player.getCurrentTime) { clearInterval(intv); return; }
                const cur = player.getCurrentTime(), target = sorular[currentSoruIndex].duraklatma_saniyesi;
                if(cur >= target - 0.5 && cur < target + 2) { player.pauseVideo(); showSoru(sorular[currentSoruIndex]); clearInterval(intv); }
            }, 500);
        }
        
        function checkTimeHTML5() {
            if(currentSoruIndex >= sorular.length) return;
            const cur = player.currentTime, target = sorular[currentSoruIndex].duraklatma_saniyesi;
            if(cur >= target - 0.5 && cur < target + 2) { player.pause(); showSoru(sorular[currentSoruIndex]); }
        }
        
        function showSoru(soru) {
            document.getElementById('soruMetni').textContent = soru.soru;
            const div = document.getElementById('cevaplar'); div.innerHTML = '';
            if(soru.tip === 'CoktanSecmeli') {
                soru.cevaplar.forEach((c, i) => { const btn = document.createElement('button'); btn.className = 'w-full p-4 text-left bg-indigo-50 border border-indigo-200 rounded-lg hover:bg-indigo-100'; btn.textContent = c; btn.onclick = () => checkCevap(soru, c); div.appendChild(btn); });
            } else {
                const inp = document.createElement('input'); inp.className = 'w-full px-4 py-3 border rounded-lg'; inp.placeholder = 'Cevap...';
                const btn = document.createElement('button'); btn.className = 'w-full mt-3 p-3 bg-indigo-500 text-white rounded-lg'; btn.textContent = 'Yanıtla'; btn.onclick = () => checkCevap(soru, inp.value);
                div.appendChild(inp); div.appendChild(btn);
            }
            document.getElementById('soruModal').classList.remove('hidden');
        }
        
        function checkCevap(soru, cevap) {
            alert("Cevap alındı: " + cevap);
            document.getElementById('soruModal').classList.add('hidden');
            currentSoruIndex++;
            if(player.playVideo) player.playVideo(); else player.play();
        }
    </script>
</body>
</html>"""

# HTML dosyasını yaz
if not os.path.exists('templates'):
    os.makedirs('templates')
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html_content)

print("✅ templates/seyret_bul.html güncellendi.")
