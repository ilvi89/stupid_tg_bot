# Telegram-бот для английского клуба (DSL Architecture)

Современный Telegram-бот для автоматизации английского клуба, построенный на **декларативной DSL архитектуре** для максимальной гибкости и надежности.

## 🎭 DSL Архитектура

Бот полностью построен на **Domain Specific Language (DSL)** для описания диалогов:
- 🎯 **Декларативные сценарии** - диалоги описываются как данные
- 🔄 **Автоматическое восстановление** - продолжение после ошибок
- 🎭 **Композиции сценариев** - сложные workflow из простых блоков
- 📊 **Встроенная аналитика** - статистика выполнения в реальном времени
- 🔧 **Горячая перезагрузка** - обновление сценариев без перезапуска
- 🛡️ **Изоляция ошибок** - проблема в одном сценарии не влияет на другие

## 🚀 Быстрый старт

### 1. Получение токена бота
1. Найдите [@BotFather](https://t.me/BotFather) в Telegram
2. Отправьте команду `/newbot`
3. Следуйте инструкциям для создания бота
4. Сохраните полученный токен

### 2. Настройка проекта
```bash
# Клонируйте проект
git clone <repository_url>
cd simple_tg_bot

# Установите зависимости
pip install -r requirements.txt

# Создайте конфигурацию
cp .env.example .env
```

### 3. Конфигурация (.env файл)
```env
# Основные настройки
BOT_TOKEN=ваш_токен_от_BotFather
MANAGER_PASSWORD=безопасный_пароль_менеджера

# Настройки базы данных
DATABASE_PATH=english_club.db

# Настройки логирования
LOG_LEVEL=INFO
LOG_FILE=bot.log

# DSL настройки
DSL_AUTO_RELOAD=True
DSL_VALIDATION_STRICT=False
DSL_DEBUG_MODE=False

# Таймауты (в секундах)
MANAGER_SESSION_TIMEOUT=3600
DSL_DEFAULT_TIMEOUT=1800
DSL_SESSION_CLEANUP_INTERVAL=3600
```

### 4. Запуск бота
```bash
# Запуск с полными проверками (рекомендуется)
python run.py

# Прямой запуск
python bot.py
```

## 🎯 Доступные сценарии

### 👤 Пользовательские сценарии:

#### Регистрация и онбординг:
- **`/start`** - Полная регистрация (12 шагов, 30 мин)
  - Согласие на обработку данных
  - Сбор персональной информации
  - Согласие на рассылку
  - Отправка документов

- **`/onboarding`** - Полный онбординг (композиция)
  - Регистрация → Профиль → Справка
  - Комплексное знакомство с системой

#### Управление профилем:
- **`/profile`** - Управление профилем (композиция)
  - Просмотр данных
  - Редактирование полей
  - Удаление аккаунта

#### Поддержка:
- **`/support`** - Обращение в поддержку (композиция)
  - Частые вопросы по категориям
  - Создание тикетов поддержки
  - Контактная информация

### 🔧 Менеджерские сценарии:

#### Авторизация:
- **`/manager`** - Авторизация менеджера
  - Безопасный ввод пароля
  - Управление сессиями
  - Автоматический выход

#### Административная панель:
- **`/dashboard`** - Полная панель управления (композиция)
  - Статистика пользователей
  - Управление рассылками  
  - Экспорт данных
  - Системные настройки

#### Специализированные функции:
- **Статистика** - Детальная аналитика пользователей
- **Рассылки** - Создание и отправка сообщений
- **Экспорт** - Выгрузка данных в CSV
- **Управление** - Системные операции

### 🛠️ Отладочные команды:
- **`/scenario_info`** - Информация о текущем сценарии
- **`/scenario_list`** - Список всех сценариев
- **`/scenario_stats`** - Статистика выполнения
- **`/scenario_reload`** - Перезагрузка сценариев (только менеджеры)
- **`/scenario_cancel`** - Отмена текущего сценария

## 🎭 Как работает DSL

### Создание сценария:
```python
from scenarios.auto_register import user_scenario
from scenarios.registry import ScenarioCategory
from dialog_dsl import DialogBuilder, InputType
from scenarios.common.validators import CommonValidators

@user_scenario(
    id="my_scenario",
    name="Мой сценарий",
    category=ScenarioCategory.SUPPORT,
    entry_points=["/my_command", "my_entry"]
)
def create_my_scenario():
    return (DialogBuilder("my_scenario", "Мой сценарий")
        .start_with("start")
        
        .add_message(
            step_id="start",
            message="👋 Привет! Начинаем сценарий.",
            next_step="ask_name"
        )
        
        .add_question(
            step_id="ask_name",
            message="Как вас зовут?",
            input_type=InputType.TEXT,
            validations=[CommonValidators.not_empty()],
            next_step="finish"
        )
        
        .add_final(
            step_id="finish",
            message="Спасибо, {ask_name}! Сценарий завершен."
        )
        
        .set_timeout(600)  # 10 минут
        .build())
```

### Автоматическая регистрация:
Сценарий автоматически регистрируется при импорте модуля и становится доступен по указанным точкам входа.

### Композиции сценариев:
```python
from scenarios.compositions import CompositionBuilder

composition = (CompositionBuilder("my_flow", "Мой поток")
    .add_scenarios(["scenario1", "scenario2", "scenario3"])
    .add_transition("scenario1", "scenario2", "success==True")
    .add_transition("scenario2", "scenario3", "continue==True")
    .set_entry_points(["/my_flow"])
    .build())
```

## 🔄 Восстановление диалогов

### Автоматическое восстановление:
При любой ошибке система предлагает варианты:
- **Продолжить** с текущего шага
- **Повторить** текущий шаг
- **Начать заново** весь сценарий
- **Отменить** выполнение

### Сохранение состояния:
- Состояние сохраняется после каждого шага
- При возвращении пользователя диалог продолжается с места остановки
- История ошибок ведется для анализа
- Автоматическая очистка истекших сессий

## 📊 Мониторинг и аналитика

### Встроенная статистика:
- Количество запусков каждого сценария
- Время выполнения и точки выхода
- Частота ошибок по шагам
- Эффективность восстановления
- Популярность различных путей

### Команды мониторинга:
```bash
/scenario_stats     # Общая статистика
/scenario_list      # Все зарегистрированные сценарии  
/scenario_info      # Текущий сценарий пользователя
```

## 🗄️ База данных

### Основная таблица пользователей:
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE NOT NULL,
    username TEXT,
    name TEXT NOT NULL,
    age INTEGER,
    english_experience TEXT,
    data_consent BOOLEAN DEFAULT 0,
    newsletter_consent BOOLEAN DEFAULT 0,
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Таблица диалоговых сессий:
```sql
CREATE TABLE dialog_sessions (
    user_id INTEGER,
    chat_id INTEGER,
    chain_id TEXT,
    current_step TEXT,
    data TEXT,              -- JSON с данными диалога
    state TEXT,             -- Состояние сессии
    created_at REAL,
    updated_at REAL,
    retry_count INTEGER,
    error_history TEXT,     -- JSON с историей ошибок
    PRIMARY KEY (user_id, chat_id)
);
```

## 🔧 Управление ботом

### Для пользователей:
1. Отправьте `/start` для регистрации
2. Используйте `/menu` для доступа ко всем функциям
3. `/profile` - управление профилем
4. `/support` - обращение в поддержку

### Для менеджеров:
1. Отправьте `/manager` и введите пароль
2. Используйте `/dashboard` для полной панели управления
3. Доступны все административные функции через сценарии
4. `/scenario_reload` для обновления сценариев без перезапуска

### Утилиты командной строки:
```bash
# Управление данными
python manage.py stats      # Статистика
python manage.py export     # Экспорт пользователей
python manage.py clear      # Очистка БД
```

## 📁 Структура проекта

```
simple_tg_bot/
├── bot.py                   # Основной DSL бот
├── run.py                   # Скрипт запуска с проверками
├── bootstrap.py             # Система инициализации DSL
├── interfaces.py            # DSL интерфейсы
├── dialog_dsl.py           # Ядро DSL системы
├── auth_manager.py         # Система авторизации
├── manage.py               # Утилиты управления БД
├── .env                    # Переменные окружения
├── .env.example            # Пример конфигурации
├── requirements.txt        # Зависимости Python
├── LICENSE                 # Лицензия MIT
├── scenarios/              # 📦 Пакет сценариев
│   ├── registry.py         # Реестр сценариев
│   ├── loader.py           # Автозагрузчик
│   ├── executor.py         # Исполнитель
│   ├── auto_register.py    # Декораторы регистрации
│   ├── compositions.py     # Композиции сценариев
│   ├── user/               # Пользовательские сценарии
│   │   ├── registration.py # Регистрация
│   │   ├── profile.py      # Профиль
│   │   └── support.py      # Поддержка
│   ├── manager/            # Менеджерские сценарии
│   │   ├── auth.py         # Авторизация
│   │   ├── broadcast.py    # Рассылки
│   │   └── administration.py # Администрирование
│   └── common/             # Общие компоненты
│       ├── actions.py      # Действия
│       └── validators.py   # Валидаторы
├── documents/              # PDF документы
│   ├── СнаОП с прочерками.pdf
│   └── Согласие_на_рассылку_*.pdf
├── examples/               # Примеры использования
└── english_club.db        # База данных (создается автоматически)
```

## 🛡️ Безопасность

### Реализованные механизмы:
- 🔐 **Авторизация менеджеров** с сессиями и таймаутами
- 🔒 **Автоматическое удаление паролей** из чатов
- 📊 **Логирование всех действий** менеджеров
- 🚫 **Контроль доступа** по типам сценариев
- 🛡️ **Валидация всех входных данных**

### Рекомендации:
1. Используйте сложный пароль менеджера (12+ символов)
2. Регулярно проверяйте логи на подозрительную активность
3. Настройте автоматические резервные копии БД
4. Ограничьте доступ к .env файлу

## 📊 Аналитика и статистика

### Автоматически собираемые метрики:
- Популярность сценариев и композиций
- Время выполнения диалогов
- Точки выхода пользователей
- Частота и типы ошибок
- Эффективность восстановления

### Доступные отчеты:
- `/scenario_stats` - статистика DSL системы
- Административная панель - статистика пользователей
- Экспорт данных - детальные CSV отчеты
- Логи - полная история операций

## ❗ Устранение неполадок

### Проблемы с запуском:
```bash
# Проверка конфигурации
python run.py --check

# Проверка сценариев
python -c "from scenarios.auto_register import ScenarioDiscovery; ScenarioDiscovery.discover_and_register_all()"
```

### Проблемы со сценариями:
```bash
# В боте
/scenario_list      # Список всех сценариев
/scenario_stats     # Статистика выполнения
/scenario_reload    # Перезагрузка (менеджеры)
/scenario_cancel    # Отмена текущего сценария
```

### Частые ошибки:

1. **"Сценарий не найден"**
   - Проверьте регистрацию: `/scenario_list`
   - Перезагрузите: `/scenario_reload`

2. **"Ошибка инициализации DSL"**
   - Проверьте файлы в папке `scenarios/`
   - Убедитесь в корректности синтаксиса

3. **"Сессия зависла"**
   - Отмените сценарий: `/scenario_cancel`
   - Посмотрите информацию: `/scenario_info`

## 🔧 Разработка новых сценариев

### Создание пользовательского сценария:
```python
# scenarios/user/my_scenario.py

from scenarios.auto_register import user_scenario
from scenarios.registry import ScenarioCategory
from dialog_dsl import DialogBuilder, InputType
from scenarios.common.validators import CommonValidators

@user_scenario(
    id="my_user_scenario",
    name="Мой пользовательский сценарий",
    category=ScenarioCategory.SUPPORT,
    entry_points=["/my_command"]
)
def create_my_scenario():
    return (DialogBuilder("my_user_scenario", "Мой сценарий")
        .start_with("start")
        .add_message("start", "Привет!", next_step="end")
        .add_final("end", "До свидания!")
        .build())
```

### Создание менеджерского сценария:
```python
# scenarios/manager/my_admin.py

from scenarios.auto_register import manager_scenario
from scenarios.registry import ScenarioCategory

@manager_scenario(
    id="my_admin_scenario",
    name="Мой административный сценарий",
    category=ScenarioCategory.ADMINISTRATION,
    entry_points=["admin_action"]
)
def create_admin_scenario():
    return (DialogBuilder("my_admin_scenario", "Админ сценарий")
        .start_with("start")
        .add_message("start", "Админ функция", next_step="end")
        .add_final("end", "Выполнено!")
        .set_permissions(["manager"])
        .build())
```

### Автоматическая регистрация:
Сценарии автоматически регистрируются при запуске бота. Проверить можно командой `/scenario_list`.

## 📈 Производительность

### Оптимизации:
- **Асинхронная обработка** всех операций
- **Кэширование активных сессий** в памяти
- **Автоматическая очистка** истекших сессий
- **Оптимизированные SQL запросы** с индексами
- **Изоляция сценариев** для параллельного выполнения

### Масштабирование:
- Горизонтальное масштабирование сценариев
- Независимая работа композиций
- Балансировка нагрузки между сценариями
- Мониторинг производительности в реальном времени

## 📚 Документация

### Основные документы:
- **`README.md`** - это руководство
- **`DSL_ARCHITECTURE.md`** - техническая архитектура
- **`DSL_MIGRATION_GUIDE.md`** - руководство по переходу
- **`DSL_IMPLEMENTATION_REPORT.md`** - отчет о реализации

### Примеры:
- **`examples/dialog_examples.py`** - примеры создания сценариев
- **`scenarios/compositions_demo.py`** - демонстрация композиций
- **`scenarios/`** - живые примеры всех сценариев

## 🤝 Поддержка

### Получение помощи:
1. **Документация** - изучите файлы в корне проекта
2. **Примеры** - посмотрите `examples/` и `scenarios/`
3. **Логи** - проверьте `bot.log` при проблемах
4. **Отладка** - используйте команды `/scenario_*`

### Сообщение об ошибках:
При обнаружении ошибок укажите:
- Версию Python и зависимостей
- Содержимое .env файла (без токенов!)
- Логи ошибок
- Шаги для воспроизведения

## 🎉 Заключение

**DSL Telegram-бот для английского клуба** предоставляет:

✅ **Современную архитектуру** - декларативные сценарии вместо императивного кода
✅ **Надежность** - автоматическое восстановление после любых ошибок  
✅ **Гибкость** - легкое добавление новых сценариев и композиций
✅ **Мониторинг** - полная видимость выполнения диалогов
✅ **Масштабируемость** - готовность к росту и развитию

**Готов к продакшену! Запускайте: `python run.py` 🚀**

---

### 🔗 Быстрые ссылки:
- 🎯 [Техническая архитектура](DSL_ARCHITECTURE.md)
- 🔄 [Руководство по переходу](DSL_MIGRATION_GUIDE.md)  
- 📊 [Отчет о реализации](DSL_IMPLEMENTATION_REPORT.md)
- 💡 [Примеры сценариев](examples/dialog_examples.py)