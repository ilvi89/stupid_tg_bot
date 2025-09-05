#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Интерфейс пользователя - обработчики для обычных пользователей
"""

import sqlite3
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from dialog_config import DIALOG_TEXTS, BUTTONS, SETTINGS

class UserInterface:
    """Класс для обработки взаимодействия с обычными пользователями"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    async def show_user_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать главное меню пользователя"""
        keyboard = [
            [InlineKeyboardButton(BUTTONS['user_menu']['profile'], callback_data="user_profile")],
            [InlineKeyboardButton(BUTTONS['user_menu']['help'], callback_data="user_help")],
            [InlineKeyboardButton(BUTTONS['user_menu']['settings'], callback_data="user_settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        menu_text = (
            "🇬🇧 <b>Главное меню</b>\n\n"
            "Добро пожаловать! Выберите действие:"
        )
        
        if update.message:
            await update.message.reply_text(menu_text, parse_mode='HTML', reply_markup=reply_markup)
        else:
            await update.callback_query.edit_message_text(menu_text, parse_mode='HTML', reply_markup=reply_markup)
    
    async def show_user_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать профиль пользователя"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        user_data = self._get_user_data(user_id)
        
        if not user_data:
            await query.edit_message_text(
                "❌ <b>Профиль не найден</b>\n\n"
                "Вы еще не прошли регистрацию. Нажмите /start для начала!",
                parse_mode='HTML'
            )
            return
        
        # Форматируем данные профиля
        newsletter_status = "✅ Включена" if user_data['newsletter_consent'] else "❌ Отключена"
        
        profile_text = (
            f"👤 <b>Ваш профиль</b>\n\n"
            f"<b>Имя:</b> {user_data['name']}\n"
            f"<b>Возраст:</b> {user_data['age']} лет\n"
            f"<b>Опыт изучения английского:</b> {user_data['english_experience']}\n"
            f"<b>Рассылка:</b> {newsletter_status}\n"
            f"<b>Дата регистрации:</b> {user_data['registration_date']}\n\n"
            f"📊 <b>Статистика:</b>\n"
            f"• Дней в клубе: {self._calculate_days_in_club(user_data['registration_date'])}\n"
            f"• Telegram ID: {user_data['telegram_id']}"
        )
        
        keyboard = [
            [InlineKeyboardButton("✏️ Изменить данные", callback_data="user_edit_profile")],
            [InlineKeyboardButton("🔄 Обновить профиль", callback_data="user_profile")],
            [InlineKeyboardButton("🔙 Назад в меню", callback_data="user_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(profile_text, parse_mode='HTML', reply_markup=reply_markup)
    
    async def show_user_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать справку для пользователя"""
        query = update.callback_query
        await query.answer()
        
        help_text = DIALOG_TEXTS['help']['user_commands']
        
        keyboard = [
            [InlineKeyboardButton("📞 Связаться с поддержкой", callback_data="user_support")],
            [InlineKeyboardButton("📚 Полезные материалы", callback_data="user_materials")],
            [InlineKeyboardButton("🔙 Назад в меню", callback_data="user_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(help_text, parse_mode='HTML', reply_markup=reply_markup)
    
    async def show_user_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать настройки пользователя"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        user_data = self._get_user_data(user_id)
        
        if not user_data:
            await query.edit_message_text(
                "❌ Для доступа к настройкам необходимо пройти регистрацию. Нажмите /start",
                parse_mode='HTML'
            )
            return
        
        newsletter_text = "✅ Включена" if user_data['newsletter_consent'] else "❌ Отключена"
        newsletter_action = "Отключить" if user_data['newsletter_consent'] else "Включить"
        
        settings_text = (
            f"⚙️ <b>Настройки</b>\n\n"
            f"<b>Текущие настройки:</b>\n"
            f"• Рассылка: {newsletter_text}\n"
            f"• Язык интерфейса: Русский\n"
            f"• Уведомления: Включены\n\n"
            f"Выберите что хотите изменить:"
        )
        
        keyboard = [
            [InlineKeyboardButton(f"📧 {newsletter_action} рассылку", 
                                callback_data=f"user_toggle_newsletter_{not user_data['newsletter_consent']}")],
            [InlineKeyboardButton("🗑️ Удалить мой аккаунт", callback_data="user_delete_confirm")],
            [InlineKeyboardButton("🔙 Назад в меню", callback_data="user_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(settings_text, parse_mode='HTML', reply_markup=reply_markup)
    
    async def toggle_newsletter(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Переключить подписку на рассылку"""
        query = update.callback_query
        await query.answer()
        
        # Извлекаем новое значение из callback_data
        new_value = query.data.split('_')[-1] == 'True'
        user_id = query.from_user.id
        
        success = self._update_newsletter_consent(user_id, new_value)
        
        if success:
            status_text = "включена" if new_value else "отключена"
            await query.edit_message_text(
                f"✅ <b>Настройки обновлены!</b>\n\n"
                f"Рассылка {status_text}.",
                parse_mode='HTML'
            )
            
            # Возвращаемся к настройкам через 2 секунды
            import asyncio
            await asyncio.sleep(2)
            await self.show_user_settings(update, context)
        else:
            await query.edit_message_text(
                "❌ Произошла ошибка при обновлении настроек. Попробуйте позже.",
                parse_mode='HTML'
            )
    
    async def confirm_delete_account(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Подтверждение удаления аккаунта"""
        query = update.callback_query
        await query.answer()
        
        confirm_text = (
            "⚠️ <b>ВНИМАНИЕ!</b>\n\n"
            "Вы собираетесь <b>полностью удалить</b> свой аккаунт из системы.\n"
            "Это действие нельзя отменить!\n\n"
            "Будут удалены:\n"
            "• Все ваши персональные данные\n"
            "• История участия в клубе\n"
            "• Настройки профиля\n\n"
            "Вы уверены, что хотите продолжить?"
        )
        
        keyboard = [
            [InlineKeyboardButton("🗑️ Да, удалить аккаунт", callback_data="user_delete_confirmed")],
            [InlineKeyboardButton("❌ Отмена", callback_data="user_settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(confirm_text, parse_mode='HTML', reply_markup=reply_markup)
    
    async def delete_user_account(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Удаление аккаунта пользователя"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        success = self._delete_user_data(user_id)
        
        if success:
            await query.edit_message_text(
                "✅ <b>Аккаунт удален</b>\n\n"
                "Ваши данные полностью удалены из системы.\n"
                "Спасибо за участие в английском клубе!\n\n"
                "Если захотите вернуться, просто нажмите /start",
                parse_mode='HTML'
            )
        else:
            await query.edit_message_text(
                "❌ Произошла ошибка при удалении аккаунта. Обратитесь к администратору.",
                parse_mode='HTML'
            )
    
    async def show_support_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать информацию о поддержке"""
        query = update.callback_query
        await query.answer()
        
        support_text = (
            "📞 <b>Поддержка</b>\n\n"
            "Если у вас есть вопросы или проблемы, вы можете:\n\n"
            "1. Написать администратору: @admin_username\n"
            "2. Отправить email: support@englishclub.com\n"
            "3. Позвонить: +7 (XXX) XXX-XX-XX\n\n"
            "⏰ <b>Время работы поддержки:</b>\n"
            "Пн-Пт: 9:00 - 18:00\n"
            "Сб-Вс: 10:00 - 16:00\n\n"
            "Мы стараемся отвечать в течение 24 часов!"
        )
        
        keyboard = [
            [InlineKeyboardButton("📧 Написать в поддержку", callback_data="user_write_support")],
            [InlineKeyboardButton("🔙 Назад к справке", callback_data="user_help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(support_text, parse_mode='HTML', reply_markup=reply_markup)
    
    async def show_materials(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать полезные материалы"""
        query = update.callback_query
        await query.answer()
        
        materials_text = (
            "📚 <b>Полезные материалы</b>\n\n"
            "🎯 <b>Для начинающих:</b>\n"
            "• Базовая грамматика\n"
            "• Первые 1000 слов\n"
            "• Простые диалоги\n\n"
            "📈 <b>Средний уровень:</b>\n"
            "• Времена в английском\n"
            "• Деловая лексика\n"
            "• Аудирование\n\n"
            "🏆 <b>Продвинутый уровень:</b>\n"
            "• Идиомы и фразеологизмы\n"
            "• Подготовка к экзаменам\n"
            "• Разговорная практика\n\n"
            "📱 <b>Мобильные приложения:</b>\n"
            "• Duolingo\n"
            "• Anki для карточек\n"
            "• BBC Learning English"
        )
        
        keyboard = [
            [InlineKeyboardButton("📖 Скачать материалы", callback_data="user_download_materials")],
            [InlineKeyboardButton("🎮 Игры и тесты", callback_data="user_games")],
            [InlineKeyboardButton("🔙 Назад к справке", callback_data="user_help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(materials_text, parse_mode='HTML', reply_markup=reply_markup)
    
    def _get_user_data(self, user_id: int) -> dict:
        """Получить данные пользователя из БД"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT telegram_id, username, name, age, english_experience, 
                       data_consent, newsletter_consent, registration_date
                FROM users WHERE telegram_id = ?
            ''', (user_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'telegram_id': result[0],
                    'username': result[1],
                    'name': result[2],
                    'age': result[3],
                    'english_experience': result[4],
                    'data_consent': bool(result[5]),
                    'newsletter_consent': bool(result[6]),
                    'registration_date': result[7]
                }
            return None
            
        except Exception as e:
            print(f"Ошибка при получении данных пользователя: {e}")
            return None
    
    def _update_newsletter_consent(self, user_id: int, consent: bool) -> bool:
        """Обновить согласие на рассылку"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE users SET newsletter_consent = ? WHERE telegram_id = ?
            ''', (consent, user_id))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Ошибка при обновлении согласия на рассылку: {e}")
            return False
    
    def _delete_user_data(self, user_id: int) -> bool:
        """Удалить данные пользователя из БД"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM users WHERE telegram_id = ?', (user_id,))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Ошибка при удалении данных пользователя: {e}")
            return False
    
    def _calculate_days_in_club(self, registration_date: str) -> int:
        """Подсчитать количество дней в клубе"""
        try:
            reg_date = datetime.strptime(registration_date.split()[0], '%Y-%m-%d')
            today = datetime.now()
            return (today - reg_date).days
        except:
            return 0