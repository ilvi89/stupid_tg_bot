#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Улучшенный Telegram-бот для английского клуба
Реализует диалоговый сценарий знакомства с новыми участниками
Включает систему авторизации менеджеров и расширенный интерфейс
"""

import logging
import sqlite3
import os
import csv
from datetime import datetime
from typing import Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# Импорт новых модулей
from dialog_config import DIALOG_TEXTS, BUTTONS, SETTINGS, FILES
from auth_manager import auth_manager
from user_interface import UserInterface
from manager_interface import ManagerInterface

# Загрузка переменных окружения
from dotenv import load_dotenv
load_dotenv()

# Настройка логирования
log_level = os.getenv('LOG_LEVEL', 'INFO')
log_file = os.getenv('LOG_FILE')

logging_config = {
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'level': getattr(logging, log_level.upper())
}

if log_file:
    logging_config['filename'] = log_file

logging.basicConfig(**logging_config)
logger = logging.getLogger(__name__)

# Состояния диалога
WAITING_NAME, WAITING_EXPERIENCE, WAITING_AGE, FINAL_CONSENT = range(4)

# Токен бота (получить у @BotFather)
BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
DATABASE_PATH = os.getenv('DATABASE_PATH', 'english_club.db')

class EnglishClubBot:
    def __init__(self):
        self.db_path = DATABASE_PATH
        self.init_database()
        
        # Инициализируем интерфейсы
        self.user_interface = UserInterface(self.db_path)
        self.manager_interface = ManagerInterface(self.db_path)
    
    def init_database(self):
        """Инициализация базы данных"""
        conn = sqlite3.connect(self.db_path)
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
        logger.info("База данных инициализирована")
    
    def save_user_data(self, user_data: Dict[str, Any]):
        """Сохранение данных пользователя в БД"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO users 
            (telegram_id, username, name, age, english_experience, data_consent, newsletter_consent)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_data['telegram_id'],
            user_data.get('username', ''),
            user_data['name'],
            user_data.get('age'),
            user_data.get('english_experience'),
            user_data.get('data_consent', False),
            user_data.get('newsletter_consent', False)
        ))
        
        conn.commit()
        conn.close()
        logger.info(f"Пользователь {user_data['name']} сохранен в БД")

