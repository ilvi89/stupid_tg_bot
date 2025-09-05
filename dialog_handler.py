#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обработчик диалогов - интеграция DSL с основным ботом
"""

import logging
from typing import Optional, Dict, Any
from telegram import Update
from telegram.ext import ContextTypes

from dialog_dsl import DialogEngine, DialogSession, DialogState, init_dialog_engine, get_dialog_engine
from dialog_maps import dialog_map


logger = logging.getLogger(__name__)


class DialogHandler:
    """Обработчик диалогов с поддержкой восстановления"""
    
    def __init__(self, db_path: str):
        self.engine = init_dialog_engine(db_path)
        self._register_all_dialogs()
    
    def _register_all_dialogs(self):
        """Зарегистрировать все диалоги в движке"""
        all_dialogs = dialog_map.get_all_dialogs()
        for dialog in all_dialogs.values():
            self.engine.register_chain(dialog)
        
        logger.info(f"Зарегистрировано {len(all_dialogs)} диалогов")
    
    async def handle_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, command: str) -> bool:
        """Обработать команду и запустить соответствующий диалог"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Проверяем, есть ли активная сессия
        active_session = await self.engine.get_session(user_id, chat_id)
        if active_session and active_session.state == DialogState.WAITING_INPUT:
            # Предлагаем завершить текущий диалог
            await self._offer_dialog_completion(update, context, active_session, command)
            return True
        
        # Ищем диалог для команды
        dialog, user_type = dialog_map.get_dialog_by_entry(command)
        if dialog:
            # Проверяем права доступа
            if not await self._check_permissions(update, context, dialog, user_type):
                return False
            
            # Запускаем диалог
            session = await self.engine.start_dialog(user_id, chat_id, dialog.id)
            await self.engine.continue_dialog(update, context, session)
            return True
        
        return False
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Обработать callback query"""
        if not update.callback_query:
            return False
        
        callback_data = update.callback_query.data
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Обработка команд восстановления диалога
        if callback_data.startswith("dialog_"):
            return await self._handle_dialog_recovery(update, context, callback_data)
        
        # Проверяем активную сессию
        session = await self.engine.get_session(user_id, chat_id)
        if session:
            return await self.engine.process_input(update, context)
        
        # Проверяем, не начинается ли новый диалог
        dialog, user_type = dialog_map.get_dialog_by_entry(callback_data)
        if dialog:
            if not await self._check_permissions(update, context, dialog, user_type):
                return False
            
            session = await self.engine.start_dialog(user_id, chat_id, dialog.id)
            await self.engine.continue_dialog(update, context, session)
            return True
        
        return False
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Обработать текстовое сообщение"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Проверяем активную сессию
        session = await self.engine.get_session(user_id, chat_id)
        if session and session.state == DialogState.WAITING_INPUT:
            return await self.engine.process_input(update, context)
        
        return False
    
    async def _handle_dialog_recovery(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                    callback_data: str) -> bool:
        """Обработать команды восстановления диалога"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        if callback_data.startswith("dialog_continue_"):
            # Продолжить с текущего шага
            session = await self.engine.get_session(user_id, chat_id)
            if session:
                session.state = DialogState.IN_PROGRESS
                await self.engine.continue_dialog(update, context, session)
                return True
        
        elif callback_data.startswith("dialog_restart_"):
            # Перезапустить диалог
            chain_id = callback_data.replace("dialog_restart_", "")
            session = await self.engine.restart_dialog(user_id, chat_id, chain_id)
            await self.engine.continue_dialog(update, context, session)
            return True
        
        elif callback_data == "dialog_cancel":
            # Отменить диалог
            await self.engine.cancel_dialog(user_id, chat_id)
            await update.callback_query.edit_message_text(
                "❌ Диалог отменен. Для начала нового диалога используйте команды бота."
            )
            return True
        
        return False
    
    async def _offer_dialog_completion(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                     active_session: DialogSession, new_command: str) -> None:
        """Предложить завершить текущий диалог"""
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        chain = self.engine.chains[active_session.chain_id]
        
        keyboard = [
            [InlineKeyboardButton("✅ Завершить текущий диалог", 
                                callback_data=f"dialog_continue_{active_session.current_step}")],
            [InlineKeyboardButton("🔁 Начать новый диалог", 
                                callback_data=f"dialog_new_{new_command}")],
            [InlineKeyboardButton("❌ Отменить текущий диалог", 
                                callback_data="dialog_cancel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"⚠️ <b>У вас есть незавершенный диалог</b>\n\n"
            f"Текущий диалог: {chain.name}\n"
            f"Шаг: {active_session.current_step}\n\n"
            f"Что вы хотите сделать?",
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    
    async def _check_permissions(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                               dialog: DialogChain, user_type: str) -> bool:
        """Проверить права доступа к диалогу"""
        if "manager" in dialog.permissions:
            from auth_manager import auth_manager
            user_id = update.effective_user.id
            
            if not auth_manager.is_authorized(user_id):
                await update.message.reply_text(
                    "🔒 Для выполнения этого действия требуется авторизация менеджера.\n"
                    "Используйте команду /manager для входа в систему."
                )
                return False
        
        return True
    
    async def get_session_info(self, user_id: int, chat_id: int) -> Optional[Dict[str, Any]]:
        """Получить информацию о сессии для отладки"""
        session = await self.engine.get_session(user_id, chat_id)
        if session:
            chain = self.engine.chains.get(session.chain_id)
            return {
                "chain_name": chain.name if chain else "Неизвестно",
                "current_step": session.current_step,
                "state": session.state.value,
                "data": session.data,
                "retry_count": session.retry_count,
                "created_at": session.created_at,
                "updated_at": session.updated_at
            }
        return None
    
    async def cleanup_expired_sessions(self, max_age: int = 86400) -> int:
        """Очистить истекшие сессии"""
        return await self.engine.storage.cleanup_expired_sessions(max_age)
    
    async def force_cancel_session(self, user_id: int, chat_id: int) -> bool:
        """Принудительно отменить сессию"""
        session = await self.engine.get_session(user_id, chat_id)
        if session:
            await self.engine.cancel_dialog(user_id, chat_id)
            return True
        return False
    
    async def get_all_active_sessions(self) -> Dict[str, Any]:
        """Получить информацию о всех активных сессиях"""
        sessions_info = {}
        for (user_id, chat_id), session in self.engine.active_sessions.items():
            chain = self.engine.chains.get(session.chain_id)
            sessions_info[f"{user_id}_{chat_id}"] = {
                "user_id": user_id,
                "chat_id": chat_id,
                "chain_name": chain.name if chain else "Неизвестно",
                "current_step": session.current_step,
                "state": session.state.value,
                "created_at": session.created_at,
                "updated_at": session.updated_at
            }
        return sessions_info


# === ИНТЕГРАЦИЯ С ОСНОВНЫМ БОТОМ ===

# Глобальный экземпляр обработчика диалогов
dialog_handler: Optional[DialogHandler] = None


def init_dialog_handler(db_path: str) -> DialogHandler:
    """Инициализировать обработчик диалогов"""
    global dialog_handler
    dialog_handler = DialogHandler(db_path)
    return dialog_handler


def get_dialog_handler() -> DialogHandler:
    """Получить экземпляр обработчика диалогов"""
    global dialog_handler
    if dialog_handler is None:
        raise RuntimeError("Обработчик диалогов не инициализирован")
    return dialog_handler


# === КОМАНДЫ ДЛЯ ОТЛАДКИ ДИАЛОГОВ ===

async def debug_dialog_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда для отладки - показать информацию о текущем диалоге"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    handler = get_dialog_handler()
    session_info = await handler.get_session_info(user_id, chat_id)
    
    if session_info:
        info_text = (
            f"🔍 <b>Информация о диалоге</b>\n\n"
            f"<b>Диалог:</b> {session_info['chain_name']}\n"
            f"<b>Текущий шаг:</b> {session_info['current_step']}\n"
            f"<b>Состояние:</b> {session_info['state']}\n"
            f"<b>Попыток:</b> {session_info['retry_count']}\n"
            f"<b>Данные:</b> {len(session_info['data'])} полей\n"
            f"<b>Создан:</b> {session_info['created_at']}\n"
            f"<b>Обновлен:</b> {session_info['updated_at']}"
        )
    else:
        info_text = "ℹ️ Активных диалогов не найдено"
    
    await update.message.reply_text(info_text, parse_mode='HTML')


async def debug_cancel_dialog(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда для отладки - отменить текущий диалог"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    handler = get_dialog_handler()
    if await handler.force_cancel_session(user_id, chat_id):
        await update.message.reply_text("✅ Текущий диалог отменен")
    else:
        await update.message.reply_text("ℹ️ Активных диалогов не найдено")


async def debug_all_sessions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда для отладки - показать все активные сессии (только для менеджеров)"""
    from auth_manager import auth_manager
    
    user_id = update.effective_user.id
    if not auth_manager.is_authorized(user_id):
        await update.message.reply_text("🔒 Команда доступна только менеджерам")
        return
    
    handler = get_dialog_handler()
    sessions = await handler.get_all_active_sessions()
    
    if sessions:
        sessions_text = "📊 <b>Активные диалоговые сессии:</b>\n\n"
        for session_key, session_info in sessions.items():
            sessions_text += (
                f"👤 Пользователь {session_info['user_id']}\n"
                f"   💬 Чат: {session_info['chat_id']}\n"
                f"   🔄 Диалог: {session_info['chain_name']}\n"
                f"   📍 Шаг: {session_info['current_step']}\n"
                f"   🔘 Состояние: {session_info['state']}\n\n"
            )
    else:
        sessions_text = "ℹ️ Активных диалоговых сессий не найдено"
    
    await update.message.reply_text(sessions_text, parse_mode='HTML')


# === МИГРАЦИЯ СУЩЕСТВУЮЩЕГО КОДА ===

class DialogMigrator:
    """Класс для миграции существующего кода на новую диалоговую систему"""
    
    @staticmethod
    async def migrate_conversation_handler(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                         handler_name: str) -> bool:
        """Мигрировать обработчик ConversationHandler на новую систему"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Карта миграции старых состояний на новые диалоги
        migration_map = {
            "start": ("user_registration", {}),
            "manager": ("manager_auth", {}),
            "WAITING_NAME": ("user_registration", {"current_step": "name_question_step"}),
            "WAITING_EXPERIENCE": ("user_registration", {"current_step": "experience_question_step"}),
            "WAITING_AGE": ("user_registration", {"current_step": "age_question_step"}),
            "FINAL_CONSENT": ("user_registration", {"current_step": "newsletter_question_step"}),
        }
        
        if handler_name in migration_map:
            dialog_id, session_data = migration_map[handler_name]
            
            handler = get_dialog_handler()
            session = await handler.engine.start_dialog(user_id, chat_id, dialog_id, session_data)
            await handler.engine.continue_dialog(update, context, session)
            return True
        
        return False


# === ДОПОЛНИТЕЛЬНЫЕ УТИЛИТЫ ===

class DialogAnalytics:
    """Аналитика диалогов"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    async def get_dialog_stats(self) -> Dict[str, Any]:
        """Получить статистику по диалогам"""
        import sqlite3
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Общая статистика
        cursor.execute("SELECT COUNT(*) FROM dialog_sessions")
        total_sessions = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM dialog_sessions WHERE state = 'completed'")
        completed_sessions = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM dialog_sessions WHERE state = 'error'")
        error_sessions = cursor.fetchone()[0]
        
        # Статистика по типам диалогов
        cursor.execute("""
            SELECT chain_id, COUNT(*) as count, 
                   AVG(updated_at - created_at) as avg_duration
            FROM dialog_sessions 
            WHERE state = 'completed'
            GROUP BY chain_id
        """)
        chain_stats = cursor.fetchall()
        
        conn.close()
        
        return {
            "total_sessions": total_sessions,
            "completed_sessions": completed_sessions,
            "error_sessions": error_sessions,
            "completion_rate": completed_sessions / total_sessions if total_sessions > 0 else 0,
            "chain_stats": {
                row[0]: {
                    "count": row[1],
                    "avg_duration": row[2]
                } for row in chain_stats
            }
        }
    
    async def get_error_analysis(self) -> Dict[str, Any]:
        """Анализ ошибок в диалогах"""
        import sqlite3
        import json
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT chain_id, current_step, error_history, retry_count
            FROM dialog_sessions 
            WHERE state = 'error' OR json_array_length(error_history) > 0
        """)
        
        error_data = cursor.fetchall()
        conn.close()
        
        error_analysis = {
            "total_errors": len(error_data),
            "errors_by_chain": {},
            "errors_by_step": {},
            "common_errors": {}
        }
        
        for row in error_data:
            chain_id, step_id, error_history_json, retry_count = row
            
            # Подсчет ошибок по цепочкам
            if chain_id not in error_analysis["errors_by_chain"]:
                error_analysis["errors_by_chain"][chain_id] = 0
            error_analysis["errors_by_chain"][chain_id] += 1
            
            # Подсчет ошибок по шагам
            if step_id not in error_analysis["errors_by_step"]:
                error_analysis["errors_by_step"][step_id] = 0
            error_analysis["errors_by_step"][step_id] += 1
            
            # Анализ типов ошибок
            try:
                error_history = json.loads(error_history_json) if error_history_json else []
                for error in error_history:
                    error_type = error.split(":")[1].strip() if ":" in error else error
                    if error_type not in error_analysis["common_errors"]:
                        error_analysis["common_errors"][error_type] = 0
                    error_analysis["common_errors"][error_type] += 1
            except:
                pass
        
        return error_analysis


# Глобальный экземпляр обработчика
dialog_handler_instance: Optional[DialogHandler] = None


def init_dialog_system(db_path: str) -> DialogHandler:
    """Инициализировать всю диалоговую систему"""
    global dialog_handler_instance
    dialog_handler_instance = DialogHandler(db_path)
    logger.info("Диалоговая система инициализирована")
    return dialog_handler_instance


def get_dialog_system() -> DialogHandler:
    """Получить экземпляр диалоговой системы"""
    global dialog_handler_instance
    if dialog_handler_instance is None:
        raise RuntimeError("Диалоговая система не инициализирована")
    return dialog_handler_instance