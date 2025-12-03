# -*- coding: utf-8 -*-
"""
Maarif Modeli Metin Oluşturma Aracı
5. Sınıf Sosyal Bilgiler için Gemini API ile metin üretimi
"""

import google.generativeai as genai
import re

def api_yapilandir(api_key):
    """Gemini API'yi yapılandırır"""
    # Şifreyi dışarıdan gelen yerine direkt Render'dan (Environment) alıyoruz:
    guvenli_anahtar = os.getenv('GOOGLE_API_KEY')
    
    if guvenli_anahtar:
        genai.configure(api_key=guvenli_anahtar)
        
        # ESKİSİ: return genai.GenerativeModel('models/gemini-pro')
        # YENİSİ (Hızlı ve Yüksek Kota):
        print("✅ Metin Üretim Modeli yapılandırıldı: models/gemini-2.0-flash")
        return genai.GenerativeModel('models/gemini-2.0-flash')
        
    print("❌ API Anahtarı bulunamadı!")
    return None

# --- YENİ VERİ YAPISI ---
# Süreç Bileşenleri, Metin Tipleri ve Prompt Şablonları
# Kullanıcının 7. maddede sağladığı tüm prompt şablonlarını içerir.

PROMPT_SABLONLARI = {
    "SB.5.1.1.": {
        "aciklama": "Dâhil olduğu gruplar ve bu gruplardaki rolleri arasındaki ilişkileri çözümleyebilme",
        "metin_tipleri": {
            "Örnek Olay (Senaryo)": "5. Sınıf Sosyal Bilgiler, 'Gruplar ve Rollerimiz' konusu için 120-140 kelimelik bir 'Örnek Olay' metni yaz. Metinde, 'Elif' adında bir 5. sınıf öğrencisinin bir gün içindeki farklı 'grupları' (örn: aile, okul, satranç kulübü) ve bu gruplardaki 'rolleri' (örn: evlat, öğrenci, takım kaptanı) anlatılsın. Metin, Elif'in bu rollerinin ona farklı 'sorumluluklar' (örn: odasını toplamak, dersi dinlemek, arkadaşlarına örnek olmak) yüklediğini 5. sınıf seviyesine uygun bir dille açıklasın.",
            "Tanımlayıcı Metin (Kavramsal)": "5. Sınıf Sosyal Bilgiler, 'Gruplar ve Rollerimiz' konusu için 120-140 kelimelik 'Tanımlayıcı Bilgi Metni' yaz. Metin, 'hak' ve 'sorumluluk' kavramlarının birbiriyle olan ilişkisini 'aile grubu' üzerinden açıklamalıdır. 'Çocuk rolü' özelinde 'haklara' (örn: barınma, sevgi görme) ve 'sorumluluklara' (örn: odasını düzenli tutma, büyüklere saygılı davranma) 5. sınıf seviyesine uygun örnekler vererek bu iki kavramın bir bütün olduğunu vurgulasın."
        }
    },
    "SB.5.1.2.": {
        "aciklama": "Kültürel özelliklere saygı duymanın birlikte yaşamaya etkisini yorumlayabilme",
        "metin_tipleri": {
            "Tanıtıcı Metin (\"Merhaba, ben...\")": "5. Sınıf Sosyal Bilgiler, 'Kültürel Zenginlikler' konusu için 120-140 kelimelik 'Tanıtıcı Metin' yaz. Metin, 'Merhaba, ben...' formatında olmalı. Konuşmacı, Türkiye'ye eğitim için 'Fas'tan' gelen 'Yusuf' adında bir öğrenci olsun. Yusuf, ülkesinin 'kültürel ögelerinden' (örn: 'kuskus' yemeği, 'kaftan' kıyafeti, 'selamlaşma' geleneği) bahsetsin. Metin, Türk kültüründe gördüğü 'misafirperverliğin' kendi kültürüyle benzerliğinden bahsederek 'farklılıklara saygının' önemini vurgulasın.",
            "Haber Metni (Kültürel Etkileşim)": "5. Sınıf Sosyal Bilgiler, 'Kültürel Zenginlikler' konusu için 'Haber Metni' formatında, 120-140 kelimelik bir metin yaz. Başlık: 'Alman Turistler, Türk Kahvesi Kültürüne Hayran Kaldı'. Metin, Mardin'i ziyaret eden bir turist grubunun, 'mırra' ve 'Türk kahvesi' ikramından nasıl etkilendiğini anlatsın. Turistlerin, kahvenin '40 yıl hatırı' olduğunu öğrenerek bu geleneği kendi ülkelerinde de anlatacaklarından bahsedilsin. Metin, 5. sınıf seviyesine uygun olmalı ve '(Genel ağdan alınmıştır.)' notunu içermelidir."
        }
    },
    "SB.5.1.3.": {
        "aciklama": "Toplumsal birliği sürdürmeye yönelik yardımlaşma ve dayanışma",
        "metin_tipleri": {
            "Detaylı Proje Anlatısı": "5. Sınıf Sosyal Bilgiler, 'Yardımlaşma ve Dayanışma' konusu için 120-140 kelimelik bir 'Sosyal Sorumluluk Projesi Anlatısı' yaz. Metin, 'Selin Öğretmen' ve 5C sınıfının 'Sivil Toplum Kuruluşları' (STK) ile işbirliği yaparak 'huzurevindeki yaşlılar' için 'Gönül Köprüsü' adında bir proje başlattığını anlatsın. Metin, projenin aşamalarını (ihtiyaçları belirleme, kermes düzenleme, elde edilen gelirle yaşlılara hediye alma) ve öğrencilerin 'dayanışma' duygusunu nasıl öğrendiklerini 5. sınıf seviyesine uygun bir dille aktarsın.",
            "Tarihsel Bilgi/Örnek": "5. Sınıf Sosyal Bilgiler, 'Yardımlaşma ve Dayanışma' konusu için 120-140 kelimelik 'Tarihsel Bilgi Metni' yaz. Metin, ecdadımızın 'Zimem Defteri' (Veresiye Defteri) geleneğini açıklamalıdır. Zenginlerin, özellikle Ramazan ayında, tanımadıkları bir bakkala girip borçluların hesabını nasıl kapattığı anlatılsın. Metin, bu uygulamada 'yardım edenin' ve 'yardım alanın' birbirini tanımamasının 'mahremiyeti' koruyarak yardımlaşmayı nasıl incelikli hâle getirdiğini 5. sınıf seviyesine uygun bir dille vurgulasın."
        }
    },
    "SB.5.2.1.": {
        "aciklama": "Yaşadığı ilin göreceli konum özelliklerini belirleyebilme",
        "metin_tipleri": {
            "Betimleyici Bilmece (\"Ben Hangi İlim?\")": "5. Sınıf Sosyal Bilgiler, 'Göreceli Konum' konusu için 'Ben Hangi İlim?' formatında, 120-140 kelimelik betimleyici bir metin yaz. 'Trabzon' ili, 'göreceli konum' özellikleri kullanılarak tanıtılsın. İpuçları: 'Doğumda Rize, batımda Giresun ile komşuyum. Kuzeyim boydan boya Karadeniz'dir. Dağlarım denize paralel uzanır. Sümela Manastırı gibi tarihi bir mekâna ev sahipliği yaparım. Fındık ve çay tarımı için konumum çok elverişlidir.' Metin, 'Bilin bakalım ben hangi ilim?' sorusuyla bitsin."
        }
    },
    "SB.5.2.2.": {
        "aciklama": "Yaşadığı ilde doğal ve beşerî çevredeki değişimi neden ve sonuçlarıyla yorumlayabilme",
        "metin_tipleri": {
            "Diyalog / Anı (Karşılaştırmalı)": "5. Sınıf Sosyal Bilgiler, 'Doğal ve Beşerî Çevredeki Değişim' konusu için 120-140 kelimelik bir 'Diyalog/Anı' metni yaz. 'Ahmet' ve 'dedesi' arasında geçsin. Dedesi, eski bir fotoğrafa bakarak 'doğal çevrenin' (örn: eskiden dut ağaçlarıyla dolu bir tarla) ve 'beşerî çevrenin' (örn: tek katlı evler) nasıl olduğunu anlatsın. O tarlanın yerine şimdi büyük bir 'alışveriş merkezi' (beşerî unsur) yapıldığını, bu 'değişimin' nedeninin (örn: nüfus artışı) ne olduğunu 5. sınıf seviyesinde açıklasın.",
            "Örnek Olay (Neden-Sonuç)": "5. Sınıf Sosyal Bilgiler, 'Doğal ve Beşerî Çevredeki Değişim' konusu için 120-140 kelimelik bir 'Örnek Olay (Neden-Sonuç)' metni yaz. Metin, 'beşerî bir unsurun' doğal çevreyi nasıl değiştirdiğini anlatsın. Örnek olarak, bir nehir üzerine 'baraj' (beşerî unsur) inşa edilmesi verilsin. Bu barajın 'sonuçları' (örn: tarlaların su altında kalması, iklimin yumuşaması, enerji üretilmesi) ve 'Yusufeli' örneğindeki gibi köylerin yer değiştirmesi 5. sınıf seviyesine uygun bir dille açıklansın."
        }
    },
    "SB.5.2.3.": {
        "aciklama": "Yaşadığı ilde meydana gelebilecek afetlerin etkilerini azaltmaya yönelik farkındalık etkinlikleri düzenleyebilme",
        "metin_tipleri": {
            "Tanımlayıcı Bilgi Metni (Risk/Afet)": "5. Sınıf Sosyal Bilgiler, 'Afetler ve Etkileri' konusu için 120-140 kelimelik 'Tanımlayıcı Bilgi Metni' yaz. Konu 'Sel' afeti olmalı. Metin, önce 'Sel'i tanımlamalıdır. Ardından 'Risk:' başlığı altında sele neden olan faktörleri (örn: dere yataklarına ev yapılması, ani ve şiddetli yağışlar, bitki örtüsünün yok edilmesi) sıralamalı. Son olarak 'Afet:' başlığı altında olası sonuçlarını (örn: ev ve iş yerlerini su basması, can ve mal kayıpları, tarım alanlarının zarar görmesi) 5. sınıf seviyesine uygun bir dille açıklamalıdır.",
            "Deney/Proje Anlatısı": "5. Sınıf Sosyal Bilgiler, 'Afetlere Yönelik Farkındalık' konusu için 120-140 kelimelik bir 'Deney/Proje Anlatısı' yaz. Metin, 'Ali' ve arkadaşlarının 'Deprem Değil, Bina Öldürür' sloganıyla 'deprem' afeti için bir proje hazırladığını anlatsın. Öğrencilerin, aynı malzemelerden 'sağlam' ve 'çürük' olmak üzere iki farklı 'maket bina' yaptıklarını belirt. 'Sarsıntı tablası' üzerinde yaptıkları deneyde, dayanıksız binanın hemen yıkıldığını, sağlam binanın ise ayakta kaldığını gösterdiklerini anlat. Metin, 'afet öncesi tedbir' almanın önemini vurgulasın."
        }
    },
    "SB.5.2.4.": {
        "aciklama": "Ülkemize komşu devletler hakkında bilgi toplayabilme",
        "metin_tipleri": {
            "Tanıtıcı Bilgi Kartı (Komşu Ülke)": "5. Sınıf Sosyal Bilgiler, 'Ülkemize Komşu Devletler' konusu için 120-140 kelimelik 'Tanıtıcı Bilgi Kartı Metni' yaz. Metin, komşumuz 'Bulgaristan' hakkında bilgi vermeli. Bulgaristan'ın 'konumunu' (Türkiye'nin kuzeybatısında), 'başkentini' (Sofya), 'yönetim şeklini', 'para birimini' (Leva) ve 'resmî dilini' 5. sınıf seviyesine uygun, tanıtıcı bir dille açıklamalıdır. Ayrıca ülkemizle olan 'sınır kapılarına' (örn: Kapıkule) kısaca değinilmelidir."
        }
    },
    "SB.5.3.1.": {
        "aciklama": "Yaşadığı ildeki ortak miras ögelerine ilişkin oluşturduğu ürünü paylaşabilme",
        "metin_tipleri": {
            "Tanımlayıcı Bilgi Metni (Kavramsal)": "5. Sınıf Sosyal Bilgiler, 'Ortak Kültürel Mirasımız' konusu için 120-140 kelimelik 'Tanımlayıcı Bilgi Metni' yaz. Metin, 'ortak miras' ögelerini sınıflandırmalıdır. 'Tarihî Mekân' (örn: Efes Antik Kenti), 'Tarihî Eser' (örn: Süleymaniye Camii) ve 'Tarihî Nesne' (örn: Pazırık Halısı) kavramlarını 5. sınıf seviyesine uygun örneklerle açıklamalı. Bu eserlerin neden 'insanlığın ortak mirası' sayıldığını ve korunmaları gerektiğini vurgulamalıdır."
        }
    },
    "SB.5.3.2.": {
        "aciklama": "Anadolu’da ilk yerleşimleri kuran toplumların sosyal hayatlarına yönelik bakış açısı geliştirebilme",
        "metin_tipleri": {
            "Tanımlayıcı/Betimleyici Metin (İlk Yerleşim Yeri)": "5. Sınıf Sosyal Bilgiler, 'Anadolu'nun İlk Yerleşim Yerleri' konusu için 120-140 kelimelik 'Betimleyici Metin' yaz. Metin, 'Çatalhöyük'teki sosyal hayatı ve barınma özelliklerini anlatmalı. Evlerin 'kerpiçten' yapıldığı, 'sokak olmadığı', evlerin bitişik nizamda olduğu ve insanların evlere 'çatıdaki açıklıklardan' merdivenle girdiği 5. sınıf seviyesinde açıklanmalı. Ayrıca duvarlara yapılan 'av sahneleri' resimlerinden de bahsedilmelidir."
        }
    },
    "SB.5.3.3.": {
        "aciklama": "Mezopotamya ve Anadolu medeniyetlerinin ortak mirasa katkılarını karşılaştırabilme",
        "metin_tipleri": {
            "Medeniyet Tanıtımı (Katkı Odaklı)": "5. Sınıf Sosyal Bilgiler, 'Medeniyetlerin Ortak Mirasa Katkıları' konusu için 120-140 kelimelik 'Tanımlayıcı Bilgi Metni' yaz. Metin, 'Sümerlerin' 'ortak mirasa' katkılarını anlatmalı. Mezopotamya'da kurulan bu medeniyetin, 'çivi yazısını' bularak 'tarihî çağları' başlattığı vurgulanmalı. Ayrıca 'tekerleği' icat ederek ulaşım ve ticareti kolaylaştırmaları ve 'Ziggurat' adlı yapıları rasathane olarak kullanmaları 5. sınıf seviyesinde açıklanmalıdır.",
            "Karşılaştırmalı Bilgi Metni (Hukuk)": "5. Sınıf Sosyal Bilgiler, 'Medeniyetlerin Ortak Mirasa Katkıları' konusu için 120-140 kelimelik 'Karşılaştırmalı Bilgi Metni' yaz. Metin, 'hukuk' alanındaki katkıları karşılaştırmalıdır. 'Sümerlerin' tarihteki ilk yazılı kanunları (Urukagina Kanunları) yaparak daha çok 'fidye' (para cezası) esasına dayandığını belirtmeli. Ardından 'Babillilerin' 'Hammabi Kanunları' ile 'kısasa kısas' (göze göz, dişe diş) yöntemini benimsediğini ve daha sert kurallar getirdiğini 5. sınıf seviyesine uygun bir dille açıklamalıdır."
        }
    },
    "SB.5.4.1.": {
        "aciklama": "Demokrasi ve cumhuriyet kavramları arasındaki ilişkiyi çözümleyebilme",
        "metin_tipleri": {
            "Tanımlayıcı Bilgi Metni (Kavramsal İlişki)": "5. Sınıf Sosyal Bilgiler, 'Demokrasi ve Cumhuriyet' konusu için 120-140 kelimelik 'Tanımlayıcı Bilgi Metni' yaz. Metin, 'demokrasi' ve 'cumhuriyet' kavramlarını ilişkilendirmelidir. 'Demokrasinin', halkın yönetime katılması, 'millî egemenlik', 'eşitlik' ve 'özgürlük' gibi ilkeleri içeren bir yaşam biçimi olduğunu açıklamalı. 'Cumhuriyetin' ise bu demokratik ilkelerin en iyi uygulandığı 'devlet yönetim biçimi' olduğunu belirtmeli. Metin, Atatürk'ün 'Demokrasinin en çağdaş ve mantıklı uygulamasını sağlayan hükümet şekli, cumhuriyettir.' sözüyle bu ilişkiyi pekiştirmelidir."
        }
    },
    "SB.5.4.2.": {
        "aciklama": "Toplum düzenine etkisi bakımından etkin vatandaş olmanın önemine yönelik çıkarımda bulunabilme",
        "metin_tipleri": {
            "Haber Metni (Etkin Vatandaşlık Uygulaması)": "5. Sınıf Sosyal Bilgiler, 'Etkin Vatandaşın Özellikleri' konusu için 'Haber Metni' formatında, 120-140 kelimelik bir metin yaz. Başlık: 'Duyarlı Vatandaş, Tarihî Çeşmeyi Kurtardı'. Metin, mahallesindeki 'ortak miras' olan eski bir çeşmenin 'hasar aldığını' fark eden 'etkin bir vatandaşın' (örn: Ali Bey) durumu anlatan bir 'dilekçe' ile 'Belediyeye' veya 'Kültür Varlıklarını Koruma Kuruluna' başvurmasını anlatsın. Bu 'sorumluluk' sayesinde çeşmenin 'restore' edildiği ve 'toplum düzenine' katkı sağlandığı vurgulansın. '(Genel ağdan alınmıştır.)' notu içermelidir."
        }
    },
    "SB.5.4.3.": {
        "aciklama": "Temel insan hak ve sorumluluklarının önemini sorgulayabilme",
        "metin_tipleri": {
            "Örnek Olay (Çatışan Haklar)": "5. Sınıf Sosyal Bilgiler, 'Temel Hak ve Sorumluluklar' konusu için 120-140 kelimelik bir 'Örnek Olay' metni yaz. Metin, 'çatışan hakları' konu almalı. Bir yanda, parkta yüksek sesle müzik dinleyerek 'eğlenme hakkını' kullanan gençler; diğer yanda, evinin penceresi parka bakan ve 'dinlenme hakkını' kullanmak isteyen hasta bir komşu (örn: teyze) olsun. Metin, 'özgürlüklerin' sınırsız olmadığını ve 'başkalarının haklarına saygı' duyarak 'sorumluluklarımızı' yerine getirmemiz gerektiğini 5. sınıf seviyesinde vurgulasın.",
            "Haber Metni (Hak İhlali/Koruma)": "5. Sınıf Sosyal Bilgiler, 'Temel Hak ve Sorumluluklar' konusu için 120-140 kelimelik bir 'Haber Metni' yaz. Metin, 'eğitim hakkının' korunmasını konu almalı. Konu, 'T.C. Millî Eğitim Bakanlığınca' uygulanan 'Taşımalı Eğitim' hizmeti olsun. Metin, köyde okulu olmayan veya 'özel gereksinimli' öğrencilerin, 'servisler' veya 'Evde Eğitim' hizmeti sayesinde 'eğitim hakkından' nasıl eşit şekilde yararlandığını 5. sınıf seviyesine uygun bir dille anlatsın. '(Genel ağdan alınmıştır.)' notu içermelidir."
        }
    },
    "SB.5.4.4.": {
        "aciklama": "Bir ihtiyaç hâlinde veya sorun karşısında başvuru yapılabilecek kurumlar hakkında bilgi toplayabilme",
        "metin_tipleri": {
            "Tanımlayıcı Bilgi Metni (Kurum Görevleri)": "5. Sınıf Sosyal Bilgiler, 'Sorunların Çözümünde Kurumlar' konusu için 120-140 kelimelik 'Tanımlayıcı Bilgi Metni' yaz. Metin, 'Belediyelerin' görev ve sorumluluklarını açıklamalıdır. Belediyelerin, il ve ilçelerde halkın 'ortak ihtiyaçlarını' karşıladığı belirtilmeli. Görevlerine (örn: 'su ve kanalizasyon' hizmetleri, 'çöplerin toplanması', 'toplu ulaşım', 'park ve bahçelerin' bakımı, 'itfaiye' hizmetleri) 5. sınıf seviyesine uygun örnekler verilmeli. Sorun anında 'ALO 153' hattından ulaşılabileceği belirtilsin.",
            "Dilekçe Örneği": "5. Sınıf Sosyal Bilgiler dersi için bir 'Dilekçe Örneği' metni oluştur. Dilekçe, '... İLÇE BELEDİYE BAŞKANLIĞINA' hitaben yazılmalıdır. Konu, 'mahalle parkındaki oyun aletlerinin (salıncak, kaydırak) kırık ve tehlikeli olması' olmalıdır. Dilekçede, 'etkin bir vatandaş' olarak 'çocukların güvenlik' ve 'oyun hakkı' için bu sorunun çözülmesi talebi, 5. sınıf seviyesine uygun resmi bir dille iletilmelidir. Metin, 'Tarih', 'Ad Soyad', 'İmza' ve 'Adres' bölümlerini içermelidir."
        }
    },
    "SB.5.5.1.": {
        "aciklama": "Kaynakları verimli kullanmanın doğa ve insanlar üzerindeki etkisini yorumlayabilme",
        "metin_tipleri": {
            "Liste / Bilgi Metni (Tasarruf Yöntemleri)": "5. Sınıf Sosyal Bilgiler, 'Kaynaklarımızın Verimli Kullanımı' konusu için 120-140 kelimelik bir 'Bilgi Metni' yaz. Metin, 'enerji tasarrufu' için 'Sıfır Atık' projesinin '5D Modeli' ilkelerinin nasıl uygulanacağını açıklamalı. 'Düşün, gerekli değilse tüketme' (örn: odadan çıkarken ışığı kapatmak) ve 'Daha az tüket' (örn: A+++ enerji tasarruflu ampul kullanmak) ilkelerine odaklanmalı. Bu davranışların 'aile bütçesine' ve 'doğal kaynakların korunmasına' olan 'olumlu etkisini' 5. sınıf seviyesinde vurgulamalıdır.",
            "Haber Metni (Tasarruf Başarısı)": "5. Sınıf Sosyal Bilgiler, 'Kaynaklarımızın Verimli Kullanımı' konusu için 'Haber Metni' formatında, 120-140 kelimelik bir metin yaz. Başlık: 'Okulumuzda Kâğıt İsrafına Son: 100 Ağaç Kurtarıldı'. Metin, bir okulda başlatılan 'Sıfır Atık' projesini anlatsın. Öğrencilerin, 'geri dönüştürülebilen' kâğıtları ayrı kutularda toplaması sayesinde bir yılda tonlarca kâğıdın 'dönüştürüldüğü' belirtilsin. Bu sayede 'ormanların' (doğal kaynak) korunduğu ve 'ekonomik kazanç' sağlandığı vurgulansın. '(Genel ağdan alınmıştır.)' notu içermelidir."
        }
    },
    "SB.5.5.2.": {
        "aciklama": "İhtiyaç ve isteklerini karşılamak için gerekli bütçeyi planlayabilme",
        "metin_tipleri": {
            "Tanımlayıcı Bilgi Metni (İhtiyaç vs. İstek)": "5. Sınıf Sosyal Bilgiler, 'Bütçemi Planlıyorum' konusu için 120-140 kelimelik 'Tanımlayıcı Bilgi Metni' yaz. Metin, 'ihtiyaç' ve 'istek' kavramlarını karşılaştırmalıdır. 'İhtiyaçların', yaşamı sürdürmek için zorunlu olan (örn: 'beslenme', 'barınma', 'giyinme') şeyler olduğunu açıklamalı. 'İsteklerin' ise zorunlu olmayan ancak bizi mutlu eden (örn: 'çikolata', 'yeni bir oyuncak') şeyler olduğunu belirtmeli. 'Bütçe' yaparken her zaman 'temel ihtiyaçlara' öncelik verilmesi gerektiğini 5. sınıf seviyesinde vurgulasın.",
            "Örnek Olay (Bütçe Planlaması)": "5. Sınıf Sosyal Bilgiler, 'Bütçemi Planlıyorum' konusu için 120-140 kelimelik bir 'Örnek Olay' metni yaz. Metin, haftalık harçlığını alan 'Ali' adında bir öğrenciyi anlatsın. Ali'nin 'gelirinin' (harçlık) ve 'giderlerinin' olduğu belirtilsin. Ali'nin 'bütçe planı' yaparak 'ihtiyaçlarını' (örn: okul kantininden yemek, kalem) ve 'isteklerini' (örn: sinemaya gitmek) listelediği anlatılsın. 'Ayağını yorganına göre uzatarak' 'tasarruf' etmeyi başardığı (örn: kumbarasına para atması) ve bunun önemini anladığı vurgulansın."
        }
    },
    "SB.5.5.3.": {
        "aciklama": "Yaşadığı ildeki ekonomik faaliyetleri özetleyebilme",
        "metin_tipleri": {
            "Tanımlayıcı Bilgi Metni (Ekonomik Faaliyet Türü)": "5. Sınıf Sosyal Bilgiler, 'İlimizdeki Ekonomik Faaliyetler' konusu için 120-140 kelimelik 'Tanımlayıcı Bilgi Metni' yaz. Metin, 'Hizmet' (üçüncül ekonomik faaliyet) sektörünü açıklamalıdır. Bu faaliyetin, tarım veya sanayi gibi doğrudan bir 'ham madde' üretmek yerine, insanların ihtiyaçlarını karşılamaya yönelik (örn: 'eğitim', 'sağlık', 'ulaşım', 'bankacılık', 'güvenlik') işleri kapsadığını 5. sınıf seviyesinde belirtmeli. Öğretmen, doktor, polis gibi mesleklerin bu gruba girdiğini örneklemelidir.",
            "Örnek Metin (İl ve Faaliyet İlişkisi)": "5. Sınıf Sosyal Bilgiler, 'İlimizdeki Ekonomik Faaliyetler' konusu için 120-140 kelimelik 'Örnek Metin' yaz. Metin, 'Antalya' ilindeki 'turizm' ve 'seracılık' faaliyetlerinin 'coğrafi özelliklerle' ilişkisini açıklamalıdır. İlin 'güneşli gün sayısının fazla' ve 'kışların ılıman' olmasının 'seracılık' için; 'deniz kıyısında' olmasının ve 'doğal/tarihî güzelliklerinin' 'yaz turizmi' için nasıl bir fırsat yarattığını 5. sınıf seviyesine uygun bir dille anlatmalıdır."
        }
    },
    "SB.5.6.1.": {
        "aciklama": "Teknolojik gelişmelerin toplum hayatına etkilerini tartışabilme",
        "metin_tipleri": {
            "Haber Metni (Olumlu/Olumsuz Etki)": "5. Sınıf Sosyal Bilgiler, 'Teknolojinin Toplum Hayatına Etkileri' konusu için 120-140 kelimelik bir 'Haber Metni' yaz. Konu, 'drone (insansız hava aracı)' teknolojisinin 'toplumsal etkileri' olmalı. Metin, bu teknolojinin 'olumlu etkilerinden' (örn: 'tarım' alanlarının ilaçlanması, 'AFAD' tarafından afet bölgelerinde arama yapılması) ve 'olumsuz etkilerinden' (örn: 'özel hayatın gizliliğinin' ihlal edilmesi) 5. sınıf seviyesinde bahsetmeli. '(Genel ağdan alınmıştır.)' notu içermelidir.",
            "Karşılaştırmalı Uzman Görüşü": "5. Sınıf Sosyal Bilgiler, 'Teknolojinin Etkileri' konusu için 120-140 kelimelik 'Karşılaştırmalı Görüş' metni yaz. Konu, 'sosyal medyanın' etkileri olmalı. 'Uzman Görüşü 1' başlığı altında, sosyal medyanın 'olumlu' yönlerini (örn: uzaktaki akrabalarla 'iletişim' kurma, bilgiye hızlı ulaşma) savun. 'Uzman Görüşü 2' başlığı altında, 'olumsuz' yönlerini (örn: 'bağımlılık' yapma, 'yüz yüze iletişimi' azaltma, 'dijital zorbalık') 5. sınıf seviyesinde vurgula."
        }
    },
    "SB.5.6.2.": {
        "aciklama": "Teknolojik ürünlerin bilinçli kullanımının önemine ilişkin ürün oluşturabilme",
        "metin_tipleri": {
            "Örnek Olay (Dijital Güvenlik Hatası)": "5. Sınıf Sosyal Bilgiler, 'Teknolojinin Bilinçli Kullanımı' konusu için 120-140 kelimelik bir 'Örnek Olay' metni yaz. Olay, 'Ecem' adında bir öğrencinin 'dijital güvenlik' hatasını anlatsın. Ecem, sosyal medya hesabının şifresini 'doğum tarihi' gibi 'tahmin edilmesi kolay' bir şifre olarak belirlesin. Metin, bu 'bilinçsiz kullanımın' 'olumsuz sonucunu' (örn: hesabının çalınması) ve 'bilinçli bir kullanıcının' ne yapması gerektiğini (örn: 'güçlü şifreler' oluşturması, 'mahremiyete' dikkat etmesi) 5. sınıf seviyesinde açıklamalıdır.",
            "Bilgi Notu (Kavramsal)": "5. Sınıf Sosyal Bilgiler, 'Teknolojinin Bilinçli Kullanımı' konusu için 120-140 kelimelik bir 'Bilgi Notu' metni yaz. Metin, 'Dijital Ayak İzi' kavramını 5. sınıf seviyesine uygun bir dille tanımlamalıdır. Genel ağda yaptığımız her işlemin (örn: gezdiğimiz siteler, yaptığımız paylaşımlar) 'iz bıraktığı' açıklanmalı. Bu izlerin 'kişisel güvenliğimiz' (mahremiyet) için neden önemli olduğunu ve 'bilinçli bir genel ağ kullanıcısı' olarak bu izleri nasıl kontrol altında tutmamız gerektiğini vurgulamalıdır."
        }
    }
}


