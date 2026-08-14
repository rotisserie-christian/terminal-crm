"""
Configuration defaults

All default values for the application configuration.
These are pure constants with no logic or side effects.
"""

# Config file path
CONFIG_FILE = "config.json"

# Default values (model)
DEFAULT_MODEL_NAME = "Qwen/Qwen3-0.6B"
DEFAULT_TEMPERATURE = 0.9
DEFAULT_TOP_K = 50
DEFAULT_TOP_P = 0.95
DEFAULT_MAX_NEW_TOKENS = 128

# Default values (UI + chat)
DEFAULT_USER_DISPLAY_NAME = "Me" 
DEFAULT_MODEL_DISPLAY_NAME = "Model"
DEFAULT_PRIMARY_COLOR = "green"
DEFAULT_SECONDARY_COLOR = "blue"
DEFAULT_AUTOSAVE_ENABLED = False

# Default values (RAG)
DEFAULT_RAG_ENABLED = False
DEFAULT_RAG_CONTEXT_PERCENTAGE = 0.25
DEFAULT_RAG_TOP_K = 10
DEFAULT_RAG_RELEVANCE_CUTOFF = 0.4
