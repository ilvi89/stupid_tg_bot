#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Менеджерские сценарии
"""

from .auth import create_manager_auth_scenario
from .broadcast import create_broadcast_scenarios
from .administration import create_admin_scenarios

__all__ = [
    'create_manager_auth_scenario',
    'create_broadcast_scenarios',
    'create_admin_scenarios'
]