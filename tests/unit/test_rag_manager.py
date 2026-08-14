import pytest
import os
import numpy as np
from src.rag.manager import RAGManager
from unittest.mock import MagicMock, patch, mock_open

class TestRAGManager:
    @patch('src.rag.manager.EmbeddingModel')
    def test_init(self, MockModel):
        manager = RAGManager(memory_dir="test_mem", embedding_model="test-model")
        assert manager.memory_dir == "test_mem"
        assert manager.chunks == []
        assert manager._loaded is False

    @patch('src.rag.manager.EmbeddingModel')
    @patch('src.rag.manager.EmbeddingsCache')
    @patch('os.path.exists')
    @patch('os.path.isfile')
    @patch('os.makedirs')
    @patch('os.listdir')
    def test_load_fresh(self, mock_listdir, mock_makedirs, mock_isfile, mock_exists, MockCache, MockModel):
        mock_exists.return_value = True
        mock_isfile.return_value = True
        mock_listdir.return_value = ["file1.md"]
        
        mock_model = MockModel.return_value
        mock_model.load.return_value = True
        mock_model.encode.return_value = np.array([[0.1, 0.2]], dtype=np.float32)
        
        mock_cache = MockCache.return_value
        mock_cache.get.return_value = None
        
        # Mock file reading
        with patch('builtins.open', mock_open(read_data="some text")):
            with patch('src.rag.manager.chunk_text', return_value=["chunk1"]):
                manager = RAGManager()
                assert manager.load() is True
                assert manager._loaded is True
                assert len(manager.chunks) == 1
                assert manager.embeddings.shape == (1, 2)

    @patch('src.rag.manager.EmbeddingModel')
    @patch('src.rag.manager.EmbeddingsCache')
    @patch('os.path.exists')
    @patch('os.path.isfile')
    @patch('os.listdir')
    def test_load_cached(self, mock_listdir, mock_isfile, mock_exists, MockCache, MockModel):
        mock_exists.return_value = True
        mock_isfile.return_value = True
        mock_listdir.return_value = ["file1.md"]
        
        mock_model = MockModel.return_value
        mock_model.load.return_value = True
        
        mock_cache = MockCache.return_value
        # Ensure it returns a tuple of (list, numpy array)
        mock_cache.get.return_value = (["chunk1"], np.array([[0.1, 0.2]], dtype=np.float32))
        
        manager = RAGManager()
        assert manager.load() is True
        assert manager._loaded is True
        assert len(manager.chunks) == 1
        assert manager.embeddings.shape == (1, 2)

    @patch('src.rag.manager.EmbeddingModel')
    @patch('src.rag.manager.EmbeddingsCache')
    def test_retrieve(self, MockCache, MockModel):
        manager = RAGManager()
        manager._loaded = True
        manager.chunks = ["chunk1", "chunk2"]
        manager.embeddings = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
        manager.chunk_metadata = [{"filename": "f1"}, {"filename": "f2"}]
        
        mock_model = MockModel.return_value
        mock_model.encode_single.return_value = np.array([1.0, 0.0], dtype=np.float32)
        
        mock_tokenizer = MagicMock()
        mock_tokenizer.encode.side_effect = lambda x: [1] * len(x) # Simplified tokenization
        
        # Should retrieve both because we have enough max_tokens
        context, tokens = manager.retrieve(
            "query",
            mock_tokenizer,
            max_tokens=100,
            min_similarity=0.0,
            relative_margin=1.0,
        )
        assert "chunk1" in context
        assert "chunk2" in context
        assert tokens == len("chunk1") + len("chunk2")

    @patch('src.rag.manager.EmbeddingModel')
    @patch('src.rag.manager.EmbeddingsCache')
    def test_retrieve_skips_when_below_cutoff(self, MockCache, MockModel):
        manager = RAGManager()
        manager._loaded = True
        manager.chunks = ["unrelated"]
        manager.embeddings = np.array([[0.0, 1.0]], dtype=np.float32)
        manager.chunk_metadata = [{"filename": "f1"}]

        MockModel.return_value.encode_single.return_value = np.array(
            [1.0, 0.0], dtype=np.float32
        )
        mock_tokenizer = MagicMock()
        mock_tokenizer.encode.side_effect = lambda x: [1] * len(x)

        context, tokens = manager.retrieve(
            "query", mock_tokenizer, max_tokens=100, min_similarity=0.4
        )
        assert context == ""
        assert tokens == 0

    @patch('src.rag.manager.EmbeddingModel')
    @patch('src.rag.manager.EmbeddingsCache')
    def test_retrieve_drops_weaker_than_relative_margin(self, MockCache, MockModel):
        manager = RAGManager()
        manager._loaded = True
        manager.chunks = ["best", "close", "far"]
        manager.embeddings = np.array(
            [
                [1.0, 0.0],
                [0.95, 0.3122499],
                [0.5, 0.8660254],
            ],
            dtype=np.float32,
        )
        manager.chunk_metadata = [
            {"filename": "f1"},
            {"filename": "f2"},
            {"filename": "f3"},
        ]

        MockModel.return_value.encode_single.return_value = np.array(
            [1.0, 0.0], dtype=np.float32
        )
        mock_tokenizer = MagicMock()
        mock_tokenizer.encode.side_effect = lambda x: [1] * len(x)

        context, tokens = manager.retrieve(
            "query",
            mock_tokenizer,
            max_tokens=100,
            min_similarity=0.4,
            relative_margin=0.1,
        )
        assert "best" in context
        assert "close" in context
        assert "far" not in context
        assert tokens == len("best") + len("close")

    def test_get_stats(self):
        manager = RAGManager()
        assert manager.get_stats()['loaded'] is False
        
        manager._loaded = True
        manager.chunks = ["c1"]
        manager.chunk_metadata = [{"filename": "f1"}]
        stats = manager.get_stats()
        assert stats['loaded'] is True
        assert stats['num_chunks'] == 1
        assert stats['num_files'] == 1
