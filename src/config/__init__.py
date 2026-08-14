"""
Configuration module

Provides centralized configuration management with validation and persistence.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from ..utils.exceptions import ConfigError
from ..utils.atomic_writes import atomic_write_json
from .defaults import *
from .validators import validate_config

logger = logging.getLogger(__name__)

# Global variables (module-level state)
# Model
MODEL_NAME = DEFAULT_MODEL_NAME
TEMPERATURE = DEFAULT_TEMPERATURE
TOP_K = DEFAULT_TOP_K
TOP_P = DEFAULT_TOP_P
MAX_NEW_TOKENS = DEFAULT_MAX_NEW_TOKENS

# UI + chat
USER_DISPLAY_NAME = DEFAULT_USER_DISPLAY_NAME
MODEL_DISPLAY_NAME = DEFAULT_MODEL_DISPLAY_NAME
PRIMARY_COLOR = DEFAULT_PRIMARY_COLOR
SECONDARY_COLOR = DEFAULT_SECONDARY_COLOR
AUTOSAVE_ENABLED = DEFAULT_AUTOSAVE_ENABLED

# RAG
RAG_ENABLED = DEFAULT_RAG_ENABLED
RAG_CONTEXT_PERCENTAGE = DEFAULT_RAG_CONTEXT_PERCENTAGE
RAG_TOP_K = DEFAULT_RAG_TOP_K
RAG_RELEVANCE_CUTOFF = DEFAULT_RAG_RELEVANCE_CUTOFF


def load_config(config_path: Optional[Path] = None) -> bool:
    """
    Load configuration from file
    
    Args:
        config_path: Optional path to config file. Uses CONFIG_FILE if None
        
    Returns:
        True if config loaded successfully, False if using defaults
        
    Raises:
        ConfigError: If config file exists but is corrupted beyond recovery
    """
    # Define globals to update
    global MODEL_NAME, TEMPERATURE, TOP_K, TOP_P, MAX_NEW_TOKENS
    global USER_DISPLAY_NAME, MODEL_DISPLAY_NAME
    global PRIMARY_COLOR, SECONDARY_COLOR, AUTOSAVE_ENABLED
    global RAG_ENABLED, RAG_CONTEXT_PERCENTAGE, RAG_TOP_K, RAG_RELEVANCE_CUTOFF

    path = Path(config_path) if config_path else Path(CONFIG_FILE)
    
    if not path.exists():
        logger.info(f"Config file not found at {path}, using defaults")
        reset_to_defaults()
        return False
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(
            f"Config file is not valid JSON: {e}",
            exc_info=True,
            extra={'config_path': str(path)}
        )
        raise ConfigError(
            f"Config file at {path} is corrupted. "
            f"Please fix or delete it. Error: {e}"
        ) from e
    except PermissionError as e:
        logger.error(f"Permission denied reading config: {path}")
        raise ConfigError(f"Cannot read config file: {e}") from e
    except OSError as e:
        logger.error(f"OS error reading config: {e}", exc_info=True)
        raise ConfigError(f"Failed to read config file: {e}") from e
    
    # Validate configuration
    errors = validate_config(config)
    if errors:
        error_msg = "; ".join(errors)
        logger.error(f"Invalid config values: {error_msg}")
        raise ConfigError(f"Config contains invalid values: {error_msg}")
    
    # Update state
    MODEL_NAME = config.get("model_name", DEFAULT_MODEL_NAME)
    TEMPERATURE = config.get("temperature", DEFAULT_TEMPERATURE)
    TOP_K = config.get("top_k", DEFAULT_TOP_K)
    TOP_P = config.get("top_p", DEFAULT_TOP_P)
    MAX_NEW_TOKENS = config.get("max_new_tokens", DEFAULT_MAX_NEW_TOKENS)
    
    USER_DISPLAY_NAME = config.get("user_display_name", DEFAULT_USER_DISPLAY_NAME)
    MODEL_DISPLAY_NAME = config.get("model_display_name", DEFAULT_MODEL_DISPLAY_NAME)
    PRIMARY_COLOR = config.get("primary_color", DEFAULT_PRIMARY_COLOR)
    SECONDARY_COLOR = config.get("secondary_color", DEFAULT_SECONDARY_COLOR)
    AUTOSAVE_ENABLED = config.get("autosave_enabled", DEFAULT_AUTOSAVE_ENABLED)
    
    RAG_ENABLED = config.get("rag_enabled", DEFAULT_RAG_ENABLED)
    RAG_CONTEXT_PERCENTAGE = config.get("rag_context_percentage", DEFAULT_RAG_CONTEXT_PERCENTAGE)
    RAG_TOP_K = config.get("rag_top_k", DEFAULT_RAG_TOP_K)
    RAG_RELEVANCE_CUTOFF = config.get(
        "rag_relevance_cutoff", DEFAULT_RAG_RELEVANCE_CUTOFF
    )
    
    logger.info(f"Config loaded successfully from {path}")
    return True


def save_config(config_path: Optional[Path] = None) -> None:
    """
    Save current configuration to file
    
    Args:
        config_path: Optional path to save config. Uses CONFIG_FILE if None
        
    Raises:
        ConfigError: If config cannot be saved
    """
    path = Path(config_path) if config_path else Path(CONFIG_FILE)
    
    # Get current state
    config = {
        "model_name": MODEL_NAME,
        "temperature": TEMPERATURE,
        "top_k": TOP_K,
        "top_p": TOP_P,
        "max_new_tokens": MAX_NEW_TOKENS,
        "user_display_name": USER_DISPLAY_NAME,
        "model_display_name": MODEL_DISPLAY_NAME,
        "primary_color": PRIMARY_COLOR,
        "secondary_color": SECONDARY_COLOR,
        "autosave_enabled": AUTOSAVE_ENABLED,
        "rag_enabled": RAG_ENABLED,
        "rag_context_percentage": RAG_CONTEXT_PERCENTAGE,
        "rag_top_k": RAG_TOP_K,
        "rag_relevance_cutoff": RAG_RELEVANCE_CUTOFF,
    }
    
    try:
        atomic_write_json(config, path)
        logger.info(f"Config saved to {path}")
    except PermissionError as e:
        logger.error(f"Permission denied writing config: {path}")
        raise ConfigError(f"Cannot write config file: {e}") from e
    except OSError as e:
        logger.error(f"OS error writing config: {e}", exc_info=True)
        raise ConfigError(f"Failed to save config: {e}") from e
    except Exception as e:
        logger.error(f"Unexpected error saving config: {e}", exc_info=True)
        raise ConfigError(f"Unexpected error saving config: {e}") from e


def reset_to_defaults() -> None:
    """Reset all configuration values to defaults"""
    global MODEL_NAME, TEMPERATURE, TOP_K, TOP_P, MAX_NEW_TOKENS
    global USER_DISPLAY_NAME, MODEL_DISPLAY_NAME
    global PRIMARY_COLOR, SECONDARY_COLOR, AUTOSAVE_ENABLED
    global RAG_ENABLED, RAG_CONTEXT_PERCENTAGE, RAG_TOP_K, RAG_RELEVANCE_CUTOFF
    
    MODEL_NAME = DEFAULT_MODEL_NAME
    TEMPERATURE = DEFAULT_TEMPERATURE
    TOP_K = DEFAULT_TOP_K
    TOP_P = DEFAULT_TOP_P
    MAX_NEW_TOKENS = DEFAULT_MAX_NEW_TOKENS
    USER_DISPLAY_NAME = DEFAULT_USER_DISPLAY_NAME
    MODEL_DISPLAY_NAME = DEFAULT_MODEL_DISPLAY_NAME
    PRIMARY_COLOR = DEFAULT_PRIMARY_COLOR
    SECONDARY_COLOR = DEFAULT_SECONDARY_COLOR
    AUTOSAVE_ENABLED = DEFAULT_AUTOSAVE_ENABLED
    RAG_ENABLED = DEFAULT_RAG_ENABLED
    RAG_CONTEXT_PERCENTAGE = DEFAULT_RAG_CONTEXT_PERCENTAGE
    RAG_TOP_K = DEFAULT_RAG_TOP_K
    RAG_RELEVANCE_CUTOFF = DEFAULT_RAG_RELEVANCE_CUTOFF
