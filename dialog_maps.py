#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Диалоговые карты для пользователей и менеджеров
Описывает все возможные пути взаимодействия с ботом
"""

from dialog_dsl import DialogBuilder, Validators, InputType, DialogChain
from typing import Dict, Any
import sqlite3


# === ДЕЙСТВИЯ ДЛЯ ДИАЛОГОВ ===

async def save_user_registration(update, context, session):
    """Сохранить данные регистрации пользователя"""
    from bot import bot_instance
    
    user_data = {
        'telegram_id': session.user_id,
        'username': session.data.get('username', ''),
        'name': session.data['name'],
        'age': int(session.data['age']),
        'english_experience': session.data['experience'],
        'data_consent': True,
        'newsletter_consent': session.data.get('newsletter_consent', False)
    }
    
    bot_instance.save_user_data(user_data)
    return {"registration_completed": True}


async def send_documents(update, context, session):
    """Отправить документы пользователю"""
    from dialog_config import FILES
    import os
    
    # Отправляем СНАОП
    snaop_file = FILES['snaop']
    if os.path.exists(snaop_file):
        await update.callback_query.message.reply_document(
            document=open(snaop_file, 'rb'),
            caption="📄 Согласие на обработку персональных данных"
        )
    
    # Отправляем согласие на рассылку, если пользователь согласился
    if session.data.get('newsletter_consent'):
        consent_file = FILES['newsletter_consent']
        if os.path.exists(consent_file):
            await update.callback_query.message.reply_document(
                document=open(consent_file, 'rb'),
                caption="📄 Согласие на получение рассылки"
            )
    
    return {}


async def check_manager_password(update, context, session):
    """Проверить пароль менеджера"""
    from auth_manager import auth_manager
    
    password = session.data.get('password', '')
    user_id = session.user_id
    
    if auth_manager.authenticate(user_id, password):
        return {"authenticated": True}
    else:
        return {"authenticated": False, "error": "Неверный пароль"}


async def export_users_data(update, context, session):
    """Экспорт данных пользователей"""
    from manager_interface import ManagerInterface
    
    # Здесь будет логика экспорта
    return {"export_completed": True}


# === ДИАЛОГОВЫЕ КАРТЫ ===

def create_user_registration_dialog() -> DialogChain:
    """Диалог регистрации пользователя"""
    return (DialogBuilder("user_registration", "Регистрация пользователя", 
                         "Полный процесс регистрации нового участника клуба")
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
                ],
                next_step="check_consent_step"
            )
            
            # 2. Проверка согласия на обработку данных
            .add_action(
                step_id="check_consent_step",
                action=lambda u, c, s: {"data_consent": s.data.get('welcome') == "data_consent_yes"},
                next_step="consent_result_step"
            )
            .add_condition("check_consent_step", {
                "data_consent==True": "name_question_step",
                "data_consent==False": "consent_denied_step"
            })
            
            # 3a. Согласие получено - запрос имени
            .add_question(
                step_id="name_question_step",
                message=(
                    "✅ <b>Отлично! Согласие на обработку данных получено.</b>\n\n"
                    "Теперь скажи, как тебя зовут? 😊"
                ),
                input_type=InputType.TEXT,
                validations=[
                    Validators.not_empty(),
                    Validators.min_length(2),
                    Validators.max_length(100)
                ],
                next_step="experience_question_step"
            )
            
            # 3b. Согласие отклонено
            .add_final(
                step_id="consent_denied_step",
                message=(
                    "❌ К сожалению, без согласия на обработку данных я не могу продолжить регистрацию.\n\n"
                    "Если передумаешь, просто напиши /start снова! 😊"
                )
            )
            
            # 4. Вопрос об опыте изучения английского
            .add_choice(
                step_id="experience_question_step",
                message="Приятно познакомиться, <b>{name}</b>! 😊\n\nТы уже изучал английский раньше?",
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
                    "{'Отлично! 👍' if experience == 'experience_yes' else 'Замечательно! Все когда-то начинали! 🌟'}\n\n"
                    "Сколько тебе лет? (Просто напиши цифру)"
                ),
                input_type=InputType.NUMBER,
                validations=[
                    Validators.is_number(),
                    Validators.age_range(5, 100)
                ],
                next_step="newsletter_question_step"
            )
            
            # 6. Вопрос о подписке на рассылку
            .add_choice(
                step_id="newsletter_question_step",
                message=(
                    "Отлично, {name}! 🎉\n\n"
                    "<b>Включи уведомления в этом боте, чтобы первым получать новости, "
                    "полезности и анонсы активностей клуба!</b>\n\n"
                    "Для этого:\n"
                    "1. Нажми на название бота вверху чата\n"
                    "2. Включи уведомления 🔔\n\n"
                    "И последний вопрос:"
                ),
                inline_keyboard=[
                    [("✅ Даю согласие на рассылку", "newsletter_yes")],
                    [("❌ Не хочу получать рассылку", "newsletter_no")]
                ],
                next_step="save_registration_step"
            )
            
            # 7. Сохранение данных
            .add_action(
                step_id="save_registration_step",
                action=save_user_registration,
                next_step="send_documents_step"
            )
            
            # 8. Отправка документов
            .add_action(
                step_id="send_documents_step",
                action=send_documents,
                next_step="registration_complete_step"
            )
            
            # 9. Завершение регистрации
            .add_final(
                step_id="registration_complete_step",
                message=(
                    "{'✅ Отлично! Ты будешь получать все новости и анонсы!' if newsletter_consent else '✅ Хорошо, рассылку отправлять не буду.'}\n\n"
                    "🎉 <b>Регистрация завершена!</b>\n\n"
                    "<b>Твои данные:</b>\n"
                    "• Имя: {name}\n"
                    "• Возраст: {age} лет\n"
                    "• Опыт изучения: {'Да' if experience == 'experience_yes' else 'Нет'}\n"
                    "• Согласие на данные: ✅\n"
                    "• Согласие на рассылку: {'✅' if newsletter_consent else '❌'}\n\n"
                    "Добро пожаловать в наш английский клуб! 🇬🇧\n"
                    "Скоро ты получишь информацию о ближайших занятиях! 📚"
                )
            )
            
            .set_timeout(1800)  # 30 минут на регистрацию
            .build())


def create_manager_auth_dialog() -> DialogChain:
    """Диалог авторизации менеджера"""
    return (DialogBuilder("manager_auth", "Авторизация менеджера",
                         "Процесс входа в панель управления")
            .start_with("request_password_step")
            
            # 1. Запрос пароля
            .add_question(
                step_id="request_password_step",
                message=(
                    "🔐 <b>Авторизация менеджера</b>\n\n"
                    "Введите пароль для доступа к панели управления:"
                ),
                input_type=InputType.TEXT,
                validations=[Validators.not_empty()],
                next_step="check_password_step"
            )
            
            # 2. Проверка пароля
            .add_action(
                step_id="check_password_step",
                action=check_manager_password,
                next_step="password_result_step"
            )
            .add_condition("check_password_step", {
                "authenticated==True": "auth_success_step",
                "authenticated==False": "auth_failed_step"
            })
            
            # 3a. Успешная авторизация
            .add_final(
                step_id="auth_success_step",
                message=(
                    "✅ <b>Доступ разрешен!</b>\n\n"
                    "Добро пожаловать в панель управления."
                )
            )
            
            # 3b. Неудачная авторизация
            .add_final(
                step_id="auth_failed_step",
                message="❌ Неверный пароль. Доступ запрещен."
            )
            
            .set_timeout(300)  # 5 минут на авторизацию
            .set_permissions(["manager"])
            .build())


def create_broadcast_dialog() -> DialogChain:
    """Диалог создания рассылки"""
    return (DialogBuilder("manager_broadcast", "Создание рассылки",
                         "Процесс создания и отправки рассылки")
            .start_with("request_message_step")
            
            # 1. Запрос сообщения для рассылки
            .add_question(
                step_id="request_message_step",
                message=(
                    "📢 <b>Рассылка сообщения</b>\n\n"
                    "Введите текст сообщения для рассылки всем пользователям, "
                    "согласившимся на получение уведомлений:"
                ),
                input_type=InputType.TEXT,
                validations=[
                    Validators.not_empty(),
                    Validators.max_length(4000)
                ],
                next_step="confirm_broadcast_step"
            )
            
            # 2. Подтверждение рассылки
            .add_choice(
                step_id="confirm_broadcast_step",
                message=(
                    "📢 <b>Подтверждение рассылки</b>\n\n"
                    "<b>Сообщение:</b>\n{request_message}\n\n"
                    "<b>Получателей:</b> {recipients_count}\n\n"
                    "Отправить?"
                ),
                inline_keyboard=[
                    [("📤 Отправить", "broadcast_confirm")],
                    [("❌ Отмена", "broadcast_cancel")]
                ],
                next_step="broadcast_result_step"
            )
            .add_condition("confirm_broadcast_step", {
                "confirm_broadcast=='broadcast_confirm'": "send_broadcast_step",
                "confirm_broadcast=='broadcast_cancel'": "broadcast_cancelled_step"
            })
            
            # 3a. Отправка рассылки
            .add_action(
                step_id="send_broadcast_step",
                action=lambda u, c, s: {"broadcast_sent": True, "sent_count": 42},  # Заглушка
                message="📤 Отправляю сообщения...",
                next_step="broadcast_success_step"
            )
            
            # 3b. Рассылка отменена
            .add_final(
                step_id="broadcast_cancelled_step",
                message="❌ Рассылка отменена"
            )
            
            # 4. Успешная отправка
            .add_final(
                step_id="broadcast_success_step",
                message="✅ Рассылка завершена! Отправлено: {sent_count} сообщений"
            )
            
            .set_timeout(600)  # 10 минут на создание рассылки
            .set_permissions(["manager"])
            .build())


def create_user_profile_edit_dialog() -> DialogChain:
    """Диалог редактирования профиля пользователя"""
    return (DialogBuilder("user_profile_edit", "Редактирование профиля",
                         "Изменение данных профиля пользователя")
            .start_with("choose_field_step")
            
            # 1. Выбор поля для редактирования
            .add_choice(
                step_id="choose_field_step",
                message=(
                    "✏️ <b>Редактирование профиля</b>\n\n"
                    "Что вы хотите изменить?"
                ),
                inline_keyboard=[
                    [("👤 Имя", "edit_name")],
                    [("🎂 Возраст", "edit_age")],
                    [("📚 Опыт изучения", "edit_experience")],
                    [("📧 Настройки рассылки", "edit_newsletter")],
                    [("❌ Отмена", "edit_cancel")]
                ],
                next_step="edit_field_step"
            )
            .add_condition("choose_field_step", {
                "choose_field=='edit_name'": "edit_name_step",
                "choose_field=='edit_age'": "edit_age_step",
                "choose_field=='edit_experience'": "edit_experience_step",
                "choose_field=='edit_newsletter'": "edit_newsletter_step",
                "choose_field=='edit_cancel'": "edit_cancelled_step"
            })
            
            # 2a. Редактирование имени
            .add_question(
                step_id="edit_name_step",
                message="Введите новое имя:",
                input_type=InputType.TEXT,
                validations=[
                    Validators.not_empty(),
                    Validators.min_length(2),
                    Validators.max_length(100)
                ],
                next_step="save_changes_step"
            )
            
            # 2b. Редактирование возраста
            .add_question(
                step_id="edit_age_step",
                message="Введите новый возраст:",
                input_type=InputType.NUMBER,
                validations=[
                    Validators.is_number(),
                    Validators.age_range(5, 100)
                ],
                next_step="save_changes_step"
            )
            
            # 2c. Редактирование опыта
            .add_choice(
                step_id="edit_experience_step",
                message="Выберите ваш опыт изучения английского:",
                inline_keyboard=[
                    [("✅ Да, изучал английский", "experience_yes")],
                    [("❌ Нет, только начинаю", "experience_no")]
                ],
                next_step="save_changes_step"
            )
            
            # 2d. Редактирование настроек рассылки
            .add_choice(
                step_id="edit_newsletter_step",
                message="Настройки рассылки:",
                inline_keyboard=[
                    [("✅ Включить рассылку", "newsletter_on")],
                    [("❌ Отключить рассылку", "newsletter_off")]
                ],
                next_step="save_changes_step"
            )
            
            # 3. Сохранение изменений
            .add_action(
                step_id="save_changes_step",
                action=lambda u, c, s: {"changes_saved": True},  # Заглушка
                next_step="changes_saved_step"
            )
            
            # 4a. Изменения сохранены
            .add_final(
                step_id="changes_saved_step",
                message="✅ <b>Изменения сохранены!</b>\n\nВаш профиль обновлен."
            )
            
            # 4b. Редактирование отменено
            .add_final(
                step_id="edit_cancelled_step",
                message="❌ Редактирование отменено"
            )
            
            .set_timeout(600)  # 10 минут на редактирование
            .build())


def create_user_support_dialog() -> DialogChain:
    """Диалог обращения в поддержку"""
    return (DialogBuilder("user_support", "Обращение в поддержку",
                         "Отправка сообщения в службу поддержки")
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
                    [("❌ Отмена", "support_cancel")]
                ],
                next_step="support_message_step"
            )
            .add_condition("support_category_step", {
                "support_category=='support_cancel'": "support_cancelled_step"
            })
            
            # 2. Ввод сообщения
            .add_question(
                step_id="support_message_step",
                message=(
                    "Опишите вашу проблему или вопрос подробно.\n"
                    "Чем больше информации вы предоставите, тем быстрее мы сможем помочь:"
                ),
                input_type=InputType.TEXT,
                validations=[
                    Validators.not_empty(),
                    Validators.min_length(10),
                    Validators.max_length(2000)
                ],
                next_step="send_support_request_step"
            )
            
            # 3. Отправка обращения
            .add_action(
                step_id="send_support_request_step",
                action=lambda u, c, s: {"ticket_id": f"TICKET_{int(time.time())}"},
                next_step="support_sent_step"
            )
            
            # 4a. Обращение отправлено
            .add_final(
                step_id="support_sent_step",
                message=(
                    "✅ <b>Ваше обращение отправлено!</b>\n\n"
                    "Номер обращения: {ticket_id}\n"
                    "Категория: {support_category}\n\n"
                    "Мы ответим вам в течение 24 часов.\n"
                    "Спасибо за обращение! 🙏"
                )
            )
            
            # 4b. Обращение отменено
            .add_final(
                step_id="support_cancelled_step",
                message="❌ Обращение в поддержку отменено"
            )
            
            .set_timeout(900)  # 15 минут на создание обращения
            .build())


# === ДИАЛОГОВАЯ КАРТА ===

class DialogMap:
    """Карта всех диалогов системы"""
    
    def __init__(self):
        self.user_dialogs = {
            "registration": create_user_registration_dialog(),
            "profile_edit": create_user_profile_edit_dialog(),
            "support": create_user_support_dialog(),
        }
        
        self.manager_dialogs = {
            "auth": create_manager_auth_dialog(),
            "broadcast": create_broadcast_dialog(),
        }
        
        # Карта переходов между диалогами
        self.dialog_transitions = {
            # Пользовательские переходы
            "user_menu": {
                "profile": "profile_edit",
                "support": "support",
                "settings": None  # Прямое меню без диалога
            },
            
            # Менеджерские переходы  
            "manager_menu": {
                "broadcast": "broadcast",
                "stats": None,  # Прямое отображение
                "users": None,  # Прямое отображение
                "export": None  # Прямое действие
            }
        }
        
        # Точки входа в диалоги
        self.entry_points = {
            # Команды
            "/start": ("registration", "user"),
            "/manager": ("auth", "manager"),
            
            # Callback данные
            "user_edit_profile": ("profile_edit", "user"),
            "user_support": ("support", "user"),
            "mgr_broadcast": ("broadcast", "manager"),
        }
    
    def get_dialog_by_entry(self, entry_point: str) -> Tuple[Optional[DialogChain], str]:
        """Получить диалог по точке входа"""
        if entry_point in self.entry_points:
            dialog_id, user_type = self.entry_points[entry_point]
            
            if user_type == "user" and dialog_id in self.user_dialogs:
                return self.user_dialogs[dialog_id], user_type
            elif user_type == "manager" and dialog_id in self.manager_dialogs:
                return self.manager_dialogs[dialog_id], user_type
        
        return None, ""
    
    def get_all_dialogs(self) -> Dict[str, DialogChain]:
        """Получить все диалоги"""
        all_dialogs = {}
        all_dialogs.update(self.user_dialogs)
        all_dialogs.update(self.manager_dialogs)
        return all_dialogs


# === ДИАГРАММА СОСТОЯНИЙ ===

DIALOG_STATE_DIAGRAM = """
Диалоговая карта Telegram-бота для английского клуба

