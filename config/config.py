import os
import logging
import logging.config
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# OpenRouter configuration
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')
OPENROUTER_BASE_URL = os.getenv('OPENROUTER_BASE_URL', 'https://generativelanguage.googleapis.com/v1beta/openai/')
OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL', 'gemini-2.0-flash-lite')

# Azure OpenAI configuration (kept for backward compatibility)
AZURE_ENDPOINT = os.getenv('AZURE_ENDPOINT', 'https://models.inference.ai.azure.com')
AZURE_MODEL_NAME = os.getenv('AZURE_MODEL_NAME', 'Phi-3-small-8k-instruct')
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')

# Database configuration
DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///text2sql.db')

# Application settings
DEBUG = os.environ.get("DEBUG", "False").lower() == "true"
SECRET_KEY = os.environ.get("SECRET_KEY", "default-dev-key-change-in-production")

# Model configuration
MAX_TOKENS = int(os.getenv('MAX_TOKENS', '2000'))
TEMPERATURE = float(os.getenv('TEMPERATURE', '0.7'))

# Message format configuration
MESSAGE_FORMAT = os.getenv('MESSAGE_FORMAT', 'openai').lower()  # 'openai' or 'llama'
# Valid options: 'openai', 'llama'
SUPPORTED_MESSAGE_FORMATS = ['openai', 'llama']

# Validate message format
if MESSAGE_FORMAT not in SUPPORTED_MESSAGE_FORMATS:
    print(f"Warning: Invalid MESSAGE_FORMAT '{MESSAGE_FORMAT}'. Defaulting to 'openai'.")
    MESSAGE_FORMAT = 'openai'

# Knowledge base configuration
UPLOADS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
os.makedirs(UPLOADS_DIR, exist_ok=True)
CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', '1000'))
CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', '200'))

# Conversation history configuration
KNOWLEDGE_CONVERSATION_HISTORY_LIMIT = int(os.getenv('KNOWLEDGE_CONVERSATION_HISTORY_LIMIT', '10'))
METADATA_CONVERSATION_HISTORY_LIMIT = int(os.getenv('METADATA_CONVERSATION_HISTORY_LIMIT', '10'))

# ChromaDB Service configuration
CHROMADB_SERVICE_URL = os.getenv('CHROMADB_SERVICE_URL', 'http://localhost:8001')
CHROMADB_SERVICE_TIMEOUT = int(os.getenv('CHROMADB_SERVICE_TIMEOUT', '30'))

# Logging configuration
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
        'detailed': {
            'format': '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        },
        'query': {
            'format': '%(asctime)s - %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'detailed',
            'stream': 'ext://sys.stdout'
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'DEBUG',
            'formatter': 'detailed',
            'filename': os.path.join(LOG_DIR, 'text2sql.log'),
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5
        },
        'error_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'ERROR',
            'formatter': 'detailed',
            'filename': os.path.join(LOG_DIR, 'error.log'),
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5
        },
        'query_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'INFO',
            'formatter': 'query',
            'filename': os.path.join(LOG_DIR, 'queries.log'),
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5
        }
    },
    'loggers': {
        'text2sql': {
            'level': 'DEBUG',
            'handlers': ['console', 'file', 'error_file'],
            'propagate': False
        },
        'text2sql.agents': {
            'level': 'DEBUG',
            'handlers': ['console', 'file', 'error_file'],
            'propagate': False
        },
        'text2sql.queries': {
            'level': 'INFO',
            'handlers': ['query_file'],
            'propagate': False
        },
        'text2sql.schema_manager': {
            'level': 'DEBUG',
            'handlers': ['console', 'file', 'error_file'],
            'propagate': False
        },
        'text2sql.sql_generator': {
            'level': 'DEBUG',
            'handlers': ['console', 'file', 'error_file'],
            'propagate': False
        }
    },
    'root': {
        'level': 'WARNING',
        'handlers': ['console', 'file']
    }
}

# Initialize logging configuration only if no handlers exist
logger = logging.getLogger('text2sql')
if not logger.hasHandlers():
    logging.config.dictConfig(LOGGING_CONFIG)

# Example: /path/to/your/mcp/server/script.py
# Ensure this path is correct for your environment
MCP_SERVER_SCRIPT_PATH = os.getenv('MCP_SERVER_SCRIPT_PATH', './src/utils/dataengineer.py')