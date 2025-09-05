#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Простой Telegram-бот для английского клуба
Реализует диалоговый сценарий знакомства с новыми участниками
"""

import logging
import sqlite3
import os
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

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния диалога
WAITING_NAME, WAITING_EXPERIENCE, WAITING_AGE, FINAL_CONSENT = range(4)

# Токен бота (получить у @BotFather)
BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')

class EnglishClubBot:
    def __init__(self):
        self.db_path = 'english_club.db'
        self.init_database()
    
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
        [InlineKeyboardButton("✅ Согласен на обработку данных", callback_data="data_consent_yes")],
        [InlineKeyboardButton("❌ Не согласен", callback_data="data_consent_no")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        "🇬🇧 <b>Привет! Добро пожаловать в английский клуб!</b>\n\n"
        "Давай знакомиться! Как тебя зовут?\n\n"
        "Но сначала мне нужно получить твое согласие на обработку персональных данных:"
    )
    
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
            "✅ <b>Отлично! Согласие на обработку данных получено.</b>\n\n"
            "Теперь скажи, как тебя зовут? 😊",
            parse_mode='HTML'
        )
        
        return WAITING_NAME
    else:
        await query.edit_message_text(
            "❌ К сожалению, без согласия на обработку данных я не могу продолжить регистрацию.\n\n"
            "Если передумаешь, просто напиши /start снова! 😊"
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
        [KeyboardButton("✅ Да, изучал английский")],
        [KeyboardButton("❌ Нет, только начинаю")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    await update.message.reply_text(
        f"Приятно познакомиться, <b>{name}</b>! 😊\n\n"
        f"Ты уже изучал английский раньше?",
        parse_mode='HTML',
        reply_markup=reply_markup
    )
    
    return WAITING_EXPERIENCE

async def get_experience(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение информации об опыте и переход к вопросу о возрасте"""
    experience = update.message.text.strip()
    
    if "да" in experience.lower() or "✅" in experience:
        context.user_data['english_experience'] = "Да"
        response = "Отлично! 👍"
    else:
        context.user_data['english_experience'] = "Нет"
        response = "Замечательно! Все когда-то начинали! 🌟"
    
    await update.message.reply_text(
        f"{response}\n\n"
        f"Сколько тебе лет? (Просто напиши цифру)",
        reply_markup=None  # Убираем клавиатуру
    )
    
    return WAITING_AGE

async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение возраста и переход к финальному согласию"""
    try:
        age = int(update.message.text.strip())
        if age < 5 or age > 100:
            await update.message.reply_text(
                "Пожалуйста, укажи реальный возраст (от 5 до 100 лет) 😊"
            )
            return WAITING_AGE
        
        context.user_data['age'] = age
        
        # Создаем клавиатуру для финального согласия
        keyboard = [
            [InlineKeyboardButton("✅ Даю согласие на рассылку", callback_data="newsletter_yes")],
            [InlineKeyboardButton("❌ Не хочу получать рассылку", callback_data="newsletter_no")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Отправляем СНАОП (если файл существует)
        snaop_file = "СнаОП с прочерками.pdf"
        if os.path.exists(snaop_file):
            await update.message.reply_document(
                document=open(snaop_file, 'rb'),
                caption="📄 Согласие на обработку персональных данных"
            )
        
        await update.message.reply_text(
            f"Отлично, {context.user_data['name']}! 🎉\n\n"
            f"<b>Включи уведомления в этом боте, чтобы первым получать новости, "
            f"полезности и анонсы активностей клуба!</b>\n\n"
            f"Для этого:\n"
            f"1. Нажми на название бота вверху чата\n"
            f"2. Включи уведомления 🔔\n\n"
            f"И последний вопрос:",
            parse_mode='HTML',
            reply_markup=reply_markup
        )
        
        return FINAL_CONSENT
        
    except ValueError:
        await update.message.reply_text(
            "Пожалуйста, напиши свой возраст цифрами (например: 25) 😊"
        )
        return WAITING_AGE

async def final_consent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка финального согласия и завершение регистрации"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "newsletter_yes":
        context.user_data['newsletter_consent'] = True
        consent_text = "✅ <b>Отлично! Ты будешь получать все новости и анонсы!</b>"
    else:
        context.user_data['newsletter_consent'] = False
        consent_text = "✅ <b>Хорошо, рассылку отправлять не буду.</b>"
    
    # Сохраняем все данные в БД
    bot_instance.save_user_data(context.user_data)
    
    # Отправляем согласие на рассылку (если файл существует)
    consent_file = "Согласие_на_рассылку_информационных_и_рекламных_сообщений_с_прочерками.pdf"
    if os.path.exists(consent_file) and context.user_data.get('newsletter_consent'):
        await query.message.reply_document(
            document=open(consent_file, 'rb'),
            caption="📄 Согласие на получение рассылки"
        )
    
    final_message = (
        f"{consent_text}\n\n"
        f"🎉 <b>Регистрация завершена!</b>\n\n"
        f"<b>Твои данные:</b>\n"
        f"• Имя: {context.user_data['name']}\n"
        f"• Возраст: {context.user_data['age']} лет\n"
        f"• Опыт изучения: {context.user_data['english_experience']}\n"
        f"• Согласие на данные: ✅\n"
        f"• Согласие на рассылку: {'✅' if context.user_data.get('newsletter_consent') else '❌'}\n\n"
        f"Добро пожаловать в наш английский клуб! 🇬🇧\n"
        f"Скоро ты получишь информацию о ближайших занятиях! 📚"
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
        "Регистрация отменена. Если захочешь зарегистрироваться, просто напиши /start! 😊"
    )
    context.user_data.clear()
    return ConversationHandler.END

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
    
    conn.close()
    
    stats_text = (
        f"📊 <b>Статистика английского клуба:</b>\n\n"
        f"👥 Всего участников: {total_users}\n"
        f"📧 Подписаны на рассылку: {newsletter_users}\n"
        f"📚 С опытом изучения: {experienced_users}\n"
        f"🆕 Новички: {total_users - experienced_users}"
    )
    
    await update.message.reply_text(stats_text, parse_mode='HTML')

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
    application.add_handler(CommandHandler('admin', admin_stats))
    
    # Запускаем бота
    print("🤖 Бот запущен! Нажмите Ctrl+C для остановки.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()