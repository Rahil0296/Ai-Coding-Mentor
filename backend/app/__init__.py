# backend/app/__init__.py
"""
Package marker for the 'app' package.
Allows imports like `from app.database import ...` to resolve for Python and Pylance.
"""

__all__ = ["database", "models", "main"]
