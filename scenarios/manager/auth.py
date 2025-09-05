#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сценарии авторизации менеджера
"""

from dialog_dsl import DialogBuilder, InputType
from ..common.validators import CommonValidators, BusinessValidators
from ..common.actions import CommonActions
from ..auto_register import manager_scenario
from ..registry import ScenarioCategory


@manager_scenario(
    id="manager_auth",
    name="Авторизация менеджера",
    description="Безопасный вход в панель управления ботом",
    category=ScenarioCategory.AUTHENTICATION,
    entry_points=["/manager", "manager", "auth"],
    tags=["auth", "security", "manager"],
    priority=10
)
def create_manager_auth_scenario():
    """Сценарий авторизации менеджера"""
    return (DialogBuilder("manager_auth", "Авторизация менеджера",
                         "Безопасный вход в панель управления ботом")
            .start_with("auth_request_step")
            .set_permissions(["manager"])
            
            # 1. Запрос пароля
            .add_question(
                step_id="auth_request_step",
                message=(
                    "🔐 <b>Авторизация менеджера</b>\n\n"
                    "Введите пароль для доступа к панели управления:\n\n"
                    "⚠️ <i>Сообщение с паролем будет автоматически удалено для безопасности</i>"
                ),
                input_type=InputType.TEXT,
                validations=[
                    CommonValidators.not_empty(),
                    CommonValidators.min_length(3)
                ],
                next_step="auth_process_step"
            )
            
            # 2. Обработка пароля
            .add_action(
                step_id="auth_process_step",
                action=lambda u, c, s: {"password": s.data.get("auth_request_step")},
                next_step="auth_check_step"
            )
            
            # 3. Проверка пароля
            .add_action(
                step_id="auth_check_step",
                action=CommonActions.authenticate_manager,
                message="🔍 Проверяем пароль..."
            )
            .add_condition("auth_check_step", {
                "auth_success==True": "auth_success_step",
                "auth_success==False": "auth_failed_step"
            })
            
            # 4a. Успешная авторизация
            .add_choice(
                step_id="auth_success_step",
                message=(
                    "✅ <b>Доступ разрешен!</b>\n\n"
                    "Добро пожаловать в панель управления.\n"
                    "Ваша сессия активна в течение 1 часа.\n\n"
                    "Что хотите сделать?"
                ),
                inline_keyboard=[
                    [("📊 Статистика", "show_stats")],
                    [("👥 Пользователи", "show_users")],
                    [("📢 Рассылка", "start_broadcast")],
                    [("📁 Экспорт данных", "export_data")],
                    [("⚙️ Настройки", "show_settings")],
                    [("🚪 Выход", "logout")]
                ]
            )
            .add_condition("auth_success_step", {
                "auth_success_step=='show_stats'": "redirect_stats",
                "auth_success_step=='show_users'": "redirect_users",
                "auth_success_step=='start_broadcast'": "redirect_broadcast",
                "auth_success_step=='export_data'": "redirect_export",
                "auth_success_step=='show_settings'": "redirect_settings",
                "auth_success_step=='logout'": "logout_step"
            })
            
            # 4b. Неудачная авторизация
            .add_choice(
                step_id="auth_failed_step",
                message=(
                    "❌ <b>Неверный пароль</b>\n\n"
                    "Доступ запрещен.\n\n"
                    "Что хотите сделать?"
                ),
                inline_keyboard=[
                    [("🔄 Попробовать снова", "retry_auth")],
                    [("❌ Отмена", "auth_cancel")]
                ]
            )
            .add_condition("auth_failed_step", {
                "auth_failed_step=='retry_auth'": "auth_request_step",
                "auth_failed_step=='auth_cancel'": "auth_cancelled_step"
            })
            
            # 5. Выход из системы
            .add_action(
                step_id="logout_step",
                action=lambda u, c, s: {
                    "logout_success": True,
                    "session_ended": True
                },
                message="🚪 Выходим из системы...",
                next_step="logout_complete_step"
            )
            
            # 6. Финальные шаги и перенаправления
            .add_final(
                step_id="auth_cancelled_step",
                message="❌ Авторизация отменена"
            )
            
            .add_final(
                step_id="logout_complete_step",
                message=(
                    "👋 <b>Вы вышли из системы управления</b>\n\n"
                    "Для повторного входа используйте команду /manager\n"
                    "Спасибо за работу! 🙏"
                )
            )
            
            # Перенаправления к другим сценариям
            .add_final(
                step_id="redirect_stats",
                message="📊 Переходим к статистике..."
            )
            
            .add_final(
                step_id="redirect_users", 
                message="👥 Переходим к управлению пользователями..."
            )
            
            .add_final(
                step_id="redirect_broadcast",
                message="📢 Переходим к созданию рассылки..."
            )
            
            .add_final(
                step_id="redirect_export",
                message="📁 Переходим к экспорту данных..."
            )
            
            .add_final(
                step_id="redirect_settings",
                message="⚙️ Переходим к настройкам..."
            )
            
            .set_timeout(300)  # 5 минут на авторизацию
            .build())


def create_session_check_scenario():
    """Сценарий проверки активной сессии менеджера"""
    return (DialogBuilder("session_check", "Проверка сессии",
                         "Проверка активности сессии менеджера")
            .start_with("check_session_step")
            .set_permissions(["manager"])
            
            # 1. Проверка сессии
            .add_action(
                step_id="check_session_step",
                action=lambda u, c, s: {
                    "session_active": True,  # Заглушка, в реальности проверка через auth_manager
                    "time_left": 1800  # 30 минут
                }
            )
            .add_condition("check_session_step", {
                "session_active==True": "session_active_step",
                "session_active==False": "session_expired_step"
            })
            
            # 2a. Сессия активна
            .add_choice(
                step_id="session_active_step",
                message=(
                    "✅ <b>Сессия активна</b>\n\n"
                    "⏰ Осталось времени: {time_left_formatted}\n\n"
                    "Что хотите сделать?"
                ),
                inline_keyboard=[
                    [("🔄 Продлить сессию", "extend_session")],
                    [("📊 Открыть панель", "open_panel")],
                    [("🚪 Завершить сессию", "end_session")]
                ]
            )
            
            # 2b. Сессия истекла
            .add_choice(
                step_id="session_expired_step",
                message=(
                    "⏰ <b>Сессия истекла</b>\n\n"
                    "Для продолжения работы необходимо авторизоваться заново.\n\n"
                    "Войти в систему?"
                ),
                inline_keyboard=[
                    [("🔐 Войти заново", "reauth")],
                    [("❌ Отмена", "session_cancel")]
                ]
            )
            .add_condition("session_expired_step", {
                "session_expired_step=='reauth'": "redirect_to_auth"
            })
            
            # 3. Финальные шаги
            .add_final(
                step_id="redirect_to_auth",
                message="🔄 Переходим к авторизации..."
            )
            
            .add_final(
                step_id="open_panel",
                message="📊 Открываем панель управления..."
            )
            
            .add_final(
                step_id="session_cancel",
                message="❌ Отменено"
            )
            
            .set_timeout(180)  # 3 минуты
            .build())