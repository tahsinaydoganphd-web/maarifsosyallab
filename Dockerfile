# Python + full libs (moviepy + scipy + piper için stabil)
FROM python:3.10-bullseye

# ffmpeg kurulumu
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean

# Çalışma dizini
WORKDIR /app

# Python paketleri
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Proje dosyaları
COPY . /app/

# Piper Linux binary çalıştırılabilir olsun
RUN chmod +x /app/piper/piper

# Render port
ENV PORT=10000
EXPOSE 10000

# Production server (Flask değil, gunicorn)
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "app:app"]
