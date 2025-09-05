#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DSL интерфейсы - обертки для работы с пользовательскими и менеджерскими функциями через сценарии
"""

import logging
from typing import Dict, Any, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from scenarios.registry import get_registry, ScenarioType
from scenarios.executor import get_executor


logger = logging.getLogger(__name__)


class DSLUserInterface:
    """Пользовательский интерфейс на основе DSL сценариев"""
    
    def __init__(self):
        self.executor = get_executor()
        self.registry = get_registry()
    
    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать главное меню пользователя"""
        # Получаем доступные пользовательские сценарии
        user_scenarios = self.registry.get_scenarios_by_type(ScenarioType.USER)
        
        keyboard = []
        
        # Основные функции
        main_functions = [
            ("👤 Мой профиль", "scenario_profile_view"),
            ("✏️ Редактировать профиль", "scenario_profile_edit"),
            ("📞 Поддержка", "scenario_support_request"),
            ("❓ Частые вопросы", "scenario_support_faq_only")
        ]
        
        for text, callback_data in main_functions:
            keyboard.append([InlineKeyboardButton(text, callback_data=callback_data)])
        
        # Дополнительные сценарии
        additional_scenarios = []
        for scenario in user_scenarios:
            if scenario.metadata.enabled and "demo" not in scenario.metadata.tags:
                for entry_point in scenario.entry_points:
                    if not entry_point.startswith("/") and entry_point not in ["start", "registration"]:
                        additional_scenarios.append(
                            (f"🎯 {scenario.metadata.name}", f"scenario_{scenario.metadata.id}")
                        )
                        break
        
        # Добавляем дополнительные сценарии (максимум 3)
        for text, callback_data in additional_scenarios[:3]:
            keyboard.append([InlineKeyboardButton(text, callback_data=callback_data)])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        menu_text = (
            "🇬🇧 <b>Главное меню</b>\n\n"
            "Добро пожаловать в английский клуб!\n"
            "Выберите действие:"
        )
        
        if update.message:
            await update.message.reply_text(menu_text, parse_mode='HTML', reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.edit_message_text(menu_text, parse_mode='HTML', reply_markup=reply_markup)
    
    async def show_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать справку пользователя"""
        help_text = (
            "🤖 <b>Справка по боту</b>\n\n"
            "📝 <b>Основные команды:</b>\n"
            "/start - Регистрация в клубе\n"
            "/menu - Главное меню\n"
            "/profile - Мой профиль\n"
            "/support - Обращение в поддержку\n"
            "/help - Эта справка\n\n"
            "🎯 <b>Доступные сценарии:</b>\n"
        )
        
        # Добавляем информацию о доступных сценариях
        user_scenarios = self.registry.get_scenarios_by_type(ScenarioType.USER)
        enabled_scenarios = [s for s in user_scenarios if s.metadata.enabled]
        
        for scenario in enabled_scenarios[:5]:  # Показываем первые 5
            help_text += f"• {scenario.metadata.name} - {scenario.metadata.description[:50]}...\n"
        
        help_text += (
            f"\n📊 Всего доступно {len(enabled_scenarios)} сценариев\n\n"
            "❓ <b>Нужна помощь?</b>\n"
            "Используйте /support для обращения в службу поддержки!"
        )
        
        keyboard = [
            [InlineKeyboardButton("📞 Обратиться в поддержку", callback_data="scenario_support_request")],
            [InlineKeyboardButton("❓ Частые вопросы", callback_data="scenario_support_faq_only")],
            [InlineKeyboardButton("🔙 В главное меню", callback_data="show_main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(help_text, parse_mode='HTML', reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.edit_message_text(help_text, parse_mode='HTML', reply_markup=reply_markup)
    
    async def handle_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Обработать callback от пользовательского меню"""
        if not update.callback_query:
            return False
        
        callback_data = update.callback_query.data
        
        if callback_data == "show_main_menu":
            await self.show_main_menu(update, context)
            return True
        elif callback_data == "show_help":
            await self.show_help(update, context)
            return True
        elif callback_data.startswith("scenario_"):
            # Передаем в исполнитель сценариев
            return await self.executor.handle_callback(update, context)
        
        return False


class DSLManagerInterface:
    """Менеджерский интерфейс на основе DSL сценариев"""
    
    def __init__(self):
        self.executor = get_executor()
        self.registry = get_registry()
    
    async def show_admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать административную панель"""
        from auth_manager import auth_manager
        
        user_id = update.effective_user.id
        if not auth_manager.is_authorized(user_id):
            await update.message.reply_text(
                "🔒 Для доступа к панели управления требуется авторизация.\n"
                "Используйте команду /manager"
            )
            return
        
        # Получаем менеджерские сценарии
        manager_scenarios = self.registry.get_scenarios_by_type(ScenarioType.MANAGER)
        enabled_scenarios = [s for s in manager_scenarios if s.metadata.enabled]
        
        keyboard = []
        
        # Основные функции
        main_functions = [
            ("📊 Статистика", "scenario_admin_stats"),
            ("👥 Пользователи", "scenario_user_management"),
            ("📢 Рассылка", "scenario_broadcast_creation"),
            ("📁 Экспорт данных", "scenario_data_export"),
            ("⚙️ Управление системой", "scenario_system_management")
        ]
        
        for text, callback_data in main_functions:
            keyboard.append([InlineKeyboardButton(text, callback_data=callback_data)])
        
        # Дополнительные функции
        keyboard.extend([
            [InlineKeyboardButton("🔄 Перезагрузить сценарии", callback_data="reload_scenarios")],
            [InlineKeyboardButton("📋 Список сценариев", callback_data="list_scenarios")],
            [InlineKeyboardButton("📊 Статистика сценариев", callback_data="scenario_stats")],
            [InlineKeyboardButton("🚪 Выход", callback_data="manager_logout")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Получаем информацию о сессии
        session_info = auth_manager.get_session_info(user_id)
        time_left = auth_manager.get_session_time_left(user_id)
        
        panel_text = (
            "🔧 <b>Панель управления</b>\n\n"
            f"👤 Менеджер: {update.effective_user.first_name}\n"
            f"⏰ Сессия истекает через: {time_left // 60} мин {time_left % 60} сек\n"
            f"🎭 Доступно сценариев: {len(enabled_scenarios)}\n\n"
            "Выберите действие:"
        )
        
        if update.message:
            await update.message.reply_text(panel_text, parse_mode='HTML', reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.edit_message_text(panel_text, parse_mode='HTML', reply_markup=reply_markup)
    
    async def show_scenario_statistics(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать статистику сценариев"""
        stats = self.registry.get_statistics()
        execution_stats = await self.executor.get_execution_statistics()
        
        stats_text = (
            "📊 <b>Статистика DSL системы</b>\n\n"
            "🎭 <b>Сценарии:</b>\n"
            f"• Всего зарегистрировано: {stats['total_scenarios']}\n"
            f"• Активных: {stats['enabled_scenarios']}\n"
            f"• Отключенных: {stats['disabled_scenarios']}\n"
            f"• Точек входа: {stats['entry_points']}\n\n"
            "🏃 <b>Выполнение:</b>\n"
            f"• Активных сессий: {execution_stats['active_executions']}\n\n"
            "📂 <b>По категориям:</b>\n"
        )
        
        for category, count in stats['categories'].items():
            if count > 0:
                stats_text += f"• {category}: {count}\n"
        
        stats_text += "\n👤 <b>По типам:</b>\n"
        for type_name, count in stats['types'].items():
            if count > 0:
                stats_text += f"• {type_name}: {count}\n"
        
        if stats['missing_dependencies']:
            stats_text += "\n⚠️ <b>Проблемы:</b>\n"
            for scenario_id, missing in stats['missing_dependencies'].items():
                stats_text += f"• {scenario_id}: нет {', '.join(missing)}\n"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data="refresh_scenario_stats")],
            [InlineKeyboardButton("📋 Список сценариев", callback_data="list_all_scenarios")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(stats_text, parse_mode='HTML', reply_markup=reply_markup)
        else:
            await update.message.reply_text(stats_text, parse_mode='HTML', reply_markup=reply_markup)
    
    async def show_scenario_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать список всех сценариев"""
        scenarios = self.registry.get_enabled_scenarios()
        
        if not scenarios:
            await update.callback_query.edit_message_text(
                "📭 <b>Нет зарегистрированных сценариев</b>"
            )
            return
        
        scenarios_text = "📋 <b>Зарегистрированные сценарии:</b>\n\n"
        
        # Группируем по типам
        by_type = {}
        for scenario in scenarios.values():
            scenario_type = scenario.metadata.type.value
            if scenario_type not in by_type:
                by_type[scenario_type] = []
            by_type[scenario_type].append(scenario)
        
        for type_name, type_scenarios in by_type.items():
            scenarios_text += f"👤 <b>{type_name.upper()}:</b>\n"
            
            for scenario in type_scenarios[:5]:  # Максимум 5 на тип
                status = "🟢" if scenario.metadata.enabled else "🔴"
                scenarios_text += (
                    f"{status} <b>{scenario.metadata.name}</b>\n"
                    f"   🆔 {scenario.metadata.id}\n"
                    f"   📂 {scenario.metadata.category.value}\n"
                    f"   🚪 {', '.join(scenario.entry_points[:2])}\n\n"
                )
        
        if len(scenarios) > 15:  # Если сценариев много
            scenarios_text += f"... и еще {len(scenarios) - 15} сценариев\n"
        
        keyboard = [
            [InlineKeyboardButton("📊 Статистика сценариев", callback_data="scenario_stats")],
            [InlineKeyboardButton("🔄 Перезагрузить", callback_data="reload_scenarios")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(scenarios_text, parse_mode='HTML', reply_markup=reply_markup)
    
    async def handle_admin_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Обработать callback от административного интерфейса"""
        if not update.callback_query:
            return False
        
        callback_data = update.callback_query.data
        
        # Проверяем авторизацию для административных функций
        from auth_manager import auth_manager
        user_id = update.effective_user.id
        
        admin_callbacks = ["scenario_stats", "list_all_scenarios", "reload_scenarios"]
        if callback_data in admin_callbacks and not auth_manager.is_authorized(user_id):
            await update.callback_query.answer("🔒 Требуется авторизация менеджера", show_alert=True)
            return True
        
        # Обработка callback'ов
        if callback_data == "show_admin_panel":
            await self.show_admin_panel(update, context)
            return True
        elif callback_data == "scenario_stats":
            await self.show_scenario_statistics(update, context)
            return True
        elif callback_data == "list_all_scenarios":
            await self.show_scenario_list(update, context)
            return True
        elif callback_data == "reload_scenarios":
            await self._reload_scenarios(update, context)
            return True
        elif callback_data == "back_to_admin_panel":
            await self.show_admin_panel(update, context)
            return True
        elif callback_data.startswith("scenario_"):
            # Передаем в исполнитель сценариев
            return await self.executor.handle_callback(update, context)
        
        return False
    
    async def _reload_scenarios(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Перезагрузить сценарии"""
        try:
            result = self.executor.reload_scenarios()
            
            if result['success']:
                reload_text = (
                    f"✅ <b>Сценарии перезагружены!</b>\n\n"
                    f"📊 Было: {result['old_count']}\n"
                    f"📊 Стало: {result['new_count']}\n"
                    f"🔄 Обновлено: {result['reloaded']}"
                )
            else:
                reload_text = f"❌ <b>Ошибка перезагрузки:</b>\n{result['error']}"
            
            keyboard = [
                [InlineKeyboardButton("📋 Список сценариев", callback_data="list_all_scenarios")],
                [InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin_panel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                reload_text, parse_mode='HTML', reply_markup=reply_markup
            )
            
        except Exception as e:
            await update.callback_query.edit_message_text(
                f"❌ <b>Критическая ошибка:</b>\n{e}",
                parse_mode='HTML'
            )


class DSLCompositionInterface:
    """Интерфейс для работы с композициями сценариев"""
    
    def __init__(self):
        self.executor = get_executor()
        self.registry = get_registry()
    
    async def show_compositions_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать меню композиций"""
        from scenarios.compositions import get_composition_manager
        
        try:
            composition_manager = get_composition_manager()
            compositions = composition_manager.registry.compositions
            
            keyboard = []
            
            # Пользовательские композиции
            user_compositions = [
                ("🎯 Полный онбординг", "composition_complete_onboarding"),
                ("👤 Управление профилем", "composition_profile_management"),
                ("📞 Поток поддержки", "composition_user_support_flow")
            ]
            
            for text, callback_data in user_compositions:
                keyboard.append([InlineKeyboardButton(text, callback_data=callback_data)])
            
            # Менеджерские композиции (если авторизован)
            from auth_manager import auth_manager
            user_id = update.effective_user.id
            
            if auth_manager.is_authorized(user_id):
                keyboard.append([InlineKeyboardButton("🔧 Панель менеджера", callback_data="composition_manager_dashboard")])
            
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            menu_text = (
                "🎭 <b>Композиции сценариев</b>\n\n"
                "Композиции - это связанные наборы сценариев для выполнения сложных задач.\n\n"
                f"📊 Доступно композиций: {len(compositions)}\n\n"
                "Выберите композицию:"
            )
            
            if update.callback_query:
                await update.callback_query.edit_message_text(menu_text, parse_mode='HTML', reply_markup=reply_markup)
            else:
                await update.message.reply_text(menu_text, parse_mode='HTML', reply_markup=reply_markup)
                
        except Exception as e:
            error_text = f"❌ Ошибка загрузки композиций: {e}"
            if update.callback_query:
                await update.callback_query.edit_message_text(error_text)
            else:
                await update.message.reply_text(error_text)
    
    async def handle_composition_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Обработать callback от композиций"""
        if not update.callback_query:
            return False
        
        callback_data = update.callback_query.data
        
        if callback_data.startswith("composition_"):
            composition_id = callback_data.replace("composition_", "")
            
            try:
                from scenarios.compositions import get_composition_manager
                composition_manager = get_composition_manager()
                
                success = await composition_manager.execute_composition(update, context, composition_id)
                
                if not success:
                    await update.callback_query.edit_message_text(
                        f"❌ Не удалось запустить композицию '{composition_id}'"
                    )
                
                return True
                
            except Exception as e:
                await update.callback_query.edit_message_text(
                    f"❌ Ошибка запуска композиции: {e}"
                )
                return True
        
        return False


class DSLSystemInterface:
    """Системный интерфейс для управления DSL"""
    
    def __init__(self):
        self.executor = get_executor()
        self.registry = get_registry()
    
    async def show_system_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать состояние системы"""
        # Проверяем права доступа
        from auth_manager import auth_manager
        user_id = update.effective_user.id
        
        if not auth_manager.is_authorized(user_id):
            await update.message.reply_text("🔒 Команда доступна только менеджерам")
            return
        
        try:
            # Статистика реестра
            registry_stats = self.registry.get_statistics()
            
            # Статистика выполнения
            execution_stats = await self.executor.get_execution_statistics()
            
            # Статистика композиций
            try:
                from scenarios.compositions import get_composition_manager
                composition_manager = get_composition_manager()
                composition_count = len(composition_manager.registry.compositions)
            except:
                composition_count = 0
            
            status_text = (
                "🖥️ <b>Состояние DSL системы</b>\n\n"
                "🎭 <b>Сценарии:</b>\n"
                f"• Зарегистрировано: {registry_stats['total_scenarios']}\n"
                f"• Активных: {registry_stats['enabled_scenarios']}\n"
                f"• Точек входа: {registry_stats['entry_points']}\n\n"
                "🏃 <b>Выполнение:</b>\n"
                f"• Активных сессий: {execution_stats['active_executions']}\n\n"
                "🎭 <b>Композиции:</b>\n"
                f"• Зарегистрировано: {composition_count}\n\n"
                "📊 <b>По типам:</b>\n"
            )
            
            for type_name, count in execution_stats['scenario_types'].items():
                if count > 0:
                    status_text += f"• {type_name}: {count}\n"
            
            keyboard = [
                [InlineKeyboardButton("🔄 Обновить", callback_data="refresh_system_status")],
                [InlineKeyboardButton("🧹 Очистить сессии", callback_data="cleanup_sessions")],
                [InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin_panel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if update.callback_query:
                await update.callback_query.edit_message_text(status_text, parse_mode='HTML', reply_markup=reply_markup)
            else:
                await update.message.reply_text(status_text, parse_mode='HTML', reply_markup=reply_markup)
                
        except Exception as e:
            error_text = f"❌ Ошибка получения статистики системы: {e}"
            if update.callback_query:
                await update.callback_query.edit_message_text(error_text)
            else:
                await update.message.reply_text(error_text)


# Глобальные интерфейсы
_user_interface: Optional[DSLUserInterface] = None
_manager_interface: Optional[DSLManagerInterface] = None
_composition_interface: Optional[DSLCompositionInterface] = None
_system_interface: Optional[DSLSystemInterface] = None


def get_user_interface() -> DSLUserInterface:
    """Получить пользовательский интерфейс"""
    global _user_interface
    if _user_interface is None:
        _user_interface = DSLUserInterface()
    return _user_interface


def get_manager_interface() -> DSLManagerInterface:
    """Получить менеджерский интерфейс"""
    global _manager_interface
    if _manager_interface is None:
        _manager_interface = DSLManagerInterface()
    return _manager_interface


def get_composition_interface() -> DSLCompositionInterface:
    """Получить интерфейс композиций"""
    global _composition_interface
    if _composition_interface is None:
        _composition_interface = DSLCompositionInterface()
    return _composition_interface


def get_system_interface() -> DSLSystemInterface:
    """Получить системный интерфейс"""
    global _system_interface
    if _system_interface is None:
        _system_interface = DSLSystemInterface()
    return _system_interface