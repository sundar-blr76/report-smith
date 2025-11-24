"""Onboarding module for database schema inference and application setup."""

from .schema_introspector import SchemaIntrospector
from .template_generator import TemplateGenerator
from .onboarding_manager import OnboardingManager

__all__ = [
    "SchemaIntrospector",
    "TemplateGenerator",
    "OnboardingManager",
]