# --- YENİDEN YAPILANDIRILMIŞ FONKSİYONLAR ---

def prompt_olustur(bilesen_kodu, metin_tipi_adi):
    """
    Gemini API için seçilen süreç bileşeni ve metin tipine göre
    dinamik bir prompt oluşturur.
    """
    
    # 1. Temel prompt şablonunu al
    try:
        bilesen_data = PROMPT_SABLONLARI[bilesen_kodu]
        base_prompt = bilesen_data["metin_tipleri"][metin_tipi_adi]
        bilesen_aciklama = bilesen_data["aciklama"]
    except KeyError:
        if bilesen_kodu not in PROMPT_SABLONLARI:
            return f"Hata: Geçersiz süreç bileşeni kodu: {bilesen_kodu}"
        if metin_tipi_adi not in PROMPT_SABLONLARI[bilesen_kodu]["metin_tipleri"]:
            return f"Hata: Geçersiz metin tipi '{metin_tipi_adi}'"
        return "Hata: Bilinmeyen bir anahtar hatası oluştu."

    # 2. Üslup, seviye ve formatlama kurallarını tanımla
    seviye_ve_ozgunluk_talimati = """
    ZORUNLU KURALLAR VE TALİMATLAR:
    
    1.  **DİL SEVİYESİ:**
        Metin, bir 5. Sınıf öğrencisinin (11-13 yaş) kolayca anlayabileceği,
        açık, sade ve akıcı bir dille yazılmalıdır. Cümleler çok uzun veya
        karmaşık olmamalıdır.
        
    2.  **KELİME SAYISI:**
        Üretilen metin MUTLAKA 120 ila 140 kelime arasında olmalıdır.
        Bu kurala harfiyen uyulmalıdır.
        
    3.  **AKADEMİK TERİM AÇIKLAMA KURALI (ÇOK ÖNEMLİ):**
        Metin içinde geçen akademik veya teknik terimler (örn: ziggurat,
        bütçe, demokrasi, dijital ayak izi vb.) ASLA parantez içinde
        açıklanmamalıdır.
        
        Bunun yerine, terimler doğal bir cümle akışı içinde açıklanmalıdır.
        Aşağıdaki kalıplardan birini kullanmak ZORUNLUDUR:
        
        ❌ YANLIŞ KULLANIM (PARANTEZ YASAK):
            - "Sümerler ziggurat (basamaklı tapınak) inşa etti."
            - "Bütçe (gelir-gider planı) yapmak önemlidir."
            
        ✅ DOĞRU KULLANIM (DOĞAL AÇIKLAMA):
            • "X adı verilen Y" kalıbı:
              "Sümerler, ziggurat adı verilen basamaklı tapınaklar inşa etti."
            • "X, yani Y" kalıbı:
              "Bütçe, yani gelir ve giderlerin planlanması, çok önemlidir."
            • "X olarak bilinen Y" kalıbı:
              "Çivi yazısı olarak bilinen bu yazı sistemi..."
            • "X, Y anlamına gelir" kalıbı:
              "Tasarruf, gelecek için para biriktirmek anlamına gelir."
            • "X denilen Y" kalıbı:
              "Millî egemenlik denilen bu kavram..."
              
    4.  **ÖZGÜNLÜK (KOPYALAMA YASAĞI):**
        Metin, bu kurallara dayalı olarak TAMAMEN ÖZGÜN üretilmelidir.
        Her çağrıda, aynı prompt kullanılsa bile, farklı ve yeni bir metin
        oluşturulmalıdır. ASLA var olan bir ders kitabından alıntı
        yapmamalı veya cümleleri birebir kopyalamamalıdır.
        Metnin üslubu bir 5. sınıf Sosyal Bilgiler kitabını TAKLİT ETMELİ
        ama içeriği ÖZGÜN olmalıdır.
        
    5.  **FORMATLAMA:**
        Metinde yıldız (*), kalın (**) gibi Markdown formatlama karakterleri
        veya HTML etiketleri KULLANMA. Tüm çıktı DÜZ METİN olmalıdır.
        (Haber Metni tipindeki 'Başlık' ve '(Genel ağdan alınmıştır.)' notu
        hariç).
    """
    
    # 3. Tüm parçaları birleştirerek nihai prompt'u oluştur
    final_prompt = f"""
    GÖREV: Bir 5. Sınıf Sosyal Bilgiler ders kitabı için, aşağıda belirtilen
    kurallara harfiyen uyarak bir metin oluştur.
    
    SÜREÇ BİLEŞENİ (KAZANIM): {bilesen_kodu} - {bilesen_aciklama}
    İSTENEN METİN TİPİ: {metin_tipi_adi}
    
    ANA TALİMAT (PROMPT ŞABLONU):
    "{base_prompt}"
    
    {seviye_ve_ozgunluk_talimati}
    
    ---
    ÇOK ÖNEMLİ HATIRLATMALAR:
    - KELİME SAYISI: 120-140 (ZORUNLU!)
    - AKADEMİK TERİMLER: Parantez içinde AÇIKLAMA YAPMA! Doğal cümle içinde açıkla!
    - ÖZGÜNLÜK: Her seferinde özgün metin üret!
    
    Çıktı olarak SADECE istenen metni doğrudan Türkçe olarak yaz.
    Öncesinde veya sonrasında 'Elbette, işte metin:' gibi ekstra bir açıklama yapma.
    """
    return final_prompt

