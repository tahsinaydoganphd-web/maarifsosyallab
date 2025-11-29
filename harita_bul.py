# harita_bul.py
# Bu dosya, ana sosyallab.py uygulaması tarafından içe aktarılmak (import) üzere tasarlanmıştır.

from flask import render_template_string, request, jsonify, session
import json 

# ###############################################################
# --- VERİ TABANLARI ---
# ###############################################################

# Açılır menü için
SUREC_BILESENLERI_HARITA = {
    "SB.5.1.2": "Kültürel özelliklere saygı duymanın birlikte yaşamaya etkisini yorumlayabilme",
    "SB.5.2.1": "Yaşadığı ilin göreceli konum özelliklerini belirleyebilme",
    "SB.5.2.2": "Yaşadığı ilde doğal ve beşerî çevredeki değişimi neden ve sonuçlarıyla yorumlayabilme",
    "SB.5.2.3": "Yaşadığı ilde meydana gelebilecek afetlerin etkilerini azaltmaya yönelik farkındalık etkinlikleri düzenleyebilme",
    "SB.5.2.4": "Ülkemize komşu devletler hakkında bilgi toplayabilme",
    "SB.5.3.1": "Yaşadığı ildeki ortak miras ögelerine ilişkin oluşturduğu ürünü paylaşabilme",
    "SB.5.3.2": "Anadolu’da ilk yerleşimleri kuran toplumların sosyal hayatlarına yönelik bakış açısı geliştirebilme",
    "SB.5.3.3": "Mezopotamya ve Anadolu medeniyetlerinin ortak mirasa katkılarını karşılaştırabilme",
    "SB.5.4.1": "Demokrasi ve cumhuriyet kavramları arasındaki ilişkiyi çözümleyebilme",
    "SB.5.6.1": "Teknolojik gelişmelerin toplum hayatına etkilerini tartışabilme",
    "SB.5.6.2": "Teknolojik ürünlerin bilinçli kullanımının önemine ilişkin ürün oluşturabilme"
}

