#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сценарии создания и отправки рассылки
"""

import time
from dialog_dsl import DialogBuilder, InputType
from ..common.validators import CommonValidators
from ..common.actions import CommonActions
from ..auto_register import manager_scenario
from ..registry import ScenarioCategory


def create_broadcast_scenarios():
    """Создать все сценарии рассылки"""
    return [
        create_broadcast_creation_scenario(),
        create_broadcast_template_scenario(),
        create_scheduled_broadcast_scenario()
    ]


def create_broadcast_creation_scenario():
    """Сценарий создания рассылки"""
    return (DialogBuilder("broadcast_creation", "Создание рассылки",
                         "Создание и отправка сообщения всем подписчикам")
            .start_with("broadcast_intro_step")
            .set_permissions(["manager"])
            
            # 1. Введение и получение подписчиков
            .add_action(
                step_id="broadcast_intro_step",
                action=CommonActions.get_newsletter_subscribers,
                message="📢 <b>Создание рассылки</b>\n\n📊 Загружаем список подписчиков...",
                next_step="check_subscribers_step"
            )
            .add_condition("broadcast_intro_step", {
                "subscribers_found==True": "message_input_step",
                "subscribers_found==False": "no_subscribers_step"
            })
            
            # 2a. Нет подписчиков
            .add_final(
                step_id="no_subscribers_step",
                message=(
                    "📭 <b>Нет подписчиков</b>\n\n"
                    "В базе данных нет пользователей, согласившихся на рассылку.\n"
                    "Рассылка невозможна."
                )
            )
            
            # 2b. Ввод сообщения для рассылки
            .add_question(
                step_id="message_input_step",
                message=(
                    "📢 <b>Создание рассылки</b>\n\n"
                    "👥 Подписчиков: {count}\n\n"
                    "Введите текст сообщения для рассылки:\n\n"
                    "💡 <i>Поддерживается HTML разметка: &lt;b&gt;жирный&lt;/b&gt;, &lt;i&gt;курсив&lt;/i&gt;</i>"
                ),
                input_type=InputType.TEXT,
                validations=[
                    CommonValidators.not_empty(),
                    CommonValidators.min_length(10),
                    CommonValidators.max_length(4000),
                    CommonValidators.min_words(3)
                ],
                next_step="message_preview_step"
            )
            
            # 3. Предварительный просмотр
            .add_choice(
                step_id="message_preview_step",
                message=(
                    "📋 <b>Предварительный просмотр рассылки</b>\n\n"
                    "📝 <b>Сообщение:</b>\n"
                    "┌─────────────────────┐\n"
                    "│ 📢 Сообщение от английского клуба:\n\n"
                    "{message_input_step}"
                    "\n└─────────────────────┘\n\n"
                    "👥 <b>Получателей:</b> {count}\n"
                    "📅 <b>Время отправки:</b> сейчас\n\n"
                    "Отправить рассылку?"
                ),
                inline_keyboard=[
                    [("📤 Отправить сейчас", "send_now")],
                    [("✏️ Изменить сообщение", "edit_message")],
                    [("👥 Выбрать получателей", "select_recipients")],
                    [("⏰ Запланировать", "schedule_broadcast")],
                    [("❌ Отмена", "broadcast_cancel")]
                ]
            )
            .add_condition("message_preview_step", {
                "message_preview_step=='send_now'": "send_broadcast_step",
                "message_preview_step=='edit_message'": "message_input_step",
                "message_preview_step=='select_recipients'": "select_recipients_step",
                "message_preview_step=='schedule_broadcast'": "redirect_to_schedule",
                "message_preview_step=='broadcast_cancel'": "broadcast_cancelled_step"
            })
            
            # 4. Выбор получателей (дополнительная фильтрация)
            .add_choice(
                step_id="select_recipients_step",
                message=(
                    "👥 <b>Выбор получателей</b>\n\n"
                    "Всего подписчиков: {count}\n\n"
                    "Выберите группу для отправки:"
                ),
                inline_keyboard=[
                    [("👥 Все подписчики", "all_subscribers")],
                    [("🆕 Только новые (неделя)", "new_users")],
                    [("📚 С опытом изучения", "experienced_users")],
                    [("🌱 Новички", "beginner_users")],
                    [("🎂 По возрасту", "age_filter")],
                    [("🔙 Назад", "back_to_preview")]
                ]
            )
            .add_condition("select_recipients_step", {
                "select_recipients_step=='all_subscribers'": "message_preview_step",
                "select_recipients_step=='back_to_preview'": "message_preview_step"
                # Остальные фильтры можно добавить позже
            })
            
            # 5. Отправка рассылки
            .add_action(
                step_id="send_broadcast_step",
                action=lambda u, c, s: {
                    "broadcast_message": s.data.get("message_input_step"),
                    "subscribers": s.data.get("subscribers", [])
                },
                message="📤 Отправляем сообщения...",
                next_step="execute_broadcast_step"
            )
            
            .add_action(
                step_id="execute_broadcast_step",
                action=CommonActions.send_broadcast_message,
                message="⏳ Идет отправка, пожалуйста подождите...",
                next_step="broadcast_result_step"
            )
            .add_condition("execute_broadcast_step", {
                "broadcast_success==True": "broadcast_success_step",
                "broadcast_success==False": "broadcast_error_step"
            })
            
            # 6a. Успешная рассылка
            .add_choice(
                step_id="broadcast_success_step",
                message=(
                    "✅ <b>Рассылка завершена!</b>\n\n"
                    "📊 <b>Статистика отправки:</b>\n"
                    "• Отправлено: {sent_count}\n"
                    "• Не доставлено: {failed_count}\n"
                    "• Всего получателей: {total_count}\n\n"
                    "🎉 Рассылка успешно выполнена!"
                ),
                inline_keyboard=[
                    [("📢 Создать новую рассылку", "create_new")],
                    [("📊 Подробная статистика", "detailed_stats")],
                    [("🔙 В панель управления", "back_to_panel")]
                ]
            )
            .add_condition("broadcast_success_step", {
                "broadcast_success_step=='create_new'": "broadcast_intro_step",
                "broadcast_success_step=='detailed_stats'": "redirect_to_stats"
            })
            
            # 6b. Ошибка рассылки
            .add_choice(
                step_id="broadcast_error_step",
                message=(
                    "❌ <b>Ошибка рассылки</b>\n\n"
                    "Произошла ошибка при отправке: {error}\n\n"
                    "Что делаем?"
                ),
                inline_keyboard=[
                    [("🔄 Попробовать снова", "retry_broadcast")],
                    [("✏️ Изменить сообщение", "edit_and_retry")],
                    [("❌ Отменить", "broadcast_cancel")]
                ]
            )
            .add_condition("broadcast_error_step", {
                "broadcast_error_step=='retry_broadcast'": "send_broadcast_step",
                "broadcast_error_step=='edit_and_retry'": "message_input_step"
            })
            
            # 7. Финальные шаги
            .add_final(
                step_id="broadcast_cancelled_step",
                message="❌ Рассылка отменена"
            )
            
            .add_final(
                step_id="redirect_to_schedule",
                message="🔄 Переходим к планировщику рассылок..."
            )
            
            .add_final(
                step_id="redirect_to_stats",
                message="🔄 Переходим к статистике..."
            )
            
            .add_final(
                step_id="back_to_panel",
                message="🔙 Возвращаемся в панель управления..."
            )
            
            .set_timeout(1800)  # 30 минут
            .build())


def create_broadcast_template_scenario():
    """Сценарий создания шаблона рассылки"""
    return (DialogBuilder("broadcast_template", "Шаблоны рассылки",
                         "Создание и управление шаблонами сообщений")
            .start_with("template_menu_step")
            .set_permissions(["manager"])
            
            # 1. Меню шаблонов
            .add_choice(
                step_id="template_menu_step",
                message=(
                    "📝 <b>Шаблоны рассылки</b>\n\n"
                    "Управление готовыми шаблонами сообщений для быстрой отправки.\n\n"
                    "Выберите действие:"
                ),
                inline_keyboard=[
                    [("➕ Создать новый шаблон", "create_template")],
                    [("📋 Использовать шаблон", "use_template")],
                    [("📝 Редактировать шаблон", "edit_template")],
                    [("🗑️ Удалить шаблон", "delete_template")],
                    [("📄 Список шаблонов", "list_templates")],
                    [("🔙 Назад", "template_back")]
                ]
            )
            
            # 2. Создание нового шаблона
            .add_question(
                step_id="create_template_step",
                message=(
                    "➕ <b>Создание шаблона</b>\n\n"
                    "Введите название шаблона:"
                ),
                input_type=InputType.TEXT,
                validations=[
                    CommonValidators.not_empty(),
                    CommonValidators.max_length(50)
                ],
                next_step="template_content_step"
            )
            
            .add_question(
                step_id="template_content_step",
                message=(
                    "📝 <b>Содержимое шаблона</b>\n\n"
                    "Название: <b>{create_template_step}</b>\n\n"
                    "Введите текст шаблона:"
                ),
                input_type=InputType.TEXT,
                validations=[
                    CommonValidators.not_empty(),
                    CommonValidators.max_length(4000)
                ],
                next_step="save_template_step"
            )
            
            # 3. Сохранение шаблона
            .add_action(
                step_id="save_template_step",
                action=lambda u, c, s: {
                    "template_saved": True,
                    "template_id": f"TMPL_{int(time.time())}",
                    "template_name": s.data.get("create_template_step"),
                    "template_content": s.data.get("template_content_step")
                },
                message="💾 Сохраняем шаблон...",
                next_step="template_saved_step"
            )
            
            .add_final(
                step_id="template_saved_step",
                message=(
                    "✅ <b>Шаблон сохранен!</b>\n\n"
                    "📝 Название: {template_name}\n"
                    "🆔 ID: {template_id}\n\n"
                    "Теперь вы можете использовать этот шаблон для быстрой рассылки."
                )
            )
            
            .add_final(
                step_id="template_back",
                message="🔙 Возвращаемся к рассылкам..."
            )
            
            .set_timeout(900)  # 15 минут
            .build())


def create_scheduled_broadcast_scenario():
    """Сценарий отложенной рассылки"""
    return (DialogBuilder("scheduled_broadcast", "Отложенная рассылка",
                         "Планирование рассылки на определенное время")
            .start_with("schedule_intro_step")
            .set_permissions(["manager"])
            
            # 1. Введение
            .add_message(
                step_id="schedule_intro_step",
                message=(
                    "⏰ <b>Отложенная рассылка</b>\n\n"
                    "Запланируйте отправку сообщения на определенное время.\n"
                    "Это удобно для анонсов мероприятий и напоминаний."
                ),
                next_step="schedule_message_step"
            )
            
            # 2. Ввод сообщения
            .add_question(
                step_id="schedule_message_step",
                message="Введите текст сообщения для отложенной отправки:",
                input_type=InputType.TEXT,
                validations=[
                    CommonValidators.not_empty(),
                    CommonValidators.max_length(4000)
                ],
                next_step="schedule_time_step"
            )
            
            # 3. Выбор времени отправки
            .add_choice(
                step_id="schedule_time_step",
                message=(
                    "⏰ <b>Время отправки</b>\n\n"
                    "Когда отправить сообщение?"
                ),
                inline_keyboard=[
                    [("🌅 Завтра утром (09:00)", "tomorrow_morning")],
                    [("🌆 Завтра вечером (18:00)", "tomorrow_evening")],
                    [("📅 Через неделю", "next_week")],
                    [("🕐 Указать точное время", "custom_time")],
                    [("📤 Отправить сейчас", "send_immediately")],
                    [("❌ Отмена", "schedule_cancel")]
                ]
            )
            .add_condition("schedule_time_step", {
                "schedule_time_step=='send_immediately'": "redirect_to_immediate",
                "schedule_time_step=='custom_time'": "custom_time_step",
                "schedule_time_step=='schedule_cancel'": "schedule_cancelled_step"
            })
            
            # 4. Ввод произвольного времени
            .add_question(
                step_id="custom_time_step",
                message=(
                    "🕐 <b>Точное время отправки</b>\n\n"
                    "Введите дату и время в формате:\n"
                    "<code>ДД.ММ.ГГГГ ЧЧ:ММ</code>\n\n"
                    "Например: <code>25.12.2024 10:30</code>"
                ),
                input_type=InputType.TEXT,
                validations=[
                    CommonValidators.not_empty(),
                    CommonValidators.regex_pattern(
                        r'^\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}$',
                        "Используйте формат: ДД.ММ.ГГГГ ЧЧ:ММ"
                    )
                ],
                next_step="schedule_confirmation_step"
            )
            
            # 5. Подтверждение планирования
            .add_choice(
                step_id="schedule_confirmation_step",
                message=(
                    "📅 <b>Подтверждение планирования</b>\n\n"
                    "📝 <b>Сообщение:</b> {schedule_message_step}\n"
                    "⏰ <b>Время отправки:</b> {schedule_time_formatted}\n"
                    "👥 <b>Получателей:</b> {count}\n\n"
                    "Запланировать рассылку?"
                ),
                inline_keyboard=[
                    [("✅ Запланировать", "confirm_schedule")],
                    [("✏️ Изменить время", "change_time")],
                    [("✏️ Изменить сообщение", "change_message")],
                    [("❌ Отмена", "schedule_cancel")]
                ]
            )
            .add_condition("schedule_confirmation_step", {
                "schedule_confirmation_step=='confirm_schedule'": "execute_schedule_step",
                "schedule_confirmation_step=='change_time'": "schedule_time_step",
                "schedule_confirmation_step=='change_message'": "schedule_message_step"
            })
            
            # 6. Выполнение планирования
            .add_action(
                step_id="execute_schedule_step",
                action=lambda u, c, s: {
                    "schedule_success": True,
                    "schedule_id": f"SCHED_{int(time.time())}",
                    "scheduled_for": s.data.get("custom_time_step", "завтра")
                },
                message="📅 Планируем рассылку...",
                next_step="schedule_success_step"
            )
            
            # 7. Успешное планирование
            .add_choice(
                step_id="schedule_success_step",
                message=(
                    "✅ <b>Рассылка запланирована!</b>\n\n"
                    "🆔 <b>ID рассылки:</b> {schedule_id}\n"
                    "⏰ <b>Время отправки:</b> {scheduled_for}\n"
                    "👥 <b>Получателей:</b> {count}\n\n"
                    "Рассылка будет автоматически отправлена в указанное время."
                ),
                inline_keyboard=[
                    [("📋 Список запланированных", "list_scheduled")],
                    [("📢 Создать новую рассылку", "create_new_broadcast")],
                    [("🔙 В панель управления", "back_to_panel")]
                ]
            )
            
            # 8. Финальные шаги и перенаправления
            .add_final(
                step_id="schedule_cancelled_step",
                message="❌ Планирование рассылки отменено"
            )
            
            .add_final(
                step_id="redirect_to_immediate",
                message="🔄 Переходим к немедленной отправке..."
            )
            
            .add_final(
                step_id="list_scheduled",
                message="🔄 Переходим к списку запланированных рассылок..."
            )
            
            .add_final(
                step_id="create_new_broadcast",
                message="🔄 Создаем новую рассылку..."
            )
            
            .add_final(
                step_id="back_to_panel",
                message="🔙 Возвращаемся в панель управления..."
            )
            
            .set_timeout(1200)  # 20 минут
            .build())