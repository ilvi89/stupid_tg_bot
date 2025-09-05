#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сценарии обращения в поддержку
"""

import time
from dialog_dsl import DialogBuilder, InputType
from ..common.validators import CommonValidators
from ..auto_register import user_scenario
from ..registry import ScenarioCategory


def create_support_scenarios():
    """Создать все сценарии поддержки"""
    return [
        create_support_request_scenario(),
        create_support_faq_scenario()
    ]


@user_scenario(
    id="support_request",
    name="Обращение в поддержку",
    description="Создание тикета обращения в службу поддержки",
    category=ScenarioCategory.SUPPORT,
    entry_points=["user_support", "support", "scenario_support_request"]
)
def create_support_request_scenario():
    """Сценарий создания обращения в поддержку"""
    return (DialogBuilder("support_request", "Обращение в поддержку",
                         "Создание тикета обращения в службу поддержки")
            .start_with("support_category_step")
            
            # 1. Выбор категории обращения
            .add_choice(
                step_id="support_category_step",
                message=(
                    "📞 <b>Обращение в поддержку</b>\n\n"
                    "Выберите категорию вашего вопроса:"
                ),
                inline_keyboard=[
                    [("🔧 Техническая проблема", "tech_support")],
                    [("📚 Вопрос об обучении", "learning_support")],
                    [("💰 Вопрос об оплате", "payment_support")],
                    [("📝 Другое", "other_support")],
                    [("❓ Частые вопросы", "faq_support")],
                    [("❌ Отмена", "support_cancel")]
                ]
            )
            .add_condition("support_category_step", {
                "support_category_step=='faq_support'": "redirect_to_faq",
                "support_category_step=='support_cancel'": "support_cancelled_step"
            })
            
            # 2. Ввод описания проблемы
            .add_question(
                step_id="support_message_step",
                message=(
                    "📝 <b>Описание проблемы</b>\n\n"
                    "Категория: <b>{category_name}</b>\n\n"
                    "Опишите вашу проблему или вопрос подробно.\n"
                    "Чем больше информации вы предоставите, тем быстрее мы сможем помочь:"
                ),
                input_type=InputType.TEXT,
                validations=[
                    CommonValidators.not_empty(),
                    CommonValidators.min_length(10),
                    CommonValidators.max_length(2000),
                    CommonValidators.min_words(3)
                ],
                next_step="contact_info_step"
            )
            
            # 3. Запрос контактной информации (опционально)
            .add_choice(
                step_id="contact_info_step",
                message=(
                    "📧 <b>Контактная информация</b>\n\n"
                    "Хотите указать дополнительные контакты для связи?\n"
                    "(Это поможет нам быстрее решить вашу проблему)"
                ),
                inline_keyboard=[
                    [("📧 Указать email", "provide_email")],
                    [("📱 Указать телефон", "provide_phone")],
                    [("⏭️ Пропустить", "skip_contact")],
                    [("❌ Отмена", "support_cancel")]
                ]
            )
            .add_condition("contact_info_step", {
                "contact_info_step=='provide_email'": "email_input_step",
                "contact_info_step=='provide_phone'": "phone_input_step",
                "contact_info_step=='skip_contact'": "create_ticket_step",
                "contact_info_step=='support_cancel'": "support_cancelled_step"
            })
            
            # 4a. Ввод email
            .add_question(
                step_id="email_input_step",
                message="Введите ваш email адрес:",
                input_type=InputType.TEXT,
                validations=[CommonValidators.email_format()],
                next_step="create_ticket_step"
            )
            
            # 4b. Ввод телефона
            .add_question(
                step_id="phone_input_step", 
                message="Введите ваш номер телефона:",
                input_type=InputType.TEXT,
                validations=[CommonValidators.phone_format()],
                next_step="create_ticket_step"
            )
            
            # 5. Создание тикета
            .add_action(
                step_id="create_ticket_step",
                action=lambda u, c, s: {
                    "ticket_id": f"TICKET_{int(time.time())}",
                    "created_at": time.time(),
                    "status": "created",
                    "contact": s.data.get("email_input_step") or s.data.get("phone_input_step") or "Telegram"
                },
                message="🎫 Создаем ваше обращение...",
                next_step="ticket_created_step"
            )
            
            # 6. Тикет создан
            .add_choice(
                step_id="ticket_created_step",
                message=(
                    "✅ <b>Ваше обращение создано!</b>\n\n"
                    "🎫 <b>Номер обращения:</b> {ticket_id}\n"
                    "📂 <b>Категория:</b> {support_category_step}\n"
                    "📝 <b>Описание:</b> {support_message_step}\n"
                    "📧 <b>Контакт:</b> {contact}\n\n"
                    "⏱️ <b>Время ответа:</b> до 24 часов\n\n"
                    "Мы свяжемся с вами для решения вопроса.\n"
                    "Спасибо за обращение! 🙏"
                ),
                inline_keyboard=[
                    [("📋 Создать еще одно обращение", "create_another")],
                    [("❓ Частые вопросы", "view_faq")],
                    [("🔙 В главное меню", "back_to_menu")]
                ]
            )
            .add_condition("ticket_created_step", {
                "ticket_created_step=='create_another'": "support_category_step",
                "ticket_created_step=='view_faq'": "redirect_to_faq"
            })
            
            # 7. Финальные шаги
            .add_final(
                step_id="support_cancelled_step",
                message="❌ Обращение в поддержку отменено"
            )
            
            .add_final(
                step_id="redirect_to_faq",
                message="🔄 Переходим к частым вопросам..."
            )
            
            .add_final(
                step_id="back_to_menu",
                message="🔙 Возвращаемся в главное меню..."
            )
            
            .set_timeout(1200)  # 20 минут
            .build())


@user_scenario(
    id="support_faq",
    name="Частые вопросы",
    description="Просмотр ответов на частые вопросы",
    category=ScenarioCategory.SUPPORT,
    entry_points=["support_faq", "scenario_support_faq"]
)
def create_support_faq_scenario():
    """Сценарий просмотра частых вопросов"""
    return (DialogBuilder("support_faq", "Частые вопросы",
                         "Просмотр ответов на частые вопросы")
            .start_with("faq_categories_step")
            
            # 1. Категории FAQ
            .add_choice(
                step_id="faq_categories_step",
                message=(
                    "❓ <b>Частые вопросы</b>\n\n"
                    "Выберите категорию:"
                ),
                inline_keyboard=[
                    [("🚀 Начало работы", "faq_getting_started")],
                    [("📚 Обучение", "faq_learning")],
                    [("💰 Оплата", "faq_payment")],
                    [("🔧 Технические вопросы", "faq_technical")],
                    [("📱 Мобильное приложение", "faq_mobile")],
                    [("🔙 Назад", "faq_back")]
                ]
            )
            .add_condition("faq_categories_step", {
                "faq_categories_step=='faq_getting_started'": "faq_getting_started_step",
                "faq_categories_step=='faq_learning'": "faq_learning_step",
                "faq_categories_step=='faq_payment'": "faq_payment_step",
                "faq_categories_step=='faq_technical'": "faq_technical_step",
                "faq_categories_step=='faq_mobile'": "faq_mobile_step",
                "faq_categories_step=='faq_back'": "faq_complete_step"
            })
            
            # 2a. FAQ - Начало работы
            .add_choice(
                step_id="faq_getting_started_step",
                message=(
                    "🚀 <b>Начало работы</b>\n\n"
                    "<b>Q: Как начать изучение?</b>\n"
                    "A: Пройдите регистрацию командой /start и выберите свой уровень.\n\n"
                    "<b>Q: Сколько это стоит?</b>\n"
                    "A: Базовые материалы бесплатны. Премиум подписка - 990₽/месяц.\n\n"
                    "<b>Q: Нужно ли знание английского?</b>\n"
                    "A: Нет! У нас есть программы для всех уровней, включая полных новичков.\n\n"
                    "Не нашли ответ?"
                ),
                inline_keyboard=[
                    [("❓ Другие категории", "back_to_faq")],
                    [("📝 Задать вопрос", "ask_question")],
                    [("🔙 Назад", "faq_back")]
                ]
            )
            
            # 2b. FAQ - Обучение
            .add_choice(
                step_id="faq_learning_step",
                message=(
                    "📚 <b>Обучение</b>\n\n"
                    "<b>Q: Как проходят занятия?</b>\n"
                    "A: Онлайн в группах до 8 человек, 2-3 раза в неделю по 60 минут.\n\n"
                    "<b>Q: Можно ли заниматься индивидуально?</b>\n"
                    "A: Да, индивидуальные занятия доступны в премиум тарифе.\n\n"
                    "<b>Q: Как отслеживать прогресс?</b>\n"
                    "A: У нас есть система тестов и персональный трекер прогресса.\n\n"
                    "Не нашли ответ?"
                ),
                inline_keyboard=[
                    [("❓ Другие категории", "back_to_faq")],
                    [("📝 Задать вопрос", "ask_question")],
                    [("🔙 Назад", "faq_back")]
                ]
            )
            
            # 2c. FAQ - Оплата
            .add_choice(
                step_id="faq_payment_step",
                message=(
                    "💰 <b>Оплата</b>\n\n"
                    "<b>Q: Какие способы оплаты?</b>\n"
                    "A: Банковские карты, СБП, PayPal, криптовалюты.\n\n"
                    "<b>Q: Можно ли вернуть деньги?</b>\n"
                    "A: Да, в течение 14 дней без объяснения причин.\n\n"
                    "<b>Q: Есть ли скидки?</b>\n"
                    "A: Да! Скидка 20% при оплате за 3 месяца, 30% за 6 месяцев.\n\n"
                    "Не нашли ответ?"
                ),
                inline_keyboard=[
                    [("❓ Другие категории", "back_to_faq")],
                    [("📝 Задать вопрос", "ask_question")],
                    [("🔙 Назад", "faq_back")]
                ]
            )
            
            # 2d. FAQ - Технические вопросы
            .add_choice(
                step_id="faq_technical_step",
                message=(
                    "🔧 <b>Технические вопросы</b>\n\n"
                    "<b>Q: Бот не отвечает, что делать?</b>\n"
                    "A: Попробуйте команду /start или обратитесь к администратору.\n\n"
                    "<b>Q: Не приходят уведомления</b>\n"
                    "A: Проверьте настройки уведомлений в Telegram и в боте.\n\n"
                    "<b>Q: Как сбросить прогресс?</b>\n"
                    "A: Используйте команду /reset или обратитесь в поддержку.\n\n"
                    "Не нашли ответ?"
                ),
                inline_keyboard=[
                    [("❓ Другие категории", "back_to_faq")],
                    [("📝 Задать вопрос", "ask_question")],
                    [("🔙 Назад", "faq_back")]
                ]
            )
            
            # 2e. FAQ - Мобильное приложение
            .add_choice(
                step_id="faq_mobile_step",
                message=(
                    "📱 <b>Мобильное приложение</b>\n\n"
                    "<b>Q: Есть ли мобильное приложение?</b>\n"
                    "A: Пока нет, но вы можете использовать Telegram на любом устройстве.\n\n"
                    "<b>Q: Планируется ли приложение?</b>\n"
                    "A: Да, мы работаем над приложением для iOS и Android.\n\n"
                    "<b>Q: Как получить уведомления?</b>\n"
                    "A: Включите push-уведомления в настройках Telegram.\n\n"
                    "Не нашли ответ?"
                ),
                inline_keyboard=[
                    [("❓ Другие категории", "back_to_faq")],
                    [("📝 Задать вопрос", "ask_question")],
                    [("🔙 Назад", "faq_back")]
                ]
            )
            
            # 3. Переходы
            .add_condition("faq_getting_started_step", {
                "faq_getting_started_step=='back_to_faq'": "faq_categories_step",
                "faq_getting_started_step=='ask_question'": "support_message_step",
                "faq_getting_started_step=='faq_back'": "faq_complete_step"
            })
            
            .add_condition("faq_learning_step", {
                "faq_learning_step=='back_to_faq'": "faq_categories_step",
                "faq_learning_step=='ask_question'": "support_message_step",
                "faq_learning_step=='faq_back'": "faq_complete_step"
            })
            
            .add_condition("faq_payment_step", {
                "faq_payment_step=='back_to_faq'": "faq_categories_step", 
                "faq_payment_step=='ask_question'": "support_message_step",
                "faq_payment_step=='faq_back'": "faq_complete_step"
            })
            
            .add_condition("faq_technical_step", {
                "faq_technical_step=='back_to_faq'": "faq_categories_step",
                "faq_technical_step=='ask_question'": "support_message_step", 
                "faq_technical_step=='faq_back'": "faq_complete_step"
            })
            
            .add_condition("faq_mobile_step", {
                "faq_mobile_step=='back_to_faq'": "faq_categories_step",
                "faq_mobile_step=='ask_question'": "support_message_step",
                "faq_mobile_step=='faq_back'": "faq_complete_step"
            })
            
            # 4. Создание тикета
            .add_action(
                step_id="create_ticket_step",
                action=lambda u, c, s: {
                    "ticket_id": f"TICKET_{int(time.time())}",
                    "category": s.data.get("support_category_step", "other"),
                    "message": s.data.get("support_message_step", ""),
                    "contact": s.data.get("email_input_step") or s.data.get("phone_input_step") or "Telegram",
                    "created_at": int(time.time())
                },
                message="🎫 Создаем ваше обращение...",
                next_step="ticket_success_step"
            )
            
            # 5. Успешное создание тикета
            .add_choice(
                step_id="ticket_success_step",
                message=(
                    "✅ <b>Обращение успешно создано!</b>\n\n"
                    "🎫 <b>Номер:</b> {ticket_id}\n"
                    "📂 <b>Категория:</b> {category}\n"
                    "📞 <b>Контакт:</b> {contact}\n\n"
                    "📧 Мы ответим вам в течение 24 часов.\n"
                    "💬 Следите за уведомлениями в боте!\n\n"
                    "Спасибо за обращение! 🙏"
                ),
                inline_keyboard=[
                    [("📋 Создать еще обращение", "create_another")],
                    [("❓ Посмотреть FAQ", "view_faq_again")],
                    [("🔙 В главное меню", "back_to_menu")]
                ]
            )
            .add_condition("ticket_success_step", {
                "ticket_success_step=='create_another'": "support_category_step",
                "ticket_success_step=='view_faq_again'": "faq_categories_step"
            })
            
            # 6. Финальные шаги
            .add_final(
                step_id="support_cancelled_step",
                message="❌ Обращение в поддержку отменено"
            )
            
            .add_final(
                step_id="redirect_to_faq",
                message="🔄 Переходим к частым вопросам..."
            )
            
            .add_final(
                step_id="faq_complete_step",
                message="✅ Надеемся, мы помогли ответить на ваши вопросы!"
            )
            
            .add_final(
                step_id="back_to_menu",
                message="🔙 Возвращаемся в главное меню..."
            )
            
            .set_timeout(1800)  # 30 минут
            .build())


@user_scenario(
    id="support_faq_only",
    name="Частые вопросы (быстрый доступ)",
    description="Быстрый доступ к часто задаваемым вопросам",
    category=ScenarioCategory.SUPPORT,
    entry_points=["scenario_support_faq_only"]
)
def create_support_faq_only_scenario():
    """Отдельный сценарий для FAQ"""
    return (DialogBuilder("support_faq_only", "Частые вопросы",
                         "Быстрый доступ к часто задаваемым вопросам")
            .start_with("faq_main_step")
            
            .add_choice(
                step_id="faq_main_step",
                message=(
                    "❓ <b>Частые вопросы</b>\n\n"
                    "Здесь собраны ответы на самые популярные вопросы.\n"
                    "Выберите интересующую категорию:"
                ),
                inline_keyboard=[
                    [("🚀 Начало работы", "faq_start")],
                    [("📚 Процесс обучения", "faq_process")],
                    [("💰 Оплата и тарифы", "faq_pricing")],
                    [("🔧 Технические вопросы", "faq_tech")],
                    [("📞 Не нашел ответ", "contact_support")],
                    [("🔙 Назад", "faq_exit")]
                ]
            )
            
            # Обработка каждой категории аналогично предыдущему сценарию
            # ... (детальная реализация)
            
            .add_final(
                step_id="faq_exit",
                message="👋 Удачи в изучении английского!"
            )
            
            .set_timeout(600)  # 10 минут
            .build())