# VERİTABANI
HARITA_VERITABANI = {
    "SB.5.1.2": [
        {"yer_adi": "Kapadokya", "sayfa": 29, "cumle": "Türkiye'nin turizm merkezlerinden Kapadokya", 
         "gorseller": [
            {"dosya": "kapadokya1.jpg", "kaynak": "DHA"}, 
            {"dosya": "kapadokya2.jpg", "kaynak": "kapadokya.org"}
        ],
         "onemi": "Kapadokya, 60 milyon yıl önce Erciyes, Hasandağı ve Güllüdağ'ın püskürttüğü lav ve küllerin oluşturduğu yumuşak tabakaların, milyonlarca yıl boyunca yağmur ve rüzgar tarafından aşındırılmasıyla ortaya çıkan 'Peribacaları' ile ünlüdür.",
         "nedenleri": "Kapadokya'nın önemi, eşsiz jeolojik yapısından ve bu yapının sunduğu korunma imkanlarından gelir."
        }
    ],
    "SB.5.2.1": [
        {"yer_adi": "Divriği Ulu Camii", "sayfa": 51, "cumle": "Bir yanda tarihî köklerim, Divriği Ulu Camii ile yükselirim.", 
         "gorseller": [],
         "onemi": "Divriği Ulu Camii ve Darüşşifası, Mengücekliler tarafından 13. yüzyılda inşa edilmiştir. UNESCO Dünya Mirası Listesi'ndedir.",
         "nedenleri": "İslam mimarisinde eşi benzeri olmayan bir barok üsluba sahiptir."
        },
        {"yer_adi": "Göreme Millî Parkı", "sayfa": 104, "cumle": "Göreme Millî Parkı...", 
         "gorseller": [],
         "onemi": "Göreme Millî Parkı, Kapadokya bölgesinin kalbidir.",
         "nedenleri": "Bizans sanatının ve Hristiyanlık tarihinin en iyi korunduğu yerlerden biridir."
        },
        {"yer_adi": "Derinkuyu (Yer altı şehri)", "sayfa": 54, "cumle": "Derinkuyu yer altı şehri...", 
         "gorseller": [],
         "onemi": "Kapadokya bölgesindeki en büyük ve en derin yer altı şehridir.",
         "nedenleri": "Düşman saldırılarından korunmak için inşa edilmiştir."
        },
        {"yer_adi": "Kaymaklı (Yer altı şehri)", "sayfa": 54, "cumle": "Kaymaklı yer altı şehri...", 
         "gorseller": [],
         "onemi": "Kaymaklı, tünellerle birbirine bağlanabilen karmaşık bir yapıdır.",
         "nedenleri": "Yer altı şehirlerinin mimari dehasını gösterir."
        }
    ],
    "SB.5.2.2": [
        {"yer_adi": "Yusufeli Barajı", "sayfa": 68, "cumle": "Yusufeli Barajı...", "gorseller": [], "onemi": "Türkiye'nin en yüksek barajıdır.", "nedenleri": "Büyük bir beşerî çevre değişikliğine neden olmuştur."}
    ],
    "SB.5.2.3": [
       {"yer_adi": "Yusufeli Barajı", "sayfa": 68, "cumle": "Yusufeli Barajı...", "gorseller": [], "onemi": "Türkiye'nin en yüksek barajıdır.", "nedenleri": "Büyük bir beşerî çevre değişikliğine neden olmuştur."}
    ],
    "SB.5.2.4": [
        {"yer_adi": "Beyaz Köşk (İzmir)", "sayfa": 83, "cumle": "Beyaz Köşk...", "map_query": "C33X+9G Konak, İzmir", "gorseller": [], "onemi": "İzmir'in tarihi yapılarındandır.", "nedenleri": "Zübeyde Hanım'ın anısını yaşatır."}
    ],
    "SB.5.3.1": [
        {"yer_adi": "Tarihî Yarımada (İstanbul)", "sayfa": 101, "cumle": "Tarihî Yarımada...", "gorseller": [], "onemi": "İstanbul'un en eski yerleşim bölgesidir.", "nedenleri": "Stratejik konumu ve imparatorluklara başkentlik yapması."},
        {"yer_adi": "Topkapı Sarayı", "sayfa": 101, "cumle": "Topkapı Sarayı...", "gorseller": [], "onemi": "Osmanlı'nın idari merkezidir.", "nedenleri": "400 yıl boyunca devleti yöneten merkez olması."},
        {"yer_adi": "Mostar Köprüsü", "sayfa": 103, "cumle": "Mostar Köprüsü...", "gorseller": [], "onemi": "Bosna-Hersek'teki tarihi köprüdür.", "nedenleri": "Kültürlerin birleşmesini simgeler."},
        {"yer_adi": "Nemrut Dağı", "sayfa": 104, "cumle": "Nemrut Dağı...", "gorseller": [], "onemi": "Kommagene Krallığı'nın anıt mezarıdır.", "nedenleri": "Doğu ve Batı sentezini yansıtması."},
        {"yer_adi": "Pamukkale Travertenleri", "sayfa": 105, "cumle": "Pamukkale...", "gorseller": [], "onemi": "Doğal bir harikadır.", "nedenleri": "Jeolojik oluşumu ve termal suları."},
        {"yer_adi": "Hierapolis", "sayfa": 105, "cumle": "Hierapolis...", "gorseller": [], "onemi": "Pamukkale üzerindeki antik kenttir.", "nedenleri": "Sağlık merkezi olması."},
        {"yer_adi": "Karain Mağarası", "sayfa": 105, "cumle": "Karain Mağarası...", "gorseller": [], "onemi": "Türkiye'nin en büyük doğal mağaralarından biridir.", "nedenleri": "En eski insan izlerini taşıması."},
        {"yer_adi": "Cacabey Medresesi", "sayfa": 106, "cumle": "Cacabey Medresesi...", "gorseller": [], "onemi": "Gökbilim medresesidir.", "nedenleri": "Bilime verilen önemi gösterir."},
        {"yer_adi": "Notre Dame Katedrali", "sayfa": 107, "cumle": "Notre Dame...", "gorseller": [], "onemi": "Gotik mimari şaheseridir.", "nedenleri": "Kültürel mirasın korunması bilinci."},
        {"yer_adi": "Efes Antik Kenti", "sayfa": 137, "cumle": "Efes...", "gorseller": [], "onemi": "Antik bir liman kentidir.", "nedenleri": "Ticaret ve din merkezi olması."},
        {"yer_adi": "Süleymaniye Camii", "sayfa": 109, "cumle": "Süleymaniye...", "gorseller": [], "onemi": "Mimar Sinan'ın eseridir.", "nedenleri": "Osmanlı mimarisinin zirvesi."},
        {"yer_adi": "Çanakkale Şehitliği", "sayfa": 109, "cumle": "Çanakkale...", "gorseller": [], "onemi": "Çanakkale Savaşı anıtıdır.", "nedenleri": "Bağımsızlık mücadelesinin simgesi."},
        {"yer_adi": "İshak Paşa Sarayı", "sayfa": 109, "cumle": "İshak Paşa...", "gorseller": [], "onemi": "Ağrı'daki Osmanlı sarayıdır.", "nedenleri": "Mimarisi ve ısıtma sistemi."},
        {"yer_adi": "Sümela Manastırı", "sayfa": 109, "cumle": "Sümela...", "gorseller": [], "onemi": "Trabzon'daki manastırdır.", "nedenleri": "Konumu ve tarihi."},
        {"yer_adi": "Hiroşima Barış Anıtı", "sayfa": 149, "cumle": "Hiroşima...", "gorseller": [], "onemi": "Atom bombası anıtıdır.", "nedenleri": "Barışın önemini hatırlatır."},
        {"yer_adi": "Safranbolu evleri", "sayfa": 149, "cumle": "Safranbolu...", "gorseller": [], "onemi": "Osmanlı kent mimarisini yansıtır.", "nedenleri": "Korunmuş tarihi dokusu."},
        {"yer_adi": "Çatalhöyük", "sayfa": 111, "cumle": "Çatalhöyük...", "gorseller": [], "onemi": "Neolitik kent yerleşimidir.", "nedenleri": "Şehirleşmenin ilk örneklerinden."}
    ],
    "SB.5.3.2": [
        {"yer_adi": "Çatalhöyük", "sayfa": 111, "cumle": "Çatalhöyük...", "gorseller": [], "onemi": "Neolitik kent.", "nedenleri": "Şehirleşme tarihi."},
        {"yer_adi": "Hacılar", "sayfa": 112, "cumle": "Hacılar...", "gorseller": [], "onemi": "Burdur'da höyük.", "nedenleri": "Seramik sanatı."},
        {"yer_adi": "Çayönü", "sayfa": 112, "cumle": "Çayönü...", "gorseller": [], "onemi": "Diyarbakır'da neolitik yerleşim.", "nedenleri": "Tarımın başlangıcı."},
        {"yer_adi": "Şarklı Keper Mağarası", "sayfa": 113, "cumle": "Şarklı Keper...", "gorseller": [], "onemi": "Gaziantep'te mağara.", "nedenleri": "Paleolitik izler."},
        {"yer_adi": "Yarımburgaz Mağarası", "sayfa": 113, "cumle": "Yarımburgaz...", "gorseller": [], "onemi": "İstanbul'da mağara.", "nedenleri": "En eski yerleşimlerden."},
        {"yer_adi": "Beldibi Mağarası", "sayfa": 113, "cumle": "Beldibi...", "gorseller": [], "onemi": "Antalya'da mağara.", "nedenleri": "Kaya resimleri."},
        {"yer_adi": "Göbeklitepe", "sayfa": 114, "cumle": "Göbeklitepe...", "gorseller": [], "onemi": "Dünyanın en eski tapınağı.", "nedenleri": "Tarihi değiştiren bulgular."},
        {"yer_adi": "Hasan Dağı", "sayfa": 120, "cumle": "Hasan Dağı...", "gorseller": [], "onemi": "Volkanik dağ.", "nedenleri": "Obsidiyen kaynağı."},
        {"yer_adi": "Hayırlı Höyüğü", "sayfa": 115, "cumle": "Hayırlı Höyüğü...", "gorseller": [], "onemi": "Mardin'de höyük.", "nedenleri": "Vatandaş bilinciyle bulundu."},
        {"yer_adi": "Karain Mağarası", "sayfa": 105, "cumle": "Karain...", "gorseller": [], "onemi": "Antalya'da mağara.", "nedenleri": "Sürekli iskan."}
    ],
    "SB.5.3.3": [
        {"yer_adi": "Ur", "sayfa": 131, "cumle": "Ur şehri...", "gorseller": [], "onemi": "Sümer şehri.", "nedenleri": "Tekerlek kalıntıları."},
        {"yer_adi": "Uruk", "sayfa": 130, "cumle": "Uruk şehri...", "gorseller": [], "onemi": "Sümer şehri.", "nedenleri": "Yazının doğuşu."},
        {"yer_adi": "Nippur", "sayfa": 130, "cumle": "Nippur...", "gorseller": [], "onemi": "Sümer dini merkezi.", "nedenleri": "Eğitim ve kültür."},
        {"yer_adi": "Louvre Müzesi", "sayfa": 131, "cumle": "Louvre...", "gorseller": [], "onemi": "Paris'te müze.", "nedenleri": "Mezopotamya eserleri."},
        {"yer_adi": "Ziggurat", "sayfa": 132, "cumle": "Ziggurat...", "gorseller": [], "onemi": "Tapınak kuleleri.", "nedenleri": "Din, bilim, depo."},
        {"yer_adi": "Babil", "sayfa": 133, "cumle": "Babil...", "gorseller": [], "onemi": "Babil başkenti.", "nedenleri": "Hammurabi Kanunları."},
        {"yer_adi": "İştar Kapısı", "sayfa": 133, "cumle": "İştar Kapısı...", "gorseller": [], "onemi": "Babil'in kapısı.", "nedenleri": "Mimari ihtişam."},
        {"yer_adi": "Babil Asma Bahçeleri", "sayfa": 133, "cumle": "Asma Bahçeler...", "gorseller": [], "onemi": "Dünyanın 7 harikası.", "nedenleri": "Mühendislik."},
        {"yer_adi": "Ninova", "sayfa": 134, "cumle": "Ninova...", "gorseller": [], "onemi": "Asur başkenti.", "nedenleri": "İlk kütüphane."},
        {"yer_adi": "Kültepe", "sayfa": 134, "cumle": "Kültepe...", "gorseller": [], "onemi": "Ticaret merkezi.", "nedenleri": "Yazının Anadolu'ya gelişi."},
        {"yer_adi": "Asurbanipal Kütüphanesi", "sayfa": 134, "cumle": "Kütüphane...", "gorseller": [], "onemi": "Ninova'da kütüphane.", "nedenleri": "Bilgi arşivi."},
        {"yer_adi": "Hattuşa", "sayfa": 135, "cumle": "Hattuşa...", "gorseller": [], "onemi": "Hitit başkenti.", "nedenleri": "Diplomasi (Kadeş)."},
        {"yer_adi": "Sardes", "sayfa": 136, "cumle": "Sardes...", "gorseller": [], "onemi": "Lidya başkenti.", "nedenleri": "Paranın icadı."},
        {"yer_adi": "Kral Yolu", "sayfa": 137, "cumle": "Kral Yolu...", "gorseller": [], "onemi": "Ticaret yolu.", "nedenleri": "İletişim ve ekonomi."},
        {"yer_adi": "Artemis Tapınağı", "sayfa": 137, "cumle": "Artemis...", "gorseller": [], "onemi": "Efes'te tapınak.", "nedenleri": "Mimari büyüklük."}
    ],
    "SB.5.4.1": [
        {"yer_adi": "TBMM", "sayfa": 18, "cumle": "TBMM...", "gorseller": [], "onemi": "Türkiye Büyük Millet Meclisi.", "nedenleri": "Milli Egemenlik."}
    ],
    "SB.5.6.1": [
        {"yer_adi": "Anadolu Medeniyetleri Müzesi", "sayfa": 129, "cumle": "Müze...", "gorseller": [], "onemi": "Ankara'da müze.", "nedenleri": "Ortak mirasın sergilenmesi."}
    ],
    "SB.5.6.2": [
        {"yer_adi": "Büyük Taarruz Şehitliği", "sayfa": 144, "cumle": "Şehitlik...", "gorseller": [], "onemi": "Afyon'da şehitlik.", "nedenleri": "Bağımsızlık sembolü."}
    ]
}


