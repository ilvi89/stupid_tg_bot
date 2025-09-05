#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Общие валидаторы для сценариев
"""

import re
from typing import List
from dialog_dsl import ValidationRule


class CommonValidators:
    """Набор общих валидаторов для использования в сценариях"""
    
    @staticmethod
    def not_empty() -> ValidationRule:
        """Проверка на непустое значение"""
        return ValidationRule(
            name="not_empty",
            validator=lambda x: bool(str(x).strip()),
            error_message="Поле не может быть пустым"
        )
    
    @staticmethod
    def min_length(min_len: int) -> ValidationRule:
        """Проверка минимальной длины"""
        return ValidationRule(
            name=f"min_length_{min_len}",
            validator=lambda x: len(str(x).strip()) >= min_len,
            error_message=f"Минимальная длина: {min_len} символов"
        )
    
    @staticmethod
    def max_length(max_len: int) -> ValidationRule:
        """Проверка максимальной длины"""
        return ValidationRule(
            name=f"max_length_{max_len}",
            validator=lambda x: len(str(x).strip()) <= max_len,
            error_message=f"Максимальная длина: {max_len} символов"
        )
    
    @staticmethod
    def is_number() -> ValidationRule:
        """Проверка на число"""
        def validate_number(x):
            try:
                int(str(x).strip())
                return True
            except ValueError:
                return False
        
        return ValidationRule(
            name="is_number",
            validator=validate_number,
            error_message="Введите число"
        )
    
    @staticmethod
    def age_range(min_age: int, max_age: int) -> ValidationRule:
        """Проверка возраста в диапазоне"""
        def validate_age(x):
            try:
                age = int(str(x).strip())
                return min_age <= age <= max_age
            except ValueError:
                return False
        
        return ValidationRule(
            name=f"age_range_{min_age}_{max_age}",
            validator=validate_age,
            error_message=f"Возраст должен быть от {min_age} до {max_age} лет"
        )
    
    @staticmethod
    def contains_words(words: List[str], case_sensitive: bool = False) -> ValidationRule:
        """Проверка содержания определенных слов"""
        def validate_contains(x):
            text = str(x)
            if not case_sensitive:
                text = text.lower()
                words_to_check = [w.lower() for w in words]
            else:
                words_to_check = words
            
            return any(word in text for word in words_to_check)
        
        return ValidationRule(
            name=f"contains_words",
            validator=validate_contains,
            error_message=f"Ответ должен содержать одно из слов: {', '.join(words)}"
        )
    
    @staticmethod
    def regex_pattern(pattern: str, error_msg: str = None) -> ValidationRule:
        """Проверка по регулярному выражению"""
        compiled_pattern = re.compile(pattern)
        
        return ValidationRule(
            name=f"regex_{pattern[:20]}",
            validator=lambda x: bool(compiled_pattern.search(str(x))),
            error_message=error_msg or f"Не соответствует шаблону: {pattern}"
        )
    
    @staticmethod
    def email_format() -> ValidationRule:
        """Проверка формата email"""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        return ValidationRule(
            name="email_format",
            validator=lambda x: bool(re.match(email_pattern, str(x).strip())),
            error_message="Введите корректный email адрес"
        )
    
    @staticmethod
    def phone_format() -> ValidationRule:
        """Проверка формата телефона"""
        phone_pattern = r'^[\+]?[1-9][\d]{0,15}$'
        
        return ValidationRule(
            name="phone_format",
            validator=lambda x: bool(re.match(phone_pattern, str(x).strip().replace(' ', '').replace('-', ''))),
            error_message="Введите корректный номер телефона"
        )
    
    @staticmethod
    def one_of_choices(choices: List[str], case_sensitive: bool = False) -> ValidationRule:
        """Проверка на один из вариантов"""
        def validate_choice(x):
            text = str(x).strip()
            if not case_sensitive:
                text = text.lower()
                choices_to_check = [c.lower() for c in choices]
            else:
                choices_to_check = choices
            
            return text in choices_to_check
        
        return ValidationRule(
            name="one_of_choices",
            validator=validate_choice,
            error_message=f"Выберите один из вариантов: {', '.join(choices)}"
        )
    
    @staticmethod
    def positive_number() -> ValidationRule:
        """Проверка на положительное число"""
        def validate_positive(x):
            try:
                num = float(str(x).strip())
                return num > 0
            except ValueError:
                return False
        
        return ValidationRule(
            name="positive_number",
            validator=validate_positive,
            error_message="Введите положительное число"
        )
    
    @staticmethod
    def range_number(min_val: float, max_val: float) -> ValidationRule:
        """Проверка числа в диапазоне"""
        def validate_range(x):
            try:
                num = float(str(x).strip())
                return min_val <= num <= max_val
            except ValueError:
                return False
        
        return ValidationRule(
            name=f"range_{min_val}_{max_val}",
            validator=validate_range,
            error_message=f"Число должно быть от {min_val} до {max_val}"
        )
    
    @staticmethod
    def no_special_chars() -> ValidationRule:
        """Проверка отсутствия специальных символов"""
        def validate_no_special(x):
            text = str(x).strip()
            # Разрешаем только буквы, цифры, пробелы и базовые знаки препинания
            allowed_pattern = r'^[a-zA-Zа-яА-Я0-9\s\.\,\!\?\-]+$'
            return bool(re.match(allowed_pattern, text))
        
        return ValidationRule(
            name="no_special_chars",
            validator=validate_no_special,
            error_message="Используйте только буквы, цифры и базовые знаки препинания"
        )
    
    @staticmethod
    def max_words(max_count: int) -> ValidationRule:
        """Проверка максимального количества слов"""
        def validate_word_count(x):
            words = str(x).strip().split()
            return len(words) <= max_count
        
        return ValidationRule(
            name=f"max_words_{max_count}",
            validator=validate_word_count,
            error_message=f"Максимум {max_count} слов"
        )
    
    @staticmethod
    def min_words(min_count: int) -> ValidationRule:
        """Проверка минимального количества слов"""
        def validate_word_count(x):
            words = str(x).strip().split()
            return len(words) >= min_count
        
        return ValidationRule(
            name=f"min_words_{min_count}",
            validator=validate_word_count,
            error_message=f"Минимум {min_count} слов"
        )


class BusinessValidators:
    """Валидаторы для бизнес-логики английского клуба"""
    
    @staticmethod
    def english_level() -> ValidationRule:
        """Проверка уровня английского"""
        levels = ["beginner", "elementary", "pre-intermediate", "intermediate", 
                 "upper-intermediate", "advanced", "proficiency"]
        
        def validate_level(x):
            text = str(x).lower().strip()
            return any(level in text for level in levels)
        
        return ValidationRule(
            name="english_level",
            validator=validate_level,
            error_message="Укажите корректный уровень английского"
        )
    
    @staticmethod
    def study_goals() -> ValidationRule:
        """Проверка целей изучения"""
        goals = ["business", "travel", "academic", "conversation", "general", "exam"]
        
        def validate_goals(x):
            text = str(x).lower().strip()
            return any(goal in text for goal in goals)
        
        return ValidationRule(
            name="study_goals",
            validator=validate_goals,
            error_message="Укажите цель изучения: бизнес, путешествия, учеба, разговор, общее развитие или экзамен"
        )
    
    @staticmethod
    def study_time_per_day() -> ValidationRule:
        """Проверка времени изучения в день"""
        def validate_time(x):
            try:
                minutes = int(str(x).strip())
                return 15 <= minutes <= 480  # от 15 минут до 8 часов
            except ValueError:
                return False
        
        return ValidationRule(
            name="study_time_per_day",
            validator=validate_time,
            error_message="Время изучения должно быть от 15 до 480 минут в день"
        )
    
    @staticmethod
    def manager_password_strength() -> ValidationRule:
        """Проверка силы пароля менеджера"""
        def validate_password(x):
            password = str(x).strip()
            
            # Минимум 8 символов
            if len(password) < 8:
                return False
            
            # Должны быть буквы и цифры
            has_letter = any(c.isalpha() for c in password)
            has_digit = any(c.isdigit() for c in password)
            
            return has_letter and has_digit
        
        return ValidationRule(
            name="manager_password_strength",
            validator=validate_password,
            error_message="Пароль должен содержать минимум 8 символов, включая буквы и цифры"
        )