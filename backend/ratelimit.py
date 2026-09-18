"""
MedPak AI — Shared rate limiter (slowapi)
Instance is created once here and used across the app.

Limits (per client IP):
  - Global:        100/minute   (applied in main.py middleware)
  - Chat message:  10/minute    (LLM cost control)
  - Login/Register: 5/minute    (brute-force protection)
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
