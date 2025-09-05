#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Примеры использования диалоговой DSL системы
"""

import time
from dialog_dsl import DialogBuilder, Validators, InputType, DialogChain, ValidationRule
from typing import Dict, Any


# === ПРОСТЫЕ ПРИМЕРЫ ===

def create_simple_greeting_dialog() -> DialogChain:
    """Простой диалог приветствия"""
    return (DialogBuilder("simple_greeting", "Простое приветствие")
            .start_with("hello")
            
            .add_message(
                step_id="hello",
                message="👋 Привет! Добро пожаловать!",
                next_step="ask_name"
            )
            
            .add_question(
                step_id="ask_name",
                message="Как тебя зовут?",
                input_type=InputType.TEXT,
                validations=[Validators.not_empty()],
                next_step="goodbye"
            )
            
            .add_final(
                step_id="goodbye",
                message="Приятно познакомиться, {ask_name}! 😊"
            )
            
            .build())


# === ПРИМЕР ИНТЕГРАЦИИ ===

def register_all_example_dialogs(dialog_engine):
    """Зарегистрировать все примеры диалогов"""
    examples = [
        create_simple_greeting_dialog(),
    ]
    
    for dialog in examples:
        dialog_engine.register_chain(dialog)
    
    print(f"Зарегистрировано {len(examples)} примеров диалогов")


if __name__ == "__main__":
    # Пример использования
    from dialog_dsl import init_dialog_engine
    
    engine = init_dialog_engine("example.db")
    register_all_example_dialogs(engine)
    
    print("Примеры диалогов готовы к использованию!")