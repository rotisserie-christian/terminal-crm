from typing import Dict, List, Optional


def validate_config(config: Dict) -> List[str]:
    """
    Validate configuration values
    
    Args:
        config: Configuration dictionary to validate
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    # Validate boolean fields
    if "autosave_enabled" in config:
        if not isinstance(config["autosave_enabled"], bool):
            errors.append(
                f"autosave_enabled must be boolean, got {type(config['autosave_enabled'])}"
            )
    
    if "rag_enabled" in config:
        if not isinstance(config["rag_enabled"], bool):
            errors.append(
                f"rag_enabled must be boolean, got {type(config['rag_enabled'])}"
            )
    
    # Validate RAG percentage
    if "rag_context_percentage" in config:
        error = validate_rag_percentage(config["rag_context_percentage"])
        if error:
            errors.append(error)
    
    # Validate RAG top_k
    if "rag_top_k" in config:
        error = validate_rag_top_k(config["rag_top_k"])
        if error:
            errors.append(error)

    if "rag_relevance_cutoff" in config:
        error = validate_rag_relevance_cutoff(config["rag_relevance_cutoff"])
        if error:
            errors.append(error)
    
    return errors


def validate_rag_percentage(value: float) -> Optional[str]:
    if not isinstance(value, (int, float)):
        return f"rag_context_percentage must be a number, got {type(value)}"
    
    if not (0.0 <= value <= 1.0):
        return f"rag_context_percentage must be between 0.0 and 1.0, got {value}"
    
    return None


def validate_rag_top_k(value: int) -> Optional[str]:
    if not isinstance(value, int):
        return f"rag_top_k must be an integer, got {type(value)}"
    
    if not (1 <= value <= 100):
        return f"rag_top_k must be between 1 and 100, got {value}"
    
    return None


def validate_rag_relevance_cutoff(value: float) -> Optional[str]:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return f"rag_relevance_cutoff must be a number, got {type(value)}"

    if not (0.0 <= value <= 1.0):
        return f"rag_relevance_cutoff must be between 0.0 and 1.0, got {value}"

    return None
