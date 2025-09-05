#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Реестр сценариев - центральная регистрация всех диалогов
"""

import logging
from typing import Dict, List, Optional, Any, Type
from dataclasses import dataclass, field
from enum import Enum

from dialog_dsl import DialogChain, DialogEngine


logger = logging.getLogger(__name__)


class ScenarioType(Enum):
    """Типы сценариев"""
    USER = "user"
    MANAGER = "manager"
    SYSTEM = "system"
    MIXED = "mixed"


class ScenarioCategory(Enum):
    """Категории сценариев"""
    REGISTRATION = "registration"
    AUTHENTICATION = "authentication"
    PROFILE = "profile"
    COMMUNICATION = "communication"
    ADMINISTRATION = "administration"
    SUPPORT = "support"
    SETTINGS = "settings"


@dataclass
class ScenarioMetadata:
    """Метаданные сценария"""
    id: str
    name: str
    description: str
    type: ScenarioType
    category: ScenarioCategory
    version: str = "1.0"
    author: str = ""
    permissions: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    enabled: bool = True
    priority: int = 0


@dataclass
class RegisteredScenario:
    """Зарегистрированный сценарий"""
    metadata: ScenarioMetadata
    chain: DialogChain
    entry_points: List[str] = field(default_factory=list)
    exit_points: List[str] = field(default_factory=list)


class ScenarioRegistry:
    """Реестр всех сценариев системы"""
    
    def __init__(self):
        self._scenarios: Dict[str, RegisteredScenario] = {}
        self._entry_points: Dict[str, str] = {}  # entry_point -> scenario_id
        self._categories: Dict[ScenarioCategory, List[str]] = {}
        self._types: Dict[ScenarioType, List[str]] = {}
        
        # Инициализируем категории
        for category in ScenarioCategory:
            self._categories[category] = []
        
        for scenario_type in ScenarioType:
            self._types[scenario_type] = []
    
    def register_scenario(self, metadata: ScenarioMetadata, chain: DialogChain,
                         entry_points: List[str] = None) -> None:
        """Зарегистрировать сценарий"""
        if metadata.id in self._scenarios:
            logger.warning(f"Сценарий '{metadata.id}' уже зарегистрирован. Перезаписываю.")
        
        scenario = RegisteredScenario(
            metadata=metadata,
            chain=chain,
            entry_points=entry_points or []
        )
        
        self._scenarios[metadata.id] = scenario
        self._categories[metadata.category].append(metadata.id)
        self._types[metadata.type].append(metadata.id)
        
        # Регистрируем точки входа
        for entry_point in scenario.entry_points:
            if entry_point in self._entry_points:
                logger.warning(f"Точка входа '{entry_point}' уже занята сценарием '{self._entry_points[entry_point]}'")
            self._entry_points[entry_point] = metadata.id
        
        logger.info(f"Зарегистрирован сценарий '{metadata.id}' ({metadata.name})")
    
    def get_scenario(self, scenario_id: str) -> Optional[RegisteredScenario]:
        """Получить сценарий по ID"""
        return self._scenarios.get(scenario_id)
    
    def get_scenario_by_entry_point(self, entry_point: str) -> Optional[RegisteredScenario]:
        """Получить сценарий по точке входа"""
        scenario_id = self._entry_points.get(entry_point)
        if scenario_id:
            return self._scenarios.get(scenario_id)
        return None
    
    def get_scenarios_by_category(self, category: ScenarioCategory) -> List[RegisteredScenario]:
        """Получить сценарии по категории"""
        scenario_ids = self._categories.get(category, [])
        return [self._scenarios[sid] for sid in scenario_ids if sid in self._scenarios]
    
    def get_scenarios_by_type(self, scenario_type: ScenarioType) -> List[RegisteredScenario]:
        """Получить сценарии по типу"""
        scenario_ids = self._types.get(scenario_type, [])
        return [self._scenarios[sid] for sid in scenario_ids if sid in self._scenarios]
    
    def get_all_scenarios(self) -> Dict[str, RegisteredScenario]:
        """Получить все зарегистрированные сценарии"""
        return self._scenarios.copy()
    
    def get_enabled_scenarios(self) -> Dict[str, RegisteredScenario]:
        """Получить только активные сценарии"""
        return {sid: scenario for sid, scenario in self._scenarios.items() 
                if scenario.metadata.enabled}
    
    def enable_scenario(self, scenario_id: str) -> bool:
        """Включить сценарий"""
        if scenario_id in self._scenarios:
            self._scenarios[scenario_id].metadata.enabled = True
            logger.info(f"Сценарий '{scenario_id}' включен")
            return True
        return False
    
    def disable_scenario(self, scenario_id: str) -> bool:
        """Отключить сценарий"""
        if scenario_id in self._scenarios:
            self._scenarios[scenario_id].metadata.enabled = False
            logger.info(f"Сценарий '{scenario_id}' отключен")
            return True
        return False
    
    def unregister_scenario(self, scenario_id: str) -> bool:
        """Удалить сценарий из реестра"""
        if scenario_id not in self._scenarios:
            return False
        
        scenario = self._scenarios[scenario_id]
        
        # Удаляем из категорий и типов
        if scenario.metadata.category in self._categories:
            try:
                self._categories[scenario.metadata.category].remove(scenario_id)
            except ValueError:
                pass
        
        if scenario.metadata.type in self._types:
            try:
                self._types[scenario.metadata.type].remove(scenario_id)
            except ValueError:
                pass
        
        # Удаляем точки входа
        entry_points_to_remove = [ep for ep, sid in self._entry_points.items() if sid == scenario_id]
        for entry_point in entry_points_to_remove:
            del self._entry_points[entry_point]
        
        # Удаляем сценарий
        del self._scenarios[scenario_id]
        
        logger.info(f"Сценарий '{scenario_id}' удален из реестра")
        return True
    
    def validate_dependencies(self) -> Dict[str, List[str]]:
        """Проверить зависимости между сценариями"""
        missing_dependencies = {}
        
        for scenario_id, scenario in self._scenarios.items():
            missing = []
            for dep in scenario.metadata.dependencies:
                if dep not in self._scenarios:
                    missing.append(dep)
            
            if missing:
                missing_dependencies[scenario_id] = missing
        
        return missing_dependencies
    
    def get_statistics(self) -> Dict[str, Any]:
        """Получить статистику реестра"""
        total_scenarios = len(self._scenarios)
        enabled_scenarios = len(self.get_enabled_scenarios())
        
        category_stats = {}
        for category in ScenarioCategory:
            category_stats[category.value] = len(self._categories[category])
        
        type_stats = {}
        for scenario_type in ScenarioType:
            type_stats[scenario_type.value] = len(self._types[scenario_type])
        
        return {
            "total_scenarios": total_scenarios,
            "enabled_scenarios": enabled_scenarios,
            "disabled_scenarios": total_scenarios - enabled_scenarios,
            "entry_points": len(self._entry_points),
            "categories": category_stats,
            "types": type_stats,
            "missing_dependencies": self.validate_dependencies()
        }


# Глобальный реестр
_global_registry: Optional[ScenarioRegistry] = None


def get_registry() -> ScenarioRegistry:
    """Получить глобальный реестр сценариев"""
    global _global_registry
    if _global_registry is None:
        _global_registry = ScenarioRegistry()
    return _global_registry


def reset_registry() -> None:
    """Сбросить глобальный реестр (для тестирования)"""
    global _global_registry
    _global_registry = None