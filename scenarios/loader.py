#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Загрузчик сценариев - автоматическое обнаружение и загрузка DSL сценариев
"""

import os
import importlib
import importlib.util
import inspect
import logging
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path

from dialog_dsl import DialogChain
from .registry import ScenarioRegistry, ScenarioMetadata, get_registry


logger = logging.getLogger(__name__)


class ScenarioLoader:
    """Загрузчик сценариев из файлов"""
    
    def __init__(self, registry: ScenarioRegistry = None):
        self.registry = registry or get_registry()
        self.loaded_modules = {}
    
    def load_from_directory(self, directory: str) -> Dict[str, Any]:
        """Загрузить все сценарии из директории"""
        results = {
            "loaded": 0,
            "errors": 0,
            "scenarios": [],
            "error_details": []
        }
        
        directory_path = Path(directory)
        if not directory_path.exists():
            logger.error(f"Директория '{directory}' не существует")
            return results
        
        # Ищем все Python файлы
        for py_file in directory_path.rglob("*.py"):
            if py_file.name.startswith("__"):
                continue
            
            try:
                result = self.load_from_file(str(py_file))
                if result["loaded"] > 0:
                    results["loaded"] += result["loaded"]
                    results["scenarios"].extend(result["scenarios"])
                else:
                    results["errors"] += 1
                    results["error_details"].extend(result["error_details"])
                    
            except Exception as e:
                results["errors"] += 1
                results["error_details"].append(f"Ошибка загрузки {py_file}: {e}")
                logger.error(f"Ошибка загрузки файла {py_file}: {e}")
        
        logger.info(f"Загружено {results['loaded']} сценариев из {directory}")
        return results
    
    def load_from_file(self, file_path: str) -> Dict[str, Any]:
        """Загрузить сценарии из файла"""
        results = {
            "loaded": 0,
            "scenarios": [],
            "error_details": []
        }
        
        try:
            # Получаем имя модуля из пути
            file_path_obj = Path(file_path)
            module_name = self._get_module_name(file_path_obj)
            
            # Загружаем модуль
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec is None or spec.loader is None:
                results["error_details"].append(f"Не удалось создать spec для {file_path}")
                return results
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Ищем функции, возвращающие DialogChain
            for name, obj in inspect.getmembers(module):
                if inspect.isfunction(obj) and name.startswith(('create_', 'build_', 'define_')):
                    try:
                        # Пытаемся вызвать функцию
                        if len(inspect.signature(obj).parameters) == 0:
                            result = obj()
                            if isinstance(result, DialogChain):
                                self._register_scenario_from_chain(result, module_name)
                                results["loaded"] += 1
                                results["scenarios"].append(result.id)
                    except Exception as e:
                        results["error_details"].append(f"Ошибка в функции {name}: {e}")
            
            # Ищем переменные типа DialogChain
            for name, obj in inspect.getmembers(module):
                if isinstance(obj, DialogChain):
                    self._register_scenario_from_chain(obj, module_name)
                    results["loaded"] += 1
                    results["scenarios"].append(obj.id)
            
            self.loaded_modules[module_name] = module
            
        except Exception as e:
            results["error_details"].append(f"Ошибка загрузки модуля {file_path}: {e}")
            logger.error(f"Ошибка загрузки модуля {file_path}: {e}")
        
        return results
    
    def _get_module_name(self, file_path: Path) -> str:
        """Получить имя модуля из пути к файлу"""
        # Создаем имя модуля на основе пути
        parts = file_path.with_suffix('').parts
        if 'scenarios' in parts:
            # Берем путь после 'scenarios'
            scenario_index = parts.index('scenarios')
            module_parts = parts[scenario_index:]
            return '.'.join(module_parts)
        else:
            return file_path.stem
    
    def _register_scenario_from_chain(self, chain: DialogChain, module_name: str) -> None:
        """Зарегистрировать сценарий из DialogChain"""
        # Создаем метаданные на основе цепочки
        metadata = ScenarioMetadata(
            id=chain.id,
            name=chain.name,
            description=chain.description,
            type=self._infer_scenario_type(chain),
            category=self._infer_scenario_category(chain),
            permissions=chain.permissions,
            author=module_name
        )
        
        # Определяем точки входа
        entry_points = self._infer_entry_points(chain)
        
        self.registry.register_scenario(metadata, chain, entry_points)
    
    def _infer_scenario_type(self, chain: DialogChain) -> ScenarioType:
        """Определить тип сценария по цепочке"""
        if "manager" in chain.permissions:
            return ScenarioType.MANAGER
        elif any(keyword in chain.id.lower() for keyword in ["admin", "system", "debug"]):
            return ScenarioType.SYSTEM
        else:
            return ScenarioType.USER
    
    def _infer_scenario_category(self, chain: DialogChain) -> ScenarioCategory:
        """Определить категорию сценария по цепочке"""
        chain_id_lower = chain.id.lower()
        
        if any(keyword in chain_id_lower for keyword in ["register", "signup", "registration"]):
            return ScenarioCategory.REGISTRATION
        elif any(keyword in chain_id_lower for keyword in ["auth", "login", "password"]):
            return ScenarioCategory.AUTHENTICATION
        elif any(keyword in chain_id_lower for keyword in ["profile", "edit", "update"]):
            return ScenarioCategory.PROFILE
        elif any(keyword in chain_id_lower for keyword in ["broadcast", "message", "send"]):
            return ScenarioCategory.COMMUNICATION
        elif any(keyword in chain_id_lower for keyword in ["admin", "manage", "control"]):
            return ScenarioCategory.ADMINISTRATION
        elif any(keyword in chain_id_lower for keyword in ["support", "help", "ticket"]):
            return ScenarioCategory.SUPPORT
        elif any(keyword in chain_id_lower for keyword in ["settings", "config", "preferences"]):
            return ScenarioCategory.SETTINGS
        else:
            return ScenarioCategory.SUPPORT  # По умолчанию
    
    def _infer_entry_points(self, chain: DialogChain) -> List[str]:
        """Определить точки входа для сценария"""
        entry_points = []
        
        chain_id_lower = chain.id.lower()
        
        # Стандартные команды
        if "registration" in chain_id_lower or "start" in chain_id_lower:
            entry_points.extend(["/start", "start"])
        
        if "auth" in chain_id_lower or "manager" in chain_id_lower:
            entry_points.extend(["/manager", "manager"])
        
        if "profile" in chain_id_lower:
            entry_points.extend(["user_edit_profile", "profile_edit"])
        
        if "support" in chain_id_lower:
            entry_points.extend(["user_support", "support"])
        
        if "broadcast" in chain_id_lower:
            entry_points.extend(["mgr_broadcast", "broadcast"])
        
        # Callback данные на основе ID
        entry_points.append(f"scenario_{chain.id}")
        
        return entry_points
    
    def reload_module(self, module_name: str) -> Dict[str, Any]:
        """Перезагрузить модуль сценариев"""
        if module_name not in self.loaded_modules:
            return {"error": f"Модуль '{module_name}' не был загружен"}
        
        try:
            # Удаляем старые сценарии этого модуля
            scenarios_to_remove = []
            for scenario_id, scenario in self._scenarios.items():
                if scenario.metadata.author == module_name:
                    scenarios_to_remove.append(scenario_id)
            
            for scenario_id in scenarios_to_remove:
                self.registry.unregister_scenario(scenario_id)
            
            # Перезагружаем модуль
            module = self.loaded_modules[module_name]
            importlib.reload(module)
            
            # Загружаем сценарии заново
            # (здесь нужна логика повторного поиска функций в модуле)
            
            return {"reloaded": len(scenarios_to_remove)}
            
        except Exception as e:
            logger.error(f"Ошибка перезагрузки модуля {module_name}: {e}")
            return {"error": str(e)}
    
    def validate_all_scenarios(self) -> Dict[str, List[str]]:
        """Проверить валидность всех сценариев"""
        validation_errors = {}
        
        for scenario_id, scenario in self._scenarios.items():
            errors = []
            
            # Проверяем цепочку
            try:
                self._validate_chain(scenario.chain)
            except Exception as e:
                errors.append(f"Ошибка в цепочке: {e}")
            
            # Проверяем зависимости
            for dep in scenario.metadata.dependencies:
                if dep not in self._scenarios:
                    errors.append(f"Отсутствует зависимость: {dep}")
            
            if errors:
                validation_errors[scenario_id] = errors
        
        return validation_errors
    
    def _validate_chain(self, chain: DialogChain) -> None:
        """Проверить валидность цепочки диалога"""
        if not chain.steps:
            raise ValueError("Цепочка не содержит шагов")
        
        if not chain.start_step:
            raise ValueError("Не указан начальный шаг")
        
        step_ids = {step.id for step in chain.steps}
        
        if chain.start_step not in step_ids:
            raise ValueError(f"Начальный шаг '{chain.start_step}' не найден")
        
        # Проверяем ссылки между шагами
        for step in chain.steps:
            if step.next_step and step.next_step not in step_ids:
                raise ValueError(f"Шаг '{step.id}' ссылается на несуществующий шаг '{step.next_step}'")
            
            for condition, target_step in step.condition_steps.items():
                if target_step not in step_ids:
                    raise ValueError(f"Условие '{condition}' в шаге '{step.id}' ссылается на несуществующий шаг '{target_step}'")


# Глобальный загрузчик
_global_loader: Optional[ScenarioLoader] = None


def get_loader() -> ScenarioLoader:
    """Получить глобальный загрузчик сценариев"""
    global _global_loader
    if _global_loader is None:
        _global_loader = ScenarioLoader()
    return _global_loader