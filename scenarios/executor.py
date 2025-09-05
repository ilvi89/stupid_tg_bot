#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Исполнитель сценариев - выполнение DSL сценариев с интеграцией в Telegram бот
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Callable
from telegram import Update
from telegram.ext import ContextTypes, Application

from dialog_dsl import DialogEngine, DialogSession, DialogState
from .registry import ScenarioRegistry, RegisteredScenario, ScenarioType, get_registry


logger = logging.getLogger(__name__)


class ScenarioExecutor:
    """Исполнитель сценариев"""
    
    def __init__(self, dialog_engine: DialogEngine, registry: ScenarioRegistry = None):
        self.engine = dialog_engine
        self.registry = registry or get_registry()
        self.active_executions: Dict[str, Any] = {}
        
        # Регистрируем все сценарии в движке диалогов
        self._register_all_scenarios()
    
    def _register_all_scenarios(self) -> None:
        """Зарегистрировать все сценарии в движке диалогов"""
        scenarios = self.registry.get_enabled_scenarios()
        for scenario_id, scenario in scenarios.items():
            self.engine.register_chain(scenario.chain)
        
        logger.info(f"Зарегистрировано {len(scenarios)} сценариев в движке диалогов")
    
    async def handle_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                            command: str) -> bool:
        """Обработать команду и запустить соответствующий сценарий"""
        # Ищем сценарий по точке входа
        scenario = self.registry.get_scenario_by_entry_point(command)
        if not scenario:
            return False
        
        if not scenario.metadata.enabled:
            logger.info(f"Сценарий '{scenario.metadata.id}' отключен")
            return False
        
        # Проверяем права доступа
        if not await self._check_permissions(update, context, scenario):
            return False
        
        # Проверяем активную сессию
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        active_session = await self.engine.get_session(user_id, chat_id)
        if active_session and active_session.state == DialogState.WAITING_INPUT:
            await self._handle_session_conflict(update, context, active_session, scenario)
            return True
        
        # Запускаем новый сценарий
        try:
            session = await self.engine.start_dialog(user_id, chat_id, scenario.chain.id)
            await self.engine.continue_dialog(update, context, session)
            
            # Записываем в активные выполнения
            execution_id = f"{user_id}_{chat_id}_{scenario.chain.id}"
            self.active_executions[execution_id] = {
                "scenario_id": scenario.metadata.id,
                "session": session,
                "started_at": session.created_at
            }
            
            logger.info(f"Запущен сценарий '{scenario.metadata.id}' для пользователя {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка запуска сценария '{scenario.metadata.id}': {e}")
            await self._send_error_message(update, context, f"Ошибка запуска сценария: {e}")
            return False
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Обработать callback query"""
        if not update.callback_query:
            return False
        
        callback_data = update.callback_query.data
        
        # Обработка команд управления сценариями
        if callback_data.startswith("scenario_"):
            return await self._handle_scenario_control(update, context, callback_data)
        
        # Передаем в движок диалогов для обработки активной сессии
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        session = await self.engine.get_session(user_id, chat_id)
        if session:
            return await self.engine.process_input(update, context)
        
        # Проверяем, не запускается ли новый сценарий
        scenario = self.registry.get_scenario_by_entry_point(callback_data)
        if scenario:
            return await self.handle_command(update, context, callback_data)
        
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
    
    async def _handle_session_conflict(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                      active_session: DialogSession, new_scenario: RegisteredScenario) -> None:
        """Обработать конфликт с активной сессией"""
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        active_scenario = self.registry.get_scenario(active_session.chain_id)
        active_name = active_scenario.metadata.name if active_scenario else "Неизвестно"
        
        keyboard = [
            [InlineKeyboardButton("✅ Завершить текущий сценарий", 
                                callback_data=f"scenario_continue_{active_session.current_step}")],
            [InlineKeyboardButton("🔄 Начать новый сценарий", 
                                callback_data=f"scenario_start_{new_scenario.metadata.id}")],
            [InlineKeyboardButton("❌ Отменить текущий сценарий", 
                                callback_data=f"scenario_cancel_{active_session.chain_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        conflict_text = (
            f"⚠️ <b>Конфликт сценариев</b>\n\n"
            f"У вас уже выполняется сценарий:\n"
            f"📋 <b>{active_name}</b>\n"
            f"📍 Шаг: {active_session.current_step}\n\n"
            f"Вы хотите запустить новый сценарий:\n"
            f"📋 <b>{new_scenario.metadata.name}</b>\n\n"
            f"Что делаем?"
        )
        
        if update.message:
            await update.message.reply_text(conflict_text, parse_mode='HTML', reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.edit_message_text(conflict_text, parse_mode='HTML', reply_markup=reply_markup)
    
    async def _handle_scenario_control(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                     callback_data: str) -> bool:
        """Обработать команды управления сценариями"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        if callback_data.startswith("scenario_continue_"):
            # Продолжить текущий сценарий
            session = await self.engine.get_session(user_id, chat_id)
            if session:
                session.state = DialogState.IN_PROGRESS
                await self.engine.continue_dialog(update, context, session)
                return True
        
        elif callback_data.startswith("scenario_start_"):
            # Запустить новый сценарий
            scenario_id = callback_data.replace("scenario_start_", "")
            scenario = self.registry.get_scenario(scenario_id)
            if scenario:
                # Отменяем текущий сценарий
                await self.engine.cancel_dialog(user_id, chat_id)
                
                # Запускаем новый
                session = await self.engine.start_dialog(user_id, chat_id, scenario.chain.id)
                await self.engine.continue_dialog(update, context, session)
                return True
        
        elif callback_data.startswith("scenario_cancel_"):
            # Отменить сценарий
            await self.engine.cancel_dialog(user_id, chat_id)
            await update.callback_query.edit_message_text(
                "❌ Сценарий отменен. Для запуска нового сценария используйте команды бота."
            )
            return True
        
        return False
    
    async def _check_permissions(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                               scenario: RegisteredScenario) -> bool:
        """Проверить права доступа к сценарию"""
        if scenario.metadata.type == ScenarioType.MANAGER:
            from auth_manager import auth_manager
            user_id = update.effective_user.id
            
            if not auth_manager.is_authorized(user_id):
                await self._send_permission_denied(update, context, scenario)
                return False
        
        # Проверяем специфичные права
        for permission in scenario.metadata.permissions:
            if permission == "manager":
                from auth_manager import auth_manager
                user_id = update.effective_user.id
                if not auth_manager.is_authorized(user_id):
                    await self._send_permission_denied(update, context, scenario)
                    return False
        
        return True
    
    async def _send_permission_denied(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                    scenario: RegisteredScenario) -> None:
        """Отправить сообщение об отказе в доступе"""
        message = (
            f"🔒 <b>Доступ запрещен</b>\n\n"
            f"Сценарий '{scenario.metadata.name}' требует дополнительных прав.\n"
            f"Обратитесь к администратору или войдите в систему."
        )
        
        if update.message:
            await update.message.reply_text(message, parse_mode='HTML')
        elif update.callback_query:
            await update.callback_query.answer(message, show_alert=True)
    
    async def _send_error_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                 error: str) -> None:
        """Отправить сообщение об ошибке"""
        message = f"❌ <b>Ошибка</b>\n\n{error}"
        
        if update.message:
            await update.message.reply_text(message, parse_mode='HTML')
        elif update.callback_query:
            await update.callback_query.edit_message_text(message, parse_mode='HTML')
    
    async def get_execution_statistics(self) -> Dict[str, Any]:
        """Получить статистику выполнения сценариев"""
        # Статистика из активных выполнений
        active_count = len(self.active_executions)
        
        # Статистика по типам сценариев
        scenario_type_stats = {}
        for scenario_type in ScenarioType:
            scenarios = self.registry.get_scenarios_by_type(scenario_type)
            scenario_type_stats[scenario_type.value] = len(scenarios)
        
        # Статистика из движка диалогов
        dialog_stats = await self.engine.storage.cleanup_expired_sessions(max_age=0)  # Не удаляем, просто считаем
        
        return {
            "active_executions": active_count,
            "registered_scenarios": len(self.registry.get_all_scenarios()),
            "enabled_scenarios": len(self.registry.get_enabled_scenarios()),
            "scenario_types": scenario_type_stats,
            "registry_stats": self.registry.get_statistics()
        }
    
    async def force_stop_execution(self, user_id: int, chat_id: int, reason: str = "Принудительная остановка") -> bool:
        """Принудительно остановить выполнение сценария"""
        session = await self.engine.get_session(user_id, chat_id)
        if session:
            await self.engine.cancel_dialog(user_id, chat_id)
            
            # Удаляем из активных выполнений
            execution_id = f"{user_id}_{chat_id}_{session.chain_id}"
            if execution_id in self.active_executions:
                del self.active_executions[execution_id]
            
            logger.info(f"Принудительно остановлен сценарий для пользователя {user_id}: {reason}")
            return True
        
        return False
    
    def reload_scenarios(self) -> Dict[str, Any]:
        """Перезагрузить все сценарии"""
        try:
            # Очищаем текущие сценарии
            old_count = len(self.registry.get_all_scenarios())
            
            # Перерегистрируем сценарии
            self._register_all_scenarios()
            
            new_count = len(self.registry.get_enabled_scenarios())
            
            return {
                "success": True,
                "old_count": old_count,
                "new_count": new_count,
                "reloaded": new_count
            }
            
        except Exception as e:
            logger.error(f"Ошибка перезагрузки сценариев: {e}")
            return {
                "success": False,
                "error": str(e)
            }


