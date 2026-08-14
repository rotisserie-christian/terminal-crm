import os
import logging
from typing import List, Dict, Tuple, Optional
import numpy as np
from .embeddings import chunk_text, cosine_similarity, EmbeddingModel
from .embeddings_cache import EmbeddingsCache


logger = logging.getLogger(__name__)


MEMORY_DIR = "memory"
SUPPORTED_EXTENSIONS = {'.md', '.txt'}
EXCLUDED_FILES = {'README.md', 'readme.md', 'README.txt', 'readme.txt'}
RELATIVE_SIMILARITY_MARGIN = 0.1


class RAGManager:
    """Manages RAG pipeline"""
    
    def __init__(self, memory_dir: str = MEMORY_DIR, embedding_model: str = "all-MiniLM-L6-v2"):
        self.memory_dir = memory_dir
        self.embedding_model = EmbeddingModel(embedding_model)
        self.cache = EmbeddingsCache()
        
        self.chunks: List[str] = []
        self.embeddings: Optional[np.ndarray] = None
        self.chunk_metadata: List[Dict] = []
        self._loaded = False
    
    def load(self, show_progress: bool = True) -> bool:
        """Load and process all files from memory directory"""
        logger.info(f"Loading RAG context from {self.memory_dir}")
        
        if not self.embedding_model.load():
            logger.error("Failed to load embedding model")
            return False
        
        if not os.path.exists(self.memory_dir):
            logger.warning(f"Memory directory {self.memory_dir} does not exist. Creating it.")
            os.makedirs(self.memory_dir)
            return True
        
        self.cache.load(self.memory_dir)
        
        all_chunks = []
        all_embeddings_list = []
        all_metadata = []
        files_to_embed = []
        chunks_to_embed = []
        existing_files = []
        
        for filename in os.listdir(self.memory_dir):
            filepath = os.path.join(self.memory_dir, filename)
            
            if not os.path.isfile(filepath):
                continue
            
            if filename in EXCLUDED_FILES:
                logger.debug(f"Skipping excluded file: {filename}")
                continue
            
            ext = os.path.splitext(filename)[1].lower()
            if ext not in SUPPORTED_EXTENSIONS:
                logger.debug(f"Skipping unsupported file: {filename}")
                continue
            
            existing_files.append(filename)
            
            cached_result = self.cache.get(filename, filepath)
            
            if cached_result is not None:
                file_chunks, file_embeddings = cached_result
                all_chunks.extend(file_chunks)
                all_embeddings_list.append(file_embeddings)
                
                for chunk in file_chunks:
                    all_metadata.append({'filename': filename, 'filepath': filepath})
                
                logger.info(f"Loaded {len(file_chunks)} chunks from {filename} (cached)")
            else:
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        text = f.read()
                    
                    file_chunks = chunk_text(text)
                    
                    if not file_chunks:
                        logger.warning(f"No chunks generated from {filename}")
                        continue
                    
                    start_idx = len(all_chunks)
                    all_chunks.extend(file_chunks)
                    chunks_to_embed.extend(file_chunks)
                    files_to_embed.append((filename, filepath, start_idx, len(file_chunks)))
                    
                    for chunk in file_chunks:
                        all_metadata.append({'filename': filename, 'filepath': filepath})
                    
                    logger.info(f"Processing {len(file_chunks)} chunks from {filename}")
                except Exception as e:
                    logger.error(f"Error loading file {filename}: {e}")
                    continue
        
        if not all_chunks and not chunks_to_embed:
            logger.warning(f"No content found in {self.memory_dir}")
            self.cache.clean(existing_files)
            self.cache.save(self.memory_dir)
            return True
        
        if chunks_to_embed:
            try:
                logger.info(f"Generating embeddings for {len(chunks_to_embed)} new/changed chunks...")
                new_embeddings = self.embedding_model.encode(
                    chunks_to_embed,
                    batch_size=32,
                    show_progress=show_progress
                )
                
                embed_offset = 0
                for filename, filepath, start_idx, num_chunks in files_to_embed:
                    file_embeddings = new_embeddings[embed_offset:embed_offset + num_chunks]
                    file_chunks = all_chunks[start_idx:start_idx + num_chunks]
                    
                    self.cache.set(filename, filepath, file_chunks, file_embeddings)
                    all_embeddings_list.append(file_embeddings)
                    
                    embed_offset += num_chunks
            except Exception as e:
                logger.error(f"Error generating embeddings: {e}")
                return False
        
        if all_embeddings_list:
            self.embeddings = np.vstack(all_embeddings_list)
            self.chunks = all_chunks
            self.chunk_metadata = all_metadata
            self._loaded = True
            
            logger.info(f"RAG context loaded: {len(self.chunks)} chunks from {len(set(m['filename'] for m in all_metadata))} files")
        else:
            logger.warning("No embeddings generated")
            return True
        
        self.cache.clean(existing_files)
        self.cache.save(self.memory_dir)
        
        return True
    
    def retrieve(
        self,
        query: str,
        tokenizer,
        max_tokens: int,
        top_k: int = 10,
        min_similarity: float = 0.4,
        relative_margin: float = RELATIVE_SIMILARITY_MARGIN,
    ) -> Tuple[str, int]:
        """Retrieve relevant chunks for a query.

        Drops chunks below min_similarity. If the best match is below
        that cutoff, returns empty so no RAG budget is spent. Also keeps
        only chunks within relative_margin of the best score.
        """
        if not self._loaded or not self.chunks:
            logger.debug("No RAG context loaded, returning empty")
            return "", 0
        
        try:
            query_embedding = self.embedding_model.encode_single(query)
            similarities = cosine_similarity(query_embedding, self.embeddings)
            top_indices = np.argsort(similarities)[-top_k:][::-1]
            best_similarity = float(similarities[top_indices[0]])

            if best_similarity < min_similarity:
                logger.info(
                    f"Skipping RAG: best similarity {best_similarity:.3f} "
                    f"below cutoff {min_similarity:.3f}"
                )
                return "", 0

            floor = max(min_similarity, best_similarity - relative_margin)
            
            selected_chunks = []
            total_tokens = 0
            
            for idx in top_indices:
                similarity = float(similarities[idx])
                if similarity < floor:
                    break

                chunk = self.chunks[idx]
                chunk_tokens = len(tokenizer.encode(chunk))
                
                if total_tokens + chunk_tokens > max_tokens:
                    if total_tokens < max_tokens * 0.8:
                        continue
                    break
                
                selected_chunks.append(chunk)
                total_tokens += chunk_tokens
                
                logger.debug(f"Retrieved chunk from {self.chunk_metadata[idx]['filename']} "
                           f"(similarity: {similarity:.3f}, tokens: {chunk_tokens})")
            
            context = "\n\n".join(selected_chunks)
            logger.info(f"Retrieved {len(selected_chunks)} chunks ({total_tokens} tokens) for query")
            return context, total_tokens
        except Exception as e:
            logger.error(f"Error during retrieval: {e}")
            return "", 0
    
    def is_loaded(self) -> bool:
        """Check if RAG context has been loaded"""
        return self._loaded
    
    def get_stats(self) -> Dict:
        """Get statistics about loaded RAG context"""
        if not self._loaded:
            return {'loaded': False, 'num_chunks': 0, 'num_files': 0}
        
        unique_files = set(m['filename'] for m in self.chunk_metadata)
        
        return {
            'loaded': True,
            'num_chunks': len(self.chunks),
            'num_files': len(unique_files),
            'files': sorted(unique_files)
        }