# ###############################################################
# --- HTML ŞABLONU (DÜZELTİLMİŞ) ---
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
            border-left: 4px solid transparent;
            transition: all 0.2s ease-in-out;
        }
        .yer-listesi-item:hover {
            background-color: #f0f9ff;
            border-left-color: #0ea5e9;
        }
        .yer-listesi-item.active {
            background-color: #e0f2fe;
            border-left-color: #0284c7;
            font-weight: 600;
        }
        
        /* GÖRSEL MODALI (LIGHTBOX) STİLLERİ */
        .modal-overlay {
        display: none;
        position: fixed;
        inset: 0;
        background-color: rgba(0, 0, 0, 0.85);
        z-index: 50;
        align-items: center;
        justify-content: center;
        padding: 1rem;
    }
    .modal-content {
        position: relative;
        max-width: 80vw;
        max-height: 90vh;
    }
    .modal-content img {
        max-width: 100%;
        max-height: 90vh;
        object-fit: contain;
        border-radius: 8px;
    }
    #modal-close-btn {
        position: absolute;
        top: -15px;
        right: -15px;
        background-color: white;
        color: black;
        width: 30px;
        height: 30px;
        border-radius: 50%;
        font-size: 1.2rem;
        font-weight: bold;
        cursor: pointer;
        border: none;
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 60;
    }

    /* Tıklanabilir görsel stili */
    .clickable-image {
        cursor: pointer;
        transition: transform 0.2s;
    }
    .clickable-image:hover {
        transform: scale(1.03);
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    }     
    </style>
    <script src="https://maps.googleapis.com/maps/api/js?key={{ maps_api_key }}&libraries=places"></script>
