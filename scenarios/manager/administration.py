#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сценарии администрирования системы
"""

from dialog_dsl import DialogBuilder, InputType
from ..common.validators import CommonValidators
from ..common.actions import CommonActions
from ..auto_register import manager_scenario
from ..registry import ScenarioCategory


def create_admin_scenarios():
    """Создать все административные сценарии"""
    return [
        create_stats_viewing_scenario(),
        create_user_management_scenario(),
        create_data_export_scenario(),
        create_system_management_scenario()
    ]


@manager_scenario(
    id="admin_stats",
    name="Статистика системы",
    description="Просмотр детальной статистики пользователей и активности",
    category=ScenarioCategory.ADMINISTRATION,
    entry_points=["admin_stats", "scenario_admin_stats"],
    tags=["admin", "stats"],
    priority=5
)
def create_stats_viewing_scenario():
    """Сценарий просмотра статистики"""
    return (DialogBuilder("admin_stats", "Статистика системы",
                         "Просмотр детальной статистики пользователей и активности")
            .start_with("load_stats_step")
            .set_permissions(["manager"])
            
            # 1. Загрузка статистики
            .add_action(
                step_id="load_stats_step",
                action=CommonActions.get_statistics,
                message="📊 Загружаем статистику...",
                next_step="show_stats_step"
            )
            .add_condition("load_stats_step", {
                "stats_success==False": "stats_error_step"
            })
            
            # 2. Отображение статистики
            .add_choice(
                step_id="show_stats_step",
                message=(
                    "📊 <b>Статистика английского клуба</b>\n\n"
                    "👥 <b>Пользователи:</b>\n"
                    "• Всего участников: {total_users}\n"
                    "• Подписаны на рассылку: {newsletter_subscribers}\n"
                    "• С опытом изучения: {experienced_users}\n"
                    "• Новички: {beginner_users}\n"
                    "• Новые за неделю: {new_this_week}\n\n"
                    "📈 <b>Общие показатели:</b>\n"
                    "• Средний возраст: {average_age} лет\n\n"
                    "Что хотите посмотреть?"
                ),
                inline_keyboard=[
                    [("📈 Детальная статистика", "detailed_stats")],
                    [("📊 По возрастам", "age_distribution")],
                    [("📅 По датам регистрации", "registration_timeline")],
                    [("🔄 Обновить данные", "refresh_stats")],
                    [("📁 Экспорт статистики", "export_stats")],
                    [("🔙 Назад", "stats_back")]
                ]
            )
            .add_condition("show_stats_step", {
                "show_stats_step=='refresh_stats'": "load_stats_step",
                "show_stats_step=='export_stats'": "redirect_to_export",
                "show_stats_step=='detailed_stats'": "detailed_stats_step"
            })
            
            # 3. Детальная статистика
            .add_action(
                step_id="detailed_stats_step",
                action=lambda u, c, s: {
                    "detailed_loaded": True,
                    "age_groups": {
                        "До 18": 5,
                        "18-25": 15,
                        "26-35": 25,
                        "36-45": 12,
                        "46+": 8
                    },
                    "daily_registrations": {
                        "2024-01-01": 3,
                        "2024-01-02": 5,
                        "2024-01-03": 2
                    }
                },
                message="📈 Загружаем детальную статистику...",
                next_step="show_detailed_stats_step"
            )
            
            .add_choice(
                step_id="show_detailed_stats_step",
                message=(
                    "📈 <b>Детальная статистика</b>\n\n"
                    "👥 <b>Возрастное распределение:</b>\n"
                    "• До 18: {age_groups[До 18]} чел.\n"
                    "• 18-25: {age_groups[18-25]} чел.\n"
                    "• 26-35: {age_groups[26-35]} чел.\n"
                    "• 36-45: {age_groups[36-45]} чел.\n"
                    "• 46+: {age_groups[46+]} чел.\n\n"
                    "📅 <b>Регистрации (последние дни):</b>\n"
                    "• Сегодня: 3 чел.\n"
                    "• Вчера: 5 чел.\n"
                    "• Позавчера: 2 чел.\n\n"
                    "Что делаем дальше?"
                ),
                inline_keyboard=[
                    [("📊 Экспорт статистики", "export_detailed")],
                    [("🔄 Обновить", "refresh_detailed")],
                    [("🔙 К общей статистике", "back_to_general")],
                    [("🏠 В панель управления", "back_to_panel")]
                ]
            )
            
            # 4. Ошибка загрузки статистики
            .add_choice(
                step_id="stats_error_step",
                message=(
                    "❌ <b>Ошибка загрузки статистики</b>\n\n"
                    "Не удалось загрузить данные: {error}\n\n"
                    "Что делаем?"
                ),
                inline_keyboard=[
                    [("🔄 Попробовать снова", "retry_stats")],
                    [("🔙 Назад", "stats_back")]
                ]
            )
            .add_condition("stats_error_step", {
                "stats_error_step=='retry_stats'": "load_stats_step"
            })
            
            # 5. Финальные шаги
            .add_final(
                step_id="redirect_to_export",
                message="🔄 Переходим к экспорту данных..."
            )
            
            .add_final(
                step_id="stats_back",
                message="🔙 Возвращаемся в панель управления..."
            )
            
            .set_timeout(600)  # 10 минут
            .build())


@manager_scenario(
    id="user_management",
    name="Управление пользователями",
    description="Просмотр, поиск и управление пользователями",
    category=ScenarioCategory.ADMINISTRATION,
    entry_points=["user_management", "scenario_user_management"],
    tags=["admin"],
    priority=4
)
def create_user_management_scenario():
    """Сценарий управления пользователями"""
    return (DialogBuilder("user_management", "Управление пользователями",
                         "Просмотр, поиск и управление пользователями системы")
            .start_with("user_menu_step")
            .set_permissions(["manager"])
            
            # 1. Меню управления пользователями
            .add_choice(
                step_id="user_menu_step",
                message=(
                    "👥 <b>Управление пользователями</b>\n\n"
                    "Выберите действие:"
                ),
                inline_keyboard=[
                    [("📋 Список пользователей", "list_users")],
                    [("🔍 Поиск пользователя", "search_user")],
                    [("📊 Статистика пользователей", "user_stats")],
                    [("🗑️ Массовые операции", "bulk_operations")],
                    [("📧 Управление подписками", "manage_subscriptions")],
                    [("🔙 Назад", "user_mgmt_back")]
                ]
            )
            
            # 2. Поиск пользователя
            .add_question(
                step_id="search_user_step",
                message=(
                    "🔍 <b>Поиск пользователя</b>\n\n"
                    "Введите имя пользователя или Telegram ID для поиска:"
                ),
                input_type=InputType.TEXT,
                validations=[CommonValidators.not_empty()],
                next_step="execute_search_step"
            )
            
            # 3. Выполнение поиска
            .add_action(
                step_id="execute_search_step",
                action=lambda u, c, s: {
                    "search_query": s.data.get("search_user_step"),
                    "search_results": [
                        {"name": "Иван Петров", "telegram_id": 12345, "age": 25},
                        {"name": "Мария Сидорова", "telegram_id": 67890, "age": 30}
                    ],  # Заглушка
                    "found_count": 2
                },
                message="🔍 Ищем пользователей...",
                next_step="search_results_step"
            )
            
            # 4. Результаты поиска
            .add_choice(
                step_id="search_results_step",
                message=(
                    "🔍 <b>Результаты поиска</b>\n\n"
                    "Запрос: <b>{search_query}</b>\n"
                    "Найдено: <b>{found_count}</b> пользователей\n\n"
                    "👤 <b>Иван Петров</b> (ID: 12345)\n"
                    "   • Возраст: 25 лет\n"
                    "   • Рассылка: ✅\n\n"
                    "👤 <b>Мария Сидорова</b> (ID: 67890)\n"
                    "   • Возраст: 30 лет\n"
                    "   • Рассылка: ❌\n\n"
                    "Что делаем?"
                ),
                inline_keyboard=[
                    [("👁️ Подробная информация", "user_details")],
                    [("✏️ Редактировать пользователя", "edit_user")],
                    [("🗑️ Удалить пользователя", "delete_user")],
                    [("🔍 Новый поиск", "new_search")],
                    [("🔙 Назад", "back_to_user_menu")]
                ]
            )
            
            # 5. Финальные шаги
            .add_final(
                step_id="user_mgmt_back",
                message="🔙 Возвращаемся в панель управления..."
            )
            
            .add_final(
                step_id="back_to_user_menu",
                message="🔙 Возвращаемся к меню пользователей..."
            )
            
            .set_timeout(900)  # 15 минут
            .build())


@manager_scenario(
    id="data_export",
    name="Экспорт данных",
    description="Экспорт пользователей и статистики",
    category=ScenarioCategory.ADMINISTRATION,
    entry_points=["data_export", "scenario_data_export"],
    tags=["admin"],
    priority=4
)
def create_data_export_scenario():
    """Сценарий экспорта данных"""
    return (DialogBuilder("data_export", "Экспорт данных",
                         "Экспорт пользователей и статистики в различных форматах")
            .start_with("export_menu_step")
            .set_permissions(["manager"])
            
            # 1. Меню экспорта
            .add_choice(
                step_id="export_menu_step",
                message=(
                    "📁 <b>Экспорт данных</b>\n\n"
                    "Выберите что экспортировать:"
                ),
                inline_keyboard=[
                    [("👥 Все пользователи", "export_all_users")],
                    [("📧 Только подписчики", "export_subscribers")],
                    [("🆕 Новые пользователи", "export_new_users")],
                    [("📊 Статистика", "export_statistics")],
                    [("⚙️ Настройки экспорта", "export_settings")],
                    [("🔙 Назад", "export_back")]
                ]
            )
            .add_condition("export_menu_step", {
                "export_menu_step=='export_all_users'": "execute_export_step"
            })
            
            # 2. Выполнение экспорта
            .add_action(
                step_id="execute_export_step",
                action=CommonActions.export_users_data,
                message="📁 Подготавливаем экспорт..."
            )
            .add_condition("execute_export_step", {
                "export_success==True": "export_success_step",
                "export_success==False": "export_error_step"
            })
            
            # 3a. Успешный экспорт
            .add_final(
                step_id="export_success_step",
                message=(
                    "✅ <b>Данные экспортированы!</b>\n\n"
                    "📁 Файл: {filename}\n"
                    "📊 Записей: {count}\n\n"
                    "Файл будет отправлен в чат."
                )
            )
            
            # 3b. Ошибка экспорта
            .add_choice(
                step_id="export_error_step",
                message=(
                    "❌ <b>Ошибка экспорта</b>\n\n"
                    "Не удалось экспортировать данные: {error}\n\n"
                    "Что делаем?"
                ),
                inline_keyboard=[
                    [("🔄 Попробовать снова", "retry_export")],
                    [("🔙 Назад", "back_to_export_menu")]
                ]
            )
            .add_condition("export_error_step", {
                "export_error_step=='retry_export'": "execute_export_step",
                "export_error_step=='back_to_export_menu'": "export_menu_step"
            })
            
            # 4. Финальные шаги
            .add_final(
                step_id="export_back",
                message="🔙 Возвращаемся в панель управления..."
            )
            
            .set_timeout(600)  # 10 минут
            .build())


@manager_scenario(
    id="system_management",
    name="Управление системой",
    description="Системные операции и настройки бота",
    category=ScenarioCategory.ADMINISTRATION,
    entry_points=["system_management", "scenario_system_management"],
    tags=["admin"],
    priority=4
)
def create_system_management_scenario():
    """Сценарий управления системой"""
    return (DialogBuilder("system_management", "Управление системой",
                         "Системные операции и настройки бота")
            .start_with("system_menu_step")
            .set_permissions(["manager"])
            
            # 1. Системное меню
            .add_choice(
                step_id="system_menu_step",
                message=(
                    "⚙️ <b>Управление системой</b>\n\n"
                    "Выберите операцию:"
                ),
                inline_keyboard=[
                    [("🗑️ Очистить базу данных", "clear_database")],
                    [("🔄 Перезагрузить сценарии", "reload_scenarios")],
                    [("📊 Системная информация", "system_info")],
                    [("🧹 Очистить сессии", "cleanup_sessions")],
                    [("📋 Логи системы", "view_logs")],
                    [("🔙 Назад", "system_back")]
                ]
            )
            .add_condition("system_menu_step", {
                "system_menu_step=='clear_database'": "clear_warning_step"
            })
            
            # 2. Предупреждение об очистке БД
            .add_choice(
                step_id="clear_warning_step",
                message=(
                    "⚠️ <b>ВНИМАНИЕ!</b>\n\n"
                    "Вы собираетесь удалить ВСЕ данные пользователей из базы данных.\n"
                    "Это действие нельзя отменить!\n\n"
                    "Будут удалены:\n"
                    "• Все пользователи\n"
                    "• Их персональные данные\n"
                    "• История регистраций\n\n"
                    "Продолжить?"
                ),
                inline_keyboard=[
                    [("🗑️ ДА, УДАЛИТЬ ВСЕ", "confirm_clear")],
                    [("❌ НЕТ, ОТМЕНИТЬ", "cancel_clear")]
                ]
            )
            .add_condition("clear_warning_step", {
                "clear_warning_step=='confirm_clear'": "execute_clear_step",
                "clear_warning_step=='cancel_clear'": "clear_cancelled_step"
            })
            
            # 3. Выполнение очистки
            .add_action(
                step_id="execute_clear_step",
                action=CommonActions.clear_database,
                message="🗑️ Очищаем базу данных..."
            )
            .add_condition("execute_clear_step", {
                "clear_success==True": "clear_success_step",
                "clear_success==False": "clear_error_step"
            })
            
            # 4a. Успешная очистка
            .add_final(
                step_id="clear_success_step",
                message=(
                    "✅ <b>База данных очищена!</b>\n\n"
                    "Удалено записей: {deleted_count}\n\n"
                    "Все пользовательские данные удалены из системы."
                )
            )
            
            # 4b. Ошибка очистки
            .add_choice(
                step_id="clear_error_step",
                message=(
                    "❌ <b>Ошибка очистки</b>\n\n"
                    "Не удалось очистить базу данных: {error}\n\n"
                    "Что делаем?"
                ),
                inline_keyboard=[
                    [("🔄 Попробовать снова", "retry_clear")],
                    [("🔙 Назад", "back_to_system")]
                ]
            )
            .add_condition("clear_error_step", {
                "clear_error_step=='retry_clear'": "clear_warning_step",
                "clear_error_step=='back_to_system'": "system_menu_step"
            })
            
            # 5. Финальные шаги
            .add_final(
                step_id="clear_cancelled_step",
                message="✅ Очистка базы данных отменена. Данные сохранены."
            )
            
            .add_final(
                step_id="system_back",
                message="🔙 Возвращаемся в панель управления..."
            )
            
            .set_timeout(300)  # 5 минут (критичные операции)
            .build())