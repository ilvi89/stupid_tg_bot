#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Пользовательские сценарии
"""

from .registration import create_user_registration_scenario
from .profile import create_profile_scenarios

__all__ = [
    'create_user_registration_scenario',
    'create_profile_scenarios'
]