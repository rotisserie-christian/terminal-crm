import pytest
from unittest.mock import MagicMock, patch
from src.app.session import ChatSession
import src.config as config

@pytest.fixture
def mock_model_handler():
    handler = MagicMock()
    handler.context_window = 2048
    handler.tokenizer = MagicMock()
    return handler

@pytest.fixture
def mock_rag_manager():
    manager = MagicMock()
    manager.is_loaded.return_value = True
    return manager

@pytest.fixture
def chat_session(mock_model_handler, mock_rag_manager):
    with patch("src.app.session.ContextManager") as MockContextManager:
        # We also need to mock config values used in __init__
        with patch("src.config.RAG_CONTEXT_PERCENTAGE", 0.1):
             session = ChatSession(mock_model_handler, mock_rag_manager)
             return session

class TestChatSession:

    def test_init(self, mock_model_handler, mock_rag_manager):
        with patch("src.app.session.ContextManager") as MockContextManager:
             # Test token budget calculations
             # available_context = 2048 - 512 = 1536
             # rag_token_budget = 1536 * 0.1 = 153
            with patch("src.config.RAG_CONTEXT_PERCENTAGE", 0.1):
                session = ChatSession(mock_model_handler, mock_rag_manager)
                
                assert session.model_handler == mock_model_handler
                assert session.rag_manager == mock_rag_manager
                assert session.available_context == 1536
                assert session.rag_token_budget == 153
                MockContextManager.assert_called_once()

    def test_get_rag_context_success(self, chat_session, mock_rag_manager, mock_model_handler):
        mock_rag_manager.retrieve.return_value = ("Retrieved context", 50)
        
        context = chat_session.get_rag_context("query")
        
        assert context == "Retrieved context"
        mock_rag_manager.retrieve.assert_called_with(
            query="query",
            tokenizer=mock_model_handler.tokenizer,
            max_tokens=chat_session.rag_token_budget,
            top_k=config.RAG_TOP_K,
            min_similarity=config.RAG_RELEVANCE_CUTOFF,
        )

    def test_get_rag_context_not_loaded(self, chat_session, mock_rag_manager):
        mock_rag_manager.is_loaded.return_value = False
        context = chat_session.get_rag_context("query")
        assert context == ""
        mock_rag_manager.retrieve.assert_not_called()

    def test_get_rag_context_exception(self, chat_session, mock_rag_manager):
        mock_rag_manager.retrieve.side_effect = Exception("RAG error")
        context = chat_session.get_rag_context("query")
        assert context == ""

    def test_prepare_prompt(self, chat_session):
        chat_session.context_manager.prepare_prompt.return_value = "Formatted prompt"
        
        prompt = chat_session.prepare_prompt("RAG context")
        
        assert prompt == "Formatted prompt"
        chat_session.context_manager.prepare_prompt.assert_called_with(
            chat_session.model_handler.tokenizer,
            chat_session.available_context,
            rag_context="RAG context"
        )
        
    def test_generate_response(self, chat_session, mock_model_handler):
        mock_model_handler.generate_stream.return_value = iter(["token1", "token2"])
        
        generator = chat_session.generate_response("prompt")
        
        assert list(generator) == ["token1", "token2"]
        mock_model_handler.generate_stream.assert_called_with("prompt")
