#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Главный скрипт запуска DSL Telegram-бота для английского клуба
Поддерживает параметры командной строки и настройку через .env
"""

import os
import sys
import argparse
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv


def parse_arguments():
    """Парсинг аргументов командной строки"""
    parser = argparse.ArgumentParser(
        description='DSL Telegram-бот для английского клуба',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python run.py                    # Обычный запуск
  python run.py --check            # Только проверка конфигурации
  python run.py --env custom.env   # Использовать другой .env файл
  python run.py --debug            # Запуск в режиме отладки
  python run.py --scenarios-only   # Только проверка сценариев
  python run.py --token TOKEN      # Передать токен напрямую
        """
    )
    
    parser.add_argument('--check', action='store_true',
                       help='Только проверить конфигурацию без запуска')
    parser.add_argument('--env', type=str, default='.env',
                       help='Путь к файлу с переменными окружения')
    parser.add_argument('--debug', action='store_true',
                       help='Запустить в режиме отладки')
    parser.add_argument('--scenarios-only', action='store_true',
                       help='Только проверить и показать сценарии')
    parser.add_argument('--token', type=str,
                       help='Токен бота (переопределяет .env)')
    parser.add_argument('--password', type=str,
                       help='Пароль менеджера (переопределяет .env)')
    parser.add_argument('--db', type=str,
                       help='Путь к базе данных (переопределяет .env)')
    
    return parser.parse_args()


def load_environment(env_file: str, args):
    """Загрузка переменных окружения с поддержкой параметров"""
    # Загружаем из файла
    if os.path.exists(env_file):
        load_dotenv(env_file)
        print(f"✅ Загружены переменные из {env_file}")
    else:
        print(f"⚠️ Файл {env_file} не найден, используются переменные по умолчанию")
    
    # Переопределяем из аргументов командной строки
    if args.token:
        os.environ['BOT_TOKEN'] = args.token
        print("✅ Токен бота установлен из аргументов")
    
    if args.password:
        os.environ['MANAGER_PASSWORD'] = args.password
        print("✅ Пароль менеджера установлен из аргументов")
    
    if args.db:
        os.environ['DATABASE_PATH'] = args.db
        print(f"✅ Путь к БД установлен: {args.db}")
    
    if args.debug:
        os.environ['LOG_LEVEL'] = 'DEBUG'
        os.environ['DSL_DEBUG_MODE'] = 'True'
        print("✅ Включен режим отладки")


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
        handlers=logging_config['handlers'],
        force=True
    )
    
    # Настраиваем уровни для внешних библиотек
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('telegram').setLevel(logging.INFO)


def check_requirements():
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


def check_token():
    """Проверка наличия токена бота"""
    token = os.getenv('BOT_TOKEN')
    if not token or token == 'your_bot_token_here':
        print("❌ BOT_TOKEN не установлен!")
        print("\nДля настройки токена:")
        print("1. Получите токен у @BotFather в Telegram")
        print("2. Установите в .env файле: BOT_TOKEN=ваш_токен")
        print("3. Или передайте параметром: python run.py --token ваш_токен")
        return False
    
    print(f"✅ BOT_TOKEN установлен: {token[:10]}...")
    return True


def check_manager_password():
    """Проверка пароля менеджера"""
    password = os.getenv('MANAGER_PASSWORD')
    if not password or password == 'your_secure_manager_password_here':
        print("⚠️ MANAGER_PASSWORD не установлен или используется значение по умолчанию")
        print("Рекомендуется установить безопасный пароль в .env файле")
        return True  # Не критично для запуска
    
    print("✅ Пароль менеджера установлен")
    return True


def check_database():
    """Проверка доступности базы данных"""
    db_path = os.getenv('DATABASE_PATH', 'english_club.db')
    
    try:
        import sqlite3
        # Пытаемся подключиться
        conn = sqlite3.connect(db_path)
        conn.close()
        print(f"✅ База данных доступна: {db_path}")
        return True
    except Exception as e:
        print(f"⚠️ Проблема с базой данных: {e}")
        print("База будет создана автоматически при первом запуске")
        return True  # Не критично


