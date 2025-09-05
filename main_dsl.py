#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Главный файл запуска DSL бота для английского клуба
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Добавляем текущую директорию в Python path
sys.path.insert(0, str(Path(__file__).parent))

from bot_dsl import DSLTelegramBot, main as bot_main


def setup_logging():
    """Настройка системы логирования"""
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    log_file = os.getenv('LOG_FILE')
    
    # Конфигурация логирования
    logging_config = {
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'level': getattr(logging, log_level.upper()),
        'handlers': []
    }
    
    # Консольный обработчик
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(logging_config['format']))
    logging_config['handlers'].append(console_handler)
    
    # Файловый обработчик
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(logging_config['format']))
        logging_config['handlers'].append(file_handler)
    
    # Настраиваем логирование
    logging.basicConfig(
        level=logging_config['level'],
        format=logging_config['format'],
        handlers=logging_config['handlers']
    )
    
    # Настраиваем уровни для внешних библиотек
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('telegram').setLevel(logging.INFO)


def check_environment():
    """Проверка переменных окружения"""
    required_vars = ['BOT_TOKEN']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var) or os.getenv(var) == 'YOUR_BOT_TOKEN_HERE':
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Отсутствуют обязательные переменные окружения: {', '.join(missing_vars)}")
        print("\nДля настройки:")
        print("1. Скопируйте .env.example в .env")
        print("2. Укажите ваш BOT_TOKEN от @BotFather")
        print("3. Настройте другие параметры по необходимости")
        return False
    
    return True


def check_dependencies():
    """Проверка установленных зависимостей"""
    try:
        import telegram
        import dotenv
        print("✅ Зависимости установлены")
        return True
    except ImportError as e:
        print(f"❌ Не установлены зависимости: {e}")
        print("Выполните: pip install -r requirements.txt")
        return False


def check_database():
    """Проверка базы данных"""
    try:
        import sqlite3
        db_path = os.getenv('DATABASE_PATH', 'english_club.db')
        
        # Пытаемся подключиться
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        table_count = cursor.fetchone()[0]
        conn.close()
        
        print(f"✅ База данных доступна (таблиц: {table_count})")
        return True
        
    except Exception as e:
        print(f"⚠️ Проблема с базой данных: {e}")
        print("База данных будет создана автоматически при первом запуске")
        return True  # Не критично


def check_scenario_files():
    """Проверка файлов сценариев"""
    scenarios_dir = Path(__file__).parent / "scenarios"
    
    if not scenarios_dir.exists():
        print("❌ Директория scenarios не найдена")
        return False
    
    # Проверяем основные файлы
    required_files = [
        "scenarios/__init__.py",
        "scenarios/registry.py", 
        "scenarios/loader.py",
        "scenarios/executor.py",
        "scenarios/user/registration.py",
        "scenarios/manager/auth.py"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Отсутствуют файлы сценариев: {missing_files}")
        return False
    
    print("✅ Файлы сценариев найдены")
    return True


def run_system_checks():
    """Запустить все проверки системы"""
    print("🔍 Проверка системы DSL бота...\n")
    
    checks = [
        ("Зависимости", check_dependencies),
        ("Переменные окружения", check_environment),
        ("База данных", check_database),
        ("Файлы сценариев", check_scenario_files)
    ]
    
    all_passed = True
    for check_name, check_func in checks:
        print(f"🔍 Проверка: {check_name}")
        if not check_func():
            all_passed = False
        print()
    
    return all_passed


def main():
    """Главная функция запуска"""
    # Настраиваем логирование
    setup_logging()
    logger = logging.getLogger(__name__)
    
    print("🚀 DSL Telegram-бот для английского клуба")
    print("=" * 50)
    
    # Проверяем систему
    if not run_system_checks():
        print("❌ Обнаружены проблемы. Исправьте их и запустите снова.")
        sys.exit(1)
    
    print("✅ Все проверки пройдены!")
    print("🚀 Запускаем DSL бота...\n")
    
    try:
        # Запускаем основной бот
        bot_main()
        
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен пользователем")
        logger.info("Бот остановлен пользователем")
        
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        logger.error(f"Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()