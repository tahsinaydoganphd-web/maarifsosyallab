# harita_bul.py
# SÜRÜM 6 (TÜR BAZLI BİLGİ KARTLARI):
# 1. Fotoğraf galerisi kaldırıldı.
# 2. Sağ tarafta seçilen yerin türüne (Ülke, Şehir, Tarihi Yer) göre değişen bilgi kartı eklendi.
# 3. Veriler gönderilen ders kitabı içeriğinden derlendi.

from flask import render_template_string, request, jsonify, session
import json

# ###############################################################
# --- VERİ TABANI (TÜRLERE GÖRE AYRILMIŞ) ---
# ###############################################################

# TÜR REHBERİ:
# "tur": "ulke"  -> Alanlar: 'baskent', 'nufus', 'para_birimi', 'bilgi'
# "tur": "sehir" -> Alanlar: 'bolge', 'ekonomik_faaliyet', 'bilgi'
# "tur": "tarih" -> Alanlar: 'donem', 'unesco', 'bilgi'

HARITA_VERITABANI = {
    "1. Ünite: BİRLİKTE YAŞAMAK": [
        {
            "ad": "Kuzey Kıbrıs Türk Cumhuriyeti",
            "tur": "ulke",
            "konum": "Kuzey Kıbrıs Türk Cumhuriyeti",
            "detay": {
                "baskent": "Lefkoşa",
                "nufus": "Yaklaşık 380.000",
                "para_birimi": "Türk Lirası",
                "bilgi": "Yavru vatan olarak bilinir. Türkiye ile derin tarihî ve kültürel bağları vardır. 1983 yılında bağımsızlığını ilan etmiştir."
            }
        },
        {
            "ad": "Azerbaycan",
            "tur": "ulke",
            "konum": "Azerbaijan",
            "detay": {
                "baskent": "Bakü",
                "nufus": "Yaklaşık 10 Milyon",
                "para_birimi": "Manat",
                "bilgi": "Kardeş ülke olarak anılır. 'İki devlet, tek millet' şiarı ile Türkiye ile güçlü ilişkileri vardır. Çay kültürü ve halı dokumacılığı meşhurdur."
            }
        },
        {
            "ad": "Türkmenistan",
            "tur": "ulke",
            "konum": "Turkmenistan",
            "detay": {
                "baskent": "Aşkabat",
                "nufus": "Yaklaşık 6 Milyon",
                "para_birimi": "Türkmen Manatı",
                "bilgi": "Orta Asya Türk cumhuriyetlerindendir. Türkmen halıları dünyaca meşhurdur. Hatta Mayıs ayının son pazarı 'Halı Bayramı' olarak kutlanır."
            }
        },
        {
            "ad": "Bulgaristan",
            "tur": "ulke",
            "konum": "Bulgaria",
            "detay": {
                "baskent": "Sofya",
                "nufus": "Yaklaşık 7 Milyon",
                "para_birimi": "Bulgar Levası",
                "bilgi": "Türkiye'nin batı komşusudur. Mart ayında 'Marteniçka' adı verilen bileklik takma geleneği vardır. Kapıkule Sınır Kapısı bu ülkeye açılır."
            }
        }
    ],
    "2. Ünite: EVİMİZ DÜNYA": [
        {
            "ad": "Yusufeli Barajı (Artvin)",
            "tur": "tarih", 
            "konum": "Yusufeli Barajı ve HES",
            "detay": {
                "donem": "Cumhuriyet Dönemi (Yeni)",
                "unesco": "Hayır",
                "bilgi": "Türkiye'nin en yüksek, dünyanın ise 5. en yüksek barajıdır. Çoruh Nehri üzerine kurulmuştur. Bölgenin doğal ve beşerî çevresini değiştirmiş, yeni yerleşim yerleri kurulmuştur."
            }
        },
        {
            "ad": "Meke Gölü (Konya)",
            "tur": "sehir",
            "konum": "Meke Gölü, Karapınar",
            "detay": {
                "bolge": "İç Anadolu Bölgesi",
                "ekonomik_faaliyet": "Turizm",
                "bilgi": "'Dünyanın Nazar Boncuğu' olarak bilinir. Volkanik patlama sonucu oluşmuş bir krater gölüdür. Son yıllarda kuraklık nedeniyle suları çekilmiştir."
            }
        },
        {
            "ad": "Beyaz Köşk (İzmir)",
            "tur": "tarih",
            "konum": "Latife Hanım Köşkü Anı Evi, Karşıyaka",
            "detay": {
                "donem": "Yakın Tarih / Milli Mücadele",
                "unesco": "Hayır",
                "bilgi": "İzmir'in Karşıyaka ilçesindedir. Atatürk'ün annesi Zübeyde Hanım'ın son günlerini geçirdiği ve vefat ettiği tarihi yapıdır."
            }
        },
        {
            "ad": "İran",
            "tur": "ulke",
            "konum": "Iran",
            "detay": {
                "baskent": "Tahran",
                "nufus": "Yaklaşık 88 Milyon",
                "para_birimi": "İran Riyali",
                "bilgi": "Türkiye'nin doğu komşusudur. Yüz ölçümü bakımından en geniş sınır komşumuzdur. Gürbulak Sınır Kapısı üzerinden ticaret yapılır."
            }
        }
    ],
    "3. Ünite: ORTAK MİRASIMIZ": [
        {
            "ad": "Göbeklitepe (Şanlıurfa)",
            "tur": "tarih",
            "konum": "Göbeklitepe",
            "detay": {
                "donem": "MÖ 10.000 (Neolitik Çağ)",
                "unesco": "EVET (Dünya Mirası Listesi)",
                "bilgi": "Tarihin bilinen en eski inanç merkezidir. 'T' biçimindeki dikilitaşlar üzerinde hayvan kabartmaları bulunur. İnsanlık tarihini değiştiren bir keşiftir."
            }
        },
        {
            "ad": "Çatalhöyük (Konya)",
            "tur": "tarih",
            "konum": "Çatalhöyük Neolitik Kenti",
            "detay": {
                "donem": "MÖ 7500 (Neolitik Çağ)",
                "unesco": "EVET (Dünya Mirası Listesi)",
                "bilgi": "Dünyanın ilk şehir yerleşmelerinden biridir. Evler birbirine bitişiktir, sokak yoktur ve evlere çatılardan girilir. İlk tarım faaliyetlerinin izleri görülür."
            }
        },
        {
            "ad": "Hattuşa / Boğazköy (Çorum)",
            "tur": "tarih",
            "konum": "Hattuşa Ören Yeri",
            "detay": {
                "donem": "Hitit İmparatorluğu",
                "unesco": "EVET (Dünya Mirası Listesi)",
                "bilgi": "Hititlerin başkentidir. Kadeş Antlaşması tableti burada bulunmuştur. Aslanlı Kapı ve Yazılıkaya önemli kalıntılardır."
            }
        },
        {
            "ad": "Nemrut Dağı (Adıyaman)",
            "tur": "tarih",
            "konum": "Nemrut Dağı Tümülüsü",
            "detay": {
                "donem": "Kommagene Krallığı",
                "unesco": "EVET (Dünya Mirası Listesi)",
                "bilgi": "2150 metre yükseklikte devasa heykeller bulunur. Kral Antiochos'un mezarı buradadır. Gün doğumu ve batımının en güzel izlendiği yerlerden biridir."
            }
        },
        {
            "ad": "Sümela Manastırı (Trabzon)",
            "tur": "tarih",
            "konum": "Sümela Manastırı, Maçka",
            "detay": {
                "donem": "Bizans Dönemi",
                "unesco": "Geçici Listede",
                "bilgi": "Sarp kayalıklar üzerine inşa edilmiştir. Doğal güzellikler içindeki konumuyla önemli bir inanç turizmi merkezidir."
            }
        },
        {
            "ad": "Mostar Köprüsü (Bosna Hersek)",
            "tur": "tarih",
            "konum": "Stari Most, Mostar",
            "detay": {
                "donem": "Osmanlı Dönemi",
                "unesco": "EVET",
                "bilgi": "Mimar Sinan'ın öğrencisi Mimar Hayreddin tarafından yapılmıştır. Kültürlerin birleşmesini simgeler. Savaşta yıkılmış, sonra aslına uygun onarılmıştır."
            }
        }
    ],
    "5. Ünite: HAYATIMIZDAKİ EKONOMİ": [
        {
            "ad": "Rize (Çay ve Ormancılık)",
            "tur": "sehir",
            "konum": "Rize, Türkiye",
            "detay": {
                "bolge": "Karadeniz Bölgesi",
                "ekonomik_faaliyet": "Tarım (Çay) ve Ormancılık",
                "bilgi": "Ülkemizin en çok yağış alan ilidir. Orman ürünleri ve çay üretimi ekonomisinin temelidir. Ayder Yaylası turizm açısından önemlidir."
            }
        },
        {
            "ad": "Batman (Petrol)",
            "tur": "sehir",
            "konum": "Batman, Türkiye",
            "detay": {
                "bolge": "Güneydoğu Anadolu Bölgesi",
                "ekonomik_faaliyet": "Madencilik (Petrol)",
                "bilgi": "Türkiye'nin ilk petrol rafinerisi buradadır. Şehir, petrolün bulunmasıyla küçük bir köyden büyük bir sanayi şehrine dönüşmüştür."
            }
        },
        {
            "ad": "Ordu (Arıcılık)",
            "tur": "sehir",
            "konum": "Ordu, Türkiye",
            "detay": {
                "bolge": "Karadeniz Bölgesi",
                "ekonomik_faaliyet": "Arıcılık ve Fındık",
                "bilgi": "Zengin bitki örtüsü sayesinde arıcılık gelişmiştir. Türkiye'de en çok bal üretilen illerden biridir."
            }
        }
    ]
}

