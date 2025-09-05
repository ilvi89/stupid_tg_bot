#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Общие действия для сценариев
"""

import os
import sqlite3
import csv
import logging
import time
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from telegram import Update
from telegram.ext import ContextTypes


logger = logging.getLogger(__name__)


class CommonActions:
    """Набор общих действий для использования в сценариях"""
    
    @staticmethod
    async def save_user_to_database(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                  session: Any) -> Dict[str, Any]:
        """Сохранить пользователя в базу данных"""
        try:
            db_path = os.getenv('DATABASE_PATH', 'english_club.db')
            
            user_data = {
                'telegram_id': session.user_id,
                'username': session.data.get('username', ''),
                'name': session.data.get('name', ''),
                'age': session.data.get('age'),
                'english_experience': session.data.get('experience', ''),
                'data_consent': session.data.get('data_consent', True),
                'newsletter_consent': session.data.get('newsletter_consent', False)
            }
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO users 
                (telegram_id, username, name, age, english_experience, data_consent, newsletter_consent)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_data['telegram_id'],
                user_data['username'],
                user_data['name'],
                user_data['age'],
                user_data['english_experience'],
                user_data['data_consent'],
                user_data['newsletter_consent']
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Пользователь {user_data['name']} сохранен в БД")
            return {"save_success": True, "user_id": user_data['telegram_id']}
            
        except Exception as e:
            logger.error(f"Ошибка сохранения пользователя: {e}")
            return {"save_success": False, "error": str(e)}
    
    @staticmethod
    async def send_document(update: Update, context: ContextTypes.DEFAULT_TYPE,
                          session: Any) -> Dict[str, Any]:
        """Отправить документ пользователю"""
        try:
            document_path = session.data.get('document_path')
            caption = session.data.get('document_caption', 'Документ')
            
            if not document_path or not os.path.exists(document_path):
                return {"send_success": False, "error": "Документ не найден"}
            
            message = update.callback_query.message if update.callback_query else update.message
            
            with open(document_path, 'rb') as doc:
                await message.reply_document(
                    document=doc,
                    caption=caption
                )
            
            return {"send_success": True, "document_sent": document_path}
            
        except Exception as e:
            logger.error(f"Ошибка отправки документа: {e}")
            return {"send_success": False, "error": str(e)}
    
    @staticmethod
    async def get_user_from_database(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                   session: Any) -> Dict[str, Any]:
        """Получить данные пользователя из базы"""
        try:
            db_path = os.getenv('DATABASE_PATH', 'english_club.db')
            user_id = session.user_id
            
            conn = sqlite3.connect(db_path)
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
                    "user_found": True,
                    "telegram_id": result[0],
                    "username": result[1],
                    "name": result[2],
                    "age": result[3],
                    "english_experience": result[4],
                    "data_consent": bool(result[5]),
                    "newsletter_consent": bool(result[6]),
                    "registration_date": result[7]
                }
            else:
                return {"user_found": False}
                
        except Exception as e:
            logger.error(f"Ошибка получения пользователя: {e}")
            return {"user_found": False, "error": str(e)}
    
    @staticmethod
    async def update_user_field(update: Update, context: ContextTypes.DEFAULT_TYPE,
                              session: Any) -> Dict[str, Any]:
        """Обновить поле пользователя в базе данных"""
        try:
            db_path = os.getenv('DATABASE_PATH', 'english_club.db')
            user_id = session.user_id
            field_name = session.data.get('field_name')
            field_value = session.data.get('field_value')
            
            if not field_name or field_value is None:
                return {"update_success": False, "error": "Не указано поле или значение"}
            
            # Маппинг полей для безопасности
            allowed_fields = {
                'name': 'name',
                'age': 'age', 
                'experience': 'english_experience',
                'newsletter': 'newsletter_consent'
            }
            
            if field_name not in allowed_fields:
                return {"update_success": False, "error": "Недопустимое поле"}
            
            db_field = allowed_fields[field_name]
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute(f'''
                UPDATE users SET {db_field} = ? WHERE telegram_id = ?
            ''', (field_value, user_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Обновлено поле {field_name} для пользователя {user_id}")
            return {"update_success": True, "updated_field": field_name}
            
        except Exception as e:
            logger.error(f"Ошибка обновления пользователя: {e}")
            return {"update_success": False, "error": str(e)}
    
    @staticmethod
    async def authenticate_manager(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                 session: Any) -> Dict[str, Any]:
        """Аутентифицировать менеджера"""
        try:
            from auth_manager import auth_manager
            
            password = session.data.get('password', '')
            user_id = session.user_id
            
            # Удаляем сообщение с паролем для безопасности
            if update.message:
                try:
                    await update.message.delete()
                except:
                    pass
            
            if auth_manager.authenticate(user_id, password):
                return {"auth_success": True, "user_id": user_id}
            else:
                return {"auth_success": False, "error": "Неверный пароль"}
                
        except Exception as e:
            logger.error(f"Ошибка аутентификации: {e}")
            return {"auth_success": False, "error": str(e)}
    
    @staticmethod
    async def get_newsletter_subscribers(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                       session: Any) -> Dict[str, Any]:
        """Получить список подписчиков рассылки"""
        try:
            db_path = os.getenv('DATABASE_PATH', 'english_club.db')
            
            conn = sqlite3.connect(db_path)
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
            
            return {
                "subscribers_found": True,
                "subscribers": subscribers,
                "count": len(subscribers)
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения подписчиков: {e}")
            return {"subscribers_found": False, "error": str(e)}
    
    @staticmethod
    async def send_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                   session: Any) -> Dict[str, Any]:
        """Отправить рассылку"""
        try:
            message_text = session.data.get('broadcast_message', '')
            subscribers = session.data.get('subscribers', [])
            
            if not message_text or not subscribers:
                return {"broadcast_success": False, "error": "Нет сообщения или получателей"}
            
            sent_count = 0
            failed_count = 0
            
            for subscriber in subscribers:
                try:
                    await context.bot.send_message(
                        chat_id=subscriber['telegram_id'],
                        text=f"📢 <b>Сообщение от английского клуба:</b>\n\n{message_text}",
                        parse_mode='HTML'
                    )
                    sent_count += 1
                    
                    # Пауза между отправками
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    failed_count += 1
                    logger.warning(f"Не удалось отправить сообщение пользователю {subscriber['telegram_id']}: {e}")
            
            return {
                "broadcast_success": True,
                "sent_count": sent_count,
                "failed_count": failed_count,
                "total_count": len(subscribers)
            }
            
        except Exception as e:
            logger.error(f"Ошибка рассылки: {e}")
            return {"broadcast_success": False, "error": str(e)}
    
    @staticmethod
    async def export_users_data(update: Update, context: ContextTypes.DEFAULT_TYPE,
                              session: Any) -> Dict[str, Any]:
        """Экспортировать данные пользователей"""
        try:
            db_path = os.getenv('DATABASE_PATH', 'english_club.db')
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT telegram_id, username, name, age, english_experience, 
                       data_consent, newsletter_consent, registration_date
                FROM users ORDER BY registration_date DESC
            ''')
            
            users = cursor.fetchall()
            conn.close()
            
            if not users:
                return {"export_success": False, "error": "Нет данных для экспорта"}
            
            filename = f"users_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([
                    'Telegram ID', 'Username', 'Имя', 'Возраст', 'Опыт изучения',
                    'Согласие на данные', 'Согласие на рассылку', 'Дата регистрации'
                ])
                
                for user in users:
                    writer.writerow([
                        user[0], user[1], user[2], user[3], user[4],
                        'Да' if user[5] else 'Нет',
                        'Да' if user[6] else 'Нет',
                        user[7]
                    ])
            
            return {
                "export_success": True,
                "filename": filename,
                "count": len(users)
            }
            
        except Exception as e:
            logger.error(f"Ошибка экспорта: {e}")
            return {"export_success": False, "error": str(e)}
    
    @staticmethod
    async def get_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE,
                           session: Any) -> Dict[str, Any]:
        """Получить статистику пользователей"""
        try:
            db_path = os.getenv('DATABASE_PATH', 'english_club.db')
            
            conn = sqlite3.connect(db_path)
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
            
            conn.close()
            
            return {
                "stats_success": True,
                "total_users": total,
                "newsletter_subscribers": newsletter,
                "experienced_users": experienced,
                "beginner_users": total - experienced,
                "average_age": round(avg_age, 1),
                "new_this_week": week_new
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {"stats_success": False, "error": str(e)}
    
    @staticmethod
    async def clear_database(update: Update, context: ContextTypes.DEFAULT_TYPE,
                           session: Any) -> Dict[str, Any]:
        """Очистить базу данных"""
        try:
            db_path = os.getenv('DATABASE_PATH', 'english_club.db')
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM users")
            count_before = cursor.fetchone()[0]
            
            cursor.execute("DELETE FROM users")
            conn.commit()
            conn.close()
            
            logger.warning(f"База данных очищена. Удалено {count_before} записей")
            return {"clear_success": True, "deleted_count": count_before}
            
        except Exception as e:
            logger.error(f"Ошибка очистки базы данных: {e}")
            return {"clear_success": False, "error": str(e)}
    
    @staticmethod
    async def log_user_action(update: Update, context: ContextTypes.DEFAULT_TYPE,
                            session: Any) -> Dict[str, Any]:
        """Записать действие пользователя в лог"""
        try:
            action = session.data.get('action', 'unknown')
            user_id = session.user_id
            
            logger.info(f"Пользователь {user_id} выполнил действие: {action}")
            
            return {"log_success": True, "action": action}
            
        except Exception as e:
            logger.error(f"Ошибка логирования: {e}")
            return {"log_success": False, "error": str(e)}
    
    @staticmethod
    async def validate_user_exists(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                 session: Any) -> Dict[str, Any]:
        """Проверить, что пользователь существует в базе"""
        try:
            db_path = os.getenv('DATABASE_PATH', 'english_club.db')
            user_id = session.user_id
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM users WHERE telegram_id = ?", (user_id,))
            exists = cursor.fetchone()[0] > 0
            
            conn.close()
            
            return {"user_exists": exists}
            
        except Exception as e:
            logger.error(f"Ошибка проверки пользователя: {e}")
            return {"user_exists": False, "error": str(e)}
    
    @staticmethod
    async def format_user_summary(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                session: Any) -> Dict[str, Any]:
        """Форматировать сводку данных пользователя"""
        try:
            name = session.data.get('name', 'Не указано')
            age = session.data.get('age', 'Не указан')
            experience = session.data.get('experience', 'Не указан')
            newsletter = session.data.get('newsletter_consent', False)
            
            summary = (
                f"• Имя: {name}\n"
                f"• Возраст: {age} лет\n"
                f"• Опыт изучения: {experience}\n"
                f"• Согласие на данные: ✅\n"
                f"• Согласие на рассылку: {'✅' if newsletter else '❌'}"
            )
            
            return {"summary_success": True, "summary": summary}
            
        except Exception as e:
            logger.error(f"Ошибка форматирования сводки: {e}")
            return {"summary_success": False, "error": str(e)}


class DatabaseActions:
    """Действия для работы с базой данных"""
    
    @staticmethod
    async def execute_query(query: str, params: tuple = None) -> Dict[str, Any]:
        """Выполнить SQL запрос"""
        try:
            db_path = os.getenv('DATABASE_PATH', 'english_club.db')
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if query.strip().upper().startswith('SELECT'):
                result = cursor.fetchall()
                conn.close()
                return {"query_success": True, "result": result}
            else:
                conn.commit()
                affected = cursor.rowcount
                conn.close()
                return {"query_success": True, "affected_rows": affected}
                
        except Exception as e:
            logger.error(f"Ошибка выполнения запроса: {e}")
            return {"query_success": False, "error": str(e)}


class FileActions:
    """Действия для работы с файлами"""
    
    @staticmethod
    async def send_file_if_exists(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                session: Any) -> Dict[str, Any]:
        """Отправить файл, если он существует"""
        try:
            file_path = session.data.get('file_path')
            caption = session.data.get('file_caption', '')
            
            if not file_path:
                return {"file_success": False, "error": "Не указан путь к файлу"}
            
            if not os.path.exists(file_path):
                return {"file_success": False, "file_exists": False}
            
            message = update.callback_query.message if update.callback_query else update.message
            
            with open(file_path, 'rb') as file:
                await message.reply_document(
                    document=file,
                    caption=caption
                )
            
            return {"file_success": True, "file_sent": True, "file_path": file_path}
            
        except Exception as e:
            logger.error(f"Ошибка отправки файла: {e}")
            return {"file_success": False, "error": str(e)}