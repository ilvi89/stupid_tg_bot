#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Пакет scenarios - DSL описания всех диалоговых сценариев бота
"""

from .registry import ScenarioRegistry, ScenarioMetadata, ScenarioType, ScenarioCategory
from .loader import ScenarioLoader
from .executor import ScenarioExecutor, ScenarioIntegrator, ScenarioOrchestrator
from .auto_register import scenario, user_scenario, manager_scenario, system_scenario
from .compositions import CompositionBuilder, CompositionManager

__all__ = [
    'ScenarioRegistry', 'ScenarioMetadata', 'ScenarioType', 'ScenarioCategory',
    'ScenarioLoader', 'ScenarioExecutor', 'ScenarioIntegrator', 'ScenarioOrchestrator',
    'scenario', 'user_scenario', 'manager_scenario', 'system_scenario',
    'CompositionBuilder', 'CompositionManager'
]