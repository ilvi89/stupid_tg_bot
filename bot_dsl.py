#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram-бот для английского клуба - полная реализация на DSL
Использует декларативные сценарии для всех диалогов
"""

import logging
import os
import asyncio
from typing import Dict, Any

from telegram.ext import Application, ContextTypes
from dotenv import load_dotenv

# Импорт DSL системы
from dsl_bootstrap import DSLBootstrap
from scenarios.executor import get_executor, get_integrator
from dsl_interfaces import get_user_interface, get_manager_interface, get_system_interface


# Загрузка переменных окружения
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

# Конфигурация
BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
DATABASE_PATH = os.getenv('DATABASE_PATH', 'english_club.db')


class DSLTelegramBot:
    """Telegram-бот на основе DSL сценариев"""
    
    def __init__(self):
        self.db_path = DATABASE_PATH
        self.application = None
        self.bootstrap = DSLBootstrap(self.db_path)
        self.init_completed = False
        
        # Инициализация компонентов
        self._init_database()
    
    def _init_database(self):
        """Инициализация базы данных"""
        import sqlite3
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица пользователей
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
    
    async def _initialize_dsl_system(self):
        """Инициализация DSL системы"""
        if self.init_completed:
            return True
        
        logger.info("Инициализация DSL системы...")
        result = await self.bootstrap.initialize()
        
        if result["success"]:
            self.init_completed = True
            logger.info("DSL система инициализирована успешно")
            
            # Выводим отчет
            report = self.bootstrap.get_initialization_report()
            print(report.replace("<b>", "").replace("</b>", "").replace("<i>", "").replace("</i>", ""))
            
            return True
        else:
            logger.error(f"Ошибка инициализации DSL: {result['error']}")
            return False
    
    async def create_application(self) -> Application:
        """Создать Telegram Application"""
        if BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
            raise ValueError("Необходимо установить BOT_TOKEN!")
        
        # Инициализируем DSL систему
        if not await self._initialize_dsl_system():
            raise RuntimeError("Не удалось инициализировать DSL систему")
        
        # Создаем приложение
        self.application = Application.builder().token(BOT_TOKEN).build()
        
        # Интегрируем сценарии с приложением
        integrator = get_integrator()
        integrator.integrate_with_application(self.application)
        
        # Добавляем дополнительные обработчики
        self._add_system_handlers()
        
        return self.application
    
    def _add_system_handlers(self):
        """Добавить системные обработчики"""
        from telegram.ext import CommandHandler
        
        # Команды отладки и управления
        debug_commands = [
            ('scenario_info', self._debug_scenario_info),
            ('scenario_list', self._debug_scenario_list),
            ('scenario_stats', self._debug_scenario_stats),
            ('scenario_reload', self._debug_scenario_reload),
            ('scenario_cancel', self._debug_scenario_cancel),
        ]
        
        for command, handler in debug_commands:
            self.application.add_handler(CommandHandler(command, handler))
        
        logger.info(f"Добавлено {len(debug_commands)} системных команд")
    
    async def _debug_scenario_info(self, update, context):
        """Команда отладки - информация о текущем сценарии"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        session = await self.dialog_engine.get_session(user_id, chat_id)
        
        if session:
            registry = get_registry()
            scenario = registry.get_scenario(session.chain_id)
            scenario_name = scenario.metadata.name if scenario else "Неизвестно"
            
            info_text = (
                f"🔍 <b>Информация о сценарии</b>\n\n"
                f"📋 <b>Сценарий:</b> {scenario_name}\n"
                f"🆔 <b>ID:</b> {session.chain_id}\n"
                f"📍 <b>Текущий шаг:</b> {session.current_step}\n"
                f"🔘 <b>Состояние:</b> {session.state.value}\n"
                f"🔄 <b>Попыток:</b> {session.retry_count}\n"
                f"📊 <b>Данных:</b> {len(session.data)} полей\n"
                f"⏰ <b>Создан:</b> {session.created_at}\n"
                f"🔄 <b>Обновлен:</b> {session.updated_at}"
            )
        else:
            info_text = "ℹ️ Активных сценариев не найдено"
        
        await update.message.reply_text(info_text, parse_mode='HTML')
    
    async def _debug_scenario_list(self, update, context):
        """Команда отладки - список всех сценариев"""
        registry = get_registry()
        scenarios = registry.get_enabled_scenarios()
        
        if scenarios:
            scenarios_text = "📋 <b>Зарегистрированные сценарии:</b>\n\n"
            
            for scenario_id, scenario in scenarios.items():
                scenarios_text += (
                    f"📌 <b>{scenario.metadata.name}</b>\n"
                    f"   🆔 ID: {scenario_id}\n"
                    f"   📂 Категория: {scenario.metadata.category.value}\n"
                    f"   👤 Тип: {scenario.metadata.type.value}\n"
                    f"   🚪 Входы: {', '.join(scenario.entry_points[:3])}\n\n"
                )
        else:
            scenarios_text = "📭 Нет зарегистрированных сценариев"
        
        await update.message.reply_text(scenarios_text, parse_mode='HTML')
    
    async def _debug_scenario_stats(self, update, context):
        """Команда отладки - статистика сценариев"""
        registry = get_registry()
        stats = registry.get_statistics()
        
        stats_text = (
            f"📊 <b>Статистика сценариев</b>\n\n"
            f"📋 <b>Общее:</b>\n"
            f"• Всего сценариев: {stats['total_scenarios']}\n"
            f"• Активных: {stats['enabled_scenarios']}\n"
            f"• Отключенных: {stats['disabled_scenarios']}\n"
            f"• Точек входа: {stats['entry_points']}\n\n"
            f"📂 <b>По категориям:</b>\n"
        )
        
        for category, count in stats['categories'].items():
            if count > 0:
                stats_text += f"• {category}: {count}\n"
        
        stats_text += f"\n👤 <b>По типам:</b>\n"
        for type_name, count in stats['types'].items():
            if count > 0:
                stats_text += f"• {type_name}: {count}\n"
        
        if stats['missing_dependencies']:
            stats_text += f"\n⚠️ <b>Проблемы с зависимостями:</b>\n"
            for scenario_id, missing in stats['missing_dependencies'].items():
                stats_text += f"• {scenario_id}: отсутствуют {', '.join(missing)}\n"
        
        await update.message.reply_text(stats_text, parse_mode='HTML')
    
    async def _debug_scenario_reload(self, update, context):
        """Команда отладки - перезагрузка сценариев"""
        # Проверяем права доступа
        from auth_manager import auth_manager
        user_id = update.effective_user.id
        
        if not auth_manager.is_authorized(user_id):
            await update.message.reply_text("🔒 Команда доступна только менеджерам")
            return
        
        try:
            # Перезагружаем сценарии
            result = self.scenario_executor.reload_scenarios()
            
            if result['success']:
                reload_text = (
                    f"✅ <b>Сценарии перезагружены!</b>\n\n"
                    f"📊 Было: {result['old_count']}\n"
                    f"📊 Стало: {result['new_count']}\n"
                    f"🔄 Перезагружено: {result['reloaded']}"
                )
            else:
                reload_text = f"❌ <b>Ошибка перезагрузки:</b> {result['error']}"
            
            await update.message.reply_text(reload_text, parse_mode='HTML')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {e}")
    
    async def _debug_scenario_cancel(self, update, context):
        """Команда отладки - отмена текущего сценария"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        if await self.scenario_executor.force_stop_execution(user_id, chat_id, "Отменено пользователем"):
            await update.message.reply_text("✅ Текущий сценарий отменен")
        else:
            await update.message.reply_text("ℹ️ Активных сценариев не найдено")
    
    async def cleanup_expired_sessions(self):
        """Очистка истекших сессий (запускается периодически)"""
        try:
            # Очищаем диалоговые сессии
            dialog_expired = await self.dialog_engine.storage.cleanup_expired_sessions(86400)  # 24 часа
            
            # Очищаем сессии авторизации
            from auth_manager import auth_manager
            auth_expired = auth_manager.cleanup_expired_sessions()
            
            if dialog_expired > 0 or auth_expired > 0:
                logger.info(f"Очищено сессий: диалоговых {dialog_expired}, авторизационных {auth_expired}")
            
        except Exception as e:
            logger.error(f"Ошибка очистки сессий: {e}")
    
    async def run(self):
        """Запустить бота"""
        # Создаем приложение
        application = await self.create_application()
        
        # Настраиваем периодическую очистку
        async def periodic_cleanup():
            while True:
                await asyncio.sleep(3600)  # Каждый час
                await self.cleanup_expired_sessions()
        
        # Запускаем очистку в фоне
        cleanup_task = asyncio.create_task(periodic_cleanup())
        
        try:
            logger.info("🤖 DSL Бот запущен! Нажмите Ctrl+C для остановки.")
            print("🤖 DSL Бот запущен! Нажмите Ctrl+C для остановки.")
            
            # Первоначальная очистка
            await self.cleanup_expired_sessions()
            
            # Показываем статистику загруженных сценариев
            registry = get_registry()
            stats = registry.get_statistics()
            logger.info(f"Активных сценариев: {stats['enabled_scenarios']}")
            
            # Запускаем polling
            await application.run_polling()
            
        except KeyboardInterrupt:
            logger.info("Получен сигнал остановки")
        finally:
            cleanup_task.cancel()
            logger.info("Бот остановлен")


def main():
    """Главная функция"""
    try:
        bot = DSLTelegramBot()
        asyncio.run(bot.run())
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        print(f"❌ Критическая ошибка: {e}")


if __name__ == '__main__':
    main()