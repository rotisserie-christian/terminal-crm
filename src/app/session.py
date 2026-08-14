import logging
from typing import Optional
from src.models import ModelHandler
from src.models import ContextManager
from src.rag import RAGManager
import src.config as config


logger = logging.getLogger(__name__)


class ChatSession:
    """
    Represents a single chat session with a loaded model and optional RAG
    
    Responsibilities:
    - Hold model, RAG, and context manager instances
    - Calculate token budgets
    - Retrieve RAG context
    """
    
    def __init__(
        self,
        model_handler: ModelHandler,
        rag_manager: Optional[RAGManager] = None
    ):
        """
        Initialize chat session
        
        Args:
            model_handler: Loaded model handler
            rag_manager: Optional RAG manager
        """

        self.model_handler = model_handler
        self.rag_manager = rag_manager
        self.context_manager = ContextManager()
        
        # Calculate token budgets
        self.available_context = model_handler.context_window - 512
        self.rag_token_budget = int(
            self.available_context * config.RAG_CONTEXT_PERCENTAGE
        )
        
        logger.info(
            f"Session initialized: {self.available_context} tokens available, "
            f"{self.rag_token_budget} for RAG"
        )
    
    def get_rag_context(self, query: str) -> str:
        """Returns: Retrieved context string (empty if unavailable)"""
        if not self.rag_manager or not self.rag_manager.is_loaded():
            return ""
        
        try:
            context, tokens = self.rag_manager.retrieve(
                query=query,
                tokenizer=self.model_handler.tokenizer,
                max_tokens=self.rag_token_budget,
                top_k=config.RAG_TOP_K,
                min_similarity=config.RAG_RELEVANCE_CUTOFF,
            )
            
            if tokens > 0:
                logger.debug(f"Retrieved {tokens} RAG tokens")
            
            return context
            
        except Exception as e:
            logger.warning(f"RAG retrieval failed: {e}")
            return ""
    
    def prepare_prompt(self, rag_context: str) -> str:
        """Returns: Formatted prompt string"""
        return self.context_manager.prepare_prompt(
            self.model_handler.tokenizer,
            self.available_context,
            rag_context=rag_context
        )
    
    def generate_response(self, prompt: str):
        """Yields: Text tokens (streaming)"""
        return self.model_handler.generate_stream(prompt)