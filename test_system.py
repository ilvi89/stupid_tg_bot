#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Полная проверка DSL системы бота
"""

import os
import sys
from pathlib import Path


def test_file_structure():
    """Тест структуры файлов"""
    print("🔍 Проверка структуры файлов...")
    
    required_files = {
        # Основные файлы
        'bot.py': 'Основной DSL бот',
        'run.py': 'Скрипт запуска с параметрами',
        'start.py': 'Быстрый запуск',
        'bootstrap.py': 'Система инициализации',
        'interfaces.py': 'DSL интерфейсы',
        'dialog_dsl.py': 'Ядро DSL системы',
        'auth_manager.py': 'Авторизация менеджеров',
        'manage.py': 'Утилиты управления БД',
        
        # Конфигурация
        '.env.example': 'Пример конфигурации',
        'requirements.txt': 'Зависимости Python',
        'LICENSE': 'Лицензия',
        
        # Документация
        'README.md': 'Главная документация',
        'QUICK_START.md': 'Быстрый старт',
        'DSL_ARCHITECTURE.md': 'Архитектура DSL',
        'DSL_MIGRATION_GUIDE.md': 'Руководство по переходу',
        'DSL_IMPLEMENTATION_REPORT.md': 'Отчет о реализации',
        
        # Структура scenarios
        'scenarios/__init__.py': 'Инициализация пакета',
        'scenarios/registry.py': 'Реестр сценариев',
        'scenarios/loader.py': 'Загрузчик сценариев',
        'scenarios/executor.py': 'Исполнитель сценариев',
        'scenarios/auto_register.py': 'Автоматическая регистрация',
        'scenarios/compositions.py': 'Композиции сценариев',
        
        # Пользовательские сценарии
        'scenarios/user/__init__.py': 'Пользовательские сценарии',
        'scenarios/user/registration.py': 'Сценарии регистрации',
        'scenarios/user/profile.py': 'Сценарии профиля',
        'scenarios/user/support.py': 'Сценарии поддержки',
        
        # Менеджерские сценарии
        'scenarios/manager/__init__.py': 'Менеджерские сценарии',
        'scenarios/manager/auth.py': 'Авторизация менеджеров',
        'scenarios/manager/broadcast.py': 'Сценарии рассылки',
        'scenarios/manager/administration.py': 'Административные сценарии',
        
        # Общие компоненты
        'scenarios/common/__init__.py': 'Общие компоненты',
        'scenarios/common/actions.py': 'Переиспользуемые действия',
        'scenarios/common/validators.py': 'Валидаторы данных',
    }
    
    missing_files = []
    for file_path, description in required_files.items():
        if not Path(file_path).exists():
            missing_files.append(f"{file_path} ({description})")
    
    if missing_files:
        print("❌ Отсутствуют файлы:")
        for file in missing_files:
            print(f"  • {file}")
        return False
    
    print(f"✅ Все {len(required_files)} файлов найдены")
    return True


def test_python_syntax():
    """Тест синтаксиса Python файлов"""
    print("\n🔍 Проверка синтаксиса Python файлов...")
    
    python_files = []
    for file_path in Path('.').rglob('*.py'):
        if '__pycache__' not in str(file_path):
            python_files.append(str(file_path))
    
    errors = []
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                compile(f.read(), file_path, 'exec')
        except SyntaxError as e:
            errors.append(f"{file_path}: {e}")
        except Exception as e:
            errors.append(f"{file_path}: {e}")
    
    if errors:
        print("❌ Ошибки синтаксиса:")
        for error in errors:
            print(f"  • {error}")
        return False
    
    print(f"✅ Синтаксис {len(python_files)} файлов корректен")
    return True


def test_env_example():
    """Тест файла .env.example"""
    print("\n🔍 Проверка .env.example...")
    
    if not Path('.env.example').exists():
        print("❌ Файл .env.example не найден")
        return False
    
    required_vars = [
        'BOT_TOKEN',
        'MANAGER_PASSWORD', 
        'DATABASE_PATH',
        'LOG_LEVEL',
        'DSL_AUTO_RELOAD'
    ]
    
    with open('.env.example', 'r') as f:
        content = f.read()
    
    missing_vars = []
    for var in required_vars:
        if var not in content:
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Отсутствуют переменные в .env.example: {missing_vars}")
        return False
    
    print("✅ Файл .env.example содержит все необходимые переменные")
    return True


def test_documentation():
    """Тест документации"""
    print("\n🔍 Проверка документации...")
    
    docs = {
        'README.md': ['DSL', 'сценарии', 'композиции'],
        'QUICK_START.md': ['run.py', 'параметры'],
        'DSL_ARCHITECTURE.md': ['архитектура', 'scenarios'],
    }
    
    errors = []
    for doc_file, keywords in docs.items():
        if not Path(doc_file).exists():
            errors.append(f"Отсутствует {doc_file}")
            continue
        
        with open(doc_file, 'r', encoding='utf-8') as f:
            content = f.read().lower()
        
        missing_keywords = []
        for keyword in keywords:
            if keyword.lower() not in content:
                missing_keywords.append(keyword)
        
        if missing_keywords:
            errors.append(f"{doc_file}: отсутствуют ключевые слова {missing_keywords}")
    
    if errors:
        print("❌ Проблемы с документацией:")
        for error in errors:
            print(f"  • {error}")
        return False
    
    print(f"✅ Документация {len(docs)} файлов корректна")
    return True


def test_scenarios_structure():
    """Тест структуры сценариев"""
    print("\n🔍 Проверка структуры сценариев...")
    
    # Проверяем наличие декораторов в файлах сценариев
    scenario_files = [
        'scenarios/user/registration.py',
        'scenarios/manager/auth.py'
    ]
    
    for file_path in scenario_files:
        if not Path(file_path).exists():
            print(f"❌ Файл {file_path} не найден")
            return False
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if '@user_scenario' not in content and '@manager_scenario' not in content:
            print(f"❌ В файле {file_path} нет декораторов сценариев")
            return False
    
    print("✅ Структура сценариев корректна")
    return True


def show_final_info():
    """Показать финальную информацию"""
    print("\n" + "="*60)
    print("🎉 DSL СИСТЕМА ГОТОВА К РАБОТЕ!")
    print("="*60)
    
    print("\n📋 Команды запуска:")
    print("  python run.py              # Полный запуск")
    print("  python run.py --check      # Проверка конфигурации")
    print("  python start.py            # Быстрый запуск")
    
    print("\n🎭 DSL команды в боте:")
    print("  /start                     # Регистрация")
    print("  /manager                   # Панель управления")
    print("  /onboarding               # Полный онбординг")
    print("  /dashboard                # Административная панель")
    print("  /scenario_list            # Список сценариев")
    
    print("\n📚 Документация:")
    print("  README.md                 # Главное руководство")
    print("  QUICK_START.md            # Быстрый старт")
    print("  DSL_ARCHITECTURE.md       # Техническая архитектура")
    
    print("\n🔧 Настройка:")
    print("  .env.example              # Пример конфигурации")
    print("  cp .env.example .env      # Создать конфигурацию")
    print("  # Отредактировать BOT_TOKEN в .env")
    
    print("\n🚀 Для запуска: python run.py")
    print("="*60)


def main():
    """Главная функция тестирования"""
    print("🧪 ПОЛНАЯ ПРОВЕРКА DSL СИСТЕМЫ")
    print("="*50)
    
    tests = [
        ("Структура файлов", test_file_structure),
        ("Синтаксис Python", test_python_syntax),
        ("Файл .env.example", test_env_example),
        ("Документация", test_documentation),
        ("Структура сценариев", test_scenarios_structure)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Ошибка в тесте '{test_name}': {e}")
            failed += 1
    
    print(f"\n📊 Результаты тестирования:")
    print(f"✅ Пройдено: {passed}")
    print(f"❌ Провалено: {failed}")
    print(f"📊 Всего тестов: {len(tests)}")
    
    if failed == 0:
        show_final_info()
        return True
    else:
        print(f"\n❌ Обнаружены проблемы в {failed} тестах")
        print("Исправьте ошибки и запустите тест снова")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)