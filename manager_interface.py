#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Интерфейс менеджера - расширенная панель управления ботом
"""

import sqlite3
import csv
import os
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError
from dialog_config import MANAGER_TEXTS, BUTTONS, SETTINGS
from auth_manager import auth_manager

class ManagerInterface:
    """Класс для обработки интерфейса менеджера"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.broadcast_sessions = {}  # user_id -> broadcast_data
    
    async def request_auth(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Запрос авторизации менеджера"""
        user_id = update.effective_user.id
        
        if auth_manager.is_authorized(user_id):
            await self.show_manager_menu(update, context)
            return
        
        await update.message.reply_text(
            MANAGER_TEXTS['auth']['request_password'],
            parse_mode='HTML'
        )
        
        # Устанавливаем состояние ожидания пароля
        context.user_data['awaiting_manager_password'] = True
    
    async def handle_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Обработка введенного пароля"""
        if not context.user_data.get('awaiting_manager_password'):
            return False
        
        user_id = update.effective_user.id
        password = update.message.text.strip()
        
        # Удаляем сообщение с паролем для безопасности
        try:
            await update.message.delete()
        except:
            pass
        
        if auth_manager.authenticate(user_id, password):
            await update.message.reply_text(
                MANAGER_TEXTS['auth']['access_granted'],
                parse_mode='HTML'
            )
            context.user_data['awaiting_manager_password'] = False
            await self.show_manager_menu(update, context)
            return True
        else:
            await update.message.reply_text(
                MANAGER_TEXTS['auth']['invalid_password'],
                parse_mode='HTML'
            )
            context.user_data['awaiting_manager_password'] = False
            return False
    
    async def check_auth(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Проверка авторизации перед выполнением действий"""
        user_id = update.effective_user.id
        
        if not auth_manager.is_authorized(user_id):
            if update.callback_query:
                await update.callback_query.answer(
                    MANAGER_TEXTS['auth']['not_authorized'], 
                    show_alert=True
                )
            else:
                await update.message.reply_text(
                    MANAGER_TEXTS['auth']['not_authorized'],
                    parse_mode='HTML'
                )
            return False
        return True
    
    async def show_manager_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать главное меню менеджера"""
        if not await self.check_auth(update, context):
            return
        
        user_id = update.effective_user.id
        session_info = auth_manager.get_session_info(user_id)
        time_left = auth_manager.get_session_time_left(user_id)
        
        keyboard = [
            [InlineKeyboardButton(BUTTONS['manager_menu']['stats'], callback_data="mgr_stats")],
            [InlineKeyboardButton(BUTTONS['manager_menu']['users'], callback_data="mgr_users"),
             InlineKeyboardButton(BUTTONS['manager_menu']['export'], callback_data="mgr_export")],
            [InlineKeyboardButton(BUTTONS['manager_menu']['broadcast'], callback_data="mgr_broadcast")],
            [InlineKeyboardButton(BUTTONS['manager_menu']['settings'], callback_data="mgr_settings"),
             InlineKeyboardButton(BUTTONS['manager_menu']['clear'], callback_data="mgr_clear")],
            [InlineKeyboardButton("🚪 Выход", callback_data="mgr_logout")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        menu_text = (
            f"{MANAGER_TEXTS['menu']['title']}\n\n"
            f"{MANAGER_TEXTS['menu']['description']}\n\n"
            f"⏰ Сессия истекает через: {time_left // 60} мин {time_left % 60} сек\n"
            f"👤 Активных сессий: {auth_manager.get_active_sessions_count()}"
        )
        
        if update.message:
            await update.message.reply_text(menu_text, parse_mode='HTML', reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.edit_message_text(menu_text, parse_mode='HTML', reply_markup=reply_markup)
    
    async def show_detailed_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать детальную статистику"""
        if not await self.check_auth(update, context):
            return
        
        query = update.callback_query
        await query.answer()
        
        stats = self._get_detailed_stats()
        
        stats_text = (
            f"{MANAGER_TEXTS['stats']['detailed_title']}\n\n"
            f"👥 Всего участников: {stats['total']}\n"
            f"📧 Подписаны на рассылку: {stats['newsletter']}\n"
            f"📚 С опытом изучения: {stats['experienced']}\n"
            f"🆕 Новички: {stats['beginners']}\n"
            f"📅 Новые за неделю: {stats['week_new']}\n"
            f"📅 Новые за месяц: {stats['month_new']}\n"
            f"🎂 Средний возраст: {stats['avg_age']:.1f} лет\n\n"
            f"📊 <b>Возрастное распределение:</b>\n"
        )
        
        for age_group, count in stats['age_groups'].items():
            stats_text += f"• {age_group}: {count} чел.\n"
        
        stats_text += f"\n📈 <b>Регистрации по дням (последние 7 дней):</b>\n"
        for date, count in stats['daily_registrations'].items():
            stats_text += f"• {date}: {count} чел.\n"
        
        keyboard = [
            [InlineKeyboardButton("📊 Экспорт статистики", callback_data="mgr_export_stats")],
            [InlineKeyboardButton("🔄 Обновить", callback_data="mgr_stats")],
            [InlineKeyboardButton("🔙 Назад", callback_data="mgr_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(stats_text, parse_mode='HTML', reply_markup=reply_markup)
    
    async def show_users_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 1) -> None:
        """Показать список пользователей с пагинацией"""
        if not await self.check_auth(update, context):
            return
        
        query = update.callback_query
        await query.answer()
        
        users_per_page = SETTINGS['pagination']['users_per_page']
        offset = (page - 1) * users_per_page
        
        users, total_count = self._get_users_page(offset, users_per_page)
        
        if not users:
            await query.edit_message_text(
                MANAGER_TEXTS['users']['no_users'],
                parse_mode='HTML'
            )
            return
        
        users_text = f"👥 <b>Пользователи (стр. {page})</b>\n\n"
        users_text += f"Показано {len(users)} из {total_count}\n\n"
        
        for user in users:
            newsletter_status = "✅" if user['newsletter_consent'] else "❌"
            users_text += (
                f"👤 <b>{user['name']}</b> ({user['age']} лет)\n"
                f"   📚 Опыт: {user['english_experience']}\n"
                f"   📧 Рассылка: {newsletter_status}\n"
                f"   📅 {user['registration_date']}\n"
                f"   🆔 ID: {user['telegram_id']}\n\n"
            )
        
        # Создаем кнопки пагинации
        keyboard = []
        nav_buttons = []
        
        if page > 1:
            nav_buttons.append(InlineKeyboardButton("⬅️ Предыдущая", callback_data=f"mgr_users_page_{page-1}"))
        
        total_pages = (total_count + users_per_page - 1) // users_per_page
        if page < total_pages:
            nav_buttons.append(InlineKeyboardButton("Следующая ➡️", callback_data=f"mgr_users_page_{page+1}"))
        
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        keyboard.extend([
            [InlineKeyboardButton("🔍 Поиск пользователя", callback_data="mgr_search_user")],
            [InlineKeyboardButton("📊 Статистика пользователей", callback_data="mgr_user_stats")],
            [InlineKeyboardButton("🔙 Назад", callback_data="mgr_menu")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(users_text, parse_mode='HTML', reply_markup=reply_markup)
    
    async def export_users_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Экспорт данных пользователей"""
        if not await self.check_auth(update, context):
            return
        
        query = update.callback_query
        await query.answer("Готовлю экспорт...")
        
        users = self._get_all_users()
        
        if not users:
            await query.edit_message_text(
                MANAGER_TEXTS['export']['no_data'],
                parse_mode='HTML'
            )
            return
        
        filename = f"users_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                'Telegram ID', 'Username', 'Имя', 'Возраст', 'Опыт изучения',
                'Согласие на данные', 'Согласие на рассылку', 'Дата регистрации'
            ])
            
            for user in users:
                writer.writerow([
                    user['telegram_id'], user['username'], user['name'],
                    user['age'], user['english_experience'],
                    'Да' if user['data_consent'] else 'Нет',
                    'Да' if user['newsletter_consent'] else 'Нет',
                    user['registration_date']
                ])
        
        success_text = MANAGER_TEXTS['export']['success'].format(
            filename=filename, count=len(users)
        )
        
        await query.edit_message_text(success_text, parse_mode='HTML')
        
        # Отправляем файл
        try:
            await query.message.reply_document(
                document=open(filename, 'rb'),
                caption=MANAGER_TEXTS['export']['caption'].format(count=len(users))
            )
        except Exception as e:
            await query.message.reply_text(f"❌ Ошибка при отправке файла: {e}")
        finally:
            # Удаляем временный файл
            try:
                os.remove(filename)
            except:
                pass
    
    async def start_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начать процесс рассылки"""
        if not await self.check_auth(update, context):
            return
        
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        await query.edit_message_text(
            MANAGER_TEXTS['broadcast']['request_message'],
            parse_mode='HTML'
        )
        
        # Сохраняем состояние ожидания сообщения для рассылки
        context.user_data['awaiting_broadcast_message'] = True
    
    async def handle_broadcast_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Обработка сообщения для рассылки"""
        if not context.user_data.get('awaiting_broadcast_message'):
            return False
        
        if not await self.check_auth(update, context):
            return True
        
        user_id = update.effective_user.id
        message_text = update.message.text
        
        if len(message_text) > SETTINGS['text_limits']['max_message_length']:
            await update.message.reply_text(
                f"❌ Сообщение слишком длинное! Максимум {SETTINGS['text_limits']['max_message_length']} символов."
            )
            return True
        
        # Получаем количество получателей
        recipients_count = self._get_newsletter_subscribers_count()
        
        confirm_text = MANAGER_TEXTS['broadcast']['confirm_template'].format(
            message=message_text,
            count=recipients_count
        )
        
        keyboard = [
            [InlineKeyboardButton("📤 Отправить", callback_data="mgr_broadcast_confirm")],
            [InlineKeyboardButton("❌ Отмена", callback_data="mgr_broadcast_cancel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Сохраняем сообщение для рассылки
        self.broadcast_sessions[user_id] = {
            'message': message_text,
            'recipients_count': recipients_count
        }
        
        context.user_data['awaiting_broadcast_message'] = False
        
        await update.message.reply_text(confirm_text, parse_mode='HTML', reply_markup=reply_markup)
        return True
    
    async def confirm_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Подтверждение и выполнение рассылки"""
        if not await self.check_auth(update, context):
            return
        
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        if user_id not in self.broadcast_sessions:
            await query.edit_message_text("❌ Сессия рассылки истекла. Начните заново.")
            return
        
        broadcast_data = self.broadcast_sessions[user_id]
        message_text = broadcast_data['message']
        
        await query.edit_message_text(MANAGER_TEXTS['broadcast']['sending'])
        
        # Получаем список получателей
        recipients = self._get_newsletter_subscribers()
        
        sent_count = 0
        failed_count = 0
        
        for recipient in recipients:
            try:
                await context.bot.send_message(
                    chat_id=recipient['telegram_id'],
                    text=f"📢 <b>Сообщение от английского клуба:</b>\n\n{message_text}",
                    parse_mode='HTML'
                )
                sent_count += 1
                
                # Пауза между отправками для избежания лимитов
                await asyncio.sleep(0.1)
                
            except TelegramError as e:
                failed_count += 1
                print(f"Ошибка отправки сообщения пользователю {recipient['telegram_id']}: {e}")
        
        success_text = MANAGER_TEXTS['broadcast']['success'].format(
            sent=sent_count, total=len(recipients)
        )
        
        if failed_count > 0:
            success_text += f"\n⚠️ Не доставлено: {failed_count}"
        
        await query.edit_message_text(success_text, parse_mode='HTML')
        
        # Очищаем сессию рассылки
        del self.broadcast_sessions[user_id]
    
    async def cancel_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Отмена рассылки"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if user_id in self.broadcast_sessions:
            del self.broadcast_sessions[user_id]
        
        await query.edit_message_text(MANAGER_TEXTS['broadcast']['cancelled'])
    
    async def show_bot_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать настройки бота"""
        if not await self.check_auth(update, context):
            return
        
        query = update.callback_query
        await query.answer()
        
        settings_text = (
            "⚙️ <b>Настройки бота</b>\n\n"
            "<b>Текущие настройки:</b>\n"
            f"• База данных: {self.db_path}\n"
            f"• Таймаут сессии: {auth_manager.session_timeout // 60} мин\n"
            f"• Пользователей на странице: {SETTINGS['pagination']['users_per_page']}\n"
            f"• Максимальная длина имени: {SETTINGS['text_limits']['max_name_length']}\n"
            f"• Лимиты возраста: {SETTINGS['age_limits']['min']}-{SETTINGS['age_limits']['max']}\n\n"
            "<b>Статистика системы:</b>\n"
            f"• Размер БД: {self._get_db_size():.2f} MB\n"
            f"• Активных сессий: {auth_manager.get_active_sessions_count()}\n"
            f"• Время работы бота: {self._get_uptime()}"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔄 Перезагрузить конфиг", callback_data="mgr_reload_config")],
            [InlineKeyboardButton("🧹 Очистить сессии", callback_data="mgr_cleanup_sessions")],
            [InlineKeyboardButton("📊 Системная информация", callback_data="mgr_system_info")],
            [InlineKeyboardButton("🔙 Назад", callback_data="mgr_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(settings_text, parse_mode='HTML', reply_markup=reply_markup)
    
    async def logout(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Выход из системы"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        auth_manager.logout(user_id)
        
        # Очищаем данные контекста
        context.user_data.clear()
        
        await query.edit_message_text(
            "👋 <b>Вы вышли из системы управления</b>\n\n"
            "Для повторного входа используйте команду /manager",
            parse_mode='HTML'
        )
    
    def _get_detailed_stats(self) -> Dict:
        """Получить детальную статистику"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Основная статистика
        cursor.execute("SELECT COUNT(*) FROM users")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE newsletter_consent = 1")
        newsletter = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE english_experience = 'Да'")
        experienced = cursor.fetchone()[0]
        
        cursor.execute("SELECT AVG(age) FROM users WHERE age IS NOT NULL")
        avg_age = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE registration_date >= date('now', '-7 days')")
        week_new = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE registration_date >= date('now', '-30 days')")
        month_new = cursor.fetchone()[0]
        
        # Возрастное распределение
        age_groups = {}
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN age < 18 THEN 'До 18'
                    WHEN age < 25 THEN '18-24'
                    WHEN age < 35 THEN '25-34'
                    WHEN age < 45 THEN '35-44'
                    WHEN age < 55 THEN '45-54'
                    ELSE '55+'
                END as age_group,
                COUNT(*) as count
            FROM users 
            WHERE age IS NOT NULL
            GROUP BY age_group
        """)
        
        for row in cursor.fetchall():
            age_groups[row[0]] = row[1]
        
        # Регистрации по дням
        daily_registrations = {}
        cursor.execute("""
            SELECT DATE(registration_date) as reg_date, COUNT(*) as count
            FROM users 
            WHERE registration_date >= date('now', '-7 days')
            GROUP BY DATE(registration_date)
            ORDER BY reg_date DESC
        """)
        
        for row in cursor.fetchall():
            daily_registrations[row[0]] = row[1]
        
        conn.close()
        
        return {
            'total': total,
            'newsletter': newsletter,
            'experienced': experienced,
            'beginners': total - experienced,
            'avg_age': avg_age,
            'week_new': week_new,
            'month_new': month_new,
            'age_groups': age_groups,
            'daily_registrations': daily_registrations
        }
    
    def _get_users_page(self, offset: int, limit: int) -> tuple:
        """Получить страницу пользователей"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Получаем пользователей для текущей страницы
        cursor.execute('''
            SELECT telegram_id, username, name, age, english_experience, 
                   newsletter_consent, registration_date
            FROM users 
            ORDER BY registration_date DESC 
            LIMIT ? OFFSET ?
        ''', (limit, offset))
        
        users = []
        for row in cursor.fetchall():
            users.append({
                'telegram_id': row[0],
                'username': row[1],
                'name': row[2],
                'age': row[3],
                'english_experience': row[4],
                'newsletter_consent': bool(row[5]),
                'registration_date': row[6]
            })
        
        # Получаем общее количество
        cursor.execute("SELECT COUNT(*) FROM users")
        total_count = cursor.fetchone()[0]
        
        conn.close()
        return users, total_count
    
    def _get_all_users(self) -> List[Dict]:
        """Получить всех пользователей"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT telegram_id, username, name, age, english_experience, 
                   data_consent, newsletter_consent, registration_date
            FROM users ORDER BY registration_date DESC
        ''')
        
        users = []
        for row in cursor.fetchall():
            users.append({
                'telegram_id': row[0],
                'username': row[1] or '',
                'name': row[2],
                'age': row[3],
                'english_experience': row[4],
                'data_consent': bool(row[5]),
                'newsletter_consent': bool(row[6]),
                'registration_date': row[7]
            })
        
        conn.close()
        return users
    
    def _get_newsletter_subscribers(self) -> List[Dict]:
        """Получить подписчиков рассылки"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT telegram_id, name FROM users 
            WHERE newsletter_consent = 1
        ''')
        
        subscribers = []
        for row in cursor.fetchall():
            subscribers.append({
                'telegram_id': row[0],
                'name': row[1]
            })
        
        conn.close()
        return subscribers
    
    def _get_newsletter_subscribers_count(self) -> int:
        """Получить количество подписчиков рассылки"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE newsletter_consent = 1")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def _get_db_size(self) -> float:
        """Получить размер базы данных в MB"""
        try:
            size_bytes = os.path.getsize(self.db_path)
            return size_bytes / (1024 * 1024)
        except:
            return 0.0
    
    def _get_uptime(self) -> str:
        """Получить время работы бота (заглушка)"""
        return "Информация недоступна"
    
    async def clear_database_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Запрос подтверждения на очистку БД"""
        if not await self.check_auth(update, context):
            return
        
        query = update.callback_query
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("✅ Да, удалить все", callback_data="mgr_clear_confirm")],
            [InlineKeyboardButton("❌ Отмена", callback_data="mgr_clear_cancel")]
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
    
    async def clear_database_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Подтверждение очистки БД"""
        if not await self.check_auth(update, context):
            return
        
        query = update.callback_query
        await query.answer()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users")
        conn.commit()
        conn.close()
        
        await query.edit_message_text(
            "✅ <b>База данных очищена!</b>\n\n"
            "Все данные пользователей удалены.",
            parse_mode='HTML'
        )
    
    async def clear_database_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Отмена операции очистки"""
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text("❌ Операция отменена")
        
        # Возвращаемся в главное меню
        await self.show_manager_menu(update, context)