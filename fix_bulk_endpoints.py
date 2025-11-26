# fix_bulk_endpoints.py
def add_missing_endpoints():
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Eksik endpoint'leri kontrol et ve ekle
    missing_endpoints = []
    
    if '@app.route(\'/delete_student_bulk\'' not in content:
        delete_endpoint = '''
@app.route('/delete_student_bulk', methods=['POST'])
def delete_student_bulk():
    """Toplu öğrenci silme"""
    try:
        import db_helper
        data = request.get_json()
        student_ids = data.get('student_ids', [])
        
        if not student_ids:
            return jsonify({'success': False, 'message': 'Silinecek öğrenci seçilmedi.'})
            
        conn = db_helper.get_db_connection()
        cur = conn.cursor()
        
        # SQL'den sil
        for student_id in student_ids:
            cur.execute("DELETE FROM users WHERE user_id = %s", (student_id,))
        
        deleted_count = cur.rowcount
        conn.commit()
        cur.close()
        conn.close()
        
        # RAM'den de temizle
        global users
        for sid in student_ids:
            if sid in users:
                del users[sid]
        
        return jsonify({'success': True, 'message': f'{deleted_count} öğrenci silindi!'})
    except Exception as e:
        print(f"Toplu silme hatası: {e}")
        return jsonify({'success': False, 'message': str(e)})
'''
        missing_endpoints.append(delete_endpoint)
        print("✅ /delete_student_bulk endpoint'i eklendi")
    
    if '@app.route(\'/update_student_bulk\'' not in content:
        update_endpoint = '''
@app.route('/update_student_bulk', methods=['POST'])
def update_student_bulk():
    """Toplu öğrenci güncelleme"""
    try:
        import db_helper
        data = request.get_json()
        student_ids = data.get('student_ids', [])
        actions = data.get('actions', {})
        
        updated_count = 0
        
        for student_id in student_ids:
            if student_id in users:
                user_data = users[student_id]
                updated = False
                
                # Sınıf Güncelle
                if actions.get('class'):
                    user_data['class'] = actions['class']
                    updated = True
                
                # Şifre Sıfırla
                if actions.get('set_password_to_lastname'):
                    last_name = user_data.get('last_name', '')
                    if last_name:
                        user_data['password'] = last_name
                        updated = True
                        
                # Eğer değişiklik varsa VERİTABANINA YAZ
                if updated:
                    users[student_id] = user_data
                    db_helper.save_user(student_id, user_data)
                    updated_count += 1
        
        return jsonify({'success': True, 'message': f'{updated_count} öğrenci güncellendi!'})
    except Exception as e:
        print(f"Toplu güncelleme hatası: {e}")
        return jsonify({'success': False, 'message': str(e)})
'''
        missing_endpoints.append(update_endpoint)
        print("✅ /update_student_bulk endpoint'i eklendi")
    
    # Eksik endpoint'leri app.py'ye ekle
    if missing_endpoints:
        # Diğer route'lardan sonra ekle
        last_route_pos = content.rfind('@app.route')
        if last_route_pos != -1:
            # Son route'dan sonraki kısmı bul
            insert_pos = content.find('\n', content.find('\n', last_route_pos)) + 1
            new_content = content[:insert_pos] + '\n'.join(missing_endpoints) + content[insert_pos:]
            
            with open('app.py', 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print("🎯 Eksik endpoint'ler eklendi! Sunucuyu yeniden başlatın.")
        else:
            print("❌ Route bulunamadı, manuel ekleme gerekli")
    else:
        print("✅ Tüm endpoint'ler mevcut")

if __name__ == "__main__":
    add_missing_endpoints()