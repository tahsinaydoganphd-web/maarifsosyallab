import re

with open('templates/login.html', 'r', encoding='utf-8') as f:
    content = f.read()

# File input'u bul ve düzelt
new_input = '<input type="file" id="excelFile" accept=".xlsx,.xls,.csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel,application/vnd.ms-excel.sheet.macroEnabled.12" class="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100" />'

# Pattern ile değiştir
content = re.sub(
    r'<input type="file" id="excelFile"[^>]*>',
    new_input,
    content
)

with open('templates/login.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Excel file input düzeltildi! Artık tüm Excel dosyaları tıklanabilir.")
