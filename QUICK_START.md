# 🚀 Быстрый старт DSL бота

## Минимальный запуск (30 секунд)

```bash
# 1. Установите зависимости
pip install python-telegram-bot>=22.0 python-dotenv>=1.0.0

# 2. Настройте токен
cp .env.example .env
# Отредактируйте BOT_TOKEN в .env файле

# 3. Запустите
python run.py
```

## Параметры запуска

### Основные команды:
```bash
python run.py                    # Полный запуск с проверками
python run.py --check            # Только проверка конфигурации
python run.py --debug            # Запуск с отладкой
python start.py                  # Быстрый запуск без проверок
```

### Настройка через параметры:
```bash
# Передача токена напрямую
python run.py --token "ваш_токен_здесь"

# Использование другого .env файла
python run.py --env production.env

# Другая база данных
python run.py --db /path/to/database.db

# Пароль менеджера
python run.py --password "новый_пароль"

# Комбинация параметров
python run.py --debug --token "токен" --password "пароль"
```

### Проверки системы:
```bash
# Проверка конфигурации
python run.py --check

# Проверка только сценариев
python run.py --scenarios-only

# Проверка с отладкой
python run.py --check --debug
```

## Конфигурация .env

### Минимальная конфигурация:
```env
BOT_TOKEN=ваш_токен_от_BotFather
MANAGER_PASSWORD=безопасный_пароль
```

### Полная конфигурация:
```env
# Основные настройки
BOT_TOKEN=ваш_токен_от_BotFather
MANAGER_PASSWORD=безопасный_пароль_менеджера

# База данных
DATABASE_PATH=english_club.db

# Логирование
LOG_LEVEL=INFO
LOG_FILE=bot.log

# DSL настройки
DSL_AUTO_RELOAD=True
DSL_DEBUG_MODE=False
DSL_DEFAULT_TIMEOUT=1800

# Таймауты
MANAGER_SESSION_TIMEOUT=3600
DSL_SESSION_CLEANUP_INTERVAL=3600
```

## Тестирование

### После запуска протестируйте:
1. **Регистрация пользователя:**
   ```
   /start → следуйте диалогу регистрации
   ```

2. **Панель менеджера:**
   ```
   /manager → введите пароль → используйте панель
   ```

3. **DSL команды:**
   ```
   /scenario_list     # Список всех сценариев
   /scenario_stats    # Статистика выполнения
   /onboarding        # Полный онбординг (композиция)
   /dashboard         # Административная панель (композиция)
   ```

## Возможные ошибки

### "ModuleNotFoundError: No module named 'telegram'"
```bash
pip install -r requirements.txt
```

### "BOT_TOKEN не установлен"
```bash
# В .env файле
BOT_TOKEN=ваш_токен

# Или параметром
python run.py --token ваш_токен
```

### "Файлы сценариев не найдены"
```bash
# Проверьте структуру
ls -la scenarios/

# Должны быть:
# scenarios/user/registration.py
# scenarios/manager/auth.py
```

### "Ошибка инициализации DSL"
```bash
# Проверьте сценарии
python run.py --scenarios-only

# Запустите с отладкой
python run.py --debug
```

## Готово! 🎉

После успешного запуска вы увидите:
```
🤖 DSL Бот запущен! Нажмите Ctrl+C для остановки.
✅ Активных сценариев: 12
```

Бот готов к работе! Протестируйте командой `/start` в Telegram.

---

**Полная документация:** [README.md](README.md)
**Техническая архитектура:** [DSL_ARCHITECTURE.md](DSL_ARCHITECTURE.md)