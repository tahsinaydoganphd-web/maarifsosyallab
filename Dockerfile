# Python + full libs
FROM python:3.10-bullseye

# ffmpeg yükle
RUN apt-get update && \
    apt-get install -y ffmpeg curl && \
    apt-get clean

# Çalışma klasörü
WORKDIR /app

# Python paketleri
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Proje dosyalarını kopyala
COPY . /app/

# Piper klasörünü oluştur
RUN mkdir -p /app/piper

# Linux için Piper binary indir (resmi release)
RUN curl -L -o /app/piper/piper \
    https://github.com/rhasspy/piper/releases/latest/download/piper_linux_x86_64 && \
    chmod +x /app/piper/piper

# Render port
ENV PORT=10000
EXPOSE 10000

# Gunicorn ile production başlat
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "app:app"]
