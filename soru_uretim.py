# -*- coding: utf-8 -*-
"""
Maarif Modeli Soru Oluşturma Aracı
5. Sınıf Sosyal Bilgiler için Gemini API ile soru üretimi
"""

import google.generativeai as genai
import re

def api_yapilandir(api_key):
    """Gemini API'yi yapılandırır"""
    # Şifreyi dışarıdan gelen yerine direkt Render'dan (Environment) alıyoruz:
    guvenli_anahtar = os.getenv('GOOGLE_API_KEY')
    
    if guvenli_anahtar:
        genai.configure(api_key=guvenli_anahtar)
        
        # LİSTENİZDE GÖRÜNEN VE ÇALIŞAN MODEL:
        print("✅ Model yapılandırıldı: models/gemini-2.0-flash")
        return genai.GenerativeModel('models/gemini-2.0-flash')
        
    return None

# --- YENİ VERİ YAPISI: SORU ÜRETİM ŞABLONLARI 
# Süreç Bileşenleri (Kazanımlar), Soru Tipleri ve Prompt Şablonları

SORU_SABLONLARI = {
    # ÜNİTE 1: BİRLİKTE YAŞAMAK
    "SB.5.1.1.": {
        "aciklama": "Dâhil olduğu gruplar ve bu gruplardaki rolleri arasındaki ilişkileri çözümleyebilme",
        "soru_tipleri": {
            "Örnek Olaya Dayalı Çoktan Seçmeli Soru": "5. Sınıf Sosyal Bilgiler, 'Gruplar ve Rollerimiz' kazanımı (SB.5.1.1.) için bir 'Örnek Olaya Dayalı Çoktan Seçmeli Soru' oluştur. Soru, bir öğrencinin (isim RASTGELE seçilsin, örn: Elif, Ahmet) yeni dâhil olduğu bir sosyal gruba (örn: okul korosu, izcilik kulübü, tiyatro ekibi) katılması senaryosunu içersin. Sorunun kökü, öğrencinin bu YENİ ROLÜ nedeniyle üstlendiği yeni 'sorumluluğun' ne olduğunu sormalıdır. Çeldiriciler, öğrencinin 'hakları' (örn: forma giyme) veya diğer gruplardaki (örn: aile) sorumlulukları olmalıdır. Soru, 4 seçenek (A, B, C, D) içermeli ve doğru cevabı ('Doğru Cevap: X') formatında belirtmelidir.",
            "Açık Uçlu Karşılaştırma Sorusu": "5. Sınıf Sosyal Bilgiler, 'Gruplar ve Rollerimiz' kazanımı (SB.5.1.1.) için bir 'Açık Uçlu Karşılaştırma Sorusu' oluştur. Soru, öğrencinin 'okul' grubundaki 'öğrenci rolü' ile 'aile' grubundaki 'evlat rolü' arasındaki **hak** ve **sorumluluk** benzerliklerini veya farklılıklarını açıklamasını istemelidir. (Örn: 'Okuldaki öğrenci rolünüz ile ailenizdeki evlat rolünüzün sorumlulukları arasındaki farklara iki örnek veriniz.')"
        }
    },
    "SB.5.1.2.": {
        "aciklama": "Kültürel özelliklere saygı duymanın birlikte yaşamaya etkisini yorumlayabilme",
        "soru_tipleri": {
            "Metne Dayalı Yorumlama Sorusu (Açık Uçlu)": "5. Sınıf Sosyal Bilgiler, 'Kültürel Zenginlikler' kazanımı (SB.5.1.2.) için bir 'Metne Dayalı Yorumlama Sorusu' oluştur. Önce, RASTGELE bir ülkeden (örn: Japonya, İtalya, Hindistan, İspanya) Türkiye'ye gelen bir turistin, bir Türk kültürel özelliğinden (örn: misafirperverlik, yemek kültürü, bayramlaşma) etkilenmesini' anlatan 80-100 kelimelik kısa bir 'Örnek Haber Metni' yaz. Ardından, bu metne dayanarak 'Metne göre, kültürel farklılıklara saygı göstermenin birlikte yaşama üzerindeki etkisi nedir? Açıklayınız.' sorusunu sor.",
            "Kavram Eşleştirme Sorusu (Tablo)": "5. Sınıf Sosyal Bilgiler, 'Kültürel Zenginlikler' kazanımı (SB.5.1.2.) için bir 'Kavram Eşleştirme Sorusu' oluştur. [Bulgaristan(Marteniçka), Türkmenistan(Telpek), Rusya(Sarafan), Japonya(Kimono), İskoçya(Kilt), Meksika(Sombrero)] listesinden RASTGELE 3 (üç) tane 'Ülke' ve 'Kültürel Öge' seçerek bir eşleştirme tablosu hazırla. Öğrencinin, ilgili kültürel ögeyi doğru ülke ile eşleştirmesini iste."
        }
    },
    "SB.5.1.3.": {
        "aciklama": "Toplumsal birliği sürdürmeye yönelik yardımlaşma ve dayanışma",
        "soru_tipleri": {
            "Örnek Olay Analizi (Çoktan Seçmeli)": "5. Sınıf Sosyal Bilgiler, 'Yardımlaşma ve Dayanışma' kazanımı (SB.5.1.3.) için bir 'Örnek Olay Analizi (Çoktan Seçmeli)' sorusu oluştur. Soru, bir grup öğrencinin (örn: 5B sınıfı) RASTGELE bir toplumsal yardımlaşma faaliyeti (örn: sokak hayvanları için kermes, huzurevi ziyareti, ihtiyaç sahipleri için kampanya) düzenlemesini anlatan kısa bir senaryo içermelidir. Sorunun kökü, 'Öğrencilerin bu davranışı öncelikle aşağıdakilerden hangisini güçlendirir?' olmalıdır. Cevap 'Toplumsal dayanışma' olmalı; çeldiriciler ise 'kültürel ögeler', 'hak ve sorumluluklar' gibi ilgisiz kavramlar olmalıdır. 4 seçenek (A, B, C, D) içermeli ve doğru cevabı ('Doğru Cevap: X') formatında belirtmelidir.",
            "Tarihsel Örnek Tanımlama (Açık Uçlu)": "5. Sınıf Sosyal Bilgiler, 'Yardımlaşma ve Dayanışma' kazanımı (SB.5.1.3.) için bir 'Açık Uçlu Tanımlama Sorusu' oluştur. Soru, 'Kültürümüzde yer alan [Sadaka Taşı, Ahilik Teşkilatı, İmece] gibi RASTGELE seçilmiş bir yardımlaşma uygulamasının toplumsal birlik açısından önemini açıklayınız.' şeklinde olmalıdır."
        }
    },
    
    # ÜNİTE 2: EVİMİZ DÜNYA
    "SB.5.2.1.": {
        "aciklama": "Yaşadığı ilin göreceli konum özelliklerini belirleyebilme",
        "soru_tipleri": {
            "Harita Yorumlama Sorusu (Açık Uçlu)": "5. Sınıf Sosyal Bilgiler, 'Göreceli Konum' kazanımı (SB.5.2.1.) için 'Harita Yorumlama Sorusu' oluştur. (Ön bilgi: Türkiye Siyasi Haritası'nın öğrencinin önünde açık olduğu varsayılacaktır). [Konya, Erzurum, İzmir, Samsun, Diyarbakır, Edirne] listesinden RASTGELE bir il seç. Soru, 'Türkiye Siyasi Haritası'na göre seçtiğin bu ilin göreceli konumunu, komşu illerini (kuzey, güney, doğu, batı olarak) belirterek açıklayınız.' şeklinde olmalıdır.",
            "Betimleyici Bilmece Sorusu (\"Ben Hangi İlim?\")": "5. Sınıf Sosyal Bilgiler, 'Göreceli Konum' kazanımı (SB.5.2.1.) için 'Betimleyici Bilmece Sorusu' oluştur. [Antalya, İstanbul, Rize, Van, Kars, Trabzon, Muğla] listesinden RASTGELE bir il hedef al. O ilin belirgin coğrafi (dağ, deniz, göl) ve komşu özelliklerini anlatan bir bilmece sor. (Örn: 'Güneyim Akdeniz, batımda Muğla var... Ben hangi ilim?') "
        }
    },
    "SB.5.2.2.": {
        "aciklama": "Yaşadığı ilde doğal ve beşerî çevredeki değişimi neden ve sonuçlarıyla yorumlayabilme",
        "soru_tipleri": {
            "Karşılaştırmalı Diyalog Analizi (Açık Uçlu)": "5. Sınıf Sosyal Bilgiler, 'Doğal ve Beşerî Çevredeki Değişim' kazanımı (SB.5.2.2.) için bir 'Diyalog Analizi Sorusu' oluştur. Önce, 'yaşlı bir kişi ile bir gencin (örn: dede-torun), bir yerin 30 yıl önceki (doğal unsurların baskın olduğu) ve şimdiki (beşerî unsurların baskın olduğu, örn: fabrikalar, köprüler, binalar) hali üzerine konuştuğu' 100 kelimelik kısa bir diyalog metni yaz. Ardından, 'Metne göre bölgede değişen 2 doğal unsur ve 2 beşerî unsuru yazınız.' sorusunu sor.",
            "Neden-Sonuç İlişkisi (Çoktan Seçmeli)": "5. Sınıf Sosyal Bilgiler, 'Doğal ve Beşerî Çevredeki Değişim' kazanımı (SB.5.2.2.) için bir 'Neden-Sonuç İlişkisi (Çoktan Seçmeli)' sorusu oluştur. Soru, 'Bir bölgeye [Organize Sanayi Bölgesi, Büyük bir Havalimanı, Turizm Tesisi] gibi RASTGELE seçilmiş bir beşerî unsurun kurulmasının, o bölgenin beşerî çevresinde yaratacağı en önemli sonuç aşağıdakilerden hangisidir?' olmalıdır. Doğru cevap 'Nüfusun artması ve yeni konut alanlarının açılması' gibi bir seçenek olmalıdır. Çeldiriciler, doğal çevreyle (örn: iklimin değişmesi) veya ilgisiz konularla (örn: tarım üretiminin artması) ilgili olmalıdır. 4 seçenek (A, B, C, D) içermeli ve doğru cevabı ('Doğru Cevap: X') formatında belirtmelidir."
        }
    },
    "SB.5.2.3.": {
        "aciklama": "Yaşadığı ilde meydana gelebilecek afetlerin etkilerini azaltmaya yönelik farkındalık etkinlikleri düzenleyebilme",
        "soru_tipleri": {
            "Tanımlayıcı Bilgi Sorusu (Risk/Afet)": "5. Sınıf Sosyal Bilgiler, 'Afetler ve Etkileri' kazanımı (SB.5.2.3.) için 'Açık Uçlu Tanımlayıcı Bilgi Sorusu' oluştur. [Heyelan, Çığ, Sel, Deprem] afetlerinden RASTGELE birini seç. Soru, 'Seçtiğin bu afetin meydana gelmesinde etkili olan risk faktörlerinden (nedenlerinden) üç tanesini yazınız.' şeklinde olmalıdır.",
            "Proje/Deney Yorumlama (Açık Uçlu)": "5. Sınıf Sosyal Bilgiler, 'Afetlere Yönelik Farkındalık' kazanımı (SB.5.2.3.) için bir 'Proje Yorumlama Sorusu' oluştur. Soru, 'Okulunuzda [Deprem, Sel] afetlerinden biriyle ilgili bir farkındalık etkinliği düzenlemek isteseydiniz, afet öncesi tedbirlerin önemini vurgulamak için nasıl bir proje veya deney tasarlardınız? Kısaca açıklayınız.' şeklinde olmalıdır."
        }
    },
    "SB.5.2.4.": {
        "aciklama": "Ülkemize komşu devletler hakkında bilgi toplayabilme",
        "soru_tipleri": {
            "Bilgi Kartı Doldurma (Açık Uçlu)": "5. Sınıf Sosyal Bilgiler, 'Ülkemize Komşu Devletler' kazanımı (SB.5.2.4.) için 'Açık Uçlu Bilgi Sorusu' oluştur. Türkiye'nin komşularından [İran, Yunanistan, Bulgaristan, Suriye, Irak, Gürcistan] RASTGELE birini seç. Soru, 'Seçtiğin bu sınır komşumuz hakkında (Başkenti, Para Birimi, Sınır Kapısı) bildiklerinizi yazınız.' şeklinde olmalıdır."
        }
    },

    # ÜNİTE 3: ORTAK MİRASIMIZ
    "SB.5.3.1.": {
        "aciklama": "Yaşadığı ildeki ortak miras ögelerine ilişkin oluşturduğu ürünü paylaşabilme",
        "soru_tipleri": {
            "Kavram Sınıflandırma (Tablo Doldurma)": "5. Sınıf Sosyal Bilgiler, 'Ortak Kültürel Mirasımız' (SB.5.3.1.) için bir 'Kavram Sınıflandırma (Tablo)' sorusu oluştur. Soruda, [Ayasofya Camii, Efes Antik Kenti, Kaşıkçı Elması, Topkapı Sarayı, Çatalhöyük, Süleymaniye Camii, İshak Paşa Sarayı] listesinden RASTGELE 3 (üç) öge seçilsin. Öğrenciden bu ögeleri 'Tarihî Mekân', 'Tarihî Eser' ve 'Tarihî Nesne' olarak doğru şekilde sınıflandırmasını isteyen bir tablo oluştur.",
            "Açık Uçlu Yorumlama Sorusu": "5. Sınıf Sosyal Bilgiler, 'Ortak Kültürel Mirasımız' (SB.5.3.1.) için bir 'Açık Uçlu Yorumlama Sorusu' oluştur. Soru, 'İnsanlığın ortak mirası sayılan eserleri (örn: Efes Antik Kenti) korumanın ve gelecek nesillere aktarmanın neden önemli olduğunu açıklayınız.' şeklinde olmalıdır."
        }
    },
    "SB.5.3.2.": {
        "aciklama": "Anadolu’da ilk yerleşimleri kuran toplumların sosyal hayatlarına yönelik bakış açısı geliştirebilme",
        "soru_tipleri": {
            "Betimleyici Metne Dayalı Açık Uçlu Soru": "5. Sınıf Sosyal Bilgiler, 'Anadolu'nun İlk Yerleşim Yerleri' (SB.5.3.2.) için bir 'Açık Uçlu Bilgi Sorusu' oluştur. Soru, 'Çatalhöyük'teki evlerin mimari özelliklerini (evlere giriş şekli, sokakların durumu) ve bu mimarinin o dönemdeki sosyal yaşama etkilerini açıklayınız.' şeklinde olmalıdır."
        }
    },
    "SB.5.3.3.": {
        "aciklama": "Mezopotamya ve Anadolu medeniyetlerinin ortak mirasa katkılarını karşılaştırabilme",
        "soru_tipleri": {
            "Karşılaştırmalı Tablo Doldurma": "5. Sınıf Sosyal Bilgiler, 'Medeniyetlerin Katkıları' (SB.5.3.3.) için bir 'Karşılaştırmalı Tablo Doldurma' sorusu oluştur. Tabloda 'Medeniyet' ve 'Ortak Mirasa Katkısı' sütunları olsun. 'Medeniyet' sütunu için [Sümerler, Lidyalılar, Hititler, Babilliler, Asurlular, Urartular] listesinden RASTGELE 3 (üç) tanesini seç. Öğrenciden, seçtiğin bu 3 medeniyetin en önemli katkısını (örn: Yazı, Para, Kanunlar, Kütüphane) karşılarına yazmasını iste.",
            "Çoktan Seçmeli Soru (Hukuk Karşılaştırma)": "5. Sınıf Sosyal Bilgiler, 'Medeniyetlerin Katkıları' (SB.5.3.3.) için bir 'Çoktan Seçmeli Karşılaştırma Sorusu' oluştur. Soru, 'Sümer kanunları daha çok 'fidye' esasına dayanırken, 'kısasa kısas' (göze göz, dişe diş) yöntemini benimseyerek daha sert kurallar getiren Mezopotamya medeniyeti aşağıdakilerden hangisidir?' olmalıdır. Doğru cevap 'Babilliler' olmalıdır. Çeldiriciler 'Sümerler', 'Hititler', 'Asurlular' olmalıdır. 4 seçenek (A, B, C, D) içermeli ve doğru cevabı ('Doğru Cevap: X') formatında belirtmelidir."
        }
    },

    # ÜNİTE 4: YAŞAYAN DEMOKRASİMİZ
    "SB.5.4.1.": {
        "aciklama": "Demokrasi ve cumhuriyet kavramları arasındaki ilişkiyi çözümleyebilme",
        "soru_tipleri": {
            "Kavramsal İlişkiyi Sorgulama (Açık Uçlu)": "5. Sınıf Sosyal Bilgiler, 'Demokrasi ve Cumhuriyet' (SB.5.4.1.) için bir 'Açık Uçlu Kavramsal Soru' oluştur. Soru, 'Atatürk'ün 'Cumhuriyet rejimi demek, demokrasi sistemi ile devlet şekli demektir.' sözünden yola çıkarak bu iki kavram arasındaki ilişkiyi açıklayınız.' olmalıdır.",
            "Bulmaca Tipi Soru (Kavram Bulma)": "5. Sınıf Sosyal Bilgiler, 'Demokrasi ve Cumhuriyet' (SB.5.4.1.) için bir 'Tanımdan Kavram Bulma Sorusu' (Bulmaca Tipi) oluştur. Soru, 'Halkın yönetme gücüne sahip olması gerektiğini savunan yönetim anlayışına ve halkın egemenliği kendi elinde tuttuğu yönetim biçimine ne ad verilir?' şeklinde olmalıdır. (Cevaplar: Demokrasi, Cumhuriyet)."
        }
    },
    "SB.5.4.2.": {
        "aciklama": "Toplum düzenine etkisi bakımından etkin vatandaş olmanın önemine yönelik çıkarımda bulunabilme",
        "soru_tipleri": {
            "Örnek Olay Analizi (Açık Uçlu)": "5. Sınıf Sosyal Bilgiler, 'Etkin Vatandaş' (SB.5.4.2.) için bir 'Örnek Olay Analizi Sorusu' oluştur. Önce, 'Bir vatandaşın (isim RASTGELE seç, örn: Selin, Ali) [marketten aldığı ürünün bozuk çıkması, otobüsün durağında durmaması, mahallesindeki parkın bakımsız olması] gibi RASTGELE bir sorunla karşılaştığı' kısa bir örnek olay ver. Ardından, 'Bu durumda etkin bir vatandaş olarak bu kişinin hangi hakkını kullanarak ne yapması gerekir? Açıklayınız.' sorusunu sor."
        }
    },
    "SB.5.4.3.": {
        "aciklama": "Temel insan hak ve sorumluluklarının önemini sorgulayabilme",
        "soru_tipleri": {
            "Örnek Olay (Çatışan Haklar) Yorumlama Sorusu": "5. Sınıf Sosyal Bilgiler, 'Temel Hak ve Sorumluluklar' (SB.5.4.3.) için bir 'Örnek Olay Yorumlama Sorusu' oluştur. 'Bir apartmanda yaşayan bir kişi, 'dinlenme hakkını' kullanarak evinde istirahat ederken, yan komşusu 'eğlenme hakkını' kullanarak yüksek sesle müzik dinlemektedir.' senaryosunu ver. Ardından, 'Bu durumda ortaya çıkan 'hakların çatışması' sorununu, 'sorumluluk' kavramı açısından nasıl çözmek gerekir? Yorumlayınız.' sorusunu sor."
        }
    },
    "SB.5.4.4.": {
        "aciklama": "Bir ihtiyaç hâlinde veya sorun karşısında başvuru yapılabilecek kurumlar hakkında bilgi toplayabilme",
        "soru_tipleri": {
            "Kurum Görevi Eşleştirme (Tablo)": "5. Sınıf Sosyal Bilgiler, 'Sorunların Çözümünde Kurumlar' (SB.5.4.4.) için bir 'Eşleştirme Sorusu' oluştur. [Sokakların temizlenmesi, Okula başlama yaşının takibi, İlçedeki eğitim kurumlarının denetlenmesi, Güvenliğin sağlanması] listesinden RASTGELE 3 (üç) 'Sorun/İhtiyaç' seç. Bunları 'Başvurulacak Kurum' (örn: Belediye, Muhtarlık, Kaymakamlık, Emniyet) listesiyle eşleştirilecek bir tablo olarak hazırla."
        }
    },

    # ÜNİTE 5: HAYATIMIZDAKİ EKONOMİ
    "SB.5.5.1.": {
        "aciklama": "Kaynakları verimli kullanmanın doğa ve insanlar üzerindeki etkisini yorumlayabilme",
        "soru_tipleri": {
            "Açık Uçlu Yorumlama Sorusu": "5. Sınıf Sosyal Bilgiler, 'Kaynakların Verimli Kullanımı' (SB.5.5.1.) için bir 'Açık Uçlu Yorumlama Sorusu' oluştur. Soru, 'Evlerimizde [su, elektrik, doğal gaz] kaynaklarından RASTGELE birini tasarruflu kullanmanın hem aile bütçemize hem de doğal kaynakların korunmasına olan etkilerini açıklayınız.' şeklinde olmalıdır.",
            "Haber Metnine Dayalı Çoktan Seçmeli Soru": "5. Sınıf Sosyal Bilgiler, 'Kaynakların Verimli Kullanımı' (SB.5.5.1.) için bir 'Haber Metnine Dayalı Çoktan Seçmeli Soru' oluştur. Önce, '[Plastik poşetlerin ücretli olması, atık kâğıtların geri dönüştürülmesi, yağmur suyunun biriktirilmesi] gibi RASTGELE bir tasarruf/geri dönüşüm senaryosu' hakkında kısa bir haber metni yaz. Ardından, 'Bu uygulamanın en önemli sonucu aşağıdakilerden hangisidir?' sorusunu sor. Doğru cevap 'Doğal kaynakların korunması ve çevre kirliliğinin azalması' gibi bir seçenek olmalıdır. 4 seçenek (A, B, C, D) içermeli ve doğru cevabı ('Doğru Cevap: X') formatında belirtmelidir."
        }
    },
    "SB.5.5.2.": {
        "aciklama": "İhtiyaç ve isteklerini karşılamak için gerekli bütçeyi planlayabilme",
        "soru_tipleri": {
            "Kavramsal Sınıflandırma Sorusu (Tablo)": "5. Sınıf Sosyal Bilgiler, 'Bütçemi Planlıyorum' (SB.5.5.2.) için bir 'Kavramsal Sınıflandırma Sorusu' oluştur. Öğrenciye ['Beslenme', 'Barınma', 'Sinemaya gitmek', 'Yeni bir oyuncak', 'Su faturası', 'Dondurma yemek'] listesinden RASTGELE 4 (dört) kalem seç. Öğrenciden bu kalemleri 'İhtiyaç' ve 'İstek' olarak sınıflandırmasını iste.",
            "Örnek Olay Analizi (Açık Uçlu)": "5. Sınıf Sosyal Bilgiler, 'Bütçemi Planlıyorum' (SB.5.5.2.) için bir 'Örnek Olay Analizi Sorusu' oluştur. 'Haftalık harçlığını alan bir öğrenci (isim RASTGELE seç, örn: Zeynep), parasının tamamıyla çok istediği [yeni bir video oyunu, pahalı bir ayakkabı, bir oyuncak] almıştır. Ancak hafta sonu alması gereken temel bir ihtiyacı (örn: kalem, defter) için parası kalmamıştır.' senaryosunu ver. Ardından, 'Bu öğrenci, bütçe planlamasında hangi hatayı yapmıştır? 'İhtiyaç' ve 'İstek' kavramlarına göre açıklayınız.' sorusunu sor."
        }
    },
    "SB.5.5.3.": {
        "aciklama": "Yaşadığı ildeki ekonomik faaliyetleri özetleyebilme",
        "soru_tipleri": {
            "İlişkilendirme Sorusu (Neden-Sonuç)": "5. Sınıf Sosyal Bilgiler, 'Ekonomik Faaliyetler' (SB.5.5.3.) için bir 'Açık Uçlu İlişkilendirme Sorusu' oluştur. Soru, '[Antalya'da seracılık ve Erzurum'da hayvancılık] VEYA [Rize'de çay tarımı ve Konya'da tahıl tarımı] gibi RASTGELE iki farklı bölge ve ekonomik faaliyeti seç. Soru, 'Bu iki ekonomik faaliyetin bu illerde gelişmesinin nedenlerini coğrafi özellikleriyle (iklim, yeryüzü şekilleri) ilişkilendirerek açıklayınız.' şeklinde olmalıdır."
        }
    },

    # ÜNİTE 6: TEKNOLOJİ VE BİLİMLER
    "SB.5.6.1.": {
        "aciklama": "Teknolojik gelişmelerin toplum hayatına etkilerini tartışabilme",
        "soru_tipleri": {
            "Karşılaştırmalı Yorumlama Sorusu (Olumlu/Olumsuz)": "5. Sınıf Sosyal Bilgiler, 'Teknolojinin Etkileri' (SB.5.6.1.) için bir 'Karşılaştırmalı Yorumlama Sorusu' oluştur. Soru, '[Akıllı telefonlar, sosyal medya, E-Devlet] gibi RASTGELE bir teknolojik gelişmeyi seç. Soru, 'Seçilen bu teknolojik gelişmenin toplumsal ilişkilere olan 'olumlu' ve 'olumsuz' etkilerini birer örnekle açıklayınız.' şeklinde olmalıdır.",
            "Haber Metni Yorumlama (Açık Uçlu)": "5. Sınıf Sosyal Bilgiler, 'Teknolojinin Etkileri' (SB.5.6.1.) için bir 'Haber Metni Yorumlama Sorusu' oluştur. Önce, '[AFAD Acil Çağrı Uygulaması, E-Nabız sistemi, Uzaktan eğitim (EBA)] gibi RASTGELE bir teknolojik uygulamanın faydasını' anlatan kısa bir metin ver. Ardından, 'Bu teknolojik gelişmenin toplumsal hayata sağladığı olumlu katkıyı açıklayınız.' sorusunu sor."
        }
    },
    "SB.5.6.2.": {
        "aciklama": "Teknolojik ürünlerin bilinçli kullanımının önemine ilişkin ürün oluşturabilme",
        "soru_tipleri": {
            "Kavram Tanımlama Sorusu (Açık Uçlu)": "5. Sınıf Sosyal Bilgiler, 'Teknolojinin Bilinçli Kullanımı' (SB.5.6.2.) için bir 'Açık Uçlu Kavram Tanımlama Sorusu' oluştur. Soru, 'Dijital ayak izi nedir? Genel ağı kullanırken kişisel güvenliğimiz (mahremiyetimiz) için neden dijital ayak izimize dikkat etmeliyiz? Açıklayınız.' şeklinde olmalıdır.",
            "Örnek Olay Analizi (Çoktan Seçmeli)": "5. Sınıf Sosyal Bilgiler, 'Teknolojinin Bilinçli Kullanımı' (SB.5.6.2.) için bir 'Örnek Olay Analizi (Çoktan Seçmeli)' sorusu oluştur. 'Bir öğrenci (isim RASTGELE seç, örn: Ecem, Ali), sosyal medya hesabının şifresini kolay hatırlamak için [doğum tarihi, okul numarası, tuttuğu takımın adı] gibi kolay tahmin edilebilir bir bilgiyi kullanmaktadır.' senaryosunu ver. Ardından, 'Bu öğrencinin davranışı, dijital güvenlik açısından hangi 'bilinçsiz kullanım' hatasına örnektir?' sorusunu sor. Doğru cevap 'Güçlü şifre oluşturmamak' olmalıdır. 4 seçenek (A, B, C, D) içermeli ve doğru cevabı ('Doğru Cevap: X') formatında belirtmelidir."
        }
    }
}

