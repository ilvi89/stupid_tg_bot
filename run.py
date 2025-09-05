#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт запуска бота с проверкой конфигурации
"""

import os
import sys

def check_requirements():
    """Проверка установленных зависимостей"""
    try:
        import telegram
        print("✅ python-telegram-bot установлен")
    except ImportError:
        print("❌ Не установлен python-telegram-bot")
        print("Выполните: pip install -r requirements.txt")
        return False
    
    return True

def check_token():
    """Проверка наличия токена бота"""
    token = os.getenv('BOT_TOKEN')
    if not token or token == 'YOUR_BOT_TOKEN_HERE':
        print("❌ BOT_TOKEN не установлен!")
        print("\nДля настройки токена:")
        print("1. Получите токен у @BotFather в Telegram")
        print("2. Установите переменную окружения:")
        print("   Linux/Mac: export BOT_TOKEN='ваш_токен'")
        print("   Windows: set BOT_TOKEN=ваш_токен")
        print("3. Или создайте файл .env с содержимым:")
        print("   BOT_TOKEN=ваш_токен")
        return False
    
    print(f"✅ BOT_TOKEN установлен: {token[:10]}...")
    return True

def check_files():
    """Проверка необходимых файлов"""
    files_status = []
    
    # Проверяем основной файл бота
    if os.path.exists('bot.py'):
        files_status.append("✅ bot.py найден")
    else:
        files_status.append("❌ bot.py не найден")
        return False
    
    # Проверяем файлы документов (опционально)
    snaop_file = "СнаОП с прочерками.pdf"
    if os.path.exists(snaop_file):
        files_status.append(f"✅ {snaop_file} найден")
    else:
        files_status.append(f"⚠️ {snaop_file} не найден (будет пропущен)")
    
    consent_file = "Согласие_на_рассылку_информационных_и_рекламных_сообщений_с_прочерками.pdf"
    if os.path.exists(consent_file):
        files_status.append(f"✅ {consent_file} найден")
    else:
        files_status.append(f"⚠️ {consent_file} не найден (будет пропущен)")
    
    for status in files_status:
        print(status)
    
    return True

def main():
    """Главная функция проверки и запуска"""
    print("🤖 Проверка конфигурации Telegram-бота для английского клуба\n")
    
    # Загружаем переменные из .env или config.env если файл существует
    env_files = ['.env', 'config.env']
    for env_file in env_files:
        if os.path.exists(env_file):
            print(f"📄 Загружаем переменные из {env_file} файла")
            try:
                with open(env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip() and not line.startswith('#'):
                            key, value = line.strip().split('=', 1)
                            os.environ[key] = value
                break
            except UnicodeDecodeError:
                print(f"⚠️ Ошибка кодировки в файле {env_file}, пробуем следующий...")
                continue
    
    # Проверяем все компоненты
    checks = [
        ("Зависимости Python", check_requirements),
        ("Токен бота", check_token),
        ("Файлы проекта", check_files)
    ]
    
    all_ok = True
    for name, check_func in checks:
        print(f"\n📋 Проверка: {name}")
        if not check_func():
            all_ok = False
    
    if all_ok:
        print("\n🚀 Все проверки пройдены! Запускаем бота...")
        print("Для остановки нажмите Ctrl+C\n")
        
        # Импортируем и запускаем основной модуль
        try:
            import bot
            bot.main()
        except KeyboardInterrupt:
            print("\n👋 Бот остановлен пользователем")
        except Exception as e:
            print(f"\n❌ Ошибка при запуске бота: {e}")
    else:
        print("\n❌ Обнаружены проблемы. Исправьте их и запустите снова.")
        sys.exit(1)

if __name__ == '__main__':
    main()