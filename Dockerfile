# Python sürümünü seç
FROM python:3.10-slim

# Çalışma klasörünü ayarla
WORKDIR /app

# Gereksinimleri kopyala ve yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Tüm proje dosyalarını kopyala
COPY . .

# Portu aç
EXPOSE 5002

# Uygulamayı başlat
CMD ["python", "app.py"]