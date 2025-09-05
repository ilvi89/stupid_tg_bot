# Архитектура диалоговой системы

## Обзор

Диалоговая система бота построена на основе DSL (Domain Specific Language), который позволяет декларативно описывать сложные диалоговые цепочки с автоматическим восстановлением состояния при ошибках.

## Ключевые компоненты

### 1. Dialog DSL (`dialog_dsl.py`)
- **DialogEngine** - основной движок диалогов
- **DialogChain** - цепочка диалога
- **DialogStep** - отдельный шаг диалога
- **DialogSession** - сессия пользователя
- **DialogBuilder** - построитель диалогов
- **Validators** - набор валидаторов

### 2. Dialog Maps (`dialog_maps.py`)
- Описание всех диалогов системы
- Карта переходов между диалогами
- Точки входа в диалоги

### 3. Dialog Handler (`dialog_handler.py`)
- Интеграция DSL с основным ботом
- Обработка команд и callback'ов
- Механизм восстановления диалогов

## Диалоговая карта

### Пользовательские диалоги

#### 1. Регистрация (`/start`)
```
Старт → Согласие на данные → [ДА/НЕТ]
                ↓ ДА              ↓ НЕТ
            Ввод имени         Отказ (КОНЕЦ)
                ↓
        Опыт английского
                ↓
           Ввод возраста
                ↓
        Согласие на рассылку
                ↓
          Сохранение данных
                ↓
         Отправка документов
                ↓
          Завершение (КОНЕЦ)
```

**Состояния ConversationHandler:**
- `WAITING_NAME` - ожидание имени
- `WAITING_EXPERIENCE` - ожидание опыта
- `WAITING_AGE` - ожидание возраста  
- `FINAL_CONSENT` - финальное согласие

**Точки восстановления:**
- После каждого шага данные сохраняются
- При ошибке предлагается продолжить с последнего шага
- Таймаут: 30 минут

#### 2. Редактирование профиля
```
Выбор поля → Ввод нового значения → Сохранение (КОНЕЦ)
     ↓
[Имя/Возраст/Опыт/Рассылка/Отмена]
```

**Восстановление:**
- Возврат к выбору поля при ошибке валидации
- Таймаут: 10 минут

#### 3. Обращение в поддержку
```
Выбор категории → Ввод сообщения → Отправка (КОНЕЦ)
```

**Восстановление:**
- Повтор ввода сообщения при ошибке
- Таймаут: 15 минут

### Менеджерские диалоги

#### 1. Авторизация (`/manager`)
```
Запрос пароля → Проверка → [УСПЕХ/ОШИБКА]
                    ↓           ↓
              Доступ разрешен  Отказ (КОНЕЦ)
                (КОНЕЦ)
```

**Восстановление:**
- Повтор ввода пароля при ошибке
- Таймаут: 5 минут

#### 2. Создание рассылки
```
Ввод сообщения → Подтверждение → [ДА/НЕТ]
                      ↓            ↓
                  Отправка     Отмена (КОНЕЦ)
                      ↓
                Результат (КОНЕЦ)
```

**Восстановление:**
- Повтор ввода сообщения при превышении лимита
- Возврат к подтверждению при ошибке отправки
- Таймаут: 10 минут

## Механизм восстановления

### Типы ошибок
1. **Валидация** - неверный формат данных
2. **Таймаут** - превышено время ожидания
3. **Системная ошибка** - ошибка в коде
4. **Прерывание** - пользователь начал новую команду

### Стратегии восстановления
1. **Продолжить** - с текущего шага
2. **Повторить** - текущий шаг заново  
3. **Перезапустить** - весь диалог сначала
4. **Отменить** - завершить диалог

### Состояния сессий
```
STARTED → IN_PROGRESS → WAITING_INPUT → COMPLETED
   ↓           ↓              ↓             ↑
ERROR ←── ERROR ←──── ERROR ──────────────┘
   ↓           ↓              ↓
PAUSED ←── PAUSED ←──── PAUSED
   ↓           ↓              ↓
CANCELLED ← CANCELLED ← CANCELLED
```

## Использование DSL