class ScenarioIntegrator:
    """Интегратор сценариев с Telegram Application"""
    
    def __init__(self, executor: ScenarioExecutor):
        self.executor = executor
    
    def integrate_with_application(self, application: Application) -> None:
        """Интегрировать сценарии с Telegram Application"""
        from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, filters
        
        # Получаем все точки входа
        scenarios = self.executor.registry.get_enabled_scenarios()
        entry_points = set()
        
        for scenario in scenarios.values():
            entry_points.update(scenario.entry_points)
        
        # Создаем обработчики команд
        command_entry_points = [ep for ep in entry_points if ep.startswith('/')]
        for command in command_entry_points:
            handler = CommandHandler(
                command.lstrip('/'), 
                self._create_command_handler(command)
            )
            application.add_handler(handler)
            logger.debug(f"Добавлен обработчик команды: {command}")
        
        # Создаем обработчик callback'ов для сценариев
        scenario_callback_handler = CallbackQueryHandler(
            self._handle_scenario_callback,
            pattern="^scenario_"
        )
        application.add_handler(scenario_callback_handler)
        
        # Создаем общий обработчик callback'ов
        general_callback_handler = CallbackQueryHandler(
            self._handle_general_callback
        )
        application.add_handler(general_callback_handler)
        
        # Создаем обработчик текстовых сообщений
        text_handler = MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self._handle_text_message
        )
        application.add_handler(text_handler)
        
        logger.info(f"Интеграция завершена. Обработчиков команд: {len(command_entry_points)}")
    
    def _create_command_handler(self, command: str) -> Callable:
        """Создать обработчик команды"""
        async def command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            await self.executor.handle_command(update, context, command)
        
        command_handler.__name__ = f"handle_{command.lstrip('/').replace('-', '_')}"
        return command_handler
    
    async def _handle_scenario_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработать callback для сценариев"""
        await self.executor.handle_callback(update, context)
    
    async def _handle_general_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработать общий callback"""
        # Сначала пытаемся обработать через сценарии
        if await self.executor.handle_callback(update, context):
            return
        
        # Если не обработано сценариями, передаем дальше
        # (здесь может быть логика для других обработчиков)
    
    async def _handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработать текстовое сообщение"""
        # Сначала пытаемся обработать через сценарии
        if await self.executor.handle_message(update, context):
            return
        
        # Если не обработано сценариями, отправляем справку
        await update.message.reply_text(
            "🤖 Привет! Для начала работы используйте:\n\n"
            "📝 Команды:\n"
            "/start - Начать регистрацию\n"
            "/manager - Панель управления\n"
            "/help - Помощь\n\n"
            "Или выберите действие в меню."
        )


class ScenarioOrchestrator:
    """Оркестратор сценариев - управление композициями и переходами"""
    
    def __init__(self, executor: ScenarioExecutor):
        self.executor = executor
        self.compositions: Dict[str, List[str]] = {}  # composition_id -> scenario_ids
        self.transitions: Dict[str, Dict[str, str]] = {}  # from_scenario -> {condition: to_scenario}
    
    def register_composition(self, composition_id: str, scenario_ids: List[str],
                           name: str = "", description: str = "") -> None:
        """Зарегистрировать композицию сценариев"""
        # Проверяем, что все сценарии существуют
        missing_scenarios = []
        for scenario_id in scenario_ids:
            if not self.executor.registry.get_scenario(scenario_id):
                missing_scenarios.append(scenario_id)
        
        if missing_scenarios:
            raise ValueError(f"Отсутствуют сценарии: {missing_scenarios}")
        
        self.compositions[composition_id] = scenario_ids
        logger.info(f"Зарегистрирована композиция '{composition_id}' из {len(scenario_ids)} сценариев")
    
    def register_transition(self, from_scenario: str, to_scenario: str, condition: str) -> None:
        """Зарегистрировать переход между сценариями"""
        if from_scenario not in self.transitions:
            self.transitions[from_scenario] = {}
        
        self.transitions[from_scenario][condition] = to_scenario
        logger.info(f"Зарегистрирован переход: {from_scenario} -> {to_scenario} при '{condition}'")
    
    async def execute_composition(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                composition_id: str) -> bool:
        """Выполнить композицию сценариев"""
        if composition_id not in self.compositions:
            logger.error(f"Композиция '{composition_id}' не найдена")
            return False
        
        scenario_ids = self.compositions[composition_id]
        
        # Выполняем первый сценарий композиции
        first_scenario_id = scenario_ids[0]
        first_scenario = self.executor.registry.get_scenario(first_scenario_id)
        
        if not first_scenario:
            logger.error(f"Первый сценарий композиции '{first_scenario_id}' не найден")
            return False
        
        # Сохраняем информацию о композиции в контексте
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        context.user_data[f"composition_{user_id}_{chat_id}"] = {
            "composition_id": composition_id,
            "scenario_ids": scenario_ids,
            "current_index": 0
        }
        
        # Запускаем первый сценарий
        return await self.executor.handle_command(update, context, first_scenario.entry_points[0])
    
    async def handle_scenario_completion(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                       completed_scenario_id: str) -> bool:
        """Обработать завершение сценария в рамках композиции"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        composition_key = f"composition_{user_id}_{chat_id}"
        
        if composition_key not in context.user_data:
            return False
        
        composition_data = context.user_data[composition_key]
        scenario_ids = composition_data["scenario_ids"]
        current_index = composition_data["current_index"]
        
        # Проверяем переходы
        if completed_scenario_id in self.transitions:
            for condition, next_scenario_id in self.transitions[completed_scenario_id].items():
                if await self._check_transition_condition(update, context, condition):
                    next_scenario = self.executor.registry.get_scenario(next_scenario_id)
                    if next_scenario:
                        return await self.executor.handle_command(update, context, next_scenario.entry_points[0])
        
        # Переходим к следующему сценарию в композиции
        next_index = current_index + 1
        if next_index < len(scenario_ids):
            next_scenario_id = scenario_ids[next_index]
            next_scenario = self.executor.registry.get_scenario(next_scenario_id)
            
            if next_scenario:
                composition_data["current_index"] = next_index
                context.user_data[composition_key] = composition_data
                
                return await self.executor.handle_command(update, context, next_scenario.entry_points[0])
        
        # Композиция завершена
        del context.user_data[composition_key]
        await update.message.reply_text(
            f"🎉 <b>Композиция сценариев завершена!</b>\n\n"
            f"Выполнено сценариев: {len(scenario_ids)}"
        )
        return True
    
    async def _check_transition_condition(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                        condition: str) -> bool:
        """Проверить условие перехода"""
        # Простая реализация условий
        try:
            if condition == "always":
                return True
            elif condition == "never":
                return False
            elif condition.startswith("user_data."):
                # Проверка данных пользователя
                key = condition.replace("user_data.", "")
                return bool(context.user_data.get(key))
            
        except Exception as e:
            logger.error(f"Ошибка проверки условия '{condition}': {e}")
        
        return False


