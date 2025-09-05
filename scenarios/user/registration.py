#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сценарий регистрации пользователя
"""

from dialog_dsl import DialogBuilder, InputType
from ..common.validators import CommonValidators
from ..common.actions import CommonActions
from ..auto_register import user_scenario
from ..registry import ScenarioCategory


@user_scenario(
    id="user_registration",
    name="Регистрация в английском клубе",
    description="Полный процесс регистрации нового участника с согласиями и сбором данных",
    category=ScenarioCategory.REGISTRATION,
    entry_points=["/start", "start", "registration"],
    tags=["registration", "onboarding", "gdpr"],
    priority=10
)
def create_user_registration_scenario():
    """Создать сценарий регистрации пользователя"""
    return (DialogBuilder("user_registration", "Регистрация в английском клубе",
                         "Полный процесс регистрации нового участника с согласиями и сбором данных")
            .start_with("welcome_step")
            
            # 1. Приветствие и согласие на обработку данных
            .add_choice(
                step_id="welcome_step",
                message=(
                    "🇬🇧 <b>Привет! Добро пожаловать в английский клуб!</b>\n\n"
                    "Давай знакомиться! Как тебя зовут?\n\n"
                    "Но сначала мне нужно получить твое согласие на обработку персональных данных:"
                ),
                inline_keyboard=[
                    [("✅ Согласен на обработку данных", "data_consent_yes")],
                    [("❌ Не согласен", "data_consent_no")]
                ]
            )
            .add_condition("welcome_step", {
                "welcome_step=='data_consent_yes'": "consent_approved_step",
                "welcome_step=='data_consent_no'": "consent_denied_step"
            })
            
            # 2a. Согласие получено
            .add_message(
                step_id="consent_approved_step",
                message=(
                    "✅ <b>Отлично! Согласие на обработку данных получено.</b>\n\n"
                    "Теперь скажи, как тебя зовут? 😊"
                ),
                next_step="name_question_step"
            )
            
            # 2b. Согласие отклонено
            .add_final(
                step_id="consent_denied_step",
                message=(
                    "❌ К сожалению, без согласия на обработку данных я не могу продолжить регистрацию.\n\n"
                    "Если передумаешь, просто напиши /start снова! 😊"
                )
            )
            
            # 3. Запрос имени
            .add_question(
                step_id="name_question_step",
                message="Введите ваше имя:",
                input_type=InputType.TEXT,
                validations=[
                    CommonValidators.not_empty(),
                    CommonValidators.min_length(2),
                    CommonValidators.max_length(100),
                    CommonValidators.no_special_chars()
                ],
                next_step="experience_question_step"
            )
            
            # 4. Вопрос об опыте изучения английского
            .add_choice(
                step_id="experience_question_step",
                message="Приятно познакомиться, <b>{name_question}</b>! 😊\n\nТы уже изучал английский раньше?",
                inline_keyboard=[
                    [("✅ Да, изучал английский", "experience_yes")],
                    [("❌ Нет, только начинаю", "experience_no")]
                ],
                next_step="age_question_step"
            )
            
            # 5. Вопрос о возрасте
            .add_question(
                step_id="age_question_step",
                message=(
                    "Сколько тебе лет? (Просто напиши цифру)"
                ),
                input_type=InputType.NUMBER,
                validations=[
                    CommonValidators.is_number(),
                    CommonValidators.age_range(5, 100)
                ],
                next_step="newsletter_question_step"
            )
            
            # 6. Вопрос о подписке на рассылку + отправка СНАОП
            .add_choice(
                step_id="newsletter_question_step",
                message=(
                    "Отлично, <b>{name_question}</b>! 🎉\n\n"
                    "<b>Включи уведомления в этом боте, чтобы первым получать новости, "
                    "полезности и анонсы активностей клуба!</b>\n\n"
                    "Для этого:\n"
                    "1. Нажми на название бота вверху чата\n"
                    "2. Включи уведомления 🔔\n\n"
                    "📄 <b>Согласие на обработку персональных данных</b>\n\n"
                    "И последний вопрос:"
                ),
                inline_keyboard=[
                    [("✅ Даю согласие на рассылку", "newsletter_yes")],
                    [("❌ Не хочу получать рассылку", "newsletter_no")]
                ],
                next_step="send_snaop_step"
            )
            
            # 7. Отправка СНАОП документа
            .add_action(
                step_id="send_snaop_step", 
                action=CommonActions.send_document,
                next_step="prepare_data_step"
            )
            
            # 8. Подготовка данных для сохранения
            .add_action(
                step_id="prepare_data_step",
                action=lambda u, c, s: {
                    "data_consent": True,
                    "name": s.data.get("name_question"),
                    "age": int(s.data.get("age_question")) if s.data.get("age_question") else None,
                    "experience": "Да" if s.data.get("experience_question") == "experience_yes" else "Нет",
                    "newsletter_consent": s.data.get("newsletter_question") == "newsletter_yes"
                },
                next_step="save_user_step"
            )
            
            # 9. Сохранение пользователя в БД
            .add_action(
                step_id="save_user_step",
                action=CommonActions.save_user_to_database,
                message="💾 Сохраняем ваши данные...",
                next_step="send_newsletter_consent_step"
            )
            
            # 10. Отправка согласия на рассылку (если нужно)
            .add_action(
                step_id="send_newsletter_consent_step",
                action=CommonActions.send_document_if_newsletter_consent,
                next_step="format_summary_step"
            )
            
            # 11. Форматирование итоговой сводки
            .add_action(
                step_id="format_summary_step",
                action=CommonActions.format_user_summary,
                next_step="registration_complete_step"
            )
            
            # 12. Завершение регистрации
            .add_final(
                step_id="registration_complete_step",
                message=(
                    "{newsletter_message}\n\n"
                    "🎉 <b>Регистрация завершена!</b>\n\n"
                    "<b>Твои данные:</b>\n"
                    "{summary}\n\n"
                    "Добро пожаловать в наш английский клуб! 🇬🇧\n"
                    "Скоро ты получишь информацию о ближайших занятиях! 📚"
                )
            )
            
            .set_timeout(1800)  # 30 минут на регистрацию
            .build())


@user_scenario(
    id="quick_registration",
    name="Быстрая регистрация", 
    description="Упрощенный процесс регистрации для возвращающихся пользователей",
    category=ScenarioCategory.REGISTRATION,
    entry_points=["quick_start", "fast_registration"],
    tags=["quick", "returning_user"],
    priority=5
)
def create_quick_registration_scenario():
    """Создать упрощенный сценарий регистрации"""
    return (DialogBuilder("quick_registration", "Быстрая регистрация",
                         "Упрощенный процесс регистрации для возвращающихся пользователей")
            .start_with("quick_start_step")
            
            # 1. Быстрое приветствие
            .add_message(
                step_id="quick_start_step",
                message=(
                    "⚡ <b>Быстрая регистрация</b>\n\n"
                    "Похоже, вы уже были с нами! Давайте обновим ваши данные."
                ),
                next_step="quick_name_step"
            )
            
            # 2. Только имя и возраст
            .add_question(
                step_id="quick_name_step",
                message="Как вас зовут?",
                input_type=InputType.TEXT,
                validations=[CommonValidators.not_empty()],
                next_step="quick_age_step"
            )
            
            .add_question(
                step_id="quick_age_step", 
                message="Ваш возраст?",
                input_type=InputType.NUMBER,
                validations=[CommonValidators.age_range(5, 100)],
                next_step="quick_save_step"
            )
            
            # 3. Быстрое сохранение
            .add_action(
                step_id="quick_save_step",
                action=CommonActions.save_user_to_database,
                next_step="quick_complete_step"
            )
            
            .add_final(
                step_id="quick_complete_step",
                message="✅ <b>Данные обновлены!</b>\n\nДобро пожаловать обратно! 🎉"
            )
            
            .set_timeout(600)  # 10 минут
            .build())