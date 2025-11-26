import os

path = 'templates/seyret_bul.html'

if os.path.exists(path):
    with open(path, 'r', encoding='utf-8') as f:
        html = f.read()

    print("Arayüz düzeltiliyor...")

    # 1. TIMELINE GENİŞLİĞİ VE KONUMU
    # 'max-w-2xl' ifadesini kaldırıp videonun tam altına yayılmasını sağlıyoruz.
    # 'mt-0' yerine 'mt-1' vererek çok hafif bir boşluk bırakıyoruz (görsel yapışıklık için).
    old_timeline = 'class="w-full max-w-2xl mx-auto bg-gray-200 rounded-full relative hidden mt-0"'
    new_timeline = 'class="w-full mx-auto bg-gray-200 rounded-full relative hidden mt-1"'
    
    if old_timeline in html:
        html = html.replace(old_timeline, new_timeline)
    else:
        # v3 veya v4'ten kalma farklı bir versiyon olabilir, alternatif deneyelim
        html = html.replace('max-w-2xl ', '') # max-w-2xl'i her halükarda sil

    # 2. KIRMIZI NOKTALARI KÜÇÜLT VE SENKRONİZE ET
    # Eski setupMarkers fonksiyonunu bulup daha gelişmişi ile değiştiriyoruz.
    # Yeni fonksiyon, videonun GERÇEK süresini alıp noktaları ona göre koyuyor.
    
    new_setup_func = """function setupMarkers() {
            const timeline = document.getElementById('timeline'); timeline.classList.remove('hidden');
            const markers = document.getElementById('markers'); markers.innerHTML = '';
            
            // SÜRE SENKRONİZASYONU (Veritabanı değil, gerçek video süresi)
            let duration = videoData.sure_saniye;
            if(player) {
                let d = 0;
                if(typeof player.getDuration === 'function') d = player.getDuration();
                else if(player.duration) d = player.duration;
                if(d > 0) duration = d;
            }

            sorular.forEach(s => {
                const m = document.createElement('div');
                const pos = (s.duraklatma_saniyesi / duration) * 100;
                // DÜZELTME: Noktalar w-1.5 (6px) yapıldı ve tam çizgi üstüne ortalandı
                m.className = 'absolute w-1.5 h-1.5 bg-red-600 rounded-full border border-white shadow z-10';
                m.style.left = `${pos}%`; 
                m.style.top = '-2px'; 
                m.style.transform = 'translateX(-50%)';
                markers.appendChild(m);
            });
        }"""

    # Eski fonksiyonu tespit edip değiştirme (Basit string değişimi yerine regex-free yöntem)
    start_marker = "function setupMarkers() {"
    end_marker = "function onPlayerStateChange" # Bir sonraki fonksiyon
    
    s_idx = html.find(start_marker)
    e_idx = html.find(end_marker)
    
    if s_idx != -1 and e_idx != -1:
        # Eski bloğu kesip atıyoruz, yenisini koyuyoruz
        html = html[:s_idx] + new_setup_func + "\n\n        " + html[e_idx:]

    # 3. TETİKLEYİCİLERİ GÜNCELLE (Video açılınca noktaları tekrar hesapla)
    # YouTube başladığında
    if "if(e.data == YT.PlayerState.PLAYING) checkTimeYT();" in html:
        html = html.replace("if(e.data == YT.PlayerState.PLAYING) checkTimeYT();", 
                            "if(e.data == YT.PlayerState.PLAYING) { setupMarkers(); checkTimeYT(); }")
    
    # HTML5 yüklendiğinde
    if "player.addEventListener('timeupdate', checkTimeHTML5);" in html:
        if "loadedmetadata" not in html: # Daha önce eklenmediyse
            html = html.replace("player.addEventListener('timeupdate', checkTimeHTML5);", 
                                "player.addEventListener('timeupdate', checkTimeHTML5); player.addEventListener('loadedmetadata', setupMarkers);")

    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print("✅ TAMAMLANDI: Timeline videoya yapıştırıldı, noktalar küçültüldü ve süre senkronizasyonu eklendi.")

else:
    print("❌ HATA: Dosya bulunamadı.")