def check_scenarios():
    """Проверка файлов сценариев"""
    scenarios_dir = Path("scenarios")
    
    if not scenarios_dir.exists():
        print("❌ Директория scenarios не найдена")
        return False
    
    required_files = [
        "scenarios/__init__.py",
        "scenarios/registry.py",
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


def check_documents():
    """Проверка документов"""
    documents_dir = Path("documents")
    
    if not documents_dir.exists():
        print("⚠️ Директория documents не найдена")
        return True  # Не критично
    
    snaop_path = os.getenv('SNAOP_DOCUMENT_PATH', 'documents/СнаОП с прочерками.pdf')
    consent_path = os.getenv('NEWSLETTER_CONSENT_PATH', 'documents/Согласие_на_рассылку_информационных_и_рекламных_сообщений_с_прочерками.pdf')
    
    if os.path.exists(snaop_path):
        print(f"✅ СНАОП документ найден")
    else:
        print(f"⚠️ СНАОП документ не найден: {snaop_path}")
    
    if os.path.exists(consent_path):
        print(f"✅ Согласие на рассылку найдено")
    else:
        print(f"⚠️ Согласие на рассылку не найдено: {consent_path}")
    
    return True


def test_dsl_system():
    """Тестирование DSL системы (без регистрации тестовых сценариев)"""
    try:
        print("🔍 Тестирование DSL системы...")
        
        # Проверяем импорты и базовую сборку цепочки
        from dialog_dsl import DialogBuilder
        
        chain = (DialogBuilder('test_scenario', 'Тест')
                 .start_with('start')
                 .add_final('start', 'Тест завершен')
                 .build())
        
        if chain and chain.name == 'Тест':
            print("✅ Тестовая цепочка DSL успешно создана")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка DSL системы: {e}")
        return False


def show_scenarios_info():
    """Показать информацию о зарегистрированных сценариях"""
    try:
        from scenarios.auto_register import ScenarioDiscovery
        
        print("\n📋 Обнаружение сценариев...")
        stats = ScenarioDiscovery.discover_and_register_all()
        
        if "error" in stats:
            print(f"❌ Ошибка обнаружения: {stats['error']}")
            return False
        
        from scenarios.registry import get_registry
        registry = get_registry()
        registry_stats = registry.get_statistics()
        
        print(f"\n📊 Статистика сценариев:")
        print(f"• Всего сценариев: {registry_stats['total_scenarios']}")
        print(f"• Активных: {registry_stats['enabled_scenarios']}")
        print(f"• Точек входа: {registry_stats['entry_points']}")
        
        print(f"\n📂 По категориям:")
        for category, count in registry_stats['categories'].items():
            if count > 0:
                print(f"• {category}: {count}")
        
        print(f"\n👤 По типам:")
        for type_name, count in registry_stats['types'].items():
            if count > 0:
                print(f"• {type_name}: {count}")
        
        if registry_stats['missing_dependencies']:
            print(f"\n⚠️ Проблемы с зависимостями:")
            for scenario_id, missing in registry_stats['missing_dependencies'].items():
                print(f"• {scenario_id}: отсутствуют {', '.join(missing)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка получения информации о сценариях: {e}")
        return False


def run_system_checks():
    """Запустить все проверки системы"""
    print("🔍 Проверка DSL системы...\n")
    
    checks = [
        ("Зависимости Python", check_requirements),
        ("Токен бота", check_token),
        ("Пароль менеджера", check_manager_password),
        ("База данных", check_database),
        ("Файлы сценариев", check_scenarios),
        ("Документы", check_documents),
        ("DSL система", test_dsl_system)
    ]
    
    all_passed = True
    critical_failed = False
    
    for check_name, check_func in checks:
        print(f"🔍 Проверка: {check_name}")
        result = check_func()
        if not result:
            all_passed = False
            # Критичные проверки
            if check_name in ["Зависимости Python", "Токен бота", "Файлы сценариев", "DSL система"]:
                critical_failed = True
        print()
    
    return all_passed, critical_failed


def main():
    """Главная функция"""
    args = parse_arguments()
    
    print("🤖 DSL Telegram-бот для английского клуба")
    print("=" * 50)
    
    # Загружаем окружение
    load_environment(args.env, args)
    
    # Настраиваем логирование
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Если только проверка сценариев
    if args.scenarios_only:
        print("\n🎭 Проверка сценариев...")
        if show_scenarios_info():
            print("\n✅ Сценарии готовы к работе!")
        else:
            print("\n❌ Проблемы со сценариями")
            sys.exit(1)
        return
    
    # Проверяем систему
    all_passed, critical_failed = run_system_checks()
    
    if critical_failed:
        print("❌ Обнаружены критичные проблемы. Исправьте их и запустите снова.")
        sys.exit(1)
    
    if not all_passed:
        print("⚠️ Обнаружены некритичные проблемы, но бот может работать.")
    else:
        print("✅ Все проверки пройдены!")
    
    # Если только проверка
    if args.check:
        print("\n🎉 Конфигурация корректна! Для запуска используйте: python run.py")
        return
    
    print("\n🚀 Запускаем DSL бота...")
    
    try:
        # Импортируем и запускаем бот
        from bot import DSLTelegramBot
        
        bot = DSLTelegramBot()
        bot.run()
        
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен пользователем")
        logger.info("Бот остановлен пользователем")
        
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        logger.error(f"Критическая ошибка: {e}")
        sys.exit(1)


    # Завершение main без явного цикла событий


if __name__ == '__main__':
    main()