import os

path = 'templates/seyret_bul.html'

with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

# Mevcut 'mt-4' (üstten boşluk) kodunu bulup 'mt-0' (boşluksuz) yapıyoruz
# Ayrıca mb-4 (alttan boşluk) varsa onu da temizliyoruz
if 'id="timeline"' in html:
    html = html.replace('hidden mt-4"', 'hidden mt-0"')
    html = html.replace('mx-auto mb-4 bg-gray-200', 'mx-auto bg-gray-200')

with open(path, 'w', encoding='utf-8') as f:
    f.write(html)

print("✅ Kırmızı noktalı çizgi videoya yapıştırıldı.")
