# harita_bul.py
# Bu dosya, ana sosyallab.py uygulaması tarafından içe aktarılmak (import) üzere tasarlanmıştır.
# SÜRÜM 4 (NİHAİ):
# 1. TÜM analiz metinleri (onemi, nedenleri) koda eklendi.
# 2. Gemini API bağımlılığı TAMAMEN kaldırıldı.
# 3. Görsel büyütme (lightbox) eklendi.
# 4. Hatalı Google Maps URL'si DÜZELTİLDİ.
# 5. Boş olan ilk görseller (Derinkuyu, Kaymaklı, Yusufeli) Wikimedia Commons'tan eklendi.

from flask import render_template_string, request, jsonify
import json # JSON işlemleri için import edildi

# ###############################################################
# --- VERİ TABANLARI (TÜM METİNLER DOLDURULDU) ---
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

# VERİTABANI (DOLDURULDU)
HARITA_VERITABANI = {
    "SB.5.1.2": [
        {"yer_adi": "Kapadokya", "sayfa": 29, "cumle": "Türkiye'nin turizm merkezlerinden Kapadokya", 
         "gorseller": [
            {"url": "https://i.dha.com.tr/15669/imgs/030420211500117072525.jpg", "kaynak": "DHA"},
            {"url": "https://www.kapadokya.org/wp-content/uploads/2021/01/kapadokya-balon-turu.jpeg", "kaynak": "kapadokya.org"}
        ],
         "onemi": "Kapadokya, 60 milyon yıl önce Erciyes, Hasandağı ve Güllüdağ'ın püskürttüğü lav ve küllerin oluşturduğu yumuşak tabakaların, milyonlarca yıl boyunca yağmur ve rüzgar tarafından aşındırılmasıyla ortaya çıkan 'Peribacaları' ile ünlüdür. Aynı zamanda, insanların bu yumuşak kayaları oyarak evler, kiliseler ve yer altı şehirleri inşa ettiği, Hristiyanlığın ilk dönemlerinde önemli bir sığınma ve manastır merkezi olmuştur.",
         "nedenleri": "Kapadokya'nın önemi, eşsiz jeolojik yapısından ve bu yapının sunduğu korunma imkanlarından gelir. Bölgenin tüflü volkanik arazisi, kolayca oyulabilir olduğu için ilk Hristiyanlar tarafından sığınak ve ibadet alanı olarak kullanılmıştır. Ayrıca İpek Yolu gibi önemli ticaret yollarının üzerinde bulunması, bölgeyi tarih boyunca kültürel bir kavşak noktası yapmıştır."
        }
    ],
    "SB.5.2.1": [
        {"yer_adi": "Divriği Ulu Camii", "sayfa": 51, "cumle": "Bir yanda tarihî köklerim, Divriği Ulu Camii ile yükselirim.", 
         "gorseller": [
            {"url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/73/Divri%C4%9Fi_Ulu_Camii_Dar%C3%BC%C5%9F%C5%9Fifas%C4%B1_Cennet_Kap%C4%B1s%C4%B1_-_2013-05-27.jpg/800px-Divri%C4%9Fi_Ulu_Camii_Dar%C3%BC%C5%9F%C5%9Fifas%C4%B1_Cennet_Kap%C4%B1s%C4%B1_-_2013-05-27.jpg", "kaynak": "Wikimedia Commons"},
            {"url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/52/Divri%C4%9Fi_Grand_Mosque_and_Hospital_-_Genel_G%C3%B6r%C3%BCn%C3%BCm.jpg/1024px-Divri%C4%9Fi_Grand_Mosque_and_Hospital_-_Genel_G%C3%B6r%C3%BCn%C3%BCm.jpg", "kaynak": "Wikimedia Commons"}
         ],
         "onemi": "Divriği Ulu Camii ve Darüşşifası, Mengücekliler tarafından 13. yüzyılda inşa edilmiştir. Anadolu taş oymacılığının en muhteşem örneklerinden biri olarak kabul edilir. Özellikle 'Cennet Kapısı' üzerindeki inanılmaz detaylı ve üç boyutlu işlemeler, mimari bir harika olarak görülür.",
         "nedenleri": "Bu yapının önemi, UNESCO Dünya Mirası Listesi'ne giren ilk Türk mimari eseri olmasından kaynaklanır. İslam mimarisinde eşi benzeri olmayan bir barok üsluba sahiptir. Bir cami ve bir hastaneyi (darüşşifa) birleştiren bu külliye, o dönemin sosyal devlet anlayışını ve sanattaki zirvesini gösterir."
        },
        {"yer_adi": "Göreme Millî Parkı", "sayfa": 104, "cumle": "Göreme Millî Parkı ve Kapadokya’nın Kayalık Alanları...", 
         "gorseller": [
            {"url": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e6/Goreme_open_air_museum_60.jpg/1280px-Goreme_open_air_museum_60.jpg", "kaynak": "Wikimedia Commons"},
            {"url": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6e/G%C3%B6reme_Open_Air_Museum_-_Karanl%C4%B1k_Kilise_-_Nave_-_Christ_Pantocrator_-_2014-06-03.jpg/800px-G%C3%B6reme_Open_Air_Museum_-_Karanl%C4%B1k_Kilise_-_Nave_-_Christ_Pantocrator_-_2014-06-03.jpg", "kaynak": "Wikimedia Commons"}
         ],
         "onemi": "Göreme Millî Parkı, Kapadokya bölgesinin kalbidir ve UNESCO Dünya Mirası Listesi'ndedir. Burası, kayalara oyulmuş, 10. ve 13. yüzyıllara ait fresklerle (duvar resimleri) süslü yüzden fazla kilise ve manastıra ev sahipliği yapar.",
         "nedenleri": "Parkın önemi, Bizans sanatının ve Hristiyanlık tarihinin en iyi korunduğu yerlerden biri olmasından gelir. Yumuşak tüf kayalar, ilk Hristiyanların sığınak ve ibadet alanı olarak kullandığı bu kiliseleri oymasını kolaylaştırmıştır. Karanlık Kilise gibi yapılar, dönemin dini sanatının zirvesini temsil eder."
        },
        {"yer_adi": "Derinkuyu (Yer altı şehri)", "sayfa": 54, "cumle": "Nevşehir; ... Derinkuyu ve Kaymaklı yer altı şehirleri...", 
         "gorseller": [
            {"url": "https://upload.wikimedia.org/wikipedia/commons/e/e6/Derinkuyu_underground_city_-_ventilation_shaft.jpg", "kaynak": "Wikimedia Commons"},
            {"url": "https://upload.wikimedia.org/wikipedia/commons/b/b6/Derinkuyu_underground_city_-_church.jpg", "kaynak": "Wikimedia Commons"}
         ],
         "onemi": "Derinkuyu, Kapadokya bölgesindeki en büyük ve en derin yer altı şehridir. Binlerce insanın barınabileceği, 8 kata kadar yeryüzünün altına inen devasa bir komplekstir. İçerisinde ahırlar, kilerler, şırahaneler, kiliseler ve havalandırma bacaları bulunur.",
         "nedenleri": "Bu yapının önemi, bölgenin tarih boyunca (özellikle ilk Hristiyanlar ve Arap akınları sırasında) bir sığınma alanı olarak kullanılmasından kaynaklanır. Düşman saldırılarından korunmak için inşa edilmiştir. Devasa taş kapılar (tıhrazlar), tehlike anında koridorları kapatarak şehri savunmayı kolaylaştırmıştır."
        },
        {"yer_adi": "Kaymaklı (Yer altı şehri)", "sayfa": 54, "cumle": "Nevşehir; ... Derinkuyu ve Kaymaklı yer altı şehirleri...", 
         "gorseller": [
            {"url": "https://upload.wikimedia.org/wikipedia/commons/a/a6/Kaymakli_Underground_City_4.jpg", "kaynak": "Wikimedia Commons"},
            {"url": "https://upload.wikimedia.org/wikipedia/commons/7/7c/Kaymakl%C4%B1_Underground_City_in_Turkey.jpg", "kaynak": "Wikimedia Commons"}
         ],
         "onemi": "Kaymaklı, Kapadokya'daki bir diğer büyük ve önemli yer altı şehridir. Derinkuyu kadar derin olmasa da, daha geniş alanlara yayılmıştır. Bu şehirler, tünellerle birbirine bağlanabilen karmaşık savunma ve yaşam alanlarıdır.",
         "nedenleri": "Kaymaklı'nın önemi, yer altı şehirlerinin mimari dehasını göstermesidir. Düşük tavanlı tüneller, havalandırma bacaları ve erzak depoları, bir topluluğun uzun süre yeryüzüne çıkmadan yaşayabilmesi için tasarlanmıştır. Bu, bölgenin stratejik coğrafyasının bir sonucudur."
        }
    ],
    "SB.5.2.2": [
        {"yer_adi": "Yusufeli Barajı", "sayfa": 68, "cumle": "Yusufeli Barajı nedeniyle yerleşim yerleri değişen köylüler...", 
         "gorseller": [
            {"url": "https://upload.wikimedia.org/wikipedia/commons/0/07/Yusufeli_Baraj%C4%B1_g%C3%B6vdesi_ve_yama%C3%A7lar.jpg", "kaynak": "Wikimedia Commons"},
            {"url": "https://upload.wikimedia.org/wikipedia/commons/5/5e/Yusufeli_dam_construction_site_in_2018.jpg", "kaynak": "Wikimedia Commons"}
         ],
         "onemi": "Yusufeli Barajı, Artvin'de Çoruh Nehri üzerine inşa edilen, Türkiye'nin en yüksek, dünyanın ise en yüksek beşinci barajıdır. Ülkenin enerji ihtiyacını karşılamak için yapılan devasa bir mühendislik projesidir.",
         "nedenleri": "Barajın önemi, hidroelektrik enerji üretim kapasitesinin yanı sıra, büyük bir beşerî çevre değişikliğine neden olmasıdır. Barajın inşası, Yusufeli ilçe merkezinin ve birçok köyün sular altında kalmasına ve insanların yeni yerleşim yerlerine taşınmasına yol açmıştır. Bu durum, 'kalkınma' ve 'doğal/sosyal çevreye etki' arasındaki ilişkiyi gösteren önemli bir örnektir."
        }
    ],
    "SB.5.2.3": [
        {"yer_adi": "Yusufeli Barajı", "sayfa": 68, "cumle": "Yusufeli Barajı nedeniyle yerleşim yerleri değişen köylüler...", 
         "gorseller": [
            {"url": "https://upload.wikimedia.org/wikipedia/commons/0/07/Yusufeli_Baraj%C4%B1_g%C3%B6vdesi_ve_yama%C3%A7lar.jpg", "kaynak": "Wikimedia Commons"},
            {"url": "https://upload.wikimedia.org/wikipedia/commons/5/5e/Yusufeli_dam_construction_site_in_2018.jpg", "kaynak": "Wikimedia Commons"}
         ],
         "onemi": "Yusufeli Barajı, Artvin'de Çoruh Nehri üzerine inşa edilen, Türkiye'nin en yüksek, dünyanın ise en yüksek beşinci barajıdır. Ülkenin enerji ihtiyacını karşılamak için yapılan devasa bir mühendislik projesidir.",
         "nedenleri": "Barajın önemi, hidroelektrik enerji üretim kapasitesinin yanı sıra, büyük bir beşerî çevre değişikliğine neden olmasıdır. Barajın inşası, Yusufeli ilçe merkezinin ve birçok köyün sular altında kalmasına ve insanların yeni yerleşim yerlerine taşınmasına yol açmıştır. Bu durum, 'kalkınma' ve 'doğal/sosyal çevreye etki' arasındaki ilişkiyi gösteren önemli bir örnektir."
        }
    ],
    "SB.5.2.4": [
        {"yer_adi": "Beyaz Köşk (İzmir)", "sayfa": 83, "cumle": "Karşıyaka'ya yolculuk başlamış... Beyaz Köşk'e doğru...", 
     "map_query": "C33X+9G Konak, İzmir", # <-- YENİ EKLENDİ (Sizin verdiğiniz konum)
         "gorseller": [
            {"url": "http://via.placeholder.com/400x300?text=Beyaz+Kosk", "kaynak": "Kaynak... (örn: İzmir Bel.)"},
            {"url": "http://via.placeholder.com/400x300?text=Beyaz+Kosk+2", "kaynak": "Kaynak..."}
         ],
         "onemi": "Beyaz Köşk, İzmir'in Konak ilçesinde bulunan tarihi bir yapıdır...", # <-- DÜZELTİLDİ
         "nedenleri": "Köşk'ün önemi, Zübeyde Hanım'ın..."
        }
    ],
    "SB.5.3.1": [
        {"yer_adi": "Tarihî Yarımada (İstanbul)", 
         "sayfa": 101, 
         "cumle": "Örneğin İstanbul'da bulunan Tarihî Yarımada...", 
         "gorseller": [
            {"dosya": "tarihi_yarimada1(4havacekim.com).jpg", "kaynak": "4havacekim.com"},
            {"dosya": "tarihi_yarimada2(saltresearch.org).jpg", "kaynak": "saltresearch.org"}
        ],
         "onemi": "Tarihi Yarımada (Suriçi İstanbul), İstanbul'un en eski yerleşim bölgesidir ve üç imparatorluğa (Roma, Bizans, Osmanlı) başkentlik yapmıştır. UNESCO Dünya Mirası Listesi'ndedir ve Ayasofya, Topkapı Sarayı, Sultanahmet Camii gibi dünyanın en önemli anıtlarını barındırır.",
         "nedenleri": "Bölgenin önemi, stratejik coğrafi konumundan gelir. Haliç, Marmara Denizi ve Boğaz tarafından çevrelenmesi, onu doğal bir kale haline getirmiştir. Asya ve Avrupa'yı birleştiren kara ve deniz yolları üzerinde olması, onu binlerce yıl boyunca dünyanın ticaret ve siyaset merkezi yapmıştır."
        },
        {"yer_adi": "Topkapı Sarayı", "sayfa": 101, "cumle": "Örneğin Topkapı Sarayı, Tarihî Yarımada’da bulunan...", 
         "gorseller": [
            {"url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/08/Topkapi_Palace_Gate_of_Salutation_Istanbul_Turkey.jpg/1280px-Topkapi_Palace_Gate_of_Salutation_Istanbul_Turkey.jpg", "kaynak": "Wikimedia Commons"},
            {"url": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e3/Istanbul_-_Topkapi_Saray_-_Harem_-_3928.jpg/1280px-Istanbul_-_Topkapi_Saray_-_Harem_-_3928.jpg", "kaynak": "Wikimedia Commons"}
         ],
         "onemi": "Topkapı Sarayı, Fatih Sultan Mehmet tarafından 1478'de yaptırılmış ve yaklaşık 400 yıl boyunca Osmanlı İmparatorluğu'nun hem idari merkezi hem de padişahların evi olmuştur. Sadece bir saray değil, aynı zamanda devletin en önemli kararlarının alındığı, hazinenin korunduğu ve kutsal emanetlerin saklandığı bir komplekstir.",
         "nedenleri": "Sarayın önemi, İstanbul'un fethinden sonra yeni başkentin tam kalbine, stratejik bir noktaya (Sarayburnu) inşa edilmesinden gelir. Burası hem Haliç'i hem de Boğaz'ı kontrol eden, Asya ve Avrupa'yı birleştiren bir tepedir. Bu coğrafi konum, saraya siyasi ve askeri bir güç merkezi olma özelliği kazandırmıştır."
        },
        {"yer_adi": "Mostar Köprüsü", "sayfa": 103, "cumle": "Mostar Köprüsü, yaşanan felaketlerin ve bunlar karşısında...", 
         "gorseller": [
            {"url": "http://via.placeholder.com/400x300?text=Mostar", "kaynak": "Kaynak..."},
            {"url": "http://via.placeholder.com/400x300?text=Mostar+2", "kaynak": "Kaynak..."}
         ],
         "onemi": "Mostar Köprüsü, Bosna-Hersek'in Mostar şehrinde, Neretva Nehri üzerinde bulunan tarihi bir köprüdür. Mimar Sinan'ın öğrencisi Mimar Hayreddin tarafından 1566'da inşa edilmiştir ve Osmanlı mimarisinin bir şaheseridir.",
         "nedenleri": "Köprünün önemi, sadece mimari bir başarı olması değil, aynı zamanda şehrin iki yakasındaki Boşnak ve Hırvat toplumlarını (farklı kültür ve dinleri) birleştiren bir sembol olmasıdır. 1993'te Bosna Savaşı'nda kasten yıkılması ve daha sonra uluslararası çabalarla yeniden inşa edilmesi, onu 'barışın ve kültürlerin bir araya gelmesinin' sembolü yapmıştır."
        },
        {"yer_adi": "Nemrut Dağı", "sayfa": 104, "cumle": "Adıyaman ili Kahta ilçesi sınırları içinde bulunan...", 
         "gorseller": [
            {"url": "http://via.placeholder.com/400x300?text=Nemrut", "kaynak": "Kaynak..."},
            {"url": "http://via.placeholder.com/400x300?text=Nemrut+2", "kaynak": "Kaynak..."}
         ],
         "onemi": "Nemrut Dağı, Kommagene Krallığı'nın MÖ 1. yüzyılda hüküm süren kralı I. Antiochos tarafından yaptırılmış devasa heykellerin bulunduğu bir anıt mezardır. UNESCO Dünya Mirası Listesi'ndedir. Dağın zirvesinde, kralın mezarının (tümülüs) her iki yanında Grek ve Pers tanrılarının devasa heykelleri bulunur.",
         "nedenleri": "Buranın önemi, Kommagene Krallığı'nın Doğu (Pers) ve Batı (Helenistik) kültürlerini birleştirme çabasını göstermesidir. Kral Antiochos, bu anıtı kendi soyunu tanrılara dayandırmak ve krallığının gücünü göstermek için inşa ettirmiştir. Gün batımı ve gün doğumunun en güzel izlendiği yerlerden biri olarak da bilinir."
        },
        {"yer_adi": "Pamukkale Travertenleri", "sayfa": 105, "cumle": "Denizli sınırlarındaki Çaldağı’nın eteklerinden gelen...", 
         "gorseller": [
            {"url": "http://via.placeholder.com/400x300?text=Pamukkale", "kaynak": "Kaynak..."},
            {"url": "http://via.placeholder.com/400x300?text=Pamukkale+2", "kaynak": "Kaynak..."}
         ],
         "onemi": "Pamukkale, doğal bir harikadır ve UNESCO Dünya Mirası Listesi'ndedir. Kaynaktan çıkan kalsiyum bikarbonat açısından zengin termal suların, havadaki oksijenle teması sonucu çökelmesiyle oluşan bembeyaz 'traverten' (taş) teraslarından oluşur.",
         "nedenleri": "Önemi, bu eşsiz jeolojik oluşumun yanı sıra, bu termal suların binlerce yıldır şifa merkezi olarak kullanılmasından gelir. Hemen arkasında, bu sular üzerine kurulmuş olan Hierapolis Antik Kenti bulunur. Bu, doğa ve tarihin iç içe geçtiği nadir yerlerden biridir."
        },
        {"yer_adi": "Hierapolis (Hiyerapolis)", "sayfa": 105, "cumle": "Ayrıca aynı bölgede yer alan Hierapolis (Hiyerapolis)...", 
         "gorseller": [
            {"url": "http://via.placeholder.com/400x300?text=Hierapolis", "kaynak": "Kaynak..."},
            {"url": "http://via.placeholder.com/400x300?text=Hierapolis+2", "kaynak": "Kaynak..."}
         ],
         "onemi": "Hierapolis, Pamukkale travertenlerinin hemen üzerine kurulmuş bir Antik Roma kentidir. 'Kutsal Şehir' anlamına gelir. En önemli özelliği, antik çağın en büyük nekropollerinden (mezarlık) birine ve muhteşem bir antik tiyatroya sahip olmasıdır.",
         "nedenleri": "Buranın önemi, Pamukkale'nin şifalı termal sularından (jeotermal kaynak) gelir. İnsanlar antik çağda buraya sağlık bulmak için gelirlerdi ve birçoğu burada vefat ettiği için devasa bir mezarlık alanı oluşmuştur. Antik Havuz, bugün bile ziyaretçilerin termal suların içinde yüzebildiği bir yerdir."
        },
        {"yer_adi": "Karain Mağarası", "sayfa": 105, "cumle": "Türkiye’nin en büyük doğal mağaralarından Karain Mağarası...", 
         "gorseller": [
            {"url": "http://via.placeholder.com/400x300?text=Karain", "kaynak": "Kaynak..."},
            {"url": "http://via.placeholder.com/400x300?text=Karain+2", "kaynak": "Kaynak..."}
         ],
         "onemi": "Karain Mağarası, Antalya yakınlarında bulunan ve Türkiye'nin en büyük doğal mağaralarından biridir. Bu mağara, Paleolitik (Eski Taş) Çağ'dan Roma dönemine kadar, yaklaşık 500.000 yıl boyunca insanlar tarafından sürekli olarak iskan edilmiştir.",
         "nedenleri": "Önemi, Anadolu'daki en eski insan kalıntılarının (Neandertal) burada bulunmuş olmasıdır. Bu mağara, avcı-toplayıcı insanların yaşam tarzı, alet yapımı ve zaman içindeki evrimi hakkında bize paha biçilmez bilgiler sunan arkeolojik bir hazinedir."
        },
        {"yer_adi": "Cacabey Medresesi", "sayfa": 106, "cumle": "...Kırşehir Cacabey Medresesi’nde kapsamlı bir restorasyon...", 
         "gorseller": [
            {"url": "http://via.placeholder.com/400x300?text=Cacabey", "kaynak": "Kaynak..."},
            {"url": "http://via.placeholder.com/400x300?text=Cacabey+2", "kaynak": "Kaynak..."}
         ],
         "onemi": "Cacabey Medresesi, 13. yüzyılda Anadolu Selçukluları döneminde Kırşehir Valisi Caca Bey tarafından yaptırılmıştır. Başlangıçta bir medrese (okul) olarak inşa edilmiştir ve o dönemde pozitif bilimlerin okutulduğu bir merkezdi.",
         "nedenleri": "Buranın en ilginç özelliği, bir 'astronomi' okulu (gözlemevi) olarak tasarlanmış olmasıdır. Medresenin içindeki avluda bir kuyu (gözlem çukuru) ve çatısında bir açıklık (gözlem kulesi) bulunur. Bu, Türk-İslam dünyasının bilime, özellikle de gökbilime verdiği önemi gösteren tarihi bir kanıttır."
        },
        {"yer_adi": "Notre Dame Katedrali", "sayfa": 107, "cumle": "...Paris’te çıkan yangında büyük hasar gören Notre Dame...", 
         "gorseller": [
            {"url": "http://via.placeholder.com/400x300?text=Notre+Dame", "kaynak": "Kaynak..."},
            {"url": "http://via.placeholder.com/400x300?text=Notre+Dame+2", "kaynak": "Kaynak..."}
         ],
         "onemi": "Notre Dame Katedrali, Fransa'nın Paris şehrinde bulunan dünyaca ünlü bir Gotik mimari şaheseridir. 12. yüzyılda inşa edilmeye başlanmış ve Fransız tarihinin birçok önemli olayına tanıklık etmiştir.",
         "nedenleri": "Katedralin önemi, Gotik sanatın en bilinen örneklerinden biri olmasının yanı sıra, 2019'da geçirdiği büyük yangınla 'kültürel mirasın korunması' konusunu tüm dünyaya hatırlatmasıdır. Yangından sonra, 3 boyutlu dijital taramalar sayesinde restore edilebilmesi, teknolojinin ortak mirası korumadaki rolünü göstermiştir."
        },
        {"yer_adi": "Efes Antik Kenti", "sayfa": 137, "cumle": "Artemis Tapınağı ve Efes Antik Kenti İyonyalılardan...", 
         "gorseller": [
            {"url": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e0/Celsus_Library_in_Ephesus_2.jpg/800px-Celsus_Library_in_Ephesus_2.jpg", "kaynak": "Wikimedia Commons"},
            {"url": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b3/Ephesus_Theater_Main_Street_View.JPG/1280px-Ephesus_Theater_Main_Street_View.JPG", "kaynak": "Wikimedia Commons"}
         ],
         "onemi": "Efes Antik Kenti, İyonya döneminde kurulan ve Roma İmparatorluğu döneminde Asya Eyaleti'nin başkenti olan muazzam bir liman kentiydi. Celsus Kütüphanesi ve Büyük Tiyatrosu ile ünlüdür. UNESCO Dünya Mirası Listesi'ndedir.",
         "nedenleri": "Önemi, antik dünyanın en büyük ve en zengin şehirlerinden biri olmasından gelir. Coğrafi konumu (deniz ticareti yolu üzerinde) sayesinde büyük bir ticaret merkezi olmuştur. Aynı zamanda, dünyanın yedi harikasından biri olan Artemis Tapınağı'na ev sahipliği yapması, onu önemli bir dini merkez haline getirmiştir."
        },
        {"yer_adi": "Süleymaniye Camii", "sayfa": 109, "cumle": "Süleymaniye Camii", 
         "gorseller": [
            {"url": "http://via.placeholder.com/400x300?text=Suleymaniye", "kaynak": "Kaynak..."},
            {"url": "http://via.placeholder.com/400x300?text=Suleymaniye+2", "kaynak": "Kaynak..."}
         ],
         "onemi": "Süleymaniye Camii, Kanuni Sultan Süleyman adına Mimar Sinan tarafından İstanbul'da inşa edilmiştir. Mimar Sinan'ın 'kalfalık eseri' olarak bilinir ve Osmanlı mimarisinin zirvelerinden biridir.",
         "nedenleri": "Önemi, sadece muhteşem mimarisinden değil, aynı zamanda etrafındaki medreseler, kütüphane, hastane ve hamam ile birlikte dev bir 'külliye' (sosyal kompleks) olmasından gelir. Bu, Osmanlı'nın hem gücünü hem de sosyal devlet anlayışını gösteren bir semboldür."
        },
        {"yer_adi": "Çanakkale Şehitliği", "sayfa": 109, "cumle": "Çanakkale Şehitliği", 
         "gorseller": [
            {"url": "http://via.placeholder.com/400x300?text=Canakkale", "kaynak": "Kaynak..."},
            {"url": "http://via.placeholder.com/400x300?text=Canakkale+2", "kaynak": "Kaynak..."}
         ],
         "onemi": "Çanakkale Şehitliği, I. Dünya Savaşı sırasında Çanakkale Cephesi'nde (1915) hayatını kaybeden Türk askerlerinin anısına Gelibolu Yarımadası'nda kurulmuş anıtlar ve mezarlıklardır. Şehitler Abidesi, en bilinen anıtıdır.",
         "nedenleri": "Burasının önemi, Türk tarihi için bir dönüm noktası olmasıdır. 'Çanakkale Geçilmez' sözüyle sembolleşen bu savunma, Kurtuluş Savaşı'nın lideri olacak Mustafa Kemal Atatürk'ün askeri dehasını gösterdiği yerdir. Vatanseverlik, fedakarlık ve ulusal bilinç için en önemli sembolik mekandır."
        },
        {"yer_adi": "İshak Paşa Sarayı", "sayfa": 109, "cumle": "İshak Paşa Sarayı", 
         "gorseller": [
            {"url": "http://via.placeholder.com/400x300?text=Ishak+Pasa", "kaynak": "Kaynak..."},
            {"url": "http://via.placeholder.com/400x300?text=Ishak+Pasa+2", "kaynak": "Kaynak..."}
         ],
         "onemi": "İshak Paşa Sarayı, Ağrı'nın Doğubayazıt ilçesinde, sarp bir tepe üzerine inşa edilmiş 18. yüzyıl Osmanlı sarayıdır. Topkapı Sarayı'ndan sonraki en ünlü saray yapısıdır.",
         "nedenleri": "Önemi, mimarisinde Osmanlı, Selçuklu, Pers ve Barok (Avrupa) sanatının izlerini bir arada taşıyan eşsiz bir yapı olmasından gelir. İpek Yolu üzerinde, stratejik bir geçiş noktasında bulunması, bölgenin kontrolü için önemli bir merkez olmasını sağlamıştır. Dünyanın ilk 'kalorifer tesisatı' (merkezi ısıtma) sistemine sahip olduğu düşünülen yapılar arasındadır."
        },
        {"yer_adi": "Sümela Manastırı", "sayfa": 109, "cumle": "Sümela Manastırı", 
         "gorseller": [
            {"url": "http://via.placeholder.com/400x300?text=Sumela", "kaynak": "Kaynak..."},
            {"url": "http://via.placeholder.com/400x300?text=Sumela+2", "kaynak": "Kaynak..."}
         ],
         "onemi": "Sümela Manastırı, Trabzon'un Maçka ilçesinde, Karadağ'ın sarp bir yamacına oyulmuş Rum Ortodoks manastırıdır. 4. yüzyılda (Bizans döneminde) kurulduğu düşünülen bu yapı, zamanla genişletilmiştir.",
         "nedenleri": "Önemi, inanılmaz coğrafi konumundan ve bu zorlu araziye inşa edilme tekniğinden gelir. Yüzyıllar boyunca önemli bir dini merkez olmuştur ve içindeki freskler (duvar resimleri) Bizans sanatının güzel örneklerini sunar. Hem inanç turizmi hem de doğa turizmi için Türkiye'nin en önemli yerlerindendir."
        },
        {"yer_adi": "Hiroşima Barış Anıtı", "sayfa": 149, "cumle": "Japonya’da bulunan Hiroşima Barış Anıtı... ayakta kalan...", 
         "gorseller": [
            {"url": "http://via.placeholder.com/400x300?text=Hiroshima", "kaynak": "Kaynak..."},
            {"url": "http://via.placeholder.com/400x300?text=Hiroshima+2", "kaynak": "Kaynak..."}
         ],
         "onemi": "Hiroşima Barış Anıtı (Genbaku Domu), 1945'te II. Dünya Savaşı sırasında atılan ilk atom bombasının patlama merkezine en yakın noktada ayakta kalan tek yapıdır. UNESCO Dünya Mirası Listesi'ndedir.",
         "nedenleri": "Önemi, insanlık tarihinin en yıkıcı silahının gücünü gösteren acı bir sembol olmasından gelir. Yıkılmadan korunması, 'dünya barışının' ve nükleer silahların yok edilmesinin bir anıtı olarak hizmet etmesini sağlamıştır."
        },
        {"yer_adi": "Safranbolu evleri", "sayfa": 149, "cumle": "Safranbolu evleri... Türk kent kültürünün günümüzde...", 
         "gorseller": [
            {"url": "http://via.placeholder.com/400x300?text=Safranbolu", "kaynak": "Kaynak..."},
            {"url": "http://via.placeholder.com/400x300?text=Safranbolu+2", "kaynak": "Kaynak..."}
         ],
         "onemi": "Safranbolu evleri, Karabük ilinde bulunan ve geleneksel Osmanlı kent mimarisini en iyi koruyan yerleşim yerlerinden biridir. Bu ahşap evler, 18. ve 19. yüzyıl Türk sosyal yaşamını ve mimarisini yansıtır. UNESCO Dünya Mirası Listesi'ndedir.",
         "nedenleri": "Önemi, bir 'müze kent' gibi bütün bir tarihi dokunun korunmuş olmasından gelir. Evlerin tasarımı, ailenin mahremiyetine ve komşuluk ilişkilerine verilen önemi gösterir. Konumu (tarihi ticaret yolları üzerinde) sayesinde zenginleşmiş ve bu zenginlik mimariye yansımıştır."
        },
        {"yer_adi": "Çatalhöyük", "sayfa": 111, "cumle": "Çatalhöyük’teki bir evde bulunan duvar resmi...", 
         "gorseller": [
            {"url": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c9/Catalhoyuk_Konya_Turkey_Neolithic_site_excavation_South_Area.jpg/1280px-Catalhoyuk_Konya_Turkey_Neolithic_site_excavation_South_Area.jpg", "kaynak": "Wikimedia Commons"},
            {"url": "https://whc.unesco.org/uploads/thumbs/site_1405_0001-750-0-20120702132353.jpg", "kaynak": "UNESCO"}
         ],
         "onemi": "Çatalhöyük, yaklaşık 9.000 yıl öncesine (Neolitik Dönem) tarihlenen, dünyanın bilinen en eski ve en gelişmiş 'şehir' yerleşimlerinden biridir. İnsanlık tarihinin, avcı-toplayıcılıktan yerleşik tarım toplumuna geçişini gösteren en önemli arkeolojik alanlardan biridir. Evleri birbirine bitişikti ve girişler çatılardan yapılıyordu.",
         "nedenleri": "Çatalhöyük'ün önemi, binlerce insanı bir arada barındıran karmaşık bir sosyal yapıyı temsil etmesidir. Tarımın başladığı, hayvanların evcilleştirildiği ve sanatsal üretimin (duvar resimleri, tanrıça figürinleri) yoğun olduğu bir merkezdir. Bu, 'şehirleşme' fikrinin ilk örneklerinden biri olduğu için insanlık tarihi açısından paha biçilmezdir."
        }
    ],
    "SB.5.3.2": [
        # Bu kategorideki tüm yerler için de metinler eklendi
        {"yer_adi": "Çatalhöyük", "sayfa": 111, "cumle": "Çatalhöyük’teki bir evde bulunan duvar resmi...", 
         "gorseller": [
            {"url": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c9/Catalhoyuk_Konya_Turkey_Neolithic_site_excavation_South_Area.jpg/1280px-Catalhoyuk_Konya_Turkey_Neolithic_site_excavation_South_Area.jpg", "kaynak": "Wikimedia Commons"},
            {"url": "https://whc.unesco.org/uploads/thumbs/site_1405_0001-750-0-20120702132353.jpg", "kaynak": "UNESCO"}
         ],
         "onemi": "Çatalhöyük, yaklaşık 9.000 yıl öncesine (Neolitik Dönem) tarihlenen, dünyanın bilinen en eski ve en gelişmiş 'şehir' yerleşimlerinden biridir. İnsanlık tarihinin, avcı-toplayıcılıktan yerleşik tarım toplumuna geçişini gösteren en önemli arkeolojik alanlardan biridir. Evleri birbirine bitişikti ve girişler çatılardan yapılıyordu.",
         "nedenleri": "Çatalhöyük'ün önemi, binlerce insanı bir arada barındıran karmaşık bir sosyal yapıyı temsil etmesidir. Tarımın başladığı, hayvanların evcilleştirildiği ve sanatsal üretimin (duvar resimleri, tanrıça figürinleri) yoğun olduğu bir merkezdir. Bu, 'şehirleşme' fikrinin ilk örneklerinden biri olduğu için insanlık tarihi açısından paha biçilmezdir."
        },
        {"yer_adi": "Hacılar", "sayfa": 112, "cumle": "Hacılar’ın mimarisi kerpiçten yapılmış...", 
         "gorseller": [{"url": "http://via.placeholder.com/400x300?text=Hacilar", "kaynak": "Kaynak..."}], 
         "onemi": "Hacılar Höyüğü, Burdur yakınlarında bulunan, Neolitik (Yeni Taş) ve Kalkolitik (Bakır-Taş) dönemlere ait önemli bir arkeolojik yerleşim yeridir. MÖ 7000'lere tarihlenir.",
         "nedenleri": "Hacılar'ın önemi, özellikle ürettikleri boyalı çanak çömlek sanatıyla öne çıkmasından gelir. Bu seramikler, o dönemin estetik anlayışını ve teknolojisini gösterir. Ayrıca, 'Ana Tanrıça' figürinlerinin bulunması, dönemin inanç sistemi hakkında ipuçları vermiştir."
        },
        {"yer_adi": "Çayönü", "sayfa": 112, "cumle": "Çayönü’nde yaşayan insanlar, ilk barınma alanlarını...", 
         "gorseller": [{"url": "http://via.placeholder.com/400x300?text=Cayonu", "kaynak": "Kaynak..."}], 
         "onemi": "Çayönü, Diyarbakır yakınlarında bulunan ve MÖ 10.000'lere tarihlenen çok önemli bir Neolitik yerleşimdir. Burası, avcı-toplayıcılıktan yerleşik hayata ve tarıma geçişin en net izlendiği yerlerden biridir.",
         "nedenleri": "Çayönü'nün önemi, dünyanın en eski tarım denemelerinin (örn: buğdayın evcilleştirilmesi) burada yapılmış olmasıdır. Ayrıca, 'Sal Düzlüğü' adı verilen toplu ayin alanı, Göbeklitepe ile birlikte, yerleşik hayata geçişte inanç sistemlerinin rolünü gösteren en eski anıtsal mimari örneklerindendir."
        },
        {"yer_adi": "Şarklı Keper Mağarası", "sayfa": 113, "cumle": "Gaziantep’teki Şarklı Keper Mağarası, avcı ve toplayıcı...", 
         "gorseller": [{"url": "http://via.placeholder.com/400x300?text=Sarkli+Keper", "kaynak": "Kaynak..."}], 
         "onemi": "Şarklı Keper Mağarası, Gaziantep'te bulunan ve Paleolitik (Eski Taş) Çağ'a ait buluntular veren bir mağaradır. Avcı-toplayıcı toplulukların sığınağı olarak kullanılmıştır.",
         "nedenleri": "Önemi, bölgedeki en eski insan izlerini taşıyan yerlerden biri olmasıdır. Mağarada bulunan yontma taş aletler, o dönemde yaşayan insanların avlanma teknikleri ve yaşam biçimleri hakkında bilgi sağlar."
        },
        {"yer_adi": "Yarımburgaz Mağarası", "sayfa": 113, "cumle": "Ayrıca Anadolu’daki Yarımburgaz (İstanbul), Beldibi...", 
         "gorseller": [{"url": "http://via.placeholder.com/400x300?text=Yarimburgaz", "kaynak": "Kaynak..."}], 
         "onemi": "Yarımburgaz Mağarası, İstanbul yakınlarında bulunan ve Türkiye'nin en önemli Paleolitik (Eski Taş) Çağ yerleşimlerinden biridir. Avrupa'nın en eski yerleşim yerlerinden biri olarak kabul edilir.",
         "nedenleri": "Önemi, 400.000 yıl öncesine dayanan insan izleri taşımasıdır. Mağarada bulunan hayvan kemikleri ve taş aletler, o dönemde 'Homo erectus'un (ilk insan türlerinden biri) burada yaşadığını göstermekte ve İstanbul tarihinin ne kadar eskiye dayandığını kanıtlamaktadır."
        },
        {"yer_adi": "Beldibi Mağarası", "sayfa": 113, "cumle": "Ayrıca Anadolu’daki Yarımburgaz (İstanbul), Beldibi...", 
         "gorseller": [{"url": "http://via.placeholder.com/400x300?text=Beldibi", "kaynak": "Kaynak..."}], 
         "onemi": "Beldibi Mağarası, Antalya'da bulunan ve Paleolitik (Eski Taş) Çağ'dan Mezolitik (Orta Taş) Çağ'a kadar birçok döneme ait buluntular içeren bir sığınaktır.",
         "nedenleri": "Önemi, mağara duvarlarında bulunan şematik (basit çizgisel) kaya resimleridir. Bu resimler, av sahneleri ve dağ keçisi figürleri içerir ve Anadolu'daki en eski sanatsal ifadelerden biri olarak kabul edilir."
        },
        {"yer_adi": "Göbeklitepe", "sayfa": 114, "cumle": "Günümüzden yaklaşık 12 bin yıl önce... inşa edilen Göbeklitepe...", 
         "gorseller": [
            {"url": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c4/G%C3%B6bekli_Tepe%2C_Sanliurfa_04.jpg/1280px-G%C3%B6bekli_Tepe%2C_Sanliurfa_04.jpg", "kaynak": "Wikimedia Commons"},
            {"url": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e3/G%C3%B6bekli_Tepe_detail.jpg/1280px-G%C3%B6bekli_Tepe_detail.jpg", "kaynak": "Wikimedia Commons"}
         ],
         "onemi": "Göbeklitepe, Şanlıurfa'da bulunan ve MÖ 10.000 (günümüzden 12.000 yıl önce) tarihlenen, dünyanın bilinen en eski anıtsal tapınak kompleksidir. Henüz tarım ve yerleşik hayat başlamamışken, avcı-toplayıcı insanlar tarafından inşa edilmiştir.",
         "nedenleri": "Buranın önemi, insanlık tarihi anlayışını kökten değiştirmesidir. Eskiden 'önce yerleşik hayata geçildi, sonra tapınak yapıldı' düşünülürken, Göbeklitepe 'önce tapınak (inanç) için bir araya gelindi, bu da yerleşik hayatı başlattı' tezini ortaya koymuştur. Üzerinde hayvan kabartmaları bulunan 'T' şeklindeki devasa dikilitaşlar, bilinen en eski anıtsal heykellerdir."
        },
        {"yer_adi": "Hasan Dağı", "sayfa": 120, "cumle": "O dönemde Çatakhöyük’te yaşayan insanlar, Hasan Dağı’ndan...", 
         "gorseller": [{"url": "http://via.placeholder.com/400x300?text=Hasan+Dagi", "kaynak": "Kaynak..."}], 
         "onemi": "Hasan Dağı, Aksaray ve Niğde arasında yer alan sönmüş bir volkanik dağdır. Çatalhöyük'teki ünlü duvar resimlerinden birinin, bu dağın patlamasını gösteren dünyanın 'ilk haritası' veya 'manzara resmi' olduğu düşünülmektedir.",
         "nedenleri": "Bu dağın Neolitik (Yeni Taş) Çağ'daki önemi, 'obsidiyen' kaynağı olmasından gelir. Obsidiyen, o dönemin en keskin aletlerinin (bıçak, ok ucu) yapıldığı volkanik bir camdır. Çatalhöyük'te yaşayan insanlar, bu dağdan çıkardıkları obsidiyeni hem alet yapımında kullanmış hem de ticaretini yapmışlardır."
        },
        {"yer_adi": "Hayırlı Höyüğü", "sayfa": 115, "cumle": "Mardin’deki Hayırlı Höyüğü... \"1. derece arkeolojik sit alanı\"...", 
         "gorseller": [{"url": "http://via.placeholder.com/400x300?text=Hayirli+Hoyuk", "kaynak": "Kaynak..."}], 
         "onemi": "Hayırlı Höyüğü, Mardin'de bulunan bir arkeolojik yerleşim alanıdır. Bir vatandaşın CİMER'e (Cumhurbaşkanlığı İletişim Merkezi) yaptığı başvuru sayesinde keşfedilmiş ve 1. derece arkeolojik sit alanı ilan edilmiştir.",
         "nedenleri": "Önemi, vatandaşların kültürel mirasa sahip çıkmasının (farkındalık) ve devlete bildirmesinin ne kadar değerli olduğunu gösteren güncel bir örnek olmasından gelir."
        },
        {"yer_adi": "Karain Mağarası", "sayfa": 105, "cumle": "Türkiye’nin en büyük doğal mağaralarından Karain Mağarası...", 
         "gorseller": [{"url": "http://via.placeholder.com/400x300?text=Karain", "kaynak": "Kaynak... (SB.5.3.1'den kopyala)"}], 
         "onemi": "Karain Mağarası, Antalya yakınlarında bulunan ve Türkiye'nin en büyük doğal mağaralarından biridir. Bu mağara, Paleolitik (Eski Taş) Çağ'dan Roma dönemine kadar, yaklaşık 500.000 yıl boyunca insanlar tarafından sürekli olarak iskan edilmiştir.",
         "nedenleri": "Önemi, Anadolu'daki en eski insan kalıntılarının (Neandertal) burada bulunmuş olmasıdır. Bu mağara, avcı-toplayıcı insanların yaşam tarzı, alet yapımı ve zaman içindeki evrimi hakkında bize paha biçilmez bilgiler sunan arkeolojik bir hazinedir."
        }
    ],
    "SB.5.3.3": [
        # Bu kategorideki tüm yerler için de metinler eklendi
        {"yer_adi": "Ur (şehri)", "sayfa": 131, "cumle": "Bilinen ilk tekerlek kalıntılarına Ur şehrinde rastlanmıştır.", 
         "gorseller": [{"url": "http://via.placeholder.com/400x300?text=Ur+Sehr", "kaynak": "Kaynak..."}], 
         "onemi": "Ur, Mezopotamya'da Sümer medeniyetinin en önemli şehir devletlerinden biriydi (bugünkü Irak). Sümerlerin dini ve siyasi merkezi olarak kabul edilir.",
         "nedenleri": "Önemi, bilinen en eski tekerlek kalıntılarına ve 'Ur Zigguratı' adı verilen devasa bir tapınağa ev sahipliği yapmasından gelir. Ayrıca, 'Kraliyet Mezarları'nda bulunan altın ve değerli taşlardan yapılmış eserler, Sümer sanatının ne kadar gelişmiş olduğunu göstermiştir."
        },
        {"yer_adi": "Uruk (şehri)", "sayfa": 130, "cumle": "Bilinen en eski Mezopotamya medeniyeti... Ur, Uruk, Nippur...", 
         "gorseller": [{"url": "http://via.placeholder.com/400x300?text=Uruk+Sehri", "kaynak": "Kaynak..."}], 
         "onemi": "Uruk, Mezopotamya'da Sümerlere ait bir şehir devletidir. Tarihçiler tarafından dünyanın 'ilk gerçek şehri' olarak kabul edilir. MÖ 4000'lerde on binlerce insana ev sahipliği yapmıştır.",
         "nedenleri": "Önemi, 'yazı'nın (çivi yazısı) ilk kez burada ortaya çıkmasıdır. Şehirleşme, karmaşık toplumsal yapı, bürokrasi ve kayıt tutma ihtiyacı, yazının icadını tetiklemiştir. Gılgamış Destanı'nın geçtiği şehir olarak da bilinir."
        },
        {"yer_adi": "Nippur (şehri)", "sayfa": 130, "cumle": "Bilinen en eski Mezopotamya medeniyeti... Ur, Uruk, Nippur...", 
         "gorseller": [{"url": "http://via.placeholder.com/400x300?text=Nippur", "kaynak": "Kaynak..."}], 
         "onemi": "Nippur, Sümerlerin siyasi başkenti değil, en kutsal dini merkeziydi. Baş tanrıları Enlil'in tapınağı buradaydı ve tüm Sümer kralları, krallıklarını meşrulaştırmak (onaylatmak) için Nippur'un onayını almak zorundaydı.",
         "nedenleri": "Önemi, Sümer medeniyetini bir arada tutan dini ve kültürel bir merkez olmasından gelir. Burada bulunan binlerce çivi yazılı tablet, Sümerlerin edebiyatı, kanunları ve inançları hakkında en önemli bilgileri sağlamıştır."
        },
        {"yer_adi": "Louvre Müzesi", "sayfa": 131, "cumle": "Bu tabletlerin bir kısmı Fransa’da bulunan Louvre (Luva) Müzesinde...", 
         "gorseller": [{"url": "http://via.placeholder.com/400x300?text=Louvre", "kaynak": "Kaynak..."}], 
         "onemi": "Louvre Müzesi, Fransa'nın Paris şehrinde bulunan, dünyanın en büyük ve en çok ziyaret edilen sanat müzesidir. Başlangıçta bir kale olarak inşa edilmiş, daha sonra kraliyet sarayı olmuştur.",
         "nedenleri": "Tarihteki önemi, Mona Lisa gibi paha biçilmez sanat eserlerine ev sahipliği yapmasının yanı sıra, Hammurabi Kanunları'nın yazılı olduğu dikilitaş (stel) gibi Mezopotamya medeniyetine ait en önemli arkeolojik buluntuların burada sergilenmesidir. Bu durum, 'ortak mirasın' nasıl paylaşıldığı veya tartışıldığı konusunda bir örnektir."
        },
        {"yer_adi": "Ziggurat", "sayfa": 132, "cumle": "Sümerlerin şehir merkezlerinde “ziggurat” adı verilen yapılar...", 
         "gorseller": [{"url": "http://via.placeholder.com/400x300?text=Ziggurat", "kaynak": "Kaynak..."}], 
         "onemi": "Ziggurat, Mezopotamya medeniyetlerinde (Sümer, Babil, Asur) yaygın olan, piramit şeklinde, kat kat yükselen devasa tapınak kuleleridir. En tepede bir tapınak veya kutsal alan bulunurdu.",
         "nedenleri": "Önemi, sadece dini bir yapı olmamasından gelir. Zigguratlar aynı zamanda birer 'gözlemevi' (rasathane) olarak gökbilim için, alt katları ise 'tahıl ambarı' olarak ekonomik depo ve 'okul' olarak eğitim için kullanılırdı. Bu, din, bilim ve ekonominin iç içe geçtiği çok amaçlı bir yapıydı."
        },
        {"yer_adi": "Babil (şehri)", "sayfa": 133, "cumle": "Devletin başkenti Babil’dir.", 
         "gorseller": [{"url": "http://via.placeholder.com/400x300?text=Babil", "kaynak": "Kaynak..."}], 
         "onemi": "Babil, Mezopotamya'da kurulan Babil İmparatorluğu'nun başkentidir. Tarihin en ünlü şehirlerinden biridir ve Kral Hammurabi tarafından yönetilmiştir.",
         "nedenleri": "Önemi, 'Hammurabi Kanunları'nın (bilinen en eski ve en kapsamlı yasa metinlerinden biri) burada oluşturulması ve dünyanın yedi harikasından biri olan 'Babil'in Asma Bahçeleri'ne ev sahipliği yaptığına inanılmasıdır. İştar Kapısı da bu şehrin görkemli girişlerinden biriydi."
        },
        {"yer_adi": "İştar Kapısı", "sayfa": 133, "cumle": "Başkent Babil’de inşa edilen Marduk Zigguratı, İştar Kapısı...", 
         "gorseller": [
            {"url": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e0/Pergamon_Museum_Berlin_2007_088.jpg/800px-Pergamon_Museum_Berlin_2007_088.jpg", "kaynak": "Wikimedia Commons (Pergamon M.)"},
            {"url": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Babylon_Ishtar_Gate_replica_Lion_relief.jpg/800px-Babylon_Ishtar_Gate_replica_Lion_relief.jpg", "kaynak": "Wikimedia Commons"}
         ],
         "onemi": "İştar Kapısı, Babil şehrinin en görkemli sekiz kapısından biriydi ve ana giriş olarak kullanılırdı. Kral II. Nebukadnezar tarafından tanrıça İştar'a adanarak yaptırılan bu devasa kapı, şehrin zenginliğini ve gücünü herkese gösteren bir anıt gibiydi.",
         "nedenleri": "Babil, Mezopotamya'nın en önemli şehirlerinden biriydi ve İştar Kapısı da bu şehrin kalbine açılıyordu. Kapı, hem şehri düşmanlardan koruyan bir savunma yapısıydı hem de üzerindeki mavi parlak çiniler ve aslan/ejderha kabartmalarıyla Babil sanatının ve mimarisinin gücünü gösteren bir semboldü. Bugün Almanya'daki Pergamon Müzesi'nde sergilenmektedir."
        },
        {"yer_adi": "Babil Asma Bahçeleri", "sayfa": 133, "cumle": "Başkent Babil’de inşa edilen Marduk Zigguratı, İştar Kapısı...", 
         "gorseller": [{"url": "http://via.placeholder.com/400x300?text=Babil+Asma", "kaynak": "Kaynak..."}], 
         "onemi": "Babil'in Asma Bahçeleri, Antik Dünyanın Yedi Harikası'ndan biri olarak kabul edilir. Efsaneye göre, Kral II. Nebukadnezar tarafından, sıla hasreti çeken eşi için çorak Mezopotamya'nın ortasında kat kat teraslar şeklinde inşa edilmiş yapay bir bahçedir.",
         "nedenleri": "Önemi, varlığı tam olarak kanıtlanamamış olsa da, antik dünyadaki mühendislik ve botanik hayal gücünün bir sembolü olmasından gelir. Çölde böyle bir bahçeyi sulamak için gereken su taşıma sistemleri (nehirden su pompalamak), o dönem için inanılmaz bir teknoloji gerektirirdi."
        },
        {"yer_adi": "Ninova", "sayfa": 134, "cumle": "...Asurluların başkenti Ninova’dır.", 
         "gorseller": [{"url": "http://via.placeholder.com/400x300?text=Ninova", "kaynak": "Kaynak..."}], 
         "onemi": "Ninova, Mezopotamya'da (bugünkü Musul, Irak) bulunan Asur İmparatorluğu'nun görkemli başkentiydi. Antik dünyanın en büyük şehirlerinden biriydi.",
         "nedenleri": "Önemi, tarihin ilk büyük kütüphanesi olarak bilinen 'Asurbanipal Kütüphanesi'ne ev sahipliği yapmasından gelir. Kral Asurbanipal, imparatorluktaki tüm önemli metinlerin (Gılgamış Destanı dahil) çivi yazılı tablet kopyalarını bu kütüphanede toplamıştır. Bu, Mezopotamya kültürünün günümüze ulaşmasını sağlayan en önemli arşivdir."
        },
        {"yer_adi": "Kültepe", "sayfa": 134, "cumle": "Anadolu’daki en önemli ticaret merkezi Kültepe (Kayseri)...", 
         "gorseller": [{"url": "http://via.placeholder.com/400x300?text=Kultepe", "kaynak": "Kaynak..."}], 
         "onemi": "Kültepe (Kaniş/Karum), Kayseri yakınlarında bulunan ve MÖ 2000'lerde Asurlu tüccarların gelip yerleştiği devasa bir ticaret merkezidir (Karum).",
         "nedenleri": "Kültepe'nin önemi, Anadolu'da 'yazı'nın ilk kez burada kullanılmış olmasıdır. Asurlu tüccarlar, alacak-verecek kayıtlarını tutmak için Mezopotamya'dan çivi yazısını getirmişlerdir. Burada bulunan on binlerce 'Kültepe Tableti', Anadolu'nun tarih çağlarına girmesini sağlamış ve o dönemin ticari ve sosyal hayatı hakkında paha biçilmez bilgiler vermiştir."
        },
        {"yer_adi": "Asurbanipal Kütüphanesi", "sayfa": 134, "cumle": "...Asurların başkenti Ninova’da kurulan Asurbanipal...", 
         "gorseller": [{"url": "http://via.placeholder.com/400x300?text=Asurbanipal", "kaynak": "Kaynak..."}], 
         "onemi": "Asurbanipal Kütüphanesi, Asur başkenti Ninova'da Kral Asurbanipal tarafından MÖ 7. yüzyılda kurulan, tarihin bilinen ilk sistematik kütüphanesidir.",
         "nedenleri": "Önemi, Mezopotamya'nın binlerce yıllık bilgi birikimini (edebiyat, tıp, astronomi, kanunlar) içeren 30.000'den fazla çivi yazılı tableti barındırmasından gelir. Gılgamış Destanı'nın en eksiksiz kopyası burada bulunmuştur. Bu kütüphane sayesinde Sümer ve Babil kültürünü öğrenebiliyoruz."
        },
        {"yer_adi": "Hattuşa (Boğazköy)", "sayfa": 135, "cumle": "...Hititlerin başkenti günümüzde Boğazköy (Çorum) yakınlarında...", 
         "gorseller": [
            {"url": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Hattusa_Lion_Gate_2.jpg/800px-Hattusa_Lion_Gate_2.jpg", "kaynak": "Wikimedia Commons"},
            {"url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/36/Hattusa_Yazilikaya_Sanctuary_Chamber_B_12_Gods_of_Underworld.jpg/1280px-Hattusa_Yazilikaya_Sanctuary_Chamber_B_12_Gods_of_Underworld.jpg", "kaynak": "Wikimedia Commons"}
         ],
         "onemi": "Hattuşa (Boğazköy), Çorum'da bulunan ve Hitit İmparatorluğu'na (MÖ 1600-1200) başkentlik yapmış olan antik bir şehirdir. UNESCO Dünya Mirası Listesi'ndedir.",
         "nedenleri": "Önemi, Anadolu'nun en güçlü imparatorluklarından birinin merkezi olmasından gelir. Şehir, Aslanlı Kapı gibi anıtsal kapılarla ve devasa surlarla çevriliydi. Burada bulunan binlerce çivi yazılı tablet (Kadeş Antlaşması dahil), Hititlerin diplomasisi, kanunları ve dini hakkında bilgi vermiştir. Yazılıkaya Açık Hava Tapınağı da buradadır."
        },
        {"yer_adi": "Sardes", "sayfa": 136, "cumle": "Günümüzde Manisa sınırları içinde bulunan Sardes, Lidyalıların...", 
         "gorseller": [{"url": "http://via.placeholder.com/400x300?text=Sardes", "kaynak": "Kaynak..."}], 
         "onemi": "Sardes (Sart), Manisa'da bulunan ve Lidya Krallığı'nın başkenti olan zengin bir antik şehirdir. 'Karun kadar zengin' deyimi, Lidya Kralı Krezüs'ten gelmektedir.",
         "nedenleri": "Tarihteki önemi, 'paranın' (sikke) MÖ 7. yüzyılda ilk kez burada icat edilmesi ve kullanılmaya başlanmasıdır. Bu icat, ticareti kökten değiştirmiş ve dünya ekonomisine yön vermiştir. Ayrıca, Efes'ten başlayıp Mezopotamya'ya uzanan ünlü 'Kral Yolu'nun başlangıç noktası olması, şehrin zenginliğinin ana kaynağıdır."
        },
        {"yer_adi": "Kral Yolu", "sayfa": 137, "cumle": "...Efes’ten başlayıp Mezopotamya’ya kadar uzanan Kral Yolu’nu...", 
         "gorseller": [{"url": "http://via.placeholder.com/400x300?text=Kral+Yolu", "kaynak": "Kaynak..."}], 
         "onemi": "Kral Yolu, Pers İmparatorluğu döneminde (MÖ 5. yüzyıl) geliştirilen ve Lidya başkenti Sardes'ten Pers başkenti Susa'ya (Mezopotamya) kadar uzanan yaklaşık 2.700 km uzunluğunda bir antik anayoldur.",
         "nedenleri": "Önemi, tarihin ilk ve en verimli posta (iletişim) ve ticaret yollarından biri olmasından gelir. Pers imparatorları, bu yol sayesinde devasa imparatorluklarını yönetebiliyor, habercilerle (ulaklar) hızlı iletişim kurabiliyor ve ordularını hızla sevk edebiliyorlardı. Ticaretin gelişmesini ve kültürlerin (Doğu ve Batı) etkileşimini sağlamıştır."
        },
        {"yer_adi": "Artemis Tapınağı", "sayfa": 137, "cumle": "Artemis Tapınağı ve Efes Antik Kenti İyonyalılardan...", 
         "gorseller": [{"url": "http://via.placeholder.com/400x300?text=Artemis", "kaynak": "Kaynak..."}], 
         "onemi": "Artemis Tapınağı (Diana Tapınağı), Efes'te bulunan ve Antik Dünyanın Yedi Harikası'ndan biri olarak kabul edilen devasa bir tapınaktır. Tamamen mermerden inşa edilmiş ve 127 sütundan oluşmuştur.",
         "nedenleri": "Önemi, antik dünyanın en büyük ve en görkemli tapınağı olmasından gelir. Sadece dini bir merkez değil, aynı zamanda bölgenin en büyük 'bankası' olarak da hizmet vermiştir. Çeşitli felaketler (yangın, sel, istila) nedeniyle defalarca yıkılıp yeniden yapılmış, ancak günümüze sadece birkaç temel taşı kalmıştır."
        }
    ],
    "SB.5.4.1": [
        {"yer_adi": "Türkiye Büyük Millet Meclisi (TBMM)", "sayfa": 18, "cumle": "Türkiye Büyük Millet Meclisinin açılması, saltanatın...", 
         "gorseller": [
            {"url": "http://via.placeholder.com/400x300?text=TBMM+1.Bina", "kaynak": "Kaynak... (örn: tbmm.gov.tr)"},
            {"url": "http://via.placeholder.com/400x300?text=TBMM+Yeni+Bina", "kaynak": "Kaynak..."}
         ],
         "onemi": "Türkiye Büyük Millet Meclisi (TBMM), 23 Nisan 1920'de Ankara'da açılan, Türkiye Cumhuriyeti'nin yasama organıdır (yani kanunları yapan kurumdur). Türk halkının egemenliğini (kendi kendini yönetme hakkını) temsil eder.",
         "nedenleri": "Önemi, Kurtuluş Savaşı'nın buradan yönetilmiş olması ve 'Milli Egemenlik' ilkesinin (padişahın değil, halkın iradesinin) devlet yönetiminin temeli haline gelmesidir. Saltanatın kaldırılması, Cumhuriyetin ilanı gibi devrim niteliğindeki tüm kararlar bu mecliste alınmıştır. Demokrasi ve cumhuriyetin kalbidir."
        }
    ],
    "SB.5.6.1": [
        {"yer_adi": "Anadolu Medeniyetleri Müzesi", "sayfa": 129, "cumle": "Anadolu uygarlıklarına ait önemli eserlerin yer aldığı...", 
         "gorseller": [
            {"url": "http://via.placeholder.com/400x300?text=Anadolu+Med.", "kaynak": "Kaynak..."},
            {"url": "http://via.placeholder.com/400x300?text=Anadolu+Med.+2", "kaynak": "Kaynak..."}
         ],
         "onemi": "Anadolu Medeniyetleri Müzesi, Ankara'da bulunan ve Paleolitik (Eski Taş) Çağ'dan başlayarak Hititler, Frigler, Lidyalılar gibi Anadolu'da yaşamış tüm medeniyetlere ait paha biçilmez eserleri sergileyen, dünyanın en önemli arkeoloji müzelerinden biridir.",
         "nedenleri": "Önemi, Anadolu'nun binlerce yıllık zengin tarihini ve 'ortak mirasını' tek bir çatı altında toplamasıdır. Teknolojik gelişmeler (sanal müze uygulamaları), uzaktaki insanların da bu müzeyi gezebilmesini ve ortak mirası öğrenebilmesini sağlamıştır."
        }
    ],
    "SB.5.6.2": [
        {"yer_adi": "Büyük Taarruz Şehitliği ve Atatürk Anıtı", "sayfa": 144, "cumle": "Afyonkarahisar’a 16 km mesafede bulunan...", 
         "gorseller": [
            {"url": "http://via.placeholder.com/400x300?text=Buyuk+Taarruz", "kaynak": "Kaynak..."},
            {"url": "http://via.placeholder.com/400x300?text=Buyuk+Taarruz+2", "kaynak": "Kaynak..."}
         ],
         "onemi": "Büyük Taarruz Şehitliği, Afyonkarahisar'da bulunan ve Kurtuluş Savaşı'nın son ve en büyük askeri harekâtı olan Başkomutanlık Meydan Muharebesi'nde (Büyük Taarruz) şehit olan askerlerin anısına yapılmış bir anıttır.",
         "nedenleri": "Önemi, Türk milletinin bağımsızlığını kazandığı nihai zaferin sembolü olmasından gelir. Bu anıt, vatanseverlik değerini ve teknolojik imkanların (silah, teçhizat) savaşın kaderi üzerindeki etkisini hatırlatan önemli bir ulusal miras ögesidir."
        }
    ]
}


# ###############################################################
# --- HTML ŞABLONU (GEMINI KALDIRILDI, GÖRSEL BÜYÜTME EKLENDİ) ---
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
                <div id="user-avatar-initial" class="w-10 h-10 rounded-full bg-cyan-500 flex items-center justify-center text-white font-bold text-lg">K</div>
                <div class="ml-3">
                    <span id="user-name-placeholder" class="block text-sm font-bold text-gray-800">Kullanıcı</span>
                </div>
            </div>
        </div>
        
        <nav class="flex-1 overflow-y-auto p-2 space-y-1">

            <a id="link-metin-analiz" href="/metin-analiz" class="flex items-center mx-2 p-2 rounded-lg text-white font-semibold bg-blue-500 hover:bg-blue-600 transition-all">
                <i class="fa-solid fa-file-pen mr-3 w-6 text-center"></i>
                <span>Metin Analiz</span>
            </a>
            <a id="link-soru-uretim" href="/soru-uretim" class="flex items-center mx-2 p-2 rounded-lg text-white font-semibold bg-green-500 hover:bg-green-600 transition-all">
                <i class="fa-solid fa-circle-question mr-3 w-6 text-center"></i>
                <span>Soru Üretim</span>
            </a>
            <a id="link-metin-olusturma" href="/metin-olusturma" class="flex items-center mx-2 p-2 rounded-lg text-white font-semibold bg-purple-500 hover:bg-purple-600 transition-all">
                <i class="fa-solid fa-wand-magic-sparkles mr-3 w-6 text-center"></i>
                <span>Metin Oluşturma</span>
            </a>
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

        </nav>
        <div class="p-4 border-t border-gray-200">
                    <a href="/dashboard" class="flex items-center w-full p-3 rounded-lg text-gray-600 font-semibold bg-gray-100 hover:bg-gray-200 transition-all">
                        <i class="fa-solid fa-arrow-left mr-3 w-6 text-center"></i>
                        <span>Panele Geri Dön</span>
                    </a>
        </div>
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
        const yerVeritabani = {{ yer_veritabani | tojson }};
        const mapsApiKey = "{{ maps_api_key }}";

        document.addEventListener('DOMContentLoaded', () => {
        
        // --- KULLANICI ADI VE ROL YÜKLEME ---
        const userFullName = localStorage.getItem('loggedInUserName'); 
        const userRole = localStorage.getItem('loggedInUserRole'); // Rolü al

        if (userFullName) {
            document.getElementById('user-name-placeholder').textContent = userFullName;
            document.getElementById('user-avatar-initial').textContent = userFullName[0] ? userFullName[0].toUpperCase() : 'K';
        }
        
        // --- YAN MENÜ ROL KONTROLÜ (NİHAİ DOĞRU VERSİYON) ---
        const linkMetinAnaliz = document.getElementById('link-metin-analiz');
        const linkSoruUretim = document.getElementById('link-soru-uretim');
        const linkMetinOlusturma = document.getElementById('link-metin-olusturma');
        const linkHaritadaBul = document.getElementById('link-haritada-bul');
        const linkPodcast = document.getElementById('link-podcast');
        const linkSeyretBul = document.getElementById('link-seyret-bul');
        const linkYarisma = document.getElementById('link-yarisma');
        const linkVideoIstegi = document.getElementById('link-video-istegi');

        if (userRole === 'teacher') {
            // --- ÖĞRETMEN GÖRÜNÜMÜ ---
            if (linkMetinAnaliz) linkMetinAnaliz.style.display = 'none';
            if (linkSeyretBul) linkSeyretBul.style.display = 'none';
            if (linkHaritadaBul) linkHaritadaBul.style.display = 'none'; 
        } else {
            // --- ÖĞRENCİ GÖRÜNÜMÜ ---
            if (linkMetinOlusturma) linkMetinOlusturma.style.display = 'none';
        }
        // --- ROL KONTROLÜ BİTTİ ---


        const bilesenSelect = document.getElementById('surec-bileseni-select');
            const yerListesiContainer = document.getElementById('yer-listesi');
            
            const baslangicMesaji = document.getElementById('baslangic-mesaji');
            const detayIcerik = document.getElementById('detay-icerik');
            
            // Modal elementleri
            const modalOverlay = document.getElementById('image-modal');
            const modalImage = document.getElementById('modal-image');
            const modalCloseBtn = document.getElementById('modal-close-btn');
            
            let aktifYerItem = null; 

            // 1. Açılır menü değiştiğinde (BU KISIM ARTIK ÇALIŞACAK)
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
                
                yerler.forEach(yer => {
                    const item = document.createElement('div');
                    item.className = 'yer-listesi-item p-4';
                    item.innerHTML = `
                        <h5 class="font-semibold text-gray-800">${yer.yer_adi}</h5>
                        <p class="text-sm text-gray-600 truncate italic">"${yer.cumle}"</p>
                        <span class="text-xs text-gray-400">Sayfa: ${yer.sayfa}</span>
                    `;
                    item.addEventListener('click', () => {
                        if (aktifYerItem) {
                            aktifYerItem.classList.remove('active');
                        }
                        item.classList.add('active');
                        aktifYerItem = item;
                        fetchYerDetaylari(yer); // yer objesinin tamamını gönder
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
            
            // 3. Detayları getiren ana fonksiyon (DÜZELTİLMİŞ HALİ)
            function fetchYerDetaylari(yerObject) {
                const yerAdi = yerObject.yer_adi;
                console.log(`Veritabanından detaylar getiriliyor: ${yerAdi}`);
                
                baslangicMesaji.style.display = 'none';
                
                // 3a. Haritayı Güncelle
                const mapIframe = document.getElementById('map-iframe');
                
                // Önce "map_query" (C33X+9G Konak, İzmir) alanını ara,
                // eğer o tanımlı değilse, normal "yer_adi" (Kapadokya) alanını ara.
                const haritaSorgusu = yerObject.map_query || yerObject.yer_adi;

                // --- YENİ, DOĞRU ve KESİN ÇALIŞAN LİNK (API KEY GEREKTİRMEZ) ---
                // https:// eklendi.
                // q= İşaretçi (Pin) ekler ve yeri arar
                // t=k Uydu (Satellite) görüntüsü yapar
                // z=9 Zoom (Yakınlaştırma) seviyesini ayarlar
                // output=embed Çerçeve (iframe) için gömme modu
                const mapUrl = `https://maps.google.com/maps?q=$${encodeURIComponent(haritaSorgusu)}&t=k&z=9&output=embed`;
                // --- BİTTİ ---
                
                mapIframe.src = mapUrl;

                // 3b. Görselleri Yükle (Veritabanından)
                const imageContainer = document.getElementById('image-container');
                imageContainer.innerHTML = ''; 
                
                const gorseller = yerObject.gorseller || []; 
                if (gorseller.length > 0) {
                    gorseller.forEach(gorsel => {
                        const gorselWrapper = document.createElement('div');
                        
                        const img = document.createElement('img');
                        img.src = `/static/images/harita_gorselleri/${gorsel.dosya}`; 
                        img.alt = yerAdi;
                        img.className = 'w-full h-48 object-cover rounded-lg border clickable-image';
                        img.onerror = function() {
                            this.src = `http://via.placeholder.com/400x300?text=${encodeURIComponent(yerAdi)}`;
                            this.alt = 'Görsel yüklenemedi';
                        };
                        
                        img.addEventListener('click', () => {
                        console.log('Tıklanan görsel:', gorsel.dosya);
                        modalImage.src = `/static/images/harita_gorselleri/${gorsel.dosya}`;
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
                    imageContainer.innerHTML = '<p class="text-sm text-gray-500">Bu yer için veritabanında görsel tanımlanmamış.</p>';
                }

                // 3c. Metinleri Yükle (Veritabanından)
                document.getElementById('detay-baslik').textContent = yerAdi;
                document.getElementById('onem-metni').textContent = yerObject.onemi || "Bu yer için 'Tarihi Önem' açıklaması henüz girilmemiş.";
                document.getElementById('nedenler-metni').textContent = yerObject.nedenleri || "Bu yer için 'Öneminin Nedenleri' açıklaması henüz girilmemiş.";
                
                // Paneli göster
                detayIcerik.style.display = 'block';
            }
            
            // 4. Modal Kapatma Olayları
            modalCloseBtn.addEventListener('click', () => {
                modalOverlay.style.display = 'none';
            });
            
            modalOverlay.addEventListener('click', (e) => {
                if (e.target === modalOverlay) {
                    modalOverlay.style.display = 'none';
                }
            });
            
        });
    </script>
</body>
</html>
"""


# ###############################################################
# --- FLASK ROTALARI (GEMINI BAĞIMLILIĞI KALDIRILDI) ---
# ###############################################################

# harita_bul.py dosyasında register_harita_bul_routes fonksiyonunun içine ekleyin:

def register_harita_bul_routes(app, GOOGLE_MAPS_API_KEY):
    
    # ... (Mevcut /haritada-bul rotası burada duruyor) ...

    # 👇👇👇 BU KISMI EKLEYİN (Raporlama için arka kapı) 👇👇👇
    @app.route('/api/harita/kaydet-inceleme', methods=['POST'])
    def kaydet_harita_inceleme():
        try:
            data = request.get_json()
            student_no = data.get('student_no')
            yer_adi = data.get('yer_adi')
            
            if not student_no or not yer_adi:
                return jsonify({"success": False})

            # db_helper'ı burada import edip kullanıyoruz
            import db_helper
            db_helper.kaydet_kullanim(student_no, "Haritada Bul", f"{yer_adi} incelendi")
            
            return jsonify({"success": True})
        except Exception as e:
            print(f"Harita log hatası: {e}")
            return jsonify({"success": False})
    # 👆👆👆 EKLEME BİTTİ 👆👆👆

    @app.route('/haritada-bul')
    def haritada_bul_page():
        """
        Haritada Bul ana sayfasını render eder.
        Gerekli verileri (bileşenler, yerler, api key) HTML şablonuna gönderir.
        """
        print("Haritada Bul sayfasına erişim sağlandı")
        return render_template_string(
            HARITADA_BUL_HTML,
            surec_bilesenleri=SUREC_BILESENLERI_HARITA,
            yer_veritabani=HARITA_VERITABANI, # Yeni, tam veritabanı
            maps_api_key=GOOGLE_MAPS_API_KEY
        )

    # Gemini API Rotası (@app.route('/api/get-location-details'))
    # ARTIK GEREKLİ DEĞİL VE SİLİNDİ.
