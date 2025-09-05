#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Система инициализации и запуска DSL бота
"""

import logging
import os
import asyncio
from typing import Dict, Any, Optional

from dialog_dsl import init_dialog_engine
from scenarios.registry import get_registry
from scenarios.loader import get_loader
from scenarios.executor import init_scenario_system
from scenarios.compositions import init_composition_manager
from scenarios.auto_register import ScenarioDiscovery
from interfaces import get_user_interface, get_manager_interface, get_composition_interface, get_system_interface


logger = logging.getLogger(__name__)


class DSLBootstrap:
    """Система инициализации DSL бота"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.dialog_engine = None
        self.scenario_executor = None
        self.scenario_integrator = None
        self.scenario_orchestrator = None
        self.composition_manager = None
        
        # Статистика инициализации
        self.init_stats = {
            "scenarios_loaded": 0,
            "compositions_loaded": 0,
            "errors": [],
            "warnings": []
        }
    
    async def initialize(self) -> Dict[str, Any]:
        """Полная инициализация DSL системы"""
        try:
            logger.info("Начинаем инициализацию DSL системы...")
            
            # 1. Инициализация движка диалогов
            await self._init_dialog_engine()
            
            # 2. Инициализация системы сценариев
            await self._init_scenario_system()
            
            # 3. Автоматическое обнаружение и регистрация сценариев
            await self._discover_and_register_scenarios()
            
            # 4. Инициализация композиций
            await self._init_compositions()
            
            # 5. Инициализация интерфейсов
            await self._init_interfaces()
            
            # 6. Валидация всей системы
            await self._validate_system()
            
            logger.info("DSL система успешно инициализирована")
            return {
                "success": True,
                "stats": self.init_stats
            }
            
        except Exception as e:
            logger.error(f"Критическая ошибка инициализации: {e}")
            return {
                "success": False,
                "error": str(e),
                "stats": self.init_stats
            }
    
    async def _init_dialog_engine(self):
        """Инициализация движка диалогов"""
        logger.info("Инициализация движка диалогов...")
        self.dialog_engine = init_dialog_engine(self.db_path)
        logger.info("✅ Движок диалогов инициализирован")
    
    async def _init_scenario_system(self):
        """Инициализация системы сценариев"""
        logger.info("Инициализация системы сценариев...")
        self.scenario_executor, self.scenario_integrator, self.scenario_orchestrator = init_scenario_system(
            self.dialog_engine
        )
        logger.info("✅ Система сценариев инициализирована")
    
    async def _discover_and_register_scenarios(self):
        """Автоматическое обнаружение и регистрация сценариев"""
        logger.info("Автоматическое обнаружение сценариев...")
        
        try:
            # Используем автообнаружение
            stats = ScenarioDiscovery.discover_and_register_all()
            
            if "error" in stats:
                self.init_stats["errors"].append(f"Ошибка автообнаружения: {stats['error']}")
            else:
                self.init_stats["scenarios_loaded"] = stats.get("total_scenarios", 0)
                logger.info(f"✅ Автоматически обнаружено {self.init_stats['scenarios_loaded']} сценариев")
            
            # Дополнительная загрузка из директории
            loader = get_loader()
            scenarios_dir = os.path.join(os.path.dirname(__file__), "scenarios")
            load_result = loader.load_from_directory(scenarios_dir)
            
            if load_result["errors"] > 0:
                for error in load_result["error_details"]:
                    self.init_stats["warnings"].append(error)
            
            self.init_stats["scenarios_loaded"] += load_result["loaded"]
            
        except Exception as e:
            error_msg = f"Ошибка обнаружения сценариев: {e}"
            self.init_stats["errors"].append(error_msg)
            logger.error(error_msg)
    
    async def _init_compositions(self):
        """Инициализация композиций"""
        logger.info("Инициализация композиций...")
        
        try:
            self.composition_manager = init_composition_manager(self.scenario_orchestrator)
            
            # Регистрируем демонстрационные композиции
            from scenarios.compositions_demo import register_all_compositions
            if register_all_compositions():
                self.init_stats["compositions_loaded"] = len(self.composition_manager.registry.compositions)
                logger.info(f"✅ Зарегистрировано {self.init_stats['compositions_loaded']} композиций")
            
        except Exception as e:
            error_msg = f"Ошибка инициализации композиций: {e}"
            self.init_stats["errors"].append(error_msg)
            logger.error(error_msg)
    
    async def _init_interfaces(self):
        """Инициализация интерфейсов"""
        logger.info("Инициализация интерфейсов...")
        
        try:
            # Инициализируем все интерфейсы (они создаются при первом вызове)
            get_user_interface()
            get_manager_interface()
            get_composition_interface()
            get_system_interface()
            
            logger.info("✅ Интерфейсы инициализированы")
            
        except Exception as e:
            error_msg = f"Ошибка инициализации интерфейсов: {e}"
            self.init_stats["errors"].append(error_msg)
            logger.error(error_msg)
    
    async def _validate_system(self):
        """Валидация всей системы"""
        logger.info("Валидация системы...")
        
        try:
            # Проверяем сценарии
            registry = get_registry()
            validation_errors = get_loader().validate_all_scenarios()
            
            if validation_errors:
                for scenario_id, errors in validation_errors.items():
                    for error in errors:
                        warning_msg = f"Сценарий '{scenario_id}': {error}"
                        self.init_stats["warnings"].append(warning_msg)
                        logger.warning(warning_msg)
            
            # Проверяем зависимости
            missing_deps = registry.validate_dependencies()
            if missing_deps:
                for scenario_id, deps in missing_deps.items():
                    warning_msg = f"Сценарий '{scenario_id}' имеет отсутствующие зависимости: {deps}"
                    self.init_stats["warnings"].append(warning_msg)
                    logger.warning(warning_msg)
            
            logger.info("✅ Валидация системы завершена")
            
        except Exception as e:
            error_msg = f"Ошибка валидации: {e}"
            self.init_stats["errors"].append(error_msg)
            logger.error(error_msg)
    
    def get_initialization_report(self) -> str:
        """Получить отчет об инициализации"""
        report = "🚀 <b>Отчет об инициализации DSL системы</b>\n\n"
        
        if self.init_stats["scenarios_loaded"] > 0:
            report += f"✅ Загружено сценариев: {self.init_stats['scenarios_loaded']}\n"
        
        if self.init_stats["compositions_loaded"] > 0:
            report += f"✅ Загружено композиций: {self.init_stats['compositions_loaded']}\n"
        
        if self.init_stats["warnings"]:
            report += f"\n⚠️ Предупреждения ({len(self.init_stats['warnings'])}):\n"
            for warning in self.init_stats["warnings"][:5]:  # Показываем первые 5
                report += f"• {warning}\n"
            
            if len(self.init_stats["warnings"]) > 5:
                report += f"• ... и еще {len(self.init_stats['warnings']) - 5}\n"
        
        if self.init_stats["errors"]:
            report += f"\n❌ Ошибки ({len(self.init_stats['errors'])}):\n"
            for error in self.init_stats["errors"]:
                report += f"• {error}\n"
        
        if not self.init_stats["errors"]:
            report += "\n🎉 Система готова к работе!"
        
        return report


