"""
Configuration model for storing application settings in the database
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Enum
import enum
from . import Base
import datetime


class ConfigType(enum.Enum):
    """Enum for configuration value types"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    TEXT = "text"


class Configuration(Base):
    """Configuration model for storing application settings"""
    __tablename__ = 'configurations'
    
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=True)
    value_type = Column(Enum(ConfigType), default=ConfigType.STRING, nullable=False)
    description = Column(Text)
    category = Column(String(100), nullable=False, default="general")
    is_sensitive = Column(Boolean, default=False)  # For passwords/keys that should be masked
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    @property
    def typed_value(self):
        """Return the value converted to its proper type"""
        if self.value is None:
            return None
            
        try:
            if self.value_type == ConfigType.INTEGER:
                return int(self.value)
            elif self.value_type == ConfigType.FLOAT:
                return float(self.value)
            elif self.value_type == ConfigType.BOOLEAN:
                return str(self.value).lower() in ('true', '1', 't', 'yes')
            else:  # STRING or TEXT
                return self.value
        except (ValueError, TypeError):
            # If conversion fails, return the raw value
            return self.value
    
    def __repr__(self):
        if self.is_sensitive:
            return f"<Configuration {self.key}=****>"
        return f"<Configuration {self.key}={self.value}>"
