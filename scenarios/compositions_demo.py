#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Демонстрация композиций сценариев
"""

from .compositions import CompositionBuilder
import logging
from .auto_register import scenario
from .registry import ScenarioType, ScenarioCategory
from dialog_dsl import DialogBuilder, InputType
from .common.validators import CommonValidators

logger = logging.getLogger(__name__)


# === ДЕМОНСТРАЦИОННЫЕ СЦЕНАРИИ ===

@scenario(
    id="demo_greeting",
    name="Демо приветствие",
    type=ScenarioType.USER,
    category=ScenarioCategory.SUPPORT,
    entry_points=["demo_hello"]
)
def create_demo_greeting():
    """Демонстрационный сценарий приветствия"""
    return (DialogBuilder("demo_greeting", "Демо приветствие")
            .start_with("hello")
            
            .add_message(
                step_id="hello",
                message="👋 Привет! Это демо сценарий.",
                next_step="ask_name"
            )
            
            .add_question(
                step_id="ask_name",
                message="Как вас зовут?",
                input_type=InputType.TEXT,
                validations=[CommonValidators.not_empty()],
                next_step="goodbye"
            )
            
            .add_final(
                step_id="goodbye",
                message="Приятно познакомиться, {ask_name}! 😊"
            )
            
            .build())


@scenario(
    id="demo_survey",
    name="Демо опрос",
    type=ScenarioType.USER,
    category=ScenarioCategory.SUPPORT,
    entry_points=["demo_survey"]
)
def create_demo_survey():
    """Демонстрационный опрос"""
    return (DialogBuilder("demo_survey", "Демо опрос")
            .start_with("survey_start")
            
            .add_message(
                step_id="survey_start",
                message="📊 Давайте проведем небольшой опрос!",
                next_step="question1"
            )
            
            .add_choice(
                step_id="question1",
                message="Нравится ли вам изучать английский?",
                inline_keyboard=[
                    [("😍 Очень нравится", "love_it")],
                    [("😊 Нравится", "like_it")],
                    [("😐 Нормально", "ok")],
                    [("😕 Не очень", "not_really")]
                ],
                next_step="question2"
            )
            
            .add_choice(
                step_id="question2",
                message="Сколько времени вы изучаете английский?",
                inline_keyboard=[
                    [("🆕 Только начал", "just_started")],
                    [("📅 Несколько месяцев", "few_months")],
                    [("📆 Больше года", "more_year")],
                    [("🎓 Много лет", "many_years")]
                ],
                next_step="survey_results"
            )
            
            .add_final(
                step_id="survey_results",
                message=(
                    "📊 <b>Спасибо за участие в опросе!</b>\n\n"
                    "Ваши ответы:\n"
                    "• Отношение: {question1}\n"
                    "• Опыт: {question2}\n\n"
                    "Результаты помогут улучшить наши программы! 🎯"
                )
            )
            
            .build())


# === ДЕМОНСТРАЦИОННЫЕ КОМПОЗИЦИИ ===

def create_demo_user_journey():
    """Демонстрационная композиция пользовательского пути"""
    return (CompositionBuilder("demo_user_journey", "Демо путь пользователя",
                              "Демонстрация полного пути пользователя от приветствия до опроса")
            .add_scenarios([
                "demo_greeting",
                "demo_survey"
            ])
            .add_transition("demo_greeting", "demo_survey", "always")
            .set_entry_points(["demo_journey", "demo_flow"])
            .set_metadata(
                demo=True,
                estimated_time="5 минут",
                difficulty="easy"
            )
            .build())


def create_complete_onboarding():
    """Композиция полного онбординга с реальными сценариями"""
    return (CompositionBuilder("complete_onboarding", "Полный онбординг",
                              "Полный цикл онбординга от регистрации до знакомства с возможностями")
            .add_scenarios([
                "user_registration",
                "profile_view"
            ])
            .add_transition("user_registration", "profile_view", "registration_completed==True")
            .set_entry_points(["/onboarding", "full_onboarding"])
            .set_metadata(
                estimated_time="15-20 минут",
                difficulty="medium",
                completion_rate=0.85
            )
            .build())


def create_manager_dashboard_flow():
    """Композиция панели управления менеджера"""
    return (CompositionBuilder("manager_dashboard", "Панель управления менеджера",
                              "Полный рабочий процесс менеджера")
            .add_scenarios([
                "manager_auth",
                "admin_stats",
                "user_management", 
                "broadcast_creation",
                "data_export",
                "system_management"
            ])
            # Переходы из авторизации
            .add_transition("manager_auth", "admin_stats", "redirect_stats==True")
            .add_transition("manager_auth", "user_management", "redirect_users==True")
            .add_transition("manager_auth", "broadcast_creation", "redirect_broadcast==True")
            .add_transition("manager_auth", "data_export", "redirect_export==True")
            .add_transition("manager_auth", "system_management", "redirect_settings==True")
            
            # Переходы между функциями
            .add_transition("admin_stats", "data_export", "export_stats==True")
            .add_transition("user_management", "data_export", "export_users==True")
            .add_transition("broadcast_creation", "admin_stats", "view_stats_after_broadcast==True")
            
            .set_entry_points(["/dashboard", "manager_panel", "admin_dashboard"])
            .set_metadata(
                estimated_time="неограничено",
                difficulty="high",
                requires_auth=True
            )
            .build())


# === СИСТЕМА РЕГИСТРАЦИИ КОМПОЗИЦИЙ ===

def register_all_compositions():
    """Зарегистрировать все композиции"""
    from .compositions import init_composition_manager, get_composition_manager
    from .executor import get_orchestrator
    
    try:
        # Инициализируем менеджер композиций
        orchestrator = get_orchestrator()
        composition_manager = init_composition_manager(orchestrator)
        
        # Регистрируем демонстрационные композиции
        demo_compositions = [
            create_demo_user_journey(),
            create_complete_onboarding()
        ]
        
        for composition in demo_compositions:
            composition_manager.register_composition(composition)
        
        logger.info(f"Зарегистрировано {len(demo_compositions)} композиций")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка регистрации композиций: {e}")
        return False


# === АВТОЗАПУСК РЕГИСТРАЦИИ ===

def auto_register_everything():
    """Автоматически зарегистрировать все сценарии и композиции"""
    try:
        # Регистрируем сценарии через автообнаружение
        from .auto_register import ScenarioDiscovery
        scenario_stats = ScenarioDiscovery.discover_and_register_all()
        
        if "error" not in scenario_stats:
            logger.info(f"Автообнаружение сценариев: {scenario_stats}")
        
        # Регистрируем композиции
        register_all_compositions()
        
        return True
        
    except Exception as e:
        logger.error(f"Ошибка автоматической регистрации: {e}")
        return False


if __name__ == "__main__":
    # Минимальный CLI-блок удалён, чтобы не тянуть служебные функции в рантайме
    print("This module is not intended to be run directly.")