class DSLLauncher:
    """Запускальщик DSL бота"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.bootstrap = DSLBootstrap(db_path)
        self.application = None
    
    async def launch(self) -> bool:
        """Запустить DSL бота"""
        try:
            # Инициализация
            print("🚀 Инициализация DSL системы...")
            init_result = await self.bootstrap.initialize()
            
            if not init_result["success"]:
                print(f"❌ Ошибка инициализации: {init_result['error']}")
                return False
            
            # Показываем отчет
            report = self.bootstrap.get_initialization_report()
            print(report.replace("<b>", "").replace("</b>", "").replace("<i>", "").replace("</i>", ""))
            
            # Создаем Telegram Application
            print("\n📱 Создание Telegram приложения...")
            from bot import DSLTelegramBot
            
            bot = DSLTelegramBot()
            self.application = bot.create_application()
            
            # Запускаем
            print("\n🤖 Запускаем DSL бота...")
            print("Для остановки нажмите Ctrl+C")
            
            await self.application.run_polling()
            
            return True
            
        except KeyboardInterrupt:
            print("\n👋 Бот остановлен пользователем")
            logger.info("Бот остановлен пользователем")
            return True
            
        except Exception as e:
            print(f"\n❌ Критическая ошибка запуска: {e}")
            logger.error(f"Критическая ошибка запуска: {e}")
            return False
    
    def get_launch_info(self) -> Dict[str, Any]:
        """Получить информацию о запуске"""
        return {
            "bootstrap_stats": self.bootstrap.init_stats,
            "application_ready": self.application is not None
        }


# Глобальный экземпляр
_global_launcher: Optional[DSLLauncher] = None


def get_launcher(db_path: str = None) -> DSLLauncher:
    """Получить глобальный запускальщик"""
    global _global_launcher
    if _global_launcher is None:
        if db_path is None:
            db_path = os.getenv('DATABASE_PATH', 'english_club.db')
        _global_launcher = DSLLauncher(db_path)
    return _global_launcher


async def quick_launch():
    """Быстрый запуск DSL бота"""
    db_path = os.getenv('DATABASE_PATH', 'english_club.db')
    launcher = get_launcher(db_path)
    return await launcher.launch()