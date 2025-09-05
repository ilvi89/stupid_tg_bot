#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DSL (Domain Specific Language) для описания диалоговых цепочек в Telegram-боте
Позволяет декларативно описывать сложные диалоги с восстановлением состояния
"""

import asyncio
import json
import sqlite3
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Callable, Any, Union, Tuple
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes


class DialogState(Enum):
    """Состояния диалога"""
    STARTED = "started"
    IN_PROGRESS = "in_progress"
    WAITING_INPUT = "waiting_input"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ERROR = "error"
    PAUSED = "paused"


class StepType(Enum):
    """Типы шагов диалога"""
    MESSAGE = "message"           # Отправка сообщения
    QUESTION = "question"         # Вопрос с ожиданием ответа
    CHOICE = "choice"            # Выбор из вариантов
    VALIDATION = "validation"     # Валидация введенных данных
    ACTION = "action"            # Выполнение действия
    CONDITION = "condition"       # Условный переход
    FINAL = "final"              # Финальный шаг


class InputType(Enum):
    """Типы ввода"""
    TEXT = "text"
    NUMBER = "number"
    CHOICE = "choice"
    CALLBACK = "callback"
    FILE = "file"
    CONTACT = "contact"
    LOCATION = "location"


@dataclass
class ValidationRule:
    """Правило валидации"""
    name: str
    validator: Callable[[Any], bool]
    error_message: str
    retry_limit: int = 3


@dataclass
class DialogStep:
    """Шаг диалога"""
    id: str
    type: StepType
    message: str = ""
    input_type: Optional[InputType] = None
    choices: List[str] = field(default_factory=list)
    validations: List[ValidationRule] = field(default_factory=list)
    next_step: Optional[str] = None
    condition_steps: Dict[str, str] = field(default_factory=dict)  # condition -> step_id
    action: Optional[Callable] = None
    keyboard: Optional[List[List[str]]] = None
    inline_keyboard: Optional[List[List[Tuple[str, str]]]] = None
    can_skip: bool = False
    timeout: Optional[int] = None
    retry_message: str = "Пожалуйста, попробуйте еще раз."


@dataclass
class DialogChain:
    """Цепочка диалога"""
    id: str
    name: str
    description: str
    steps: List[DialogStep]
    start_step: str
    data_schema: Dict[str, type] = field(default_factory=dict)
    permissions: List[str] = field(default_factory=list)
    timeout: int = 3600  # Таймаут всей цепочки в секундах
    auto_save: bool = True
    recovery_enabled: bool = True


@dataclass
class DialogSession:
    """Сессия диалога"""
    user_id: int
    chat_id: int
    chain_id: str
    current_step: str
    data: Dict[str, Any] = field(default_factory=dict)
    state: DialogState = DialogState.STARTED
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    retry_count: int = 0
    error_history: List[str] = field(default_factory=list)


class DialogStorage(ABC):
    """Абстрактное хранилище состояний диалогов"""
    
    @abstractmethod
    async def save_session(self, session: DialogSession) -> None:
        """Сохранить сессию"""
        pass
    
    @abstractmethod
    async def load_session(self, user_id: int, chat_id: int) -> Optional[DialogSession]:
        """Загрузить сессию"""
        pass
    
    @abstractmethod
    async def delete_session(self, user_id: int, chat_id: int) -> None:
        """Удалить сессию"""
        pass
    
    @abstractmethod
    async def cleanup_expired_sessions(self, max_age: int = 86400) -> int:
        """Очистить истекшие сессии"""
        pass


class SQLiteDialogStorage(DialogStorage):
    """Хранилище состояний диалогов в SQLite"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Инициализация таблиц для хранения диалогов"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dialog_sessions (
                user_id INTEGER,
                chat_id INTEGER,
                chain_id TEXT,
                current_step TEXT,
                data TEXT,
                state TEXT,
                created_at REAL,
                updated_at REAL,
                retry_count INTEGER DEFAULT 0,
                error_history TEXT,
                PRIMARY KEY (user_id, chat_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def save_session(self, session: DialogSession) -> None:
        """Сохранить сессию"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO dialog_sessions 
            (user_id, chat_id, chain_id, current_step, data, state, created_at, updated_at, retry_count, error_history)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session.user_id,
            session.chat_id,
            session.chain_id,
            session.current_step,
            json.dumps(session.data, ensure_ascii=False),
            session.state.value,
            session.created_at,
            session.updated_at,
            session.retry_count,
            json.dumps(session.error_history, ensure_ascii=False)
        ))
        
        conn.commit()
        conn.close()
    
    async def load_session(self, user_id: int, chat_id: int) -> Optional[DialogSession]:
        """Загрузить сессию"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT chain_id, current_step, data, state, created_at, updated_at, retry_count, error_history
            FROM dialog_sessions WHERE user_id = ? AND chat_id = ?
        ''', (user_id, chat_id))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return DialogSession(
                user_id=user_id,
                chat_id=chat_id,
                chain_id=result[0],
                current_step=result[1],
                data=json.loads(result[2]) if result[2] else {},
                state=DialogState(result[3]),
                created_at=result[4],
                updated_at=result[5],
                retry_count=result[6],
                error_history=json.loads(result[7]) if result[7] else []
            )
        return None
    
    async def delete_session(self, user_id: int, chat_id: int) -> None:
        """Удалить сессию"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM dialog_sessions WHERE user_id = ? AND chat_id = ?', 
                      (user_id, chat_id))
        
        conn.commit()
        conn.close()
    
    async def cleanup_expired_sessions(self, max_age: int = 86400) -> int:
        """Очистить истекшие сессии"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_time = time.time() - max_age
        cursor.execute('DELETE FROM dialog_sessions WHERE updated_at < ?', (cutoff_time,))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted_count


class DialogEngine:
    """Движок диалогов"""
    
    def __init__(self, storage: DialogStorage):
        self.storage = storage
        self.chains: Dict[str, DialogChain] = {}
        self.active_sessions: Dict[Tuple[int, int], DialogSession] = {}
    
    def register_chain(self, chain: DialogChain) -> None:
        """Зарегистрировать цепочку диалога"""
        self.chains[chain.id] = chain
    
    async def start_dialog(self, user_id: int, chat_id: int, chain_id: str, 
                          initial_data: Dict[str, Any] = None) -> DialogSession:
        """Начать диалог"""
        if chain_id not in self.chains:
            raise ValueError(f"Цепочка диалога '{chain_id}' не найдена")
        
        chain = self.chains[chain_id]
        
        # Создаем новую сессию
        session = DialogSession(
            user_id=user_id,
            chat_id=chat_id,
            chain_id=chain_id,
            current_step=chain.start_step,
            data=initial_data or {},
            state=DialogState.STARTED
        )
        
        # Сохраняем сессию
        await self.storage.save_session(session)
        self.active_sessions[(user_id, chat_id)] = session
        
        return session
    
    async def get_session(self, user_id: int, chat_id: int) -> Optional[DialogSession]:
        """Получить активную сессию"""
        key = (user_id, chat_id)
        
        # Сначала проверяем в памяти
        if key in self.active_sessions:
            return self.active_sessions[key]
        
        # Загружаем из хранилища
        session = await self.storage.load_session(user_id, chat_id)
        if session and session.state not in [DialogState.COMPLETED, DialogState.CANCELLED]:
            self.active_sessions[key] = session
            return session
        
        return None
    
    async def process_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Обработать ввод пользователя в рамках диалога"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        session = await self.get_session(user_id, chat_id)
        if not session:
            return False
        
        chain = self.chains[session.chain_id]
        current_step = self._get_step(chain, session.current_step)
        
        if not current_step:
            await self._handle_error(update, context, session, "Шаг диалога не найден")
            return True
        
        try:
            # Обработка ввода в зависимости от типа шага
            if current_step.type == StepType.QUESTION:
                await self._process_question_input(update, context, session, current_step)
            elif current_step.type == StepType.CHOICE:
                await self._process_choice_input(update, context, session, current_step)
            elif current_step.type == StepType.VALIDATION:
                await self._process_validation_input(update, context, session, current_step)
            
            return True
            
        except Exception as e:
            await self._handle_error(update, context, session, str(e))
            return True
    
    async def continue_dialog(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                            session: DialogSession) -> None:
        """Продолжить диалог с текущего шага"""
        chain = self.chains[session.chain_id]
        current_step = self._get_step(chain, session.current_step)
        
        if current_step:
            await self._execute_step(update, context, session, current_step)
    
    async def restart_dialog(self, user_id: int, chat_id: int, chain_id: str) -> DialogSession:
        """Перезапустить диалог с начала"""
        await self.cancel_dialog(user_id, chat_id)
        return await self.start_dialog(user_id, chat_id, chain_id)
    
    async def cancel_dialog(self, user_id: int, chat_id: int) -> None:
        """Отменить диалог"""
        session = await self.get_session(user_id, chat_id)
        if session:
            session.state = DialogState.CANCELLED
            await self.storage.save_session(session)
            
            key = (user_id, chat_id)
            if key in self.active_sessions:
                del self.active_sessions[key]
    
    def _get_step(self, chain: DialogChain, step_id: str) -> Optional[DialogStep]:
        """Получить шаг по ID"""
        for step in chain.steps:
            if step.id == step_id:
                return step
        return None
    
    async def _execute_step(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                           session: DialogSession, step: DialogStep) -> None:
        """Выполнить шаг диалога"""
        session.state = DialogState.IN_PROGRESS
        session.updated_at = time.time()
        
        if step.type == StepType.MESSAGE:
            await self._send_message(update, context, session, step)
            await self._move_to_next_step(update, context, session, step)
        
        elif step.type == StepType.QUESTION:
            await self._send_question(update, context, session, step)
            session.state = DialogState.WAITING_INPUT
        
        elif step.type == StepType.CHOICE:
            await self._send_choice(update, context, session, step)
            session.state = DialogState.WAITING_INPUT
        
        elif step.type == StepType.ACTION:
            await self._execute_action(update, context, session, step)
            await self._move_to_next_step(update, context, session, step)
        
        elif step.type == StepType.FINAL:
            await self._send_message(update, context, session, step)
            session.state = DialogState.COMPLETED
            await self._cleanup_session(session)
        
        await self.storage.save_session(session)
    
    async def _send_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                           session: DialogSession, step: DialogStep) -> None:
        """Отправить сообщение"""
        message_text = step.message.format(**session.data)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(message_text, parse_mode='HTML')
        else:
            await update.message.reply_text(message_text, parse_mode='HTML')
    
    async def _send_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                            session: DialogSession, step: DialogStep) -> None:
        """Отправить вопрос"""
        message_text = step.message.format(**session.data)
        reply_markup = None
        
        if step.keyboard:
            keyboard = [[KeyboardButton(text) for text in row] for row in step.keyboard]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(message_text, parse_mode='HTML')
            if reply_markup:
                await update.callback_query.message.reply_text("Выберите вариант:", reply_markup=reply_markup)
        else:
            await update.message.reply_text(message_text, parse_mode='HTML', reply_markup=reply_markup)
    
    async def _send_choice(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                          session: DialogSession, step: DialogStep) -> None:
        """Отправить выбор"""
        message_text = step.message.format(**session.data)
        
        if step.inline_keyboard:
            keyboard = []
            for row in step.inline_keyboard:
                button_row = []
                for text, callback_data in row:
                    button_row.append(InlineKeyboardButton(text, callback_data=callback_data))
                keyboard.append(button_row)
            reply_markup = InlineKeyboardMarkup(keyboard)
        else:
            # Создаем inline клавиатуру из choices
            keyboard = []
            for choice in step.choices:
                keyboard.append([InlineKeyboardButton(choice, callback_data=f"choice_{choice}")])
            reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(message_text, parse_mode='HTML', reply_markup=reply_markup)
        else:
            await update.message.reply_text(message_text, parse_mode='HTML', reply_markup=reply_markup)
    
    async def _execute_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                             session: DialogSession, step: DialogStep) -> None:
        """Выполнить действие"""
        if step.action:
            try:
                result = await step.action(update, context, session)
                if result:
                    session.data.update(result)
            except Exception as e:
                await self._handle_error(update, context, session, f"Ошибка выполнения действия: {e}")
    
    async def _process_question_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                     session: DialogSession, step: DialogStep) -> None:
        """Обработать ввод на вопрос"""
        user_input = None
        
        if update.message and update.message.text:
            user_input = update.message.text.strip()
        elif update.callback_query and update.callback_query.data:
            user_input = update.callback_query.data
        
        if user_input is None:
            await self._send_retry_message(update, context, session, step)
            return
        
        # Валидация
        if not await self._validate_input(update, context, session, step, user_input):
            return
        
        # Сохраняем данные
        field_name = step.id.replace('_step', '').replace('get_', '')
        session.data[field_name] = user_input
        
        # Переходим к следующему шагу
        await self._move_to_next_step(update, context, session, step)
    
    async def _process_choice_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                   session: DialogSession, step: DialogStep) -> None:
        """Обработать выбор"""
        if not update.callback_query:
            await self._send_retry_message(update, context, session, step)
            return
        
        choice = update.callback_query.data
        
        # Проверяем валидность выбора
        valid_choices = [f"choice_{c}" for c in step.choices]
        if step.inline_keyboard:
            valid_choices.extend([callback for _, callback in sum(step.inline_keyboard, [])])
        
        if choice not in valid_choices:
            await self._send_retry_message(update, context, session, step)
            return
        
        # Сохраняем выбор
        field_name = step.id.replace('_step', '').replace('choose_', '')
        if choice.startswith('choice_'):
            session.data[field_name] = choice.replace('choice_', '')
        else:
            session.data[field_name] = choice
        
        # Переходим к следующему шагу
        await self._move_to_next_step(update, context, session, step)
    
    async def _validate_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                             session: DialogSession, step: DialogStep, user_input: str) -> bool:
        """Валидировать ввод"""
        for validation in step.validations:
            if not validation.validator(user_input):
                session.retry_count += 1
                
                if session.retry_count >= validation.retry_limit:
                    await self._handle_error(update, context, session, 
                                           f"Превышено количество попыток для шага '{step.id}'")
                    return False
                
                await update.message.reply_text(validation.error_message)
                await self.storage.save_session(session)
                return False
        
        session.retry_count = 0  # Сбрасываем счетчик при успешной валидации
        return True
    
    async def _move_to_next_step(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                session: DialogSession, current_step: DialogStep) -> None:
        """Перейти к следующему шагу"""
        next_step_id = None
        
        # Проверяем условные переходы
        if current_step.condition_steps:
            for condition, step_id in current_step.condition_steps.items():
                if await self._check_condition(session, condition):
                    next_step_id = step_id
                    break
        
        # Если нет условного перехода, используем обычный
        if not next_step_id:
            next_step_id = current_step.next_step
        
        if next_step_id:
            session.current_step = next_step_id
            chain = self.chains[session.chain_id]
            next_step = self._get_step(chain, next_step_id)
            
            if next_step:
                await self._execute_step(update, context, session, next_step)
        else:
            # Диалог завершен
            session.state = DialogState.COMPLETED
            await self._cleanup_session(session)
    
    async def _check_condition(self, session: DialogSession, condition: str) -> bool:
        """Проверить условие"""
        # Простая реализация условий
        try:
            # Поддержка простых условий вида "field==value" или "field!=value"
            if '==' in condition:
                field, value = condition.split('==')
                return str(session.data.get(field.strip())) == value.strip()
            elif '!=' in condition:
                field, value = condition.split('!=')
                return str(session.data.get(field.strip())) != value.strip()
            elif 'in' in condition:
                field, values = condition.split(' in ')
                values_list = [v.strip().strip('"\'') for v in values.strip('[]').split(',')]
                return str(session.data.get(field.strip())) in values_list
            
        except Exception:
            pass
        
        return False
    
    async def _send_retry_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                 session: DialogSession, step: DialogStep) -> None:
        """Отправить сообщение о повторной попытке"""
        await update.message.reply_text(step.retry_message)
    
    async def _handle_error(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                           session: DialogSession, error: str) -> None:
        """Обработать ошибку диалога"""
        session.state = DialogState.ERROR
        session.error_history.append(f"{time.time()}: {error}")
        
        # Предлагаем варианты восстановления
        keyboard = [
            [InlineKeyboardButton("🔄 Продолжить с текущего шага", callback_data=f"dialog_continue_{session.current_step}")],
            [InlineKeyboardButton("🔁 Начать диалог заново", callback_data=f"dialog_restart_{session.chain_id}")],
            [InlineKeyboardButton("❌ Отменить", callback_data="dialog_cancel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        error_text = (
            f"⚠️ <b>Произошла ошибка в диалоге</b>\n\n"
            f"Ошибка: {error}\n\n"
            f"Что вы хотите сделать?"
        )
        
        if update.callback_query:
            await update.callback_query.edit_message_text(error_text, parse_mode='HTML', reply_markup=reply_markup)
        else:
            await update.message.reply_text(error_text, parse_mode='HTML', reply_markup=reply_markup)
        
        await self.storage.save_session(session)
    
    async def _cleanup_session(self, session: DialogSession) -> None:
        """Очистить завершенную сессию"""
        key = (session.user_id, session.chat_id)
        if key in self.active_sessions:
            del self.active_sessions[key]
        
        if session.state == DialogState.COMPLETED:
            # Удаляем из хранилища только завершенные сессии
            await self.storage.delete_session(session.user_id, session.chat_id)


class DialogBuilder:
    """Построитель диалогов"""
    
    def __init__(self, chain_id: str, name: str, description: str = ""):
        self.chain = DialogChain(
            id=chain_id,
            name=name,
            description=description,
            steps=[],
            start_step=""
        )
        self.current_step_id = None
    
    def start_with(self, step_id: str) -> 'DialogBuilder':
        """Установить начальный шаг"""
        self.chain.start_step = step_id
        return self
    
    def add_message(self, step_id: str, message: str, next_step: str = None) -> 'DialogBuilder':
        """Добавить шаг-сообщение"""
        step = DialogStep(
            id=step_id,
            type=StepType.MESSAGE,
            message=message,
            next_step=next_step
        )
        self.chain.steps.append(step)
        return self
    
    def add_question(self, step_id: str, message: str, input_type: InputType = InputType.TEXT,
                    validations: List[ValidationRule] = None, next_step: str = None,
                    keyboard: List[List[str]] = None) -> 'DialogBuilder':
        """Добавить шаг-вопрос"""
        step = DialogStep(
            id=step_id,
            type=StepType.QUESTION,
            message=message,
            input_type=input_type,
            validations=validations or [],
            next_step=next_step,
            keyboard=keyboard
        )
        self.chain.steps.append(step)
        return self
    
    def add_choice(self, step_id: str, message: str, choices: List[str] = None,
                  inline_keyboard: List[List[Tuple[str, str]]] = None,
                  next_step: str = None) -> 'DialogBuilder':
        """Добавить шаг-выбор"""
        step = DialogStep(
            id=step_id,
            type=StepType.CHOICE,
            message=message,
            choices=choices or [],
            inline_keyboard=inline_keyboard,
            next_step=next_step
        )
        self.chain.steps.append(step)
        return self
    
    def add_action(self, step_id: str, action: Callable, message: str = "",
                  next_step: str = None) -> 'DialogBuilder':
        """Добавить шаг-действие"""
        step = DialogStep(
            id=step_id,
            type=StepType.ACTION,
            message=message,
            action=action,
            next_step=next_step
        )
        self.chain.steps.append(step)
        return self
    
    def add_final(self, step_id: str, message: str) -> 'DialogBuilder':
        """Добавить финальный шаг"""
        step = DialogStep(
            id=step_id,
            type=StepType.FINAL,
            message=message
        )
        self.chain.steps.append(step)
        return self
    
    def add_condition(self, step_id: str, conditions: Dict[str, str]) -> 'DialogBuilder':
        """Добавить условные переходы к последнему шагу"""
        if self.chain.steps:
            self.chain.steps[-1].condition_steps.update(conditions)
        return self
    
    def set_timeout(self, timeout: int) -> 'DialogBuilder':
        """Установить таймаут цепочки"""
        self.chain.timeout = timeout
        return self
    
    def set_permissions(self, permissions: List[str]) -> 'DialogBuilder':
        """Установить права доступа"""
        self.chain.permissions = permissions
        return self
    
    def build(self) -> DialogChain:
        """Построить цепочку диалога"""
        if not self.chain.start_step:
            raise ValueError("Не установлен начальный шаг диалога")
        
        # Проверяем, что все шаги имеют корректные ссылки
        step_ids = {step.id for step in self.chain.steps}
        for step in self.chain.steps:
            if step.next_step and step.next_step not in step_ids:
                raise ValueError(f"Шаг '{step.id}' ссылается на несуществующий шаг '{step.next_step}'")
        
        return self.chain


# Предопределенные валидаторы
class Validators:
    """Набор готовых валидаторов"""
    
    @staticmethod
    def min_length(min_len: int) -> ValidationRule:
        return ValidationRule(
            name=f"min_length_{min_len}",
            validator=lambda x: len(str(x)) >= min_len,
            error_message=f"Минимальная длина: {min_len} символов"
        )
    
    @staticmethod
    def max_length(max_len: int) -> ValidationRule:
        return ValidationRule(
            name=f"max_length_{max_len}",
            validator=lambda x: len(str(x)) <= max_len,
            error_message=f"Максимальная длина: {max_len} символов"
        )
    
    @staticmethod
    def age_range(min_age: int, max_age: int) -> ValidationRule:
        def validate_age(x):
            try:
                age = int(x)
                return min_age <= age <= max_age
            except ValueError:
                return False
        
        return ValidationRule(
            name=f"age_range_{min_age}_{max_age}",
            validator=validate_age,
            error_message=f"Возраст должен быть от {min_age} до {max_age} лет"
        )
    
    @staticmethod
    def is_number() -> ValidationRule:
        def validate_number(x):
            try:
                int(x)
                return True
            except ValueError:
                return False
        
        return ValidationRule(
            name="is_number",
            validator=validate_number,
            error_message="Введите число"
        )
    
    @staticmethod
    def not_empty() -> ValidationRule:
        return ValidationRule(
            name="not_empty",
            validator=lambda x: bool(str(x).strip()),
            error_message="Поле не может быть пустым"
        )
    
    @staticmethod
    def contains_words(words: List[str]) -> ValidationRule:
        return ValidationRule(
            name=f"contains_words",
            validator=lambda x: any(word.lower() in str(x).lower() for word in words),
            error_message=f"Ответ должен содержать одно из слов: {', '.join(words)}"
        )


# Глобальный экземпляр движка диалогов
dialog_engine: Optional[DialogEngine] = None


def init_dialog_engine(db_path: str) -> DialogEngine:
    """Инициализировать движок диалогов"""
    global dialog_engine
    storage = SQLiteDialogStorage(db_path)
    dialog_engine = DialogEngine(storage)
    return dialog_engine


def get_dialog_engine() -> DialogEngine:
    """Получить экземпляр движка диалогов"""
    global dialog_engine
    if dialog_engine is None:
        raise RuntimeError("Движок диалогов не инициализирован. Вызовите init_dialog_engine() сначала.")
    return dialog_engine