def prompt_olustur(bilesen_kodu, soru_tipi_adi):
    """
    Gemini API için seçilen süreç bileşeni (kazanım) ve soru tipine göre
    dinamik bir prompt oluşturur.
    (v2 - Genel soru tiplerini destekler)
    """
    
    # 1. Temel prompt şablonunu ve kazanım açıklamasını al
    try:
        bilesen_data = SORU_SABLONLARI[bilesen_kodu]
        bilesen_aciklama = bilesen_data["aciklama"]
    except KeyError:
        return f"Hata: Geçersiz süreç bileşeni kodu: {bilesen_kodu}"

    # --- YENİ BÖLÜM: GENEL SORU TİPLERİ ---
    if soru_tipi_adi == "GENEL_COKTAN_SECME":
        # Eğer "Genel Çoktan Seçmeli" seçildiyse, kazanım açıklamasını kullanarak 
        # spesifik olmayan, genel bir talimat oluştur:
        base_prompt = f"5. Sınıf Sosyal Bilgiler, '{bilesen_aciklama}' kazanımı (SB.{bilesen_kodu}) ile ilgili, bu kazanımı ölçen özgün bir 'Çoktan Seçmeli Soru' oluştur. Soru, 4 seçenek (A, B, C, D) içermeli ve doğru cevabı ('Doğru Cevap: X') formatında belirtmelidir."
    
    elif soru_tipi_adi == "GENEL_METIN_YORUM":
        # Eğer "Genel Metne Dayalı" seçildiyse, genel bir metin/yorum talimatı oluştur:
        base_prompt = f"5. Sınıf Sosyal Bilgiler, '{bilesen_aciklama}' kazanımı (SB.{bilesen_kodu}) ile ilgili, bu kazanımı ölçen bir 'Metne Dayalı Yorumlama Sorusu (Açık Uçlu)' oluştur. Önce, bu kazanımla ilgili 80-100 kelimelik kısa bir 'Örnek Olay' veya 'Metin' yaz. Ardından, bu metne dayanarak 'Metne göre...' ile başlayan bir yorumlama sorusu sor."
    
    # --- ESKİ BÖLÜM: SPESİFİK SORU TİPLERİ ---
    else:
        # Eğer spesifik bir tip seçildiyse (örn: "Tablo Doldurma"), 
        # onu doğrudan sözlükten al:
        try:
            base_prompt = bilesen_data["soru_tipleri"][soru_tipi_adi]
        except KeyError:
            return f"Hata: Geçersiz soru tipi '{soru_tipi_adi}'"
            
    # 2. Üslup, seviye ve formatlama kurallarını tanımla
    seviye_ve_ozgunluk_talimati = """
    ZORUNLU KURALLAR VE TALİMATLAR:
    
    1.  **DİL SEVİYESİ:**
        Soru metni, bir 5. Sınıf öğrencisinin (11-13 yaş) kolayca anlayabileceği,
        açık, sade ve akıcı bir dille yazılmalıdır.
        
    2.  **SORU FORMATI (ÇOK ÖNEMLİ):**
        - Soru, açık ve net bir soru köküne sahip olmalıdır.
        - Eğer bir 'Çoktan Seçmeli Soru' isteniyorsa, MUTLAKA 4 adet seçenek
          (A, B, C, D) içermelidir.
        - Çoktan seçmeli sorunun sonunda, doğru cevap MUTLAKA
          'Doğru Cevap: X' formatında, yeni bir satırda belirtilmelidir.
          
    3.  **CEVAP ANAHTARI KURALI (YENİ):**
        - 'Çoktan Seçmeli' sorular zaten 'Doğru Cevap: X' satırını içerir.
        - 'Açık Uçlu', 'Tablo' veya 'Eşleştirme' gibi diğer tüm sorular için,
          soru metninin hemen altına, yeni bir satıra '---CEVAP---' ayıracı
          koymalı ve onun altına da 5. sınıf seviyesine uygun,
          kısa ve net bir 'Örnek Cevap' yazmalısın.
          
        ÖRNEK (Açık Uçlu Soru):
        Metne göre, kültürel farklılıklara saygı göstermenin birlikte yaşama
        üzerindeki etkisi nedir? Açıklayınız.
        ---CEVAP---
        Kültürel farklılıklara saygı göstermek, toplumdaki insanlar arasında
        hoşgörüyü ve anlayışı artırır. Bu durum, insanların bir arada
        barış içinde yaşamasına yardımcı olur.
            
    4.  **AKADEMİK TERİM AÇIKLAMA KURALI (ÇOK ÖNEMLİ):**
        Soru metni içinde geçen akademik veya teknik terimler
        (örn: ziggurat, bütçe, demokrasi, dijital ayak izi vb.) ASLA
        parantez içinde açıklanmamalıdır.
        
        Bunun yerine, terimler doğal bir cümle akışı içinde açıklanmalıdır.
        
        ❌ YANLIŞ KULLANIM (PARANTEZ YASAK):
            - "Sümerlerin ziggurat (basamaklı tapınak) yapmasının nedeni..."
            
        ✅ DOĞRU KULLANIM (DOĞAL AÇIKLAMA):
            • "Sümerlerin, ziggurat adı verilen basamaklı tapınakları..."
            
    5.  **ÖZGÜNLÜK (KOPYALAMA YASAĞI):**
        Soru, bu kurallara dayalı olarak TAMAMEN ÖZGÜN üretilmelidir.
        Her çağrıda, aynı prompt kullanılsa bile, farklı ve yeni bir soru
        oluşturulmalıdır. ASLA var olan bir ders kitabından alıntı
        yapmamalı veya cümleleri birebir kopyalamamalıdır.
        
    6.  **FORMATLAMA:**
        Metinde yıldız (*), kalın (**) gibi Markdown formatlama karakterleri
        veya HTML etiketleri KULLANMA. Tüm çıktı DÜZ METİN olmalıdır.
    """
    
    # 3. Tüm parçaları birleştirerek nihai prompt'u oluştur
    final_prompt = f"""
    GÖREV: Bir 5. Sınıf Sosyal Bilgiler ders kitabı için, aşağıda belirtilen
    kurallara harfiyen uyarak bir SORU oluştur.
    
    SÜREÇ BİLEŞENİ (KAZANIM): {bilesen_kodu} - {bilesen_aciklama}
    İSTENEN SORU TİPİ: {soru_tipi_adi}
    
    ANA TALİMAT (PROMPT ŞABLONU):
    "{base_prompt}"
    
    {seviye_ve_ozgunluk_talimati}
    
    ---
    ÇOK ÖNEMLİ HATIRLATMALAR:
    - SEVİYE: 5. Sınıf (11-13 yaş)
    - AKADEMİK TERİMLER: Parantez içinde AÇIKLAMA YAPMA!
    - ÖZGÜNLÜK: Her seferinde özgün soru üret!
    - ÇOKTAN SEÇMELİ İSE: Mutlaka 4 seçenek (A, B, C, D) ve 'Doğru Cevap: X' satırı ekle.
    
    Çıktı olarak SADECE istenen soruyu doğrudan Türkçe olarak yaz.
    Öncesinde veya sonrasında 'Elbette, işte soru:' gibi ekstra bir açıklama yapma.
    """
    return final_prompt

    # 2. Üslup, seviye ve formatlama kurallarını tanımla
    seviye_ve_ozgunluk_talimati = """
    ZORUNLU KURALLAR VE TALİMATLAR:
    
    1.  **DİL SEVİYESİ:**
        Soru metni, bir 5. Sınıf öğrencisinin (11-13 yaş) kolayca anlayabileceği,
        açık, sade ve akıcı bir dille yazılmalıdır.
        
    2.  **SORU FORMATI (ÇOK ÖNEMLİ):**
        - Soru, açık ve net bir soru köküne sahip olmalıdır.
        - Eğer bir 'Çoktan Seçmeli Soru' isteniyorsa, MUTLAKA 4 adet seçenek
          (A, B, C, D) içermelidir.
        - Çoktan seçmeli sorunun sonunda, doğru cevap MUTLAKA
          'Doğru Cevap: X' formatında, yeni bir satırda belirtilmelidir.
          
    3.  **CEVAP ANAHTARI KURALI (YENİ):**
        - 'Çoktan Seçmeli' sorular zaten 'Doğru Cevap: X' satırını içerir.
        - 'Açık Uçlu', 'Tablo' veya 'Eşleştirme' gibi diğer tüm sorular için,
          soru metninin hemen altına, yeni bir satıra '---CEVAP---' ayıracı
          koymalı ve onun altına da 5. sınıf seviyesine uygun,
          kısa ve net bir 'Örnek Cevap' yazmalısın.
          
        ÖRNEK (Açık Uçlu Soru):
        Metne göre, kültürel farklılıklara saygı göstermenin birlikte yaşama
        üzerindeki etkisi nedir? Açıklayınız.
        ---CEVAP---
        Kültürel farklılıklara saygı göstermek, toplumdaki insanlar arasında
        hoşgörüyü ve anlayışı artırır. Bu durum, insanların bir arada
        barış içinde yaşamasına yardımcı olur.
            
    4.  **AKADEMİK TERİM AÇIKLAMA KURALI (ÇOK ÖNEMLİ):**
        Soru metni içinde geçen akademik veya teknik terimler
        (örn: ziggurat, bütçe, demokrasi, dijital ayak izi vb.) ASLA
        parantez içinde açıklanmamalıdır.
        
        Bunun yerine, terimler doğal bir cümle akışı içinde açıklanmalıdır.
        
        ❌ YANLIŞ KULLANIM (PARANTEZ YASAK):
            - "Sümerlerin ziggurat (basamaklı tapınak) yapmasının nedeni..."
            
        ✅ DOĞRU KULLANIM (DOĞAL AÇIKLAMA):
            • "Sümerlerin, ziggurat adı verilen basamaklı tapınakları..."
            
    5.  **ÖZGÜNLÜK (KOPYALAMA YASAĞI):**
        Soru, bu kurallara dayalı olarak TAMAMEN ÖZGÜN üretilmelidir.
        Her çağrıda, aynı prompt kullanılsa bile, farklı ve yeni bir soru
        oluşturulmalıdır. ASLA var olan bir ders kitabından alıntı
        yapmamalı veya cümleleri birebir kopyalamamalıdır.
        
    6.  **FORMATLAMA:**
        Metinde yıldız (*), kalın (**) gibi Markdown formatlama karakterleri
        veya HTML etiketleri KULLANMA. Tüm çıktı DÜZ METİN olmalıdır.
    """
    
    # 3. Tüm parçaları birleştirerek nihai prompt'u oluştur
    final_prompt = f"""
    GÖREV: Bir 5. Sınıf Sosyal Bilgiler ders kitabı için, aşağıda belirtilen
    kurallara harfiyen uyarak bir SORU oluştur.
    
    SÜREÇ BİLEŞENİ (KAZANIM): {bilesen_kodu} - {bilesen_aciklama}
    İSTENEN SORU TİPİ: {soru_tipi_adi}
    
    ANA TALİMAT (PROMPT ŞABLONU):
    "{base_prompt}"
    
    {seviye_ve_ozgunluk_talimati}
    
    ---
    ÇOK ÖNEMLİ HATIRLATMALAR:
    - SEVİYE: 5. Sınıf (11-13 yaş)
    - AKADEMİK TERİMLER: Parantez içinde AÇIKLAMA YAPMA!
    - ÖZGÜNLÜK: Her seferinde özgün soru üret!
    - ÇOKTAN SEÇMELİ İSE: Mutlaka 4 seçenek (A, B, C, D) ve 'Doğru Cevap: X' satırı ekle.
    
    Çıktı olarak SADECE istenen soruyu doğrudan Türkçe olarak yaz.
    Öncesinde veya sonrasında 'Elbette, işte soru:' gibi ekstra bir açıklama yapma.
    """
    return final_prompt

