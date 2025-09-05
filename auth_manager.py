#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль авторизации и управления сессиями менеджеров
"""

import os
import time
import hashlib
from typing import Dict, Optional
from datetime import datetime, timedelta

class AuthManager:
    """Менеджер авторизации для управления доступом менеджеров"""
    
    def __init__(self):
        self.manager_password = os.getenv('MANAGER_PASSWORD', 'admin123')
        self.session_timeout = int(os.getenv('MANAGER_SESSION_TIMEOUT', '3600'))  # 1 час
        self.active_sessions: Dict[int, Dict] = {}  # user_id -> session_info
    
    def authenticate(self, user_id: int, password: str) -> bool:
        """
        Проверка пароля и создание сессии
        
        Args:
            user_id: ID пользователя Telegram
            password: Введенный пароль
            
        Returns:
            bool: True если аутентификация успешна
        """
        if password == self.manager_password:
            self._create_session(user_id)
            return True
        return False
    
    def is_authorized(self, user_id: int) -> bool:
        """
        Проверка авторизации пользователя
        
        Args:
            user_id: ID пользователя Telegram
            
        Returns:
            bool: True если пользователь авторизован
        """
        if user_id not in self.active_sessions:
            return False
        
        session = self.active_sessions[user_id]
        if self._is_session_expired(session):
            self._remove_session(user_id)
            return False
        
        # Обновляем время последней активности
        session['last_activity'] = time.time()
        return True
    
    def logout(self, user_id: int) -> bool:
        """
        Выход из системы (удаление сессии)
        
        Args:
            user_id: ID пользователя Telegram
            
        Returns:
            bool: True если сессия была удалена
        """
        return self._remove_session(user_id)
    
    def get_session_info(self, user_id: int) -> Optional[Dict]:
        """
        Получение информации о сессии
        
        Args:
            user_id: ID пользователя Telegram
            
        Returns:
            Dict или None: Информация о сессии
        """
        if user_id in self.active_sessions and not self._is_session_expired(self.active_sessions[user_id]):
            return self.active_sessions[user_id].copy()
        return None
    
    def cleanup_expired_sessions(self) -> int:
        """
        Очистка истекших сессий
        
        Returns:
            int: Количество удаленных сессий
        """
        expired_users = []
        for user_id, session in self.active_sessions.items():
            if self._is_session_expired(session):
                expired_users.append(user_id)
        
        for user_id in expired_users:
            self._remove_session(user_id)
        
        return len(expired_users)
    
    def get_active_sessions_count(self) -> int:
        """
        Получение количества активных сессий
        
        Returns:
            int: Количество активных сессий
        """
        self.cleanup_expired_sessions()
        return len(self.active_sessions)
    
    def _create_session(self, user_id: int) -> None:
        """Создание новой сессии"""
        now = time.time()
        session_token = self._generate_session_token(user_id, now)
        
        self.active_sessions[user_id] = {
            'user_id': user_id,
            'created_at': now,
            'last_activity': now,
            'session_token': session_token,
            'expires_at': now + self.session_timeout
        }
    
    def _remove_session(self, user_id: int) -> bool:
        """Удаление сессии"""
        if user_id in self.active_sessions:
            del self.active_sessions[user_id]
            return True
        return False
    
    def _is_session_expired(self, session: Dict) -> bool:
        """Проверка истечения сессии"""
        return time.time() > session['expires_at']
    
    def _generate_session_token(self, user_id: int, timestamp: float) -> str:
        """Генерация токена сессии"""
        data = f"{user_id}:{timestamp}:{self.manager_password}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def get_session_time_left(self, user_id: int) -> Optional[int]:
        """
        Получение оставшегося времени сессии в секундах
        
        Args:
            user_id: ID пользователя Telegram
            
        Returns:
            int или None: Оставшееся время в секундах
        """
        if user_id not in self.active_sessions:
            return None
        
        session = self.active_sessions[user_id]
        if self._is_session_expired(session):
            return 0
        
        return int(session['expires_at'] - time.time())
    
    def extend_session(self, user_id: int, additional_time: int = None) -> bool:
        """
        Продление сессии
        
        Args:
            user_id: ID пользователя Telegram
            additional_time: Дополнительное время в секундах (по умолчанию - стандартный timeout)
            
        Returns:
            bool: True если сессия была продлена
        """
        if user_id not in self.active_sessions:
            return False
        
        if additional_time is None:
            additional_time = self.session_timeout
        
        session = self.active_sessions[user_id]
        session['expires_at'] = time.time() + additional_time
        session['last_activity'] = time.time()
        
        return True


# Глобальный экземпляр менеджера авторизации
auth_manager = AuthManager()