# ###############################################################
# --- HTML ŞABLONU ---
# ###############################################################

HARITADA_BUL_HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Haritada Bul</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    
    <style> 
        body { font-family: 'Inter', sans-serif; background-color: #f3f4f6; } 
        
        .yer-listesi-item {
            cursor: pointer;
            transition: all 0.2s ease-in-out;
        }
        .yer-listesi-item:hover {
            background-color: #f0f9ff;
            padding-left: 1rem;
        }
        .yer-listesi-item.active {
            background-color: #e0f2fe;
            border-left: 4px solid #0284c7;
            font-weight: 600;
        }
        
        /* BİLGİ KARTI STİLLERİ */
        .info-card {
            transition: all 0.3s ease;
            opacity: 0;
            transform: translateY(10px);
        }
        .info-card.show {
            opacity: 1;
            transform: translateY(0);
        }
        
        .type-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .type-ulke { background-color: #fee2e2; color: #991b1b; } /* Kırmızı */
        .type-sehir { background-color: #dbeafe; color: #1e40af; } /* Mavi */
        .type-tarih { background-color: #fef3c7; color: #92400e; } /* Sarı */
    </style>
</head>
<body class="flex h-screen overflow-hidden">
    
    <aside class="w-64 bg-white text-gray-800 shadow-lg flex flex-col fixed h-full z-10">
        <div class="px-6 py-4 border-b border-gray-200 text-center">
            <h1 class="text-xl font-extrabold text-blue-600 tracking-wide mb-2">Maarif SosyalLab</h1>
            <div class="flex items-center justify-center space-x-2">
                <div class="w-8 h-8 rounded-full bg-cyan-500 flex items-center justify-center text-white font-bold text-sm">
                    {{ user_name[0] if user_name else 'K' }}
                </div>
                <span class="text-sm font-bold text-gray-700 truncate">{{ user_name }}</span>
            </div>
        </div>
        
        <nav class="flex-1 overflow-y-auto p-2 space-y-1 text-sm">
            {% if user_role == 'student' %}
            <a href="/metin-analiz" class="flex items-center mx-2 p-2 rounded hover:bg-gray-100"><i class="fa-solid fa-file-pen w-6 text-center text-blue-500"></i><span>Metin Analiz</span></a>
            <a href="/soru-uretim" class="flex items-center mx-2 p-2 rounded hover:bg-gray-100"><i class="fa-solid fa-circle-question w-6 text-center text-green-500"></i><span>Soru Üretim</span></a>
            {% endif %}
            
            {% if user_role == 'teacher' %}
            <a href="/metin-olusturma" class="flex items-center mx-2 p-2 rounded hover:bg-gray-100"><i class="fa-solid fa-wand-magic-sparkles w-6 text-center text-purple-500"></i><span>Metin Oluşturma</span></a>
            {% endif %}

            {% if user_role == 'student' %}
            <a href="/haritada-bul" class="flex items-center mx-2 p-2 rounded bg-orange-100 text-orange-700 font-bold"><i class="fa-solid fa-map-location-dot w-6 text-center"></i><span>Haritada Bul</span></a>
            <a href="/podcast_paneli" class="flex items-center mx-2 p-2 rounded hover:bg-gray-100"><i class="fa-solid fa-microphone-lines w-6 text-center text-red-500"></i><span>Podcast Yap</span></a>
            <a href="/seyret-bul-liste" class="flex items-center mx-2 p-2 rounded hover:bg-gray-100"><i class="fa-solid fa-magnifying-glass-plus w-6 text-center text-indigo-500"></i><span>Seyret Bul</span></a>
            <a href="/yarisma-secim" class="flex items-center mx-2 p-2 rounded hover:bg-gray-100"><i class="fa-solid fa-trophy w-6 text-center text-teal-500"></i><span>Beceri/Değer Avcısı</span></a>
            <a href="/video-istegi" class="flex items-center mx-2 p-2 rounded hover:bg-gray-100"><i class="fa-solid fa-video w-6 text-center text-pink-500"></i><span>Video İsteği</span></a>
            {% endif %}
            
            <a href="/dashboard" class="flex items-center mx-2 p-2 rounded hover:bg-gray-200 mt-4 text-gray-500"><i class="fa-solid fa-arrow-left w-6 text-center"></i><span>Panele Dön</span></a>
        </nav>
    </aside>

    <main class="ml-64 flex-1 p-6 h-screen overflow-hidden flex flex-col">
        <h2 class="text-2xl font-bold text-gray-800 mb-4 flex items-center">
            <i class="fa-solid fa-map-location-dot text-orange-500 mr-2"></i> Haritada Bul
        </h2>
        
        <div class="flex flex-1 gap-6 h-full overflow-hidden">
            
            <div class="w-1/4 flex flex-col gap-4">
                <div class="bg-white p-4 rounded-lg shadow-md border-t-4 border-blue-500">
                    <label class="block text-xs font-bold text-gray-500 uppercase mb-1">1. Adım: Ünite Seçin</label>
                    <select id="unite-select" class="w-full p-2 border rounded focus:ring-2 focus:ring-blue-400 outline-none text-sm">
                        <option value="">Seçiniz...</option>
                        {% for unite in harita_veritabani.keys() %}
                        <option value="{{ unite }}">{{ unite }}</option>
                        {% endfor %}
                    </select>
                </div>

                <div class="bg-white rounded-lg shadow-md flex-1 overflow-hidden flex flex-col border-t-4 border-orange-500">
                    <div class="p-3 bg-gray-50 border-b">
                        <label class="block text-xs font-bold text-gray-500 uppercase">2. Adım: Yer Seçin</label>
                    </div>
                    <div id="yer-listesi" class="flex-1 overflow-y-auto p-2 space-y-1">
                        <p class="text-sm text-gray-400 text-center mt-10">Lütfen önce bir ünite seçiniz.</p>
                    </div>
                </div>
            </div>

            <div class="w-5/12 bg-gray-200 rounded-lg shadow-inner overflow-hidden relative border border-gray-300">
                <iframe id="map-iframe" class="w-full h-full object-cover" 
                        src="https://www.google.com/maps?q=Turkey&output=embed&t=h" 
                        allowfullscreen loading="lazy">
                </iframe>
                <div id="map-loading" class="absolute inset-0 bg-white bg-opacity-80 flex items-center justify-center hidden">
                    <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
                </div>
            </div>

            <div class="w-1/3 bg-white rounded-lg shadow-lg border border-gray-200 overflow-y-auto relative">
                <div id="info-empty" class="absolute inset-0 flex flex-col items-center justify-center text-gray-400 p-6 text-center">
                    <i class="fa-solid fa-circle-info text-5xl mb-3 text-gray-300"></i>
                    <p>Detaylı bilgi görmek için sol listeden bir yer seçiniz.</p>
                </div>

                <div id="info-content" class="p-6 hidden info-card">
                    <div class="flex justify-between items-start mb-4">
                        <span id="info-tur-badge" class="type-badge">TÜR</span>
                    </div>
                    
                    <h3 id="info-baslik" class="text-2xl font-bold text-gray-800 mb-4 leading-tight">Yer Adı</h3>
                    
                    <div id="info-dynamic-fields" class="space-y-4">
                        </div>

                    <div class="mt-6 pt-4 border-t border-gray-100">
                        <h4 class="text-sm font-bold text-gray-500 uppercase mb-2">Genel Bilgi</h4>
                        <p id="info-aciklama" class="text-gray-700 leading-relaxed text-sm"></p>
                    </div>
                </div>
            </div>

        </div>
    </main>

    <script>
        const haritaVeritabani = {{ harita_veritabani | tojson }};
        const loggedInUserNo = "{{ user_no }}";

        document.addEventListener('DOMContentLoaded', () => {
            const uniteSelect = document.getElementById('unite-select');
            const yerListesi = document.getElementById('yer-listesi');
            const mapIframe = document.getElementById('map-iframe');
            
            const infoEmpty = document.getElementById('info-empty');
            const infoContent = document.getElementById('info-content');
            const infoBaslik = document.getElementById('info-baslik');
            const infoTurBadge = document.getElementById('info-tur-badge');
            const infoAciklama = document.getElementById('info-aciklama');
            const infoDynamicFields = document.getElementById('info-dynamic-fields');

            let activeItem = null;

            // Ünite Değişimi
            uniteSelect.addEventListener('change', (e) => {
                const secilen = e.target.value;
                yerListesi.innerHTML = '';
                resetInfoPanel();

                if(!secilen) {
                    yerListesi.innerHTML = '<p class="text-sm text-gray-400 text-center mt-10">Lütfen bir ünite seçiniz.</p>';
                    return;
                }

                const yerler = haritaVeritabani[secilen] || [];
                if(yerler.length === 0) {
                    yerListesi.innerHTML = '<p class="text-sm text-gray-400 text-center mt-10">Veri bulunamadı.</p>';
                    return;
                }

                yerler.forEach(yer => {
                    const div = document.createElement('div');
                    div.className = 'yer-listesi-item p-3 border-b border-gray-100 flex items-center justify-between';
                    
                    // İkon belirle
                    let ikon = 'fa-map-pin';
                    if(yer.tur === 'ulke') ikon = 'fa-flag';
                    if(yer.tur === 'tarih') ikon = 'fa-landmark';
                    if(yer.tur === 'sehir') ikon = 'fa-city';

                    div.innerHTML = `
                        <div class="flex items-center gap-3">
                            <div class="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center text-gray-500">
                                <i class="fa-solid ${ikon}"></i>
                            </div>
                            <span class="text-sm font-medium text-gray-700">${yer.ad}</span>
                        </div>
                        <i class="fa-solid fa-chevron-right text-gray-300 text-xs"></i>
                    `;

                    div.addEventListener('click', () => {
                        if(activeItem) activeItem.classList.remove('active');
                        div.classList.add('active');
                        activeItem = div;
                        yerSecildi(yer);
                    });

                    yerListesi.appendChild(div);
                });
            });

            function yerSecildi(yer) {
                // 1. Haritayı Güncelle
                const sorgu = yer.konum || yer.ad;
                // t=h (Hybrid: Uydu + İsimler)
                mapIframe.src = `https://www.google.com/maps?q=${encodeURIComponent(sorgu)}&output=embed&t=h`;

                // 2. Sağ Paneli Güncelle
                infoEmpty.classList.add('hidden');
                infoContent.classList.remove('hidden');
                
                // Animasyon reset
                infoContent.classList.remove('show');
                void infoContent.offsetWidth; // trigger reflow
                infoContent.classList.add('show');

                infoBaslik.textContent = yer.ad;
                infoAciklama.textContent = yer.detay.bilgi;

                // Tür Ayarları
                infoTurBadge.className = 'type-badge'; // reset
                infoDynamicFields.innerHTML = ''; // temizle

                if(yer.tur === 'ulke') {
                    infoTurBadge.textContent = 'ÜLKE';
                    infoTurBadge.classList.add('type-ulke');
                    infoDynamicFields.innerHTML = `
                        <div class="grid grid-cols-2 gap-4">
                            <div class="bg-gray-50 p-3 rounded border">
                                <span class="text-xs text-gray-500 block">BAŞKENT</span>
                                <span class="font-bold text-gray-800">${yer.detay.baskent}</span>
                            </div>
                            <div class="bg-gray-50 p-3 rounded border">
                                <span class="text-xs text-gray-500 block">NÜFUS</span>
                                <span class="font-bold text-gray-800">${yer.detay.nufus}</span>
                            </div>
                            <div class="col-span-2 bg-gray-50 p-3 rounded border">
                                <span class="text-xs text-gray-500 block">PARA BİRİMİ</span>
                                <span class="font-bold text-gray-800">${yer.detay.para_birimi}</span>
                            </div>
                        </div>
                    `;
                } 
                else if(yer.tur === 'sehir') {
                    infoTurBadge.textContent = 'ŞEHİR / BÖLGE';
                    infoTurBadge.classList.add('type-sehir');
                    infoDynamicFields.innerHTML = `
                        <div class="bg-blue-50 p-3 rounded border border-blue-100 mb-2">
                            <span class="text-xs text-blue-500 block font-bold">BÖLGE</span>
                            <span class="font-bold text-blue-900">${yer.detay.bolge}</span>
                        </div>
                        <div class="bg-green-50 p-3 rounded border border-green-100">
                            <span class="text-xs text-green-600 block font-bold">EKONOMİK FAALİYET</span>
                            <span class="font-bold text-green-900">${yer.detay.ekonomik_faaliyet}</span>
                        </div>
                    `;
                }
                else if(yer.tur === 'tarih') {
                    infoTurBadge.textContent = 'TARİHİ YER';
                    infoTurBadge.classList.add('type-tarih');
                    infoDynamicFields.innerHTML = `
                        <div class="bg-amber-50 p-3 rounded border border-amber-100 mb-2">
                            <span class="text-xs text-amber-600 block font-bold">DÖNEM / MEDENİYET</span>
                            <span class="font-bold text-amber-900">${yer.detay.donem}</span>
                        </div>
                        <div class="flex items-center gap-2 bg-gray-50 p-3 rounded border">
                            <i class="fa-solid fa-landmark text-gray-400"></i>
                            <div>
                                <span class="text-xs text-gray-500 block">UNESCO LİSTESİ</span>
                                <span class="font-bold text-gray-800">${yer.detay.unesco}</span>
                            </div>
                        </div>
                    `;
                }

                // Loglama
                if (loggedInUserNo) {
                    fetch('/api/harita/kaydet-inceleme', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ student_no: loggedInUserNo, yer_adi: yer.ad })
                    }).catch(console.error);
                }
            }

            function resetInfoPanel() {
                infoEmpty.classList.remove('hidden');
                infoContent.classList.add('hidden');
            }
        });
    </script>
</body>
</html>
"""

# ###############################################################
# --- FLASK ROTALARI ---
# ###############################################################

def register_harita_bul_routes(app, GOOGLE_MAPS_API_KEY):
    
    @app.route('/api/harita/kaydet-inceleme', methods=['POST'])
    def kaydet_harita_inceleme():
        try:
            data = request.get_json()
            student_no = data.get('student_no')
            yer_adi = data.get('yer_adi')
            if not student_no or not yer_adi: return jsonify({"success": False})

            import db_helper
            db_helper.kaydet_kullanim(student_no, "Haritada Bul", f"{yer_adi} incelendi")
            return jsonify({"success": True})
        except Exception as e:
            print(f"Harita log hatası: {e}")
            return jsonify({"success": False})

    @app.route('/haritada-bul')
    def haritada_bul_page():
        """
        Haritada Bul ana sayfasını render eder.
        """
        user_name = session.get('name', 'Kullanıcı')
        user_role = session.get('role', 'student')
        user_no = session.get('user_no', '')

        return render_template_string(
            HARITADA_BUL_HTML,
            harita_veritabani=HARITA_VERITABANI,
            maps_api_key=GOOGLE_MAPS_API_KEY,
            user_name=user_name,
            user_role=user_role,
            user_no=user_no
        )