=== ПОЛЬЗОВАТЕЛЬСКИЕ ДИАЛОГИ ===

1. РЕГИСТРАЦИЯ (/start)
   ┌─────────────┐
   │   Старт     │
   └─────┬───────┘
         │
   ┌─────▼───────┐     НЕТ    ┌──────────────┐
   │  Согласие   ├───────────►│  Отказ       │
   │  на данные  │            │  (КОНЕЦ)     │
   └─────┬───────┘            └──────────────┘
         │ ДА
   ┌─────▼───────┐
   │  Ввод имени │
   └─────┬───────┘
         │
   ┌─────▼───────┐
   │   Опыт      │
   │ английского │
   └─────┬───────┘
         │
   ┌─────▼───────┐
   │ Ввод возраста│
   └─────┬───────┘
         │
   ┌─────▼───────┐
   │  Согласие   │
   │ на рассылку │
   └─────┬───────┘
         │
   ┌─────▼───────┐
   │ Сохранение  │
   │   данных    │
   └─────┬───────┘
         │
   ┌─────▼───────┐
   │  Отправка   │
   │ документов  │
   └─────┬───────┘
         │
   ┌─────▼───────┐
   │ Завершение  │
   │  (КОНЕЦ)    │
   └─────────────┘

2. РЕДАКТИРОВАНИЕ ПРОФИЛЯ
   ┌─────────────┐
   │ Выбор поля  │
   └─────┬───────┘
         │
   ┌─────▼───────┐
   │ Ввод нового │
   │  значения   │
   └─────┬───────┘
         │
   ┌─────▼───────┐
   │ Сохранение  │
   │  (КОНЕЦ)    │
   └─────────────┘

