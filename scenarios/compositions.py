#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Композиции сценариев - комбинации связанных диалогов
"""

import logging
from typing import Dict, List, Any
from dataclasses import dataclass, field

from .registry import ScenarioRegistry, get_registry
from .executor import ScenarioOrchestrator


logger = logging.getLogger(__name__)


@dataclass
class ScenarioComposition:
    """Композиция сценариев"""
    id: str
    name: str
    description: str
    scenario_ids: List[str]
    transitions: Dict[str, Dict[str, str]] = field(default_factory=dict)
    entry_points: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class CompositionBuilder:
    """Построитель композиций сценариев"""
    
    def __init__(self, composition_id: str, name: str, description: str = ""):
        self.composition = ScenarioComposition(
            id=composition_id,
            name=name,
            description=description,
            scenario_ids=[]
        )
    
    def add_scenario(self, scenario_id: str) -> 'CompositionBuilder':
        """Добавить сценарий в композицию"""
        if scenario_id not in self.composition.scenario_ids:
            self.composition.scenario_ids.append(scenario_id)
        return self
    
    def add_scenarios(self, scenario_ids: List[str]) -> 'CompositionBuilder':
        """Добавить несколько сценариев"""
        for scenario_id in scenario_ids:
            self.add_scenario(scenario_id)
        return self
    
    def add_transition(self, from_scenario: str, to_scenario: str, condition: str) -> 'CompositionBuilder':
        """Добавить переход между сценариями"""
        if from_scenario not in self.composition.transitions:
            self.composition.transitions[from_scenario] = {}
        
        self.composition.transitions[from_scenario][condition] = to_scenario
        return self
    
    def set_entry_points(self, entry_points: List[str]) -> 'CompositionBuilder':
        """Установить точки входа в композицию"""
        self.composition.entry_points = entry_points
        return self
    
    def set_metadata(self, **metadata) -> 'CompositionBuilder':
        """Установить метаданные"""
        self.composition.metadata.update(metadata)
        return self
    
    def build(self) -> ScenarioComposition:
        """Построить композицию"""
        if not self.composition.scenario_ids:
            raise ValueError("Композиция должна содержать хотя бы один сценарий")
        
        return self.composition


class CompositionRegistry:
    """Реестр композиций сценариев"""
    
    def __init__(self):
        self.compositions: Dict[str, ScenarioComposition] = {}
        self.entry_points: Dict[str, str] = {}  # entry_point -> composition_id
    
    def register_composition(self, composition: ScenarioComposition) -> None:
        """Зарегистрировать композицию"""
        self.compositions[composition.id] = composition
        
        # Регистрируем точки входа
        for entry_point in composition.entry_points:
            if entry_point in self.entry_points:
                logger.warning(f"Точка входа '{entry_point}' уже занята композицией '{self.entry_points[entry_point]}'")
            self.entry_points[entry_point] = composition.id
        
        logger.info(f"Зарегистрирована композиция '{composition.id}' ({composition.name})")
    
    def get_composition(self, composition_id: str) -> ScenarioComposition:
        """Получить композицию по ID"""
        return self.compositions.get(composition_id)
    
    def get_composition_by_entry_point(self, entry_point: str) -> ScenarioComposition:
        """Получить композицию по точке входа"""
        composition_id = self.entry_points.get(entry_point)
        if composition_id:
            return self.compositions.get(composition_id)
        return None


# === ПРЕДОПРЕДЕЛЕННЫЕ КОМПОЗИЦИИ ===

def create_user_onboarding_composition():
    """Композиция полного онбординга пользователя"""
    return (CompositionBuilder("user_onboarding", "Полный онбординг пользователя",
                              "Полный цикл знакомства с новым пользователем")
            .add_scenarios([
                "user_registration",
                "profile_view"
            ])
            .add_transition("user_registration", "profile_view", "registration_completed==True")
            .set_entry_points(["/onboarding", "full_registration"])
            .set_metadata(
                duration_estimate="10-15 минут",
                complexity="medium",
                success_rate=0.85
            )
            .build())


def create_manager_workflow_composition():
    """Композиция рабочего процесса менеджера"""
    return (CompositionBuilder("manager_workflow", "Рабочий процесс менеджера",
                              "Полный цикл работы менеджера от входа до выполнения задач")
            .add_scenarios([
                "manager_auth",
                "admin_stats"
            ])
            .add_transition("manager_auth", "admin_stats", "auth_success==True")
            .set_entry_points(["/manager_flow", "manager_workflow"])
            .set_metadata(
                duration_estimate="5-20 минут",
                complexity="high",
                requires_auth=True
            )
            .build())


def create_user_support_flow_composition():
    """Композиция потока поддержки пользователя (удалена)"""
    return (CompositionBuilder("user_support_flow", "Поток поддержки пользователя",
                              "Деактивировано")
            .add_scenarios([
                "user_registration"
            ])
            .set_entry_points([])
            .build())


def create_profile_management_composition():
    """Композиция управления профилем"""
    return (CompositionBuilder("profile_management", "Управление профилем",
                              "Полный цикл работы с профилем пользователя")
            .add_scenarios([
                "profile_view",
                "profile_edit", 
                "profile_delete"
            ])
            .add_transition("profile_view", "profile_edit", "edit_profile==True")
            .add_transition("profile_view", "profile_delete", "delete_profile==True")
            .add_transition("profile_edit", "profile_view", "edit_completed==True")
            .set_entry_points(["/profile", "user_profile", "manage_profile"])
            .set_metadata(
                duration_estimate="3-10 минут",
                complexity="medium",
                requires_registration=True
            )
            .build())


def create_admin_dashboard_composition():
    """Композиция административной панели"""
    return (CompositionBuilder("admin_dashboard", "Административная панель",
                              "Полный набор административных функций")
            .add_scenarios([
                "manager_auth",
                "admin_stats",
                "user_management",
                "data_export",
                "system_management"
            ])
            # Переходы из авторизации
            .add_transition("manager_auth", "admin_stats", "auth_success_step=='show_stats'")
            .add_transition("manager_auth", "user_management", "auth_success_step=='show_users'")
            .add_transition("manager_auth", "data_export", "auth_success_step=='export_data'")
            .add_transition("manager_auth", "system_management", "auth_success_step=='show_settings'")
            
            # Переходы между административными функциями
            .add_transition("admin_stats", "data_export", "export_stats==True")
            .add_transition("user_management", "data_export", "export_users==True")
            
            
            .set_entry_points(["/admin", "/dashboard", "admin_panel"])
            .set_metadata(
                duration_estimate="неограничено",
                complexity="high",
                requires_auth=True,
                session_timeout=3600
            )
            .build())


class CompositionManager:
    """Менеджер композиций"""
    
    def __init__(self, orchestrator: ScenarioOrchestrator = None):
        self.registry = CompositionRegistry()
        self.orchestrator = orchestrator
        self._register_default_compositions()
    
    def _register_default_compositions(self):
        """Зарегистрировать предопределенные композиции"""
        default_compositions = [
            create_user_onboarding_composition(),
            create_manager_workflow_composition(),
            create_user_support_flow_composition(),
            create_profile_management_composition(),
            create_admin_dashboard_composition()
        ]
        
        for composition in default_compositions:
            self.register_composition(composition)
        
        logger.info(f"Зарегистрировано {len(default_compositions)} композиций по умолчанию")
    
    def register_composition(self, composition: ScenarioComposition) -> None:
        """Зарегистрировать композицию"""
        self.registry.register_composition(composition)
        
        # Регистрируем переходы в оркестраторе
        if self.orchestrator:
            self.orchestrator.register_composition(
                composition.id, 
                composition.scenario_ids,
                composition.name,
                composition.description
            )
            
            # Регистрируем переходы
            for from_scenario, conditions in composition.transitions.items():
                for condition, to_scenario in conditions.items():
                    self.orchestrator.register_transition(from_scenario, to_scenario, condition)
    
    async def execute_composition(self, update, context, composition_id: str) -> bool:
        """Выполнить композицию"""
        if not self.orchestrator:
            logger.error("Оркестратор не инициализирован")
            return False
        
        return await self.orchestrator.execute_composition(update, context, composition_id)
    
    def get_composition_info(self, composition_id: str) -> Dict[str, Any]:
        """Получить информацию о композиции"""
        composition = self.registry.get_composition(composition_id)
        if not composition:
            return {"found": False}
        
        scenario_registry = get_registry()
        scenario_names = []
        
        for scenario_id in composition.scenario_ids:
            scenario = scenario_registry.get_scenario(scenario_id)
            if scenario:
                scenario_names.append(scenario.metadata.name)
            else:
                scenario_names.append(f"MISSING: {scenario_id}")
        
        return {
            "found": True,
            "name": composition.name,
            "description": composition.description,
            "scenario_count": len(composition.scenario_ids),
            "scenario_names": scenario_names,
            "entry_points": composition.entry_points,
            "transitions_count": sum(len(conditions) for conditions in composition.transitions.values()),
            "metadata": composition.metadata
        }


# Глобальный менеджер композиций
_global_composition_manager: CompositionManager = None


def get_composition_manager() -> CompositionManager:
    """Получить глобальный менеджер композиций"""
    global _global_composition_manager
    if _global_composition_manager is None:
        raise RuntimeError("Менеджер композиций не инициализирован")
    return _global_composition_manager


def init_composition_manager(orchestrator: ScenarioOrchestrator = None) -> CompositionManager:
    """Инициализировать менеджер композиций"""
    global _global_composition_manager
    _global_composition_manager = CompositionManager(orchestrator)
    return _global_composition_manager