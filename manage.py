#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Утилита управления ботом и базой данных
"""

import sqlite3
import os
import sys
from datetime import datetime
import csv

DATABASE_PATH = 'english_club.db'

def init_db():
    """Инициализация базы данных"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            name TEXT NOT NULL,
            age INTEGER,
            english_experience TEXT,
            data_consent BOOLEAN DEFAULT 0,
            newsletter_consent BOOLEAN DEFAULT 0,
            registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ База данных инициализирована")

def show_stats():
    """Показать статистику"""
    if not os.path.exists(DATABASE_PATH):
        print("❌ База данных не найдена. Запустите сначала бота.")
        return
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM users")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE newsletter_consent = 1")
    newsletter = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE english_experience = 'Да'")
    experienced = cursor.fetchone()[0]
    
    cursor.execute("SELECT AVG(age) FROM users WHERE age IS NOT NULL")
    avg_age = cursor.fetchone()[0]
    
    print(f"\n📊 Статистика английского клуба:")
    print(f"👥 Всего участников: {total}")
    print(f"📧 Подписаны на рассылку: {newsletter}")
    print(f"📚 С опытом изучения: {experienced}")
    print(f"🆕 Новички: {total - experienced}")
    if avg_age:
        print(f"🎂 Средний возраст: {avg_age:.1f} лет")
    
    conn.close()

def export_users():
    """Экспорт пользователей в CSV"""
    if not os.path.exists(DATABASE_PATH):
        print("❌ База данных не найдена")
        return
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT telegram_id, username, name, age, english_experience, 
               data_consent, newsletter_consent, registration_date
        FROM users ORDER BY registration_date DESC
    ''')
    
    users = cursor.fetchall()
    conn.close()
    
    if not users:
        print("📭 Нет пользователей для экспорта")
        return
    
    filename = f"users_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            'Telegram ID', 'Username', 'Имя', 'Возраст', 'Опыт изучения',
            'Согласие на данные', 'Согласие на рассылку', 'Дата регистрации'
        ])
        
        for user in users:
            writer.writerow(user)
    
    print(f"✅ Данные экспортированы в файл: {filename}")
    print(f"📊 Экспортировано пользователей: {len(users)}")

def clear_db():
    """Очистка базы данных"""
    if not os.path.exists(DATABASE_PATH):
        print("❌ База данных не найдена")
        return
    
    confirm = input("⚠️ Вы уверены, что хотите удалить ВСЕ данные? (да/нет): ")
    if confirm.lower() != 'да':
        print("❌ Операция отменена")
        return
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users")
    conn.commit()
    conn.close()
    
    print("✅ База данных очищена")

def show_users():
    """Показать список пользователей"""
    if not os.path.exists(DATABASE_PATH):
        print("❌ База данных не найдена")
        return
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT name, age, english_experience, newsletter_consent, registration_date
        FROM users ORDER BY registration_date DESC LIMIT 20
    ''')
    
    users = cursor.fetchall()
    conn.close()
    
    if not users:
        print("📭 Пользователи не найдены")
        return
    
    print(f"\n👥 Последние {len(users)} пользователей:")
    print("-" * 80)
    
    for user in users:
        name, age, experience, newsletter, reg_date = user
        newsletter_status = "✅" if newsletter else "❌"
        print(f"👤 {name}, {age} лет, опыт: {experience}, рассылка: {newsletter_status}")
        print(f"   📅 Зарегистрирован: {reg_date}")
        print("-" * 40)

def main():
    """Главное меню управления"""
    if len(sys.argv) < 2:
        print("🔧 Утилита управления ботом английского клуба")
        print("\nДоступные команды:")
        print("  init     - Инициализировать базу данных")
        print("  stats    - Показать статистику")
        print("  users    - Показать список пользователей")
        print("  export   - Экспортировать пользователей в CSV")
        print("  clear    - Очистить базу данных")
        print("\nПример: python manage.py stats")
        return
    
    command = sys.argv[1].lower()
    
    commands = {
        'init': init_db,
        'stats': show_stats,
        'users': show_users,
        'export': export_users,
        'clear': clear_db
    }
    
    if command in commands:
        commands[command]()
    else:
        print(f"❌ Неизвестная команда: {command}")
        print("Используйте: python manage.py для списка команд")

if __name__ == '__main__':
    main()