3. ОБРАЩЕНИЕ В ПОДДЕРЖКУ
   ┌─────────────┐
   │   Выбор     │
   │ категории   │
   └─────┬───────┘
         │
   ┌─────▼───────┐
   │    Ввод     │
   │  сообщения  │
   └─────┬───────┘
         │
   ┌─────▼───────┐
   │  Отправка   │
   │  (КОНЕЦ)    │
   └─────────────┘

=== МЕНЕДЖЕРСКИЕ ДИАЛОГИ ===

1. АВТОРИЗАЦИЯ (/manager)
   ┌─────────────┐
   │ Запрос      │
   │ пароля      │
   └─────┬───────┘
         │
   ┌─────▼───────┐     НЕТ    ┌──────────────┐
   │  Проверка   ├───────────►│    Отказ     │
   │  пароля     │            │   (КОНЕЦ)    │
   └─────┬───────┘            └──────────────┘
         │ ДА
   ┌─────▼───────┐
   │   Доступ    │
   │ разрешен    │
   │  (КОНЕЦ)    │
   └─────────────┘

2. СОЗДАНИЕ РАССЫЛКИ
   ┌─────────────┐
   │    Ввод     │
   │ сообщения   │
   └─────┬───────┘
         │
   ┌─────▼───────┐     НЕТ    ┌──────────────┐
   │Подтверждение├───────────►│   Отмена     │
   │  рассылки   │            │  (КОНЕЦ)     │
   └─────┬───────┘            └──────────────┘
         │ ДА
   ┌─────▼───────┐
   │  Отправка   │
   └─────┬───────┘
         │
   ┌─────▼───────┐
   │ Результат   │
   │  (КОНЕЦ)    │
   └─────────────┘

=== МЕХАНИЗМ ВОССТАНОВЛЕНИЯ ===

При любой ошибке в диалоге:
┌─────────────┐
│   ОШИБКА    │
└─────┬───────┘
      │
┌─────▼───────┐
│ Предложение │
│восстановления│
└─────┬───────┘
      │
┌─────▼───────┐
│  Выбор:     │
│ 1. Продолжить│
│ 2. Начать   │
│    заново   │
│ 3. Отменить │
└─────────────┘

=== СОСТОЯНИЯ СЕССИЙ ===

STARTED ──► IN_PROGRESS ──► WAITING_INPUT ──► COMPLETED
    │              │              │              │
    ▼              ▼              ▼              │
  ERROR ◄────── ERROR ◄────── ERROR             │
    │              │              │              │
    ▼              ▼              ▼              │
 PAUSED ────► PAUSED ────► PAUSED              │
    │              │              │              │
    ▼              ▼              ▼              │
CANCELLED ◄── CANCELLED ◄── CANCELLED ◄────────┘
"""


# Создаем глобальную карту диалогов
dialog_map = DialogMap()