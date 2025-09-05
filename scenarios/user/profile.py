#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сценарии работы с профилем пользователя
"""

from dialog_dsl import DialogBuilder, InputType
from ..common.validators import CommonValidators
from ..common.actions import CommonActions


def create_profile_scenarios():
    """Создать все сценарии работы с профилем"""
    return [
        create_profile_view_scenario(),
        create_profile_edit_scenario(),
        create_profile_delete_scenario()
    ]


def create_profile_view_scenario():
    """Сценарий просмотра профиля"""
    return (DialogBuilder("profile_view", "Просмотр профиля",
                         "Отображение данных профиля пользователя")
            .start_with("load_profile_step")
            
            # 1. Загрузка данных профиля
            .add_action(
                step_id="load_profile_step",
                action=CommonActions.get_user_from_database,
                message="🔍 Загружаем ваш профиль...",
                next_step="check_profile_exists_step"
            )
            .add_condition("load_profile_step", {
                "user_found==True": "show_profile_step",
                "user_found==False": "no_profile_step"
            })
            
            # 2a. Показать профиль
            .add_choice(
                step_id="show_profile_step",
                message=(
                    "👤 <b>Ваш профиль</b>\n\n"
                    "<b>Имя:</b> {name}\n"
                    "<b>Возраст:</b> {age} лет\n"
                    "<b>Опыт изучения английского:</b> {english_experience}\n"
                    "<b>Рассылка:</b> {'✅ Включена' if newsletter_consent else '❌ Отключена'}\n"
                    "<b>Дата регистрации:</b> {registration_date}\n\n"
                    "Что хотите сделать?"
                ),
                inline_keyboard=[
                    [("✏️ Редактировать", "edit_profile")],
                    [("🔄 Обновить", "refresh_profile")],
                    [("🗑️ Удалить аккаунт", "delete_profile")],
                    [("🔙 Назад", "back_to_menu")]
                ]
            )
            .add_condition("show_profile_step", {
                "show_profile_step=='edit_profile'": "redirect_to_edit",
                "show_profile_step=='refresh_profile'": "load_profile_step",
                "show_profile_step=='delete_profile'": "redirect_to_delete"
            })
            
            # 2b. Профиль не найден
            .add_choice(
                step_id="no_profile_step",
                message=(
                    "❌ <b>Профиль не найден</b>\n\n"
                    "Вы еще не прошли регистрацию.\n\n"
                    "Что хотите сделать?"
                ),
                inline_keyboard=[
                    [("📝 Пройти регистрацию", "start_registration")],
                    [("🔙 Назад", "back_to_menu")]
                ]
            )
            
            # 3. Перенаправления (финальные шаги с инструкциями)
            .add_final(
                step_id="redirect_to_edit",
                message="🔄 Переходим к редактированию профиля..."
            )
            
            .add_final(
                step_id="redirect_to_delete", 
                message="🔄 Переходим к удалению аккаунта..."
            )
            
            .add_final(
                step_id="back_to_menu",
                message="🔙 Возвращаемся в главное меню..."
            )
            
            .set_timeout(300)  # 5 минут
            .build())


def create_profile_edit_scenario():
    """Сценарий редактирования профиля"""
    return (DialogBuilder("profile_edit", "Редактирование профиля",
                         "Изменение данных профиля пользователя")
            .start_with("load_current_data_step")
            
            # 1. Загружаем текущие данные
            .add_action(
                step_id="load_current_data_step",
                action=CommonActions.get_user_from_database,
                message="📋 Загружаем ваши текущие данные...",
                next_step="choose_field_step"
            )
            .add_condition("load_current_data_step", {
                "user_found==False": "no_profile_for_edit_step"
            })
            
            # 2. Выбор поля для редактирования
            .add_choice(
                step_id="choose_field_step",
                message=(
                    "✏️ <b>Редактирование профиля</b>\n\n"
                    "<b>Текущие данные:</b>\n"
                    "• Имя: {name}\n"
                    "• Возраст: {age} лет\n"
                    "• Опыт: {english_experience}\n"
                    "• Рассылка: {'Включена' if newsletter_consent else 'Отключена'}\n\n"
                    "Что хотите изменить?"
                ),
                inline_keyboard=[
                    [("👤 Имя", "edit_name")],
                    [("🎂 Возраст", "edit_age")],
                    [("📚 Опыт изучения", "edit_experience")],
                    [("📧 Настройки рассылки", "edit_newsletter")],
                    [("❌ Отмена", "edit_cancel")]
                ]
            )
            .add_condition("choose_field_step", {
                "choose_field_step=='edit_name'": "edit_name_step",
                "choose_field_step=='edit_age'": "edit_age_step", 
                "choose_field_step=='edit_experience'": "edit_experience_step",
                "choose_field_step=='edit_newsletter'": "edit_newsletter_step",
                "choose_field_step=='edit_cancel'": "edit_cancelled_step"
            })
            
            # 3a. Редактирование имени
            .add_question(
                step_id="edit_name_step",
                message="Введите новое имя:",
                input_type=InputType.TEXT,
                validations=[
                    CommonValidators.not_empty(),
                    CommonValidators.min_length(2),
                    CommonValidators.max_length(100)
                ],
                next_step="save_name_step"
            )
            
            .add_action(
                step_id="save_name_step",
                action=lambda u, c, s: {
                    "field_name": "name",
                    "field_value": s.data.get("edit_name_step")
                },
                next_step="update_field_step"
            )
            
            # 3b. Редактирование возраста
            .add_question(
                step_id="edit_age_step",
                message="Введите новый возраст:",
                input_type=InputType.NUMBER,
                validations=[
                    CommonValidators.is_number(),
                    CommonValidators.age_range(5, 100)
                ],
                next_step="save_age_step"
            )
            
            .add_action(
                step_id="save_age_step",
                action=lambda u, c, s: {
                    "field_name": "age",
                    "field_value": int(s.data.get("edit_age_step"))
                },
                next_step="update_field_step"
            )
            
            # 3c. Редактирование опыта
            .add_choice(
                step_id="edit_experience_step",
                message="Выберите ваш опыт изучения английского:",
                inline_keyboard=[
                    [("✅ Да, изучал английский", "exp_yes")],
                    [("❌ Нет, только начинаю", "exp_no")]
                ],
                next_step="save_experience_step"
            )
            
            .add_action(
                step_id="save_experience_step",
                action=lambda u, c, s: {
                    "field_name": "experience", 
                    "field_value": "Да" if s.data.get("edit_experience_step") == "exp_yes" else "Нет"
                },
                next_step="update_field_step"
            )
            
            # 3d. Редактирование рассылки
            .add_choice(
                step_id="edit_newsletter_step",
                message="Настройки рассылки:",
                inline_keyboard=[
                    [("✅ Включить рассылку", "newsletter_on")],
                    [("❌ Отключить рассылку", "newsletter_off")]
                ],
                next_step="save_newsletter_step"
            )
            
            .add_action(
                step_id="save_newsletter_step",
                action=lambda u, c, s: {
                    "field_name": "newsletter",
                    "field_value": s.data.get("edit_newsletter_step") == "newsletter_on"
                },
                next_step="update_field_step"
            )
            
            # 4. Обновление поля в БД
            .add_action(
                step_id="update_field_step",
                action=CommonActions.update_user_field,
                message="💾 Сохраняем изменения...",
                next_step="update_result_step"
            )
            .add_condition("update_field_step", {
                "update_success==True": "edit_success_step",
                "update_success==False": "edit_error_step"
            })
            
            # 5a. Успешное обновление
            .add_choice(
                step_id="edit_success_step",
                message=(
                    "✅ <b>Изменения сохранены!</b>\n\n"
                    "Поле '{updated_field}' успешно обновлено.\n\n"
                    "Что делаем дальше?"
                ),
                inline_keyboard=[
                    [("✏️ Изменить еще что-то", "edit_more")],
                    [("👁️ Посмотреть профиль", "view_profile")],
                    [("🔙 В главное меню", "back_to_menu")]
                ]
            )
            .add_condition("edit_success_step", {
                "edit_success_step=='edit_more'": "choose_field_step",
                "edit_success_step=='view_profile'": "redirect_to_view"
            })
            
            # 5b. Ошибка обновления
            .add_choice(
                step_id="edit_error_step",
                message=(
                    "❌ <b>Ошибка сохранения</b>\n\n"
                    "Не удалось сохранить изменения: {error}\n\n"
                    "Что делаем?"
                ),
                inline_keyboard=[
                    [("🔄 Попробовать снова", "retry_edit")],
                    [("❌ Отменить", "edit_cancel")]
                ]
            )
            .add_condition("edit_error_step", {
                "edit_error_step=='retry_edit'": "choose_field_step"
            })
            
            # 6. Финальные шаги
            .add_final(
                step_id="no_profile_for_edit_step",
                message=(
                    "❌ <b>Профиль не найден</b>\n\n"
                    "Сначала пройдите регистрацию командой /start"
                )
            )
            
            .add_final(
                step_id="edit_cancelled_step",
                message="❌ Редактирование отменено"
            )
            
            .add_final(
                step_id="redirect_to_view",
                message="🔄 Переходим к просмотру профиля..."
            )
            
            .set_timeout(900)  # 15 минут
            .build())


def create_profile_delete_scenario():
    """Сценарий удаления профиля"""
    return (DialogBuilder("profile_delete", "Удаление аккаунта",
                         "Полное удаление аккаунта пользователя из системы")
            .start_with("delete_warning_step")
            
            # 1. Предупреждение об удалении
            .add_choice(
                step_id="delete_warning_step",
                message=(
                    "⚠️ <b>ВНИМАНИЕ!</b>\n\n"
                    "Вы собираетесь <b>полностью удалить</b> свой аккаунт из системы.\n"
                    "Это действие нельзя отменить!\n\n"
                    "Будут удалены:\n"
                    "• Все ваши персональные данные\n"
                    "• История участия в клубе\n"
                    "• Настройки профиля\n\n"
                    "Вы уверены, что хотите продолжить?"
                ),
                inline_keyboard=[
                    [("🗑️ Да, удалить аккаунт", "confirm_delete")],
                    [("❌ Отмена", "cancel_delete")]
                ]
            )
            .add_condition("delete_warning_step", {
                "delete_warning_step=='confirm_delete'": "final_confirmation_step",
                "delete_warning_step=='cancel_delete'": "delete_cancelled_step"
            })
            
            # 2. Финальное подтверждение
            .add_choice(
                step_id="final_confirmation_step",
                message=(
                    "🔴 <b>ПОСЛЕДНЕЕ ПРЕДУПРЕЖДЕНИЕ</b>\n\n"
                    "Вы точно хотите удалить аккаунт?\n"
                    "После этого восстановление будет невозможно!"
                ),
                inline_keyboard=[
                    [("🗑️ УДАЛИТЬ НАВСЕГДА", "delete_confirmed")],
                    [("❌ НЕТ, ОТМЕНИТЬ", "cancel_delete")]
                ]
            )
            .add_condition("final_confirmation_step", {
                "final_confirmation_step=='delete_confirmed'": "execute_delete_step",
                "final_confirmation_step=='cancel_delete'": "delete_cancelled_step"
            })
            
            # 3. Выполнение удаления
            .add_action(
                step_id="execute_delete_step",
                action=lambda u, c, s: CommonActions.execute_query(
                    "DELETE FROM users WHERE telegram_id = ?", 
                    (s.user_id,)
                ),
                message="🗑️ Удаляем ваши данные...",
                next_step="delete_complete_step"
            )
            
            # 4a. Удаление завершено
            .add_final(
                step_id="delete_complete_step",
                message=(
                    "✅ <b>Аккаунт удален</b>\n\n"
                    "Ваши данные полностью удалены из системы.\n"
                    "Спасибо за участие в английском клубе!\n\n"
                    "Если захотите вернуться, просто нажмите /start"
                )
            )
            
            # 4b. Удаление отменено
            .add_final(
                step_id="delete_cancelled_step",
                message=(
                    "✅ <b>Удаление отменено</b>\n\n"
                    "Ваш аккаунт остается активным.\n"
                    "Рады, что вы остаетесь с нами! 😊"
                )
            )
            
            .set_timeout(600)  # 10 минут
            .build())