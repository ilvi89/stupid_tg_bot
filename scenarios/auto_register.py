#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Автоматическая регистрация сценариев при импорте модулей
"""

import logging
from typing import Any, Callable

from dialog_dsl import DialogChain
from .registry import ScenarioRegistry, ScenarioMetadata, ScenarioType, ScenarioCategory, get_registry


logger = logging.getLogger(__name__)


def scenario(id: str = None, name: str = None, description: str = "", 
            type: ScenarioType = ScenarioType.USER,
            category: ScenarioCategory = ScenarioCategory.SUPPORT,
            entry_points: list = None, permissions: list = None,
            version: str = "1.0", author: str = "", tags: list = None,
            enabled: bool = True, priority: int = 0):
    """
    Декоратор для автоматической регистрации сценариев
    
    Использование:
    @scenario(
        id="my_scenario",
        name="Мой сценарий", 
        type=ScenarioType.USER,
        category=ScenarioCategory.REGISTRATION,
        entry_points=["/start", "begin"]
    )
    def create_my_scenario():
        return DialogBuilder(...).build()
    """
    def decorator(func: Callable[[], DialogChain]):
        def wrapper():
            # Вызываем оригинальную функцию для получения цепочки
            chain = func()
            
            # Создаем метаданные
            metadata = ScenarioMetadata(
                id=id or func.__name__.replace("create_", "").replace("_scenario", ""),
                name=name or func.__name__.replace("_", " ").title(),
                description=description or func.__doc__ or "",
                type=type,
                category=category,
                version=version,
                author=author or func.__module__,
                permissions=permissions or [],
                tags=tags or [],
                enabled=enabled,
                priority=priority
            )
            
            # Регистрируем в глобальном реестре
            registry = get_registry()
            registry.register_scenario(metadata, chain, entry_points or [])
            
            return chain
        
        # Сохраняем оригинальные атрибуты функции
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        wrapper.__module__ = func.__module__
        wrapper._scenario_metadata = {
            'id': id,
            'name': name,
            'type': type,
            'category': category
        }
        
        # Автоматически вызываем функцию для регистрации сценария при импорте
        try:
            wrapper()
            logger.info(f"Автоматически зарегистрирован сценарий '{id}' из модуля '{func.__module__}'")
        except Exception as e:
            logger.error(f"Ошибка автоматической регистрации сценария '{id}': {e}")
        
        return wrapper
    
    return decorator


def user_scenario(id: str = None, name: str = None, description: str = "",
                 category: ScenarioCategory = ScenarioCategory.SUPPORT,
                 entry_points: list = None, **kwargs):
    """Декоратор для пользовательских сценариев"""
    return scenario(
        id=id, name=name, description=description,
        type=ScenarioType.USER, category=category,
        entry_points=entry_points, **kwargs
    )


def manager_scenario(id: str = None, name: str = None, description: str = "",
                    category: ScenarioCategory = ScenarioCategory.ADMINISTRATION,
                    entry_points: list = None, **kwargs):
    """Декоратор для менеджерских сценариев"""
    return scenario(
        id=id, name=name, description=description,
        type=ScenarioType.MANAGER, category=category,
        entry_points=entry_points, permissions=["manager"], **kwargs
    )


def system_scenario(id: str = None, name: str = None, description: str = "",
                   category: ScenarioCategory = ScenarioCategory.ADMINISTRATION,
                   entry_points: list = None, **kwargs):
    """Декоратор для системных сценариев"""
    return scenario(
        id=id, name=name, description=description,
        type=ScenarioType.SYSTEM, category=category,
        entry_points=entry_points, permissions=["manager"], **kwargs
    )


class ScenarioDiscovery:
    """Обнаружение и автоматическая регистрация сценариев"""
    
    @staticmethod
    def discover_and_register_all():
        """Обнаружить и зарегистрировать все сценарии в пакете scenarios"""
        try:
            from .registry import get_registry
            
            # Импортируем все модули сценариев для запуска декораторов
            from . import user, manager
            
            # Пользовательские сценарии
            from .user import registration, profile
            
            # Менеджерские сценарии  
            from .manager import auth, administration
            
            registry = get_registry()
            stats = registry.get_statistics()
            
            logger.info(f"Автоматически обнаружено и зарегистрировано {stats['total_scenarios']} сценариев")
            
            return stats
            
        except ImportError as e:
            logger.error(f"Ошибка импорта модулей сценариев: {e}")
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Ошибка обнаружения сценариев: {e}")
            return {"error": str(e)}


# Функция для ручной регистрации без декораторов
def register_scenario_function(func: Callable[[], DialogChain], 
                              metadata: ScenarioMetadata,
                              entry_points: list = None):
    """Зарегистрировать функцию как сценарий"""
    try:
        chain = func()
        registry = get_registry()
        registry.register_scenario(metadata, chain, entry_points or [])
        logger.info(f"Зарегистрирован сценарий '{metadata.id}' из функции '{func.__name__}'")
    except Exception as e:
        logger.error(f"Ошибка регистрации сценария из функции '{func.__name__}': {e}")


# Утилиты для работы с метаданными
def get_scenario_metadata(func: Callable) -> dict:
    """Получить метаданные сценария из функции"""
    return getattr(func, '_scenario_metadata', {})


def is_scenario_function(func: Callable) -> bool:
    """Проверить, является ли функция сценарием"""
    return hasattr(func, '_scenario_metadata')