def metin_uret(bilesen_kodu, metin_tipi_adi, model):
    """
    Metin üretir ve döndürür
    
    Args:
        bilesen_kodu: Süreç bileşeni kodu (örn: "SB.5.1.1.")
        metin_tipi_adi: Metin tipi adı (örn: "Örnek Olay (Senaryo)")
        model: Gemini model nesnesi
    
    Returns:
        dict: {"success": bool, "metin": str, "kelime_sayisi": int, "uyari": str}
    """
    
    # Prompt oluştur
    prompt = prompt_olustur(bilesen_kodu, metin_tipi_adi)
    
    if prompt.startswith("Hata:"):
        return {"success": False, "metin": prompt, "kelime_sayisi": 0, "uyari": ""}
    
    if not model:
        return {"success": False, "metin": "❌ HATA: Gemini API yapılandırılmamış!", "kelime_sayisi": 0, "uyari": ""}
    
    # API çağrısı
    try:
        response = model.generate_content(prompt, request_options={'timeout': 60})
        
        # Markdown karakterlerini temizle (başlık ve haber notu hariç)
        # Sadece satır başı/sonundaki * ve **'ları temizle
        cleaned_text = re.sub(r'^\*\s*|\s*\*\s*$', '', response.text, flags=re.MULTILINE)
        cleaned_text = re.sub(r'\*\*(.*?)\*\*', r'\1', cleaned_text) # Kalın
        
        # Kelime sayısı
        kelime_sayisi = len(cleaned_text.split())
        
        # Uyarı mesajı (Yeni kural: 120-140)
        uyari = ""
        if kelime_sayisi < 120 or kelime_sayisi > 140:
            uyari = f"⚠️ Kelime sayısı hedef aralığın dışında! (120-140 arası olmalı, şu an: {kelime_sayisi})"
        
        return {
            "success": True,
            "metin": cleaned_text.strip(),
            "kelime_sayisi": kelime_sayisi,
            "uyari": uyari
        }
        
    except Exception as e:
        hata_mesaji = str(e)
        # API'nin içerik engelleme mesajını daha anlaşılır hale getir
        if "response.prompt_feedback" in hata_mesaji:
            hata_mesaji = "❌ HATA: Üretilen içerik güvenlik filtrelerine takıldı. Lütfen tekrar deneyin."
        elif "DeadlineExceeded" in hata_mesaji:
             hata_mesaji = "❌ HATA: API isteği zaman aşımına uğradı. Lütfen tekrar deneyin."
        
        return {
            "success": False,
            "metin": f"❌ HATA: Metin üretilemedi.\n{hata_mesaji}",
            "kelime_sayisi": 0,
            "uyari": ""
        }

# Test için
if __name__ == "__main__":
    print("Maarif Modeli Metin Oluşturma Aracı - Test Modu")
    print("Bu modül ana panel dosyası tarafından import edilecek")
    
    # Bu modülün doğrudan çalıştırılması test amaçlıdır.
    # Gerçek kullanım için bir API KEY ve bir panel arayüzü gerekir.
    
    print("\nPROMPT_SABLONLARI sözlüğünden örnek veri:")
    print(f"Bileşen Kodu: SB.5.1.1.")
    print(f"Açıklama: {PROMPT_SABLONLARI['SB.5.1.1.']['aciklama']}")
    print(f"Mevcut Metin Tipleri: {list(PROMPT_SABLONLARI['SB.5.1.1.']['metin_tipleri'].keys())}")
    
    print("\nÖrnek Prompt Oluşturma Testi (SB.5.5.2. - Örnek Olay):")
    test_prompt = prompt_olustur("SB.5.5.2.", "Örnek Olay (Bütçe Planlaması)")

    print(test_prompt)