</head>
<body class="flex h-screen">
    
        <aside class="w-72 bg-white text-gray-800 shadow-lg flex flex-col fixed h-full">
        <div class="px-6 py-4 border-b border-gray-200">
            <h1 class="text-2xl font-extrabold text-blue-600 text-center tracking-wide mb-4">
                Maarif SosyalLab
            </h1>

            <div class="mb-4">
                <div class="w-full p-2 flex items-center justify-center overflow-hidden">
                    <img src="/videolar/maarif.png"  
                         alt="Maarif Logo" 
                         class="w-auto h-auto max-w-full max-h-24 object-contain rounded-lg">
                </div>
            </div>

            <div class="flex items-center">
                <div id="user-avatar-initial" class="w-10 h-10 rounded-full bg-cyan-500 flex items-center justify-center text-white font-bold text-lg">
                    {{ user_name[0] if user_name else 'K' }}
                </div>
                <div class="ml-3">
                    <span id="user-name-placeholder" class="block text-sm font-bold text-gray-800">{{ user_name }}</span>
                </div>
            </div>
        </div>
        
        <nav class="flex-1 overflow-y-auto p-2 space-y-1">

            {% if user_role == 'student' %}
            <a id="link-metin-analiz" href="/metin-analiz" class="flex items-center mx-2 p-2 rounded-lg text-white font-semibold bg-blue-500 hover:bg-blue-600 transition-all">
                <i class="fa-solid fa-file-pen mr-3 w-6 text-center"></i>
                <span>Metin Analiz</span>
            </a>
            <a id="link-soru-uretim" href="/soru-uretim" class="flex items-center mx-2 p-2 rounded-lg text-white font-semibold bg-green-500 hover:bg-green-600 transition-all">
                <i class="fa-solid fa-circle-question mr-3 w-6 text-center"></i>
                <span>Soru Üretim</span>
            </a>
            {% endif %}

            {% if user_role == 'teacher' %}
            <a id="link-metin-olusturma" href="/metin-olusturma" class="flex items-center mx-2 p-2 rounded-lg text-white font-semibold bg-purple-500 hover:bg-purple-600 transition-all">
                <i class="fa-solid fa-wand-magic-sparkles mr-3 w-6 text-center"></i>
                <span>Metin Oluşturma</span>
            </a>
            {% endif %}

            {% if user_role == 'student' %}
            <a id="link-haritada-bul" href="/haritada-bul" class="flex items-center mx-2 p-2 rounded-lg text-white font-semibold bg-orange-600 ring-2 ring-orange-300 transition-all">
                <i class="fa-solid fa-map-location-dot mr-3 w-6 text-center"></i>
                <span>Haritada Bul</span>
            </a>
            <a id="link-podcast" href="/podcast_paneli" class="flex items-center mx-2 p-2 rounded-lg text-white font-semibold bg-red-500 hover:bg-red-600 transition-all">
                <i class="fa-solid fa-microphone-lines mr-3 w-6 text-center"></i>
                <span>Podcast Yap</span>
            </a>
            <a id="link-seyret-bul" href="/seyret-bul-liste" class="flex items-center mx-2 p-2 rounded-lg text-white font-semibold bg-indigo-500 hover:bg-indigo-600 transition-all">
                <i class="fa-solid fa-magnifying-glass-plus mr-3 w-6 text-center"></i>
                <span>Seyret Bul</span>
            </a>
            <a id="link-yarisma" href="/yarisma-secim" class="flex items-center mx-2 p-2 rounded-lg text-white font-semibold bg-teal-500 hover:bg-teal-600 transition-all">
                <i class="fa-solid fa-trophy mr-3 w-6 text-center"></i>
                <span>Beceri/Değer Avcısı</span>
            </a>
            <a id="link-video-istegi" href="/video-istegi" class="flex items-center mx-2 p-2 rounded-lg text-white font-semibold bg-pink-500 hover:bg-pink-600 transition-all">
                <i class="fa-solid fa-video mr-3 w-6 text-center"></i>
                <span>Video İsteği</span>
            </a>
            {% endif %}
            
            <a href="/dashboard" class="flex items-center mx-2 p-2 rounded-lg text-gray-600 font-semibold bg-gray-100 hover:bg-gray-200 transition-all mt-4">
                <i class="fa-solid fa-arrow-left mr-3 w-6 text-center"></i>
                <span>Panele Geri Dön</span>
            </a>

        </nav>
    </aside>

    <main class="ml-72 flex-1 p-6 md:p-8 overflow-y-auto h-screen">
        <h2 class="text-3xl font-bold text-gray-800 mb-6">Haritada Bul</h2>
        
        <div class="grid grid-cols-12 gap-6">
            <div class="col-span-4">
                <div class="bg-white p-4 rounded-lg shadow h-64 flex flex-col"> 
                    <label for="surec-bileseni-select" class="block text-sm font-medium text-gray-700 mb-2">1. Süreç Bileşeni Seçin:</label>
                    <select id="surec-bileseni-select" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500 bg-white">
                        <option value="">Lütfen bir bileşen seçin...</option>
                        {% for kod, aciklama in surec_bilesenleri.items() %}
                        <option value="{{ kod }}" title="{{ aciklama }}">{{ kod }} - {{ aciklama[:40] }}...</option>
                        {% endfor %}
                    </select>
                </div>
            </div>
            <div class="col-span-8">
                <div class="bg-white p-4 rounded-lg shadow h-64 overflow-y-auto"> 
                    <label class="block text-sm font-medium text-gray-700 mb-2">2. Yeri Seçin:</label>
                    <div id="yer-listesi" class="divide-y divide-gray-200">
                        <p class="text-sm text-gray-500 p-4 text-center">Yerleri listelemek için lütfen bir süreç bileşeni seçin.</p>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="mt-6">
            <div id="detay-paneli" class="bg-white rounded-lg shadow overflow-hidden relative">
                
                <div id="baslangic-mesaji" class="flex items-center justify-center h-96">
                    <p class="text-lg text-gray-500 p-8 text-center">
                        <i class="fa-solid fa-arrow-left text-2xl mb-4"></i><br>
                        Detayları görmek için lütfen yukarıdaki listeden bir yer seçin.
                    </p>
                </div>
                
                <div id="detay-icerik" class="hidden p-6 space-y-4">
                     <h3 id="detay-baslik" class="text-2xl font-bold text-gray-800"></h3>
                    
                    <div>
                        <h4 class="text-lg font-semibold text-gray-700 mb-2">Harita</h4>
                        <iframe id="map-iframe" width="100%" height="300" style="border:0;" loading="lazy" allowfullscreen referrerpolicy="no-referrer-when-downgrade" src="">
                        </iframe>
                    </div>

                    <div>
                        <h4 class="text-lg font-semibold text-gray-700 mb-2">Görseller</h4>
                        <div id="image-container" class="grid grid-cols-2 gap-4">
                            </div>
                    </div>
                    
                    <div>
                        <h4 class="text-lg font-semibold text-gray-700 mb-2">Tarihteki Önemi</h4>
                        <p id="onem-metni" class="text-gray-600 bg-gray-50 p-4 rounded-lg border"></p>
                    </div>
                    
                    <div>
                        <h4 class="text-lg font-semibold text-gray-700 mb-2">Öneminin Nedenleri</h4>
                        <p id="nedenler-metni" class="text-gray-600 bg-gray-50 p-4 rounded-lg border"></p>
                    </div>
                </div>
            </div>
        </div>
    </main>

    <div id="image-modal" class="modal-overlay" style="display: none;">
        <button id="modal-close-btn">×</button>
        <div class="modal-content">
            <img id="modal-image" src="" alt="Büyütülmüş Görsel">
        </div>
    </div>
    
    <script>
        // Veritabanını JS'ye aktar (Hata olmaması için tojson filtresi kullanılıyor)
        const yerVeritabani = {{ yer_veritabani | tojson }};
        const mapsApiKey = "{{ maps_api_key }}";
        const loggedInUserNo = "{{ user_no }}";

        document.addEventListener('DOMContentLoaded', () => {
            const bilesenSelect = document.getElementById('surec-bileseni-select');
            const yerListesiContainer = document.getElementById('yer-listesi');
            
            const baslangicMesaji = document.getElementById('baslangic-mesaji');
            const detayIcerik = document.getElementById('detay-icerik');
            
            const modalOverlay = document.getElementById('image-modal');
            const modalImage = document.getElementById('modal-image');
            const modalCloseBtn = document.getElementById('modal-close-btn');
            
            let aktifYerItem = null; 

            // 1. Açılır menü değiştiğinde
            bilesenSelect.addEventListener('change', (e) => {
                const secilenKod = e.target.value;
                yerListesiContainer.innerHTML = ''; 
                resetDetayPaneli(); 
                
                if (!secilenKod) {
                    yerListesiContainer.innerHTML = '<p class="text-sm text-gray-500 p-4 text-center">Yerleri listelemek için lütfen bir süreç bileşeni seçin.</p>';
                    return;
                }
                const yerler = yerVeritabani[secilenKod] || [];
                if (yerler.length === 0) {
                     yerListesiContainer.innerHTML = '<p class="text-sm text-gray-500 p-4 text-center">Bu bileşen için yer bulunamadı.</p>';
                    return;
                }
                
                // LİSTE OLUŞTURMA DÖNGÜSÜ
                yerler.forEach(yer => {
                    const item = document.createElement('div');
                    item.className = 'yer-listesi-item p-4 border-b border-gray-100 flex justify-between items-center';
                    item.innerHTML = `
                        <div>
                            <span class="font-semibold text-gray-700 block">${yer.yer_adi}</span>
                            <span class="text-xs text-gray-500">Sayfa: ${yer.sayfa}</span>
                        </div>
                        <i class="fa-solid fa-chevron-right text-gray-400"></i>
                    `;
                    
                    item.addEventListener('click', () => {
                        if (aktifYerItem) {
                            aktifYerItem.classList.remove('active');
                        }
                        item.classList.add('active');
                        aktifYerItem = item;
                        fetchYerDetaylari(yer); 
                        
                        // İnceleme kaydı (Raporlama)
                        if (loggedInUserNo) {
                            fetch('/api/harita/kaydet-inceleme', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ 
                                    student_no: loggedInUserNo, 
                                    yer_adi: yer.yer_adi 
                                })
                            }).catch(err => console.error("Log hatası:", err));
                        }
                    });
                    
                    yerListesiContainer.appendChild(item);
                });
            });
            
            function resetDetayPaneli() {
                baslangicMesaji.style.display = 'flex';
                detayIcerik.style.display = 'none';
                if (aktifYerItem) {
                    aktifYerItem.classList.remove('active');
                    aktifYerItem = null;
                }
            }
            
            // 3. Detayları Gösteren Fonksiyon
            function fetchYerDetaylari(yerObject) {
                const yerAdi = yerObject.yer_adi;
                
                baslangicMesaji.style.display = 'none';
                
                // Harita URL'si (Düzeltilmiş)
                const haritaSorgusu = yerObject.map_query || yerObject.yer_adi;
                const mapUrl = `https://maps.google.com/maps?q=${encodeURIComponent(haritaSorgusu)}&t=k&z=9&output=embed`;
                document.getElementById('map-iframe').src = mapUrl;

                // Görseller
                const imageContainer = document.getElementById('image-container');
                imageContainer.innerHTML = ''; 
                
                const gorseller = yerObject.gorseller || []; 
                if (gorseller.length > 0) {
                    gorseller.forEach(gorsel => {
                        const gorselWrapper = document.createElement('div');
                        
                        const img = document.createElement('img');
                        // Dosya adı varsa static'ten, yoksa url'den al
                        if (gorsel.dosya) {
                            img.src = `/static/images/harita_gorselleri/${gorsel.dosya}`;
                        } else {
                            img.src = gorsel.url;
                        }
                        
                        img.alt = yerAdi;
                        img.className = 'w-full h-48 object-cover rounded-lg border clickable-image';
                        img.onerror = function() {
                            this.src = `http://via.placeholder.com/400x300?text=${encodeURIComponent(yerAdi)}`;
                        };
                        
                        img.addEventListener('click', () => {
                            modalImage.src = img.src;
                            modalOverlay.style.display = 'flex';
                        });
                        
                        const kaynakText = document.createElement('p');
                        kaynakText.className = 'text-xs text-gray-500 italic mt-1';
                        kaynakText.textContent = `Kaynak: ${gorsel.kaynak || 'Bilinmiyor'}`;
                        
                        gorselWrapper.appendChild(img);
                        gorselWrapper.appendChild(kaynakText);
                        imageContainer.appendChild(gorselWrapper);
                    });
                } else {
                    imageContainer.innerHTML = '<p class="text-sm text-gray-500">Bu yer için görsel bulunamadı.</p>';
                }

                // Metinler
                document.getElementById('detay-baslik').textContent = yerAdi;
                document.getElementById('onem-metni').textContent = yerObject.onemi || "Bilgi yok.";
                document.getElementById('nedenler-metni').textContent = yerObject.nedenleri || "Bilgi yok.";
                
                detayIcerik.style.display = 'block';
            }
            
            // Modal Kapatma
            modalCloseBtn.addEventListener('click', () => { modalOverlay.style.display = 'none'; });
            modalOverlay.addEventListener('click', (e) => { if (e.target === modalOverlay) modalOverlay.style.display = 'none'; });
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
        # Session'dan bilgileri al (Varsayılanlar güvenli)
        user_name = session.get('name', 'Kullanıcı')
        user_role = session.get('role', 'student')
        user_no = session.get('user_no', '')

        return render_template_string(
            HARITADA_BUL_HTML,
            surec_bilesenleri=SUREC_BILESENLERI_HARITA,
            yer_veritabani=HARITA_VERITABANI,
            maps_api_key=GOOGLE_MAPS_API_KEY,
            user_name=user_name,
            user_role=user_role,
            user_no=user_no
        )