### Создание простого диалога
```python
from dialog_dsl import DialogBuilder, Validators, InputType

dialog = (DialogBuilder("simple_dialog", "Простой диалог")
    .start_with("greeting")
    
    .add_message(
        step_id="greeting",
        message="Привет! Как дела?",
        next_step="ask_name"
    )
    
    .add_question(
        step_id="ask_name", 
        message="Как тебя зовут?",
        input_type=InputType.TEXT,
        validations=[Validators.not_empty()],
        next_step="final"
    )
    
    .add_final(
        step_id="final",
        message="Приятно познакомиться, {ask_name}!"
    )
    
    .set_timeout(300)
    .build())
```

### Создание диалога с выбором
```python
dialog = (DialogBuilder("choice_dialog", "Диалог с выбором")
    .start_with("choose_option")
    
    .add_choice(
        step_id="choose_option",
        message="Выберите опцию:",
        inline_keyboard=[
            [("Опция 1", "option1")],
            [("Опция 2", "option2")]
        ],
        next_step="process_choice"
    )
    .add_condition("choose_option", {
        "choose_option=='option1'": "option1_step",
        "choose_option=='option2'": "option2_step"
    })
    
    .add_final("option1_step", "Вы выбрали опцию 1")
    .add_final("option2_step", "Вы выбрали опцию 2")
    
    .build())
```

### Создание диалога с действием
```python
async def custom_action(update, context, session):
    # Выполняем какое-то действие
    result = await some_async_operation()
    return {"result": result}

dialog = (DialogBuilder("action_dialog", "Диалог с действием")
    .start_with("start")
    
    .add_action(
        step_id="start",
        action=custom_action,
        message="Выполняю действие...",
        next_step="show_result"
    )
    
    .add_final(
        step_id="show_result", 
        message="Результат: {result}"
    )
    
    .build())
```

## Интеграция с ботом

### В основном файле бота
```python
from dialog_handler import init_dialog_system, get_dialog_system

# В конструкторе бота
self.dialog_handler = init_dialog_system(self.db_path)

# В обработчиках
async def handle_text_messages(update, context):
    # Сначала проверяем диалоговую систему
    if await bot_instance.dialog_handler.handle_message(update, context):
        return
    # ... остальная логика

async def handle_callbacks(update, context):
    # Сначала проверяем диалоговую систему  
    if await bot_instance.dialog_handler.handle_callback(update, context):
        return
    # ... остальная логика
```

## Команды отладки

### Для пользователей
- `/dialog_info` - информация о текущем диалоге
- `/dialog_cancel` - отменить текущий диалог

### Для менеджеров
- `/dialog_sessions` - показать все активные сессии

## База данных

### Таблица dialog_sessions
```sql
CREATE TABLE dialog_sessions (
    user_id INTEGER,
    chat_id INTEGER,
    chain_id TEXT,
    current_step TEXT,
    data TEXT,  -- JSON
    state TEXT,
    created_at REAL,
    updated_at REAL,
    retry_count INTEGER DEFAULT 0,
    error_history TEXT,  -- JSON
    PRIMARY KEY (user_id, chat_id)
);
```

## Аналитика

Система предоставляет аналитику:
- Общее количество сессий
- Процент завершенных диалогов
- Средняя продолжительность диалогов
- Анализ ошибок по шагам
- Наиболее проблемные места

## Расширение системы

### Добавление нового диалога
1. Создайте диалог с помощью DialogBuilder
2. Добавьте его в dialog_maps.py
3. Зарегистрируйте точку входа в entry_points
4. Диалог автоматически станет доступен

### Добавление нового типа валидации
```python
class Validators:
    @staticmethod
    def custom_validator() -> ValidationRule:
        return ValidationRule(
            name="custom",
            validator=lambda x: your_validation_logic(x),
            error_message="Ошибка валидации"
        )
```

### Добавление нового типа шага
Расширьте enum StepType и добавьте обработку в DialogEngine._execute_step()

## Преимущества новой системы

1. **Декларативность** - диалоги описываются как данные
2. **Восстанавливаемость** - автоматическое восстановление после ошибок
3. **Масштабируемость** - легко добавлять новые диалоги
4. **Отладка** - встроенные инструменты отладки
5. **Аналитика** - детальная статистика использования
6. **Тестируемость** - диалоги можно тестировать изолированно

## Миграция

Существующий код остается работоспособным благодаря fallback механизму. Новые диалоги обрабатываются новой системой, старые - старой системой ConversationHandler.

Постепенно можно мигрировать все диалоги на новую систему для получения всех преимуществ.