def soru_uret(bilesen_kodu, soru_tipi_adi, model):
    """
    Soru üretir ve cevabını rubrik formatında oluşturur.
    
    Returns:
        dict: {"success": bool, "metin": str (Soru), "rubrik_cevap": str (Rubrik), "is_mcq": bool}
    """
    
    try:
        # 1. Gerekli bilgileri al
        bilesen_data = SORU_SABLONLARI.get(bilesen_kodu, {})
        bilesen_aciklama = bilesen_data.get('aciklama', 'Bilinmeyen Süreç Bileşeni')

        # 2. Soru prompt'unu oluştur
        prompt_soru = prompt_olustur(bilesen_kodu, soru_tipi_adi)
        if prompt_soru.startswith("Hata:"):
            return {"success": False, "metin": prompt_soru}

        if not model:
            return {"success": False, "metin": "❌ HATA: Gemini API yapılandırılmamış!"}

        # 3. Gemini Çağrısı 1: Soruyu Üret
        print(f"Rubrik Adım 1: '{soru_tipi_adi}' sorusu üretiliyor...")
        response_soru = model.generate_content(prompt_soru, request_options={'timeout': 60})
        
        cleaned_text = re.sub(r'^\*\s*|\s*\*\s*$', '', response_soru.text, flags=re.MULTILINE)
        cleaned_text = re.sub(r'\*\*(.*?)\*\*', r'\1', cleaned_text).strip()
        
        # 4. Soru Tipini Kontrol Et (MCQ mi, Açık Uçlu mu?)
        is_mcq = "Çoktan Seçmeli" in soru_tipi_adi or "Doğru Cevap:" in cleaned_text

        if is_mcq:
            # Soru Çoktan Seçmeli ise, rubriğe gerek yok. Olduğu gibi döndür.
            print("Rubrik Adım 2: Çoktan seçmeli soru, rubrik atlandı.")
            return {
                "success": True,
                "metin": cleaned_text,
                "rubrik_cevap": None,
                "is_mcq": True,
                "kelime_sayisi": kelime_sayisi_hesapla(cleaned_text)
            }
        
        # 5. Soru Açık Uçlu ise, Rubrik Üret
        print("Rubrik Adım 2: Açık uçlu soru, rubrik üretilecek...")
        
        soru_metni = cleaned_text
        basit_cevap = "[Basit cevap yok]" # Varsayılan

        # Eğer soruda ---CEVAP--- bloğu varsa, onu ayıralım
        if '---CEVAP---' in cleaned_text:
            parts = cleaned_text.split('---CEVAP---', 1)
            soru_metni = parts[0].strip()
            basit_cevap = parts[1].strip()

        # 6. Gemini Çağrısı 2: Rubriği Üret
        prompt_rubrik = rubrik_prompt_olustur(soru_metni, basit_cevap, bilesen_aciklama)
        
        print("Rubrik Adım 3: Rubrik prompt'u Gemini'ye gönderiliyor...")
        response_rubrik = model.generate_content(prompt_rubrik, request_options={'timeout': 90})
        rubrik_metni = response_rubrik.text.strip()

        # 7. Nihai sonucu döndür
        return {
            "success": True,
            "metin": soru_metni, # Sadece soru
            "rubrik_cevap": rubrik_metni, # Sadece rubrik
            "is_mcq": False,
            "kelime_sayisi": kelime_sayisi_hesapla(soru_metni)
        }

    except Exception as e:
        hata_mesaji = str(e)
        if "response.prompt_feedback" in hata_mesaji:
            hata_mesaji = "❌ HATA: İçerik güvenlik filtrelerine takıldı."
        elif "DeadlineExceeded" in hata_mesaji:
             hata_mesaji = "❌ HATA: API zaman aşımına uğradı."
        
        return {
            "success": False,
            "metin": f"❌ HATA: Soru/Rubrik üretilemedi.\n{hata_mesaji}",
        }
        
