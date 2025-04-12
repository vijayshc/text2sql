"""
Models package for the Text2SQL application.
This package contains the database models used throughout the application.
"""

from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

from .user import User, Role, Permission, AuditLog
from .configuration import Configuration, ConfigType