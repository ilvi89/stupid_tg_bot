#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Простой скрипт быстрого запуска DSL бота
Для случаев, когда нужен минимальный запуск без проверок
"""

import asyncio
import os
from dotenv import load_dotenv


def quick_start():
    """Быстрый запуск без проверок"""
    # Загружаем конфиги окружения
    if os.path.exists('.env'):
        load_dotenv('.env')
    # Поддержка альтернативного имени файла
    if os.path.exists('config.env'):
        load_dotenv('config.env')
    
    # Проверяем токен
    token = os.getenv('BOT_TOKEN')
    if not token or token == 'your_bot_token_here':
        print("❌ Установите BOT_TOKEN в .env файле")
        return
    
    print("🚀 Быстрый запуск DSL бота...")
    
    try:
        from bot import DSLTelegramBot
        bot = DSLTelegramBot()
        # run() синхронный и сам запускает polling
        bot.run()
    except Exception as e:
        print(f"❌ Ошибка: {e}")


if __name__ == '__main__':
    quick_start()