# BU 3 YENİ FONKSİYONU soru_uretim.py DOSYASINA EKLEYİN

def kelime_sayisi_hesapla(metin):
    """Metindeki kelime sayısını hesaplar (metin_analiz'den kopyalandı)"""
    return len(metin.split())

def json_parse_et(api_yaniti):
    """API yanıtından JSON çıkarır ve parse eder (metin_analiz'den kopyalandı)"""
    try:
        # JSON bloğunu bul
        json_match = re.search(r'\{.*\}', api_yaniti, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            return json.loads(json_str)
        
        # Eğer direkt JSON ise
        return json.loads(api_yaniti)
    except:
        return None

# soru_uretim.py dosyasında, mevcut 'rubrik_prompt_olustur_ fonksiyonunu BUNUNLA DEĞİŞTİRİN

def rubrik_prompt_olustur(soru_metni, basit_cevap, bilesen_aciklamasi):
    """
    (SÜRÜM 2 - TEMİZ HTML)
    Verilen soruya ve basit cevaba göre 10 puanlık detaylı bir
    puanlama anahtarı (rubrik) oluşturur.
    ÖNEMLİ: Cevap anahtarı kısmını <span class="answer-key">...</span> içine alır.
    """
    prompt = f"""
    Sen 5. Sınıf Sosyal Bilgiler öğretmenisin. Görevin, bir soruya ve onun basit cevabına bakarak, 10 puanlık detaylı bir puanlama anahtarı (rubrik) oluşturmaktır.

    Rubrik, öğrencinin 10 puanı alması için HANGİ ANA KAVRAMLARA yer vermesi gerektiğini, 5 puan (kısmi cevap) için ne yazması gerektiğini ve 0 puan (yanlış cevap) için hangi hataları yapacağını belirtmelidir.

    KAZANIM (İçerik): {bilesen_aciklamasi}
    SORU:
    {soru_metni}

    SORUNUN BASİT CEVABI (İpucu):
    {basit_cevap}

    ---
    ÇOK ÖNEMLİ KURALLAR:
    1.  Çıktında ASLA <strong>, <b>, <u>, **, *, <, > gibi biçimlendirme sembolleri KULLANMA.
    2.  Puan aldıracak anahtar cevap ifadelerini <span class="answer-key">...</span> etiketlerinin içine almalısın.

    ÖRNEK RUBRİK FORMATI (Bu formatı kullan):
    "Eğer Altı çizili cümlede <span class="answer-key">günümüz teknolojisiyle kaydedilen dijital dosyaların, gelecekte teknolojinin eskimesi (teknolojik köhneleşme) nedeniyle açılamama riskini</span> yazarsan 10 puan alırsın. Eğer sadece <span class="answer-key">"dosyaların bozulması"</span> gibi yüzeysel bir açıklama yapar, teknolojinin eskimesi boyutuna değinmezsen 5 puan alırsın. Eğer cevabında, endişeyi yanlış yorumlarsa (örn: "elektrik kesintisi", "internet olmaması" vb.) sıfır (0) puan alırsın."
    ---

    Puanlama Anahtarı (Rubrik) Çıktın:
    """
    return prompt
    
# Test için
if __name__ == "__main__":
    print("Maarif Modeli Soru Oluşturma Aracı - Test Modu")
    print("Bu modül ana panel dosyası tarafından import edilecek")
    
    # Bu modülün doğrudan çalıştırılması test amaçlıdır.
    # Gerçek kullanım için bir API KEY ve bir panel arayüzü gerekir.
    
    print("\nSORU_SABLONLARI sözlüğünden örnek veri:")
    print(f"Bileşen Kodu: SB.5.6.2.")
    print(f"Açıklama: {SORU_SABLONLARI['SB.5.6.2.']['aciklama']}")
    print(f"Mevcut Soru Tipleri: {list(SORU_SABLONLARI['SB.5.6.2.']['soru_tipleri'].keys())}")
    
    print("\nÖrnek Prompt Oluşturma Testi (SB.5.6.2. - Örnek Olay Analizi):")
    test_prompt = prompt_olustur("SB.5.6.2.", "Örnek Olay Analizi (Çoktan Seçmeli)")

    print(test_prompt)


