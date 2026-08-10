class TerminalChatError(Exception):
    """Base exception for all Terminal Chat errors."""
    pass

class ConfigError(TerminalChatError):
    """Configuration-related errors."""
    pass

class ModelError(TerminalChatError):
    """Model loading/inference errors."""
    pass

class ModelLoadError(ModelError):
    """Failed to load model."""
    pass

class ModelInferenceError(ModelError):
    """Error during model generation."""
    pass

class StorageError(TerminalChatError):
    """File storage errors."""
    pass

class ChatLoadError(StorageError):
    """Failed to load chat history."""
    pass

class ChatSaveError(StorageError):
    """Failed to save chat history."""
    pass

class CrmDbError(StorageError):
    """CRM database errors."""
    pass

class LeadLoadError(StorageError):
    """Failed to load lead JSON files."""
    pass

class RAGError(TerminalChatError):
    """RAG system errors."""
    pass

class EmbeddingError(RAGError):
    """Failed to generate embeddings."""
    pass

class CacheError(RAGError):
    """Cache operation failed."""
    pass