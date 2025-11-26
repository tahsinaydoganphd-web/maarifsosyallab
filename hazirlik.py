import os
import subprocess

def dosya_olustur(isim, icerik):
    with open(isim, "w", encoding="utf-8") as f:
        f.write(icerik)
    print(f"✅ {isim} oluşturuldu.")

def main():
    print("🚀 Vercel Hazırlık Robotu Çalışıyor...")

    # 1. vercel.json Oluştur (Vercel ayar dosyası)
    vercel_json = """{
    "version": 2,
    "builds": [
        {
            "src": "app.py",
            "use": "@vercel/python"
        }
    ],
    "routes": [
        {
            "src": "/(.*)",
            "dest": "app.py"
        }
    ]
}"""
    dosya_olustur("vercel.json", vercel_json)

    # 2. .gitignore Oluştur (Gereksiz dosyalar gitmesin)
    gitignore = """__pycache__/
*.pyc
venv/
.env
.DS_Store
"""
    dosya_olustur(".gitignore", gitignore)

    # 3. requirements.txt Oluştur (Kütüphaneleri listele)
    print("📦 Kütüphaneler listeleniyor (pip freeze)...")
    try:
        result = subprocess.run(["pip", "freeze"], capture_output=True, text=True)
        with open("requirements.txt", "w") as f:
            f.write(result.stdout)
        print("✅ requirements.txt oluşturuldu.")
    except Exception as e:
        print(f"❌ Hata: requirements.txt oluşturulamadı. Manuel ekleyin. ({e})")

    print("\n🎉 HAZIRLIK TAMAMLANDI!")
    print("------------------------------------------------")
    print("Şimdi terminale sırasıyla şunları yapıştırın:")
    print("1. git init")
    print("2. git add .")
    print("3. git commit -m 'Otomatik hazırlık'")
    print("4. (GitHub'dan aldığınız repo linkini ekleyin ve pushlayın)")

if __name__ == "__main__":
    main()