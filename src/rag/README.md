### /src/rag
- `manager.py` - Main RAG orchestrator: loads files from `/memory`, chunks text, generates embeddings, retrieves relevant chunks
- `embeddings.py` - Chunking logic, embedding model management, and cosine similarity calculations
- `embeddings_cache.py` - Cache embeddings to avoid regenerating for unchanged files

## RAG Process

1. **Initialization** (on chat start):
   - Scan `/memory` directory for `.md` and `.txt` files
   - Load embedding cache from disk (`.embeddings_cache.pkl`)
   - For each file:
     - Check if file is cached and unchanged
     - If cached: load chunks and embeddings (f a s t)
     - If new/changed: chunk text and queue for embedding
   - If new/changed: generate embeddings, update cache with new embeddings, save cache to disk

2. **Query-Time Retrieval** (each user message):
   - Generate embedding for user's query
   - Calculate cosine similarity between query and all chunk embeddings (bruteforce, but good enough for up to ~1m tokens)
   - Select top-k most similar chunks
   - Skip RAG entirely if the best cosine score is below `rag_relevance_cutoff`
   - Keep only chunks within 0.1 of the best score (and still above the cutoff)
   - Use tokenizer for precise token counting
   - Fit remaining chunks within RAG token budget (25% of context window)

3. **Prompt Construction** (in `context_manager.py`):
   - System prompt (always included, ~100-500 tokens)
   - RAG context (retrieved chunks, up to 25% of context window)
   - Chat history (fills remaining ~70%, pruned as needed)