# Создаем экземпляр бота
bot_instance = EnglishClubBot()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало диалога - приветствие и запрос имени"""
    user = update.effective_user
    
    # Сохраняем базовую информацию о пользователе
    context.user_data['telegram_id'] = user.id
    context.user_data['username'] = user.username
    
    # Создаем клавиатуру для согласия на обработку данных
    keyboard = [
        [InlineKeyboardButton(BUTTONS['data_consent']['yes'], callback_data="data_consent_yes")],
        [InlineKeyboardButton(BUTTONS['data_consent']['no'], callback_data="data_consent_no")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = DIALOG_TEXTS['welcome']['full_text']
    
    await update.message.reply_text(
        welcome_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )
    
    return WAITING_NAME

async def handle_data_consent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка согласия на обработку данных"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "data_consent_yes":
        context.user_data['data_consent'] = True
        
        await query.edit_message_text(
            DIALOG_TEXTS['data_consent']['approved'],
            parse_mode='HTML'
        )
        
        return WAITING_NAME
    else:
        await query.edit_message_text(
            DIALOG_TEXTS['data_consent']['denied']
        )
        return ConversationHandler.END

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение имени и переход к вопросу об опыте"""
    if not context.user_data.get('data_consent'):
        await update.message.reply_text(
            "Пожалуйста, сначала дай согласие на обработку данных, нажав /start"
        )
        return ConversationHandler.END
    
    name = update.message.text.strip()
    context.user_data['name'] = name
    
    # Создаем клавиатуру для вопроса об опыте
    keyboard = [
        [KeyboardButton(BUTTONS['experience']['yes'])],
        [KeyboardButton(BUTTONS['experience']['no'])]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    greeting_text = DIALOG_TEXTS['name_received']['greeting'].format(name=name)
    question_text = DIALOG_TEXTS['name_received']['question']
    
    await update.message.reply_text(
        f"{greeting_text}\n\n{question_text}",
        parse_mode='HTML',
        reply_markup=reply_markup
    )
    
    return WAITING_EXPERIENCE

async def get_experience(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение информации об опыте и переход к вопросу о возрасте"""
    experience = update.message.text.strip()
    
    if "да" in experience.lower() or "✅" in experience:
        context.user_data['english_experience'] = "Да"
        response = DIALOG_TEXTS['experience']['yes_response']
    else:
        context.user_data['english_experience'] = "Нет"
        response = DIALOG_TEXTS['experience']['no_response']
    
    await update.message.reply_text(
        f"{response}\n\n"
        f"{DIALOG_TEXTS['age']['question']}",
        reply_markup=None  # Убираем клавиатуру
    )
    
    return WAITING_AGE

async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение возраста и переход к финальному согласию"""
    try:
        age = int(update.message.text.strip())
        min_age = SETTINGS['age_limits']['min']
        max_age = SETTINGS['age_limits']['max']
        
        if age < min_age or age > max_age:
            await update.message.reply_text(
                DIALOG_TEXTS['age']['invalid_age'].format(min_age=min_age, max_age=max_age)
            )
            return WAITING_AGE
        
        context.user_data['age'] = age
        
        # Создаем клавиатуру для финального согласия
        keyboard = [
            [InlineKeyboardButton(BUTTONS['newsletter']['yes'], callback_data="newsletter_yes")],
            [InlineKeyboardButton(BUTTONS['newsletter']['no'], callback_data="newsletter_no")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Отправляем СНАОП вместе с вопросом (если файл существует)
        snaop_file = FILES['snaop']
        if os.path.exists(snaop_file):
            await update.message.reply_document(
                document=open(snaop_file, 'rb'),
                caption=(
                    f"{DIALOG_TEXTS['notifications']['final_greeting'].format(name=context.user_data['name'])}\n\n"
                    f"{DIALOG_TEXTS['notifications']['info']}\n\n"
                    f"📄 <b>Согласие на обработку персональных данных</b>"
                ),
                parse_mode='HTML',
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                f"{DIALOG_TEXTS['notifications']['final_greeting'].format(name=context.user_data['name'])}\n\n"
                f"{DIALOG_TEXTS['notifications']['info']}",
                parse_mode='HTML',
                reply_markup=reply_markup
            )
        
        return FINAL_CONSENT
        
    except ValueError:
        await update.message.reply_text(
            DIALOG_TEXTS['age']['invalid_format']
        )
        return WAITING_AGE

async def final_consent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка финального согласия и завершение регистрации"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "newsletter_yes":
        context.user_data['newsletter_consent'] = True
        consent_text = DIALOG_TEXTS['newsletter']['yes_response']
    else:
        context.user_data['newsletter_consent'] = False
        consent_text = DIALOG_TEXTS['newsletter']['no_response']
    
    # Сохраняем все данные в БД
    bot_instance.save_user_data(context.user_data)
    
    # Отправляем согласие на рассылку (если файл существует и пользователь согласился)
    consent_file = FILES['newsletter_consent']
    if os.path.exists(consent_file) and context.user_data.get('newsletter_consent'):
        await query.message.reply_document(
            document=open(consent_file, 'rb'),
            caption="📄 Согласие на получение рассылки"
        )
    
    newsletter_status = '✅' if context.user_data.get('newsletter_consent') else '❌'
    
    summary = DIALOG_TEXTS['registration_complete']['summary_template'].format(
        name=context.user_data['name'],
        age=context.user_data['age'],
        experience=context.user_data['english_experience'],
        newsletter_status=newsletter_status
    )
    
    final_message = (
        f"{consent_text}\n\n"
        f"{DIALOG_TEXTS['registration_complete']['title']}\n\n"
        f"{DIALOG_TEXTS['registration_complete']['summary_title']}\n"
        f"{summary}\n\n"
        f"{DIALOG_TEXTS['registration_complete']['welcome']}\n"
        f"{DIALOG_TEXTS['registration_complete']['next_steps']}"
    )
    
    await query.edit_message_text(
        final_message,
        parse_mode='HTML'
    )
    
    # Очищаем данные пользователя
    context.user_data.clear()
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена диалога"""
    await update.message.reply_text(
        DIALOG_TEXTS['cancel']['message']
    )
    context.user_data.clear()
    return ConversationHandler.END

# Новые обработчики для пользовательского интерфейса
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /help"""
    await update.message.reply_text(
        DIALOG_TEXTS['help']['user_commands'],
        parse_mode='HTML'
    )

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /menu"""
    await bot_instance.user_interface.show_user_menu(update, context)

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /profile"""
    # Создаем факе callback_query для совместимости
    class FakeCallbackQuery:
        def __init__(self, user, message):
            self.from_user = user
            self.message = message
        async def answer(self): pass
        async def edit_message_text(self, text, **kwargs):
            await self.message.reply_text(text, **kwargs)
    
    fake_query = FakeCallbackQuery(update.effective_user, update.message)
    update.callback_query = fake_query
    
    await bot_instance.user_interface.show_user_profile(update, context)

# Обработчики для менеджеров
async def manager_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /manager"""
    await bot_instance.manager_interface.request_auth(update, context)

async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка текстовых сообщений вне диалогов"""
    # Проверяем, не ожидаем ли мы пароль менеджера
    if await bot_instance.manager_interface.handle_password(update, context):
        return
    
    # Проверяем, не ожидаем ли мы сообщение для рассылки
    if await bot_instance.manager_interface.handle_broadcast_message(update, context):
        return
    
    # Обычная обработка сообщений
    await update.message.reply_text(
        "🤖 Привет! Для начала работы напиши /start\n\n"
        "📝 Доступные команды:\n"
        "/start - Начать регистрацию\n"
        "/menu - Открыть меню\n"
        "/profile - Мой профиль\n"
        "/help - Помощь"
    )

# Обработчики callback данных
async def handle_user_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка callback'ов пользовательского интерфейса"""
    query = update.callback_query
    data = query.data
    
    if data == "user_menu":
        await bot_instance.user_interface.show_user_menu(update, context)
    elif data == "user_profile":
        await bot_instance.user_interface.show_user_profile(update, context)
    elif data == "user_help":
        await bot_instance.user_interface.show_user_help(update, context)
    elif data == "user_settings":
        await bot_instance.user_interface.show_user_settings(update, context)
    elif data.startswith("user_toggle_newsletter_"):
        await bot_instance.user_interface.toggle_newsletter(update, context)
    elif data == "user_delete_confirm":
        await bot_instance.user_interface.confirm_delete_account(update, context)
    elif data == "user_delete_confirmed":
        await bot_instance.user_interface.delete_user_account(update, context)
    elif data == "user_support":
        await bot_instance.user_interface.show_support_info(update, context)
    elif data == "user_materials":
        await bot_instance.user_interface.show_materials(update, context)

async def handle_manager_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка callback'ов менеджерского интерфейса"""
    query = update.callback_query
    data = query.data
    
    if data == "mgr_menu":
        await bot_instance.manager_interface.show_manager_menu(update, context)
    elif data == "mgr_stats":
        await bot_instance.manager_interface.show_detailed_stats(update, context)
    elif data == "mgr_users" or data.startswith("mgr_users_page_"):
        page = 1
        if data.startswith("mgr_users_page_"):
            page = int(data.split("_")[-1])
        await bot_instance.manager_interface.show_users_list(update, context, page)
    elif data == "mgr_export":
        await bot_instance.manager_interface.export_users_data(update, context)
    elif data == "mgr_broadcast":
        await bot_instance.manager_interface.start_broadcast(update, context)
    elif data == "mgr_broadcast_confirm":
        await bot_instance.manager_interface.confirm_broadcast(update, context)
    elif data == "mgr_broadcast_cancel":
        await bot_instance.manager_interface.cancel_broadcast(update, context)
    elif data == "mgr_settings":
        await bot_instance.manager_interface.show_bot_settings(update, context)
    elif data == "mgr_logout":
        await bot_instance.manager_interface.logout(update, context)
    elif data == "mgr_clear":
        await clear_manager_data(query)
    elif data == "confirm_clear":
        await confirm_clear_data(query)
    elif data == "manager_cancel":
        await manager_cancel(query)

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Простая статистика для администратора"""
    conn = sqlite3.connect(bot_instance.db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE newsletter_consent = 1")
    newsletter_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE english_experience = 'Да'")
    experienced_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT AVG(age) FROM users WHERE age IS NOT NULL")
    avg_age = cursor.fetchone()[0]
    
    conn.close()
    
    stats_text = (
        f"📊 <b>Статистика английского клуба:</b>\n\n"
        f"👥 Всего участников: {total_users}\n"
        f"📧 Подписаны на рассылку: {newsletter_users}\n"
        f"📚 С опытом изучения: {experienced_users}\n"
        f"🆕 Новички: {total_users - experienced_users}"
    )
    
    if avg_age:
        stats_text += f"\n🎂 Средний возраст: {avg_age:.1f} лет"
    
    await update.message.reply_text(stats_text, parse_mode='HTML')

# Устаревшие обработчики (оставляем для совместимости)
async def manager_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Менеджерское меню - перенаправляем на новый интерфейс"""
    await manager_command(update, context)

async def handle_manager_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка callback'ов менеджерского меню - перенаправляем на новый интерфейс"""
    await handle_manager_callbacks(update, context)

async def show_manager_stats(query) -> None:
    """Показать детальную статистику"""
    conn = sqlite3.connect(bot_instance.db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE newsletter_consent = 1")
    newsletter_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE english_experience = 'Да'")
    experienced_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT AVG(age) FROM users WHERE age IS NOT NULL")
    avg_age = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE registration_date >= date('now', '-7 days')")
    new_week = cursor.fetchone()[0]
    
    conn.close()
    
    stats_text = (
        f"📊 <b>Детальная статистика:</b>\n\n"
        f"👥 Всего участников: {total_users}\n"
        f"📧 Подписаны на рассылку: {newsletter_users}\n"
        f"📚 С опытом изучения: {experienced_users}\n"
        f"🆕 Новички: {total_users - experienced_users}\n"
        f"📅 Новые за неделю: {new_week}"
    )
    
    if avg_age:
        stats_text += f"\n🎂 Средний возраст: {avg_age:.1f} лет"
    
    await query.edit_message_text(stats_text, parse_mode='HTML')

async def show_manager_users(query) -> None:
    """Показать список пользователей"""
    conn = sqlite3.connect(bot_instance.db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT name, age, english_experience, newsletter_consent, registration_date
        FROM users ORDER BY registration_date DESC LIMIT 10
    ''')
    
    users = cursor.fetchall()
    conn.close()
    
    if not users:
        await query.edit_message_text("📭 Пользователи не найдены")
        return
    
    users_text = "👥 <b>Последние 10 пользователей:</b>\n\n"
    
    for user in users:
        name, age, experience, newsletter, reg_date = user
        newsletter_status = "✅" if newsletter else "❌"
        users_text += f"👤 <b>{name}</b>, {age} лет\n"
        users_text += f"   📚 Опыт: {experience}\n"
        users_text += f"   📧 Рассылка: {newsletter_status}\n"
        users_text += f"   📅 {reg_date}\n\n"
    
    await query.edit_message_text(users_text, parse_mode='HTML')

async def export_manager_data(query) -> None:
    """Экспорт данных пользователей"""
    conn = sqlite3.connect(bot_instance.db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT telegram_id, username, name, age, english_experience, 
               data_consent, newsletter_consent, registration_date
        FROM users ORDER BY registration_date DESC
    ''')
    
    users = cursor.fetchall()
    conn.close()
    
    if not users:
        await query.edit_message_text("📭 Нет пользователей для экспорта")
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
    
    await query.edit_message_text(
        f"✅ <b>Данные экспортированы!</b>\n\n"
        f"📁 Файл: {filename}\n"
        f"📊 Пользователей: {len(users)}",
        parse_mode='HTML'
    )
    
    # Отправляем файл
    await query.message.reply_document(
        document=open(filename, 'rb'),
        caption=f"📊 Экспорт пользователей ({len(users)} записей)"
    )

async def clear_manager_data(query) -> None:
    """Запрос подтверждения на очистку БД"""
    keyboard = [
        [InlineKeyboardButton("✅ Да, удалить все", callback_data="confirm_clear")],
        [InlineKeyboardButton("❌ Отмена", callback_data="manager_cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "⚠️ <b>ВНИМАНИЕ!</b>\n\n"
        "Вы собираетесь удалить ВСЕ данные пользователей из базы данных.\n"
        "Это действие нельзя отменить!\n\n"
        "Продолжить?",
        parse_mode='HTML',
        reply_markup=reply_markup
    )

async def confirm_clear_data(query) -> None:
    """Подтверждение очистки БД"""
    conn = sqlite3.connect(bot_instance.db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users")
    conn.commit()
    conn.close()
    
    await query.edit_message_text(
        "✅ <b>База данных очищена!</b>\n\n"
        "Все данные пользователей удалены.",
        parse_mode='HTML'
    )

async def manager_cancel(query) -> None:
    """Отмена операции"""
    await query.edit_message_text("❌ Операция отменена")

def main() -> None:
    """Главная функция запуска бота"""
    if BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
        print("❌ Ошибка: Необходимо установить BOT_TOKEN!")
        print("Получите токен у @BotFather и установите переменную окружения BOT_TOKEN")
        return
    
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Создаем обработчик диалога
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            WAITING_NAME: [
                CallbackQueryHandler(handle_data_consent, pattern="^data_consent_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)
            ],
            WAITING_EXPERIENCE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_experience)
            ],
            WAITING_AGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)
            ],
            FINAL_CONSENT: [
                CallbackQueryHandler(final_consent, pattern="^newsletter_")
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    # Добавляем обработчики
    application.add_handler(conv_handler)
    
    # Пользовательские команды
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('menu', menu_command))
    application.add_handler(CommandHandler('profile', profile_command))
    
    # Менеджерские команды
    application.add_handler(CommandHandler('admin', admin_stats))
    application.add_handler(CommandHandler('manager', manager_command))
    
    # Обработчики callback'ов
    application.add_handler(CallbackQueryHandler(handle_user_callbacks, pattern="^user_"))
    application.add_handler(CallbackQueryHandler(handle_manager_callbacks, pattern="^mgr_"))
    
    # Старые обработчики для совместимости
    application.add_handler(CallbackQueryHandler(handle_manager_callback, pattern="^manager_"))
    application.add_handler(CallbackQueryHandler(confirm_clear_data, pattern="^confirm_clear$"))
    application.add_handler(CallbackQueryHandler(manager_cancel, pattern="^manager_cancel$"))
    
    # Обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))
    
    # Запускаем бота
    logger.info("🤖 Бот запущен! Нажмите Ctrl+C для остановки.")
    print("🤖 Бот запущен! Нажмите Ctrl+C для остановки.")
    
    # Очищаем истекшие сессии при запуске
    expired_count = auth_manager.cleanup_expired_sessions()
    if expired_count > 0:
        logger.info(f"Очищено {expired_count} истекших сессий")
    
    application.run_polling()

if __name__ == '__main__':
    main()