# Глобальные экземпляры
_global_executor: Optional[ScenarioExecutor] = None
_global_integrator: Optional[ScenarioIntegrator] = None
_global_orchestrator: Optional[ScenarioOrchestrator] = None


def get_executor() -> ScenarioExecutor:
    """Получить глобальный исполнитель сценариев"""
    global _global_executor
    if _global_executor is None:
        raise RuntimeError("Исполнитель сценариев не инициализирован")
    return _global_executor


def get_integrator() -> ScenarioIntegrator:
    """Получить глобальный интегратор сценариев"""
    global _global_integrator
    if _global_integrator is None:
        raise RuntimeError("Интегратор сценариев не инициализирован")
    return _global_integrator


def get_orchestrator() -> ScenarioOrchestrator:
    """Получить глобальный оркестратор сценариев"""
    global _global_orchestrator
    if _global_orchestrator is None:
        raise RuntimeError("Оркестратор сценариев не инициализирован")
    return _global_orchestrator


def init_scenario_system(dialog_engine: DialogEngine) -> tuple:
    """Инициализировать всю систему сценариев"""
    global _global_executor, _global_integrator, _global_orchestrator
    
    _global_executor = ScenarioExecutor(dialog_engine)
    _global_integrator = ScenarioIntegrator(_global_executor)
    _global_orchestrator = ScenarioOrchestrator(_global_executor)
    
    logger.info("Система сценариев инициализирована")
    return _global_executor, _global_integrator, _global_orchestrator