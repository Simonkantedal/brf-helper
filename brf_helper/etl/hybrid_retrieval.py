import pickle
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from rank_bm25 import BM25Okapi
import logging

logger = logging.getLogger(__name__)


class HybridRetriever:
    """Hybrid retrieval combining BM25 (sparse) and vector search (dense)"""
    
    def __init__(
        self,
        vector_store,
        bm25_cache_path: str = "./chroma_db/bm25_index.pkl",
        alpha: float = 0.7  # Weight for vector search (1-alpha for BM25)
    ):
        self.vector_store = vector_store
        self.bm25_cache_path = Path(bm25_cache_path)
        self.bm25_cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.alpha = alpha
        
        # BM25 components
        self.bm25_index = None
        self.document_texts = []
        self.document_ids = []
        self.document_metadatas = []
        
        # Load existing BM25 index if available
        self._load_bm25_index()
    
    def build_bm25_index(self, force_rebuild: bool = False) -> None:
        """Build or rebuild the BM25 index from vector store documents"""
        if self.bm25_index is not None and not force_rebuild:
            logger.info("BM25 index already exists. Use force_rebuild=True to rebuild.")
            return
        
        if not self.vector_store.collection:
            raise ValueError("Vector store collection not available")
        
        logger.info("Building BM25 index...")
        
        # Get all documents from vector store
        all_docs = self.vector_store.collection.get()
        
        self.document_texts = all_docs["documents"]
        self.document_ids = all_docs["ids"]
        self.document_metadatas = all_docs["metadatas"] or [{}] * len(self.document_texts)
        
        # Tokenize documents for BM25
        tokenized_docs = [doc.lower().split() for doc in self.document_texts]
        
        # Create BM25 index
        self.bm25_index = BM25Okapi(tokenized_docs)
        
        # Save to cache
        self._save_bm25_index()
        
        logger.info(f"BM25 index built with {len(self.document_texts)} documents")
    
    def search(
        self,
        query: str,
        query_embedding: List[float],
        n_results: int = 5,
        where: Optional[Dict] = None,
        alpha: Optional[float] = None
    ) -> Dict:
        """
        Hybrid search combining BM25 and vector similarity
        
        Args:
            query: Text query for BM25 search
            query_embedding: Vector embedding for semantic search
            n_results: Number of results to return
            where: Metadata filter (applied to vector search)
            alpha: Weight for vector search (overrides instance alpha)
        
        Returns:
            Dict with combined results
        """
        if alpha is None:
            alpha = self.alpha
        
        # Ensure BM25 index is available
        if self.bm25_index is None:
            logger.warning("BM25 index not found, building now...")
            self.build_bm25_index()
        
        # Get more results from each method to allow for better fusion
        search_k = min(n_results * 3, len(self.document_texts))
        
        # BM25 search
        bm25_scores = self._bm25_search(query, search_k)
        
        # Vector search
        vector_results = self.vector_store.search(
            query_embedding=query_embedding,
            n_results=search_k,
            where=where
        )
        
        # Combine and rank results
        combined_results = self._fuse_results(
            bm25_scores, vector_results, alpha, n_results
        )
        
        return combined_results
    
    def _bm25_search(self, query: str, k: int) -> List[Tuple[str, float]]:
        """Perform BM25 search and return (doc_id, score) tuples"""
        query_tokens = query.lower().split()
        doc_scores = self.bm25_index.get_scores(query_tokens)
        
        # Get top k documents with their scores
        scored_docs = list(zip(self.document_ids, doc_scores))
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        return scored_docs[:k]
    
    def _fuse_results(
        self,
        bm25_scores: List[Tuple[str, float]],
        vector_results: Dict,
        alpha: float,
        n_results: int
    ) -> Dict:
        """Fuse BM25 and vector search results using weighted scoring"""
        
        # Normalize BM25 scores
        bm25_dict = {}
        if bm25_scores:
            max_bm25 = max(score for _, score in bm25_scores)
            min_bm25 = min(score for _, score in bm25_scores)
            
            # Avoid division by zero
            bm25_range = max_bm25 - min_bm25 if max_bm25 > min_bm25 else 1.0
            
            for doc_id, score in bm25_scores:
                normalized_score = (score - min_bm25) / bm25_range
                bm25_dict[doc_id] = normalized_score
        
        # Normalize vector distances (convert to similarity scores)
        vector_dict = {}
        vector_ids = vector_results["ids"]
        vector_distances = vector_results["distances"]
        
        if vector_distances:
            max_dist = max(vector_distances)
            min_dist = min(vector_distances)
            
            # Convert distances to similarities (1 - normalized_distance)
            dist_range = max_dist - min_dist if max_dist > min_dist else 1.0
            
            for doc_id, distance in zip(vector_ids, vector_distances):
                # Convert distance to similarity score
                normalized_similarity = 1.0 - ((distance - min_dist) / dist_range)
                vector_dict[doc_id] = normalized_similarity
        
        # Combine scores
        all_doc_ids = set(bm25_dict.keys()) | set(vector_dict.keys())
        combined_scores = {}
        
        for doc_id in all_doc_ids:
            bm25_score = bm25_dict.get(doc_id, 0.0)
            vector_score = vector_dict.get(doc_id, 0.0)
            
            # Weighted combination
            combined_score = alpha * vector_score + (1 - alpha) * bm25_score
            combined_scores[doc_id] = combined_score
        
        # Sort by combined score and take top n_results
        sorted_results = sorted(
            combined_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:n_results]
        
        # Build result dictionary in same format as vector_store.search
        result_ids = [doc_id for doc_id, _ in sorted_results]
        result_scores = [score for _, score in sorted_results]
        
        # Get document texts and metadatas for the results
        result_documents = []
        result_metadatas = []
        
        # Create lookup dictionaries for efficient access
        id_to_text = dict(zip(self.document_ids, self.document_texts))
        id_to_metadata = dict(zip(self.document_ids, self.document_metadatas))
        
        for doc_id in result_ids:
            result_documents.append(id_to_text.get(doc_id, ""))
            result_metadatas.append(id_to_metadata.get(doc_id, {}))
        
        # Convert scores back to distances for compatibility
        result_distances = [1.0 - score for score in result_scores]
        
        return {
            "documents": result_documents,
            "metadatas": result_metadatas,
            "distances": result_distances,
            "ids": result_ids
        }
    
    def _save_bm25_index(self):
        """Save BM25 index and document data to cache file"""
        try:
            cache_data = {
                "bm25_index": self.bm25_index,
                "document_texts": self.document_texts,
                "document_ids": self.document_ids,
                "document_metadatas": self.document_metadatas
            }
            
            with open(self.bm25_cache_path, 'wb') as f:
                pickle.dump(cache_data, f)
            
            logger.info(f"BM25 index saved to {self.bm25_cache_path}")
        except Exception as e:
            logger.warning(f"Failed to save BM25 index: {e}")
    
    def _load_bm25_index(self):
        """Load BM25 index and document data from cache file"""
        if not self.bm25_cache_path.exists():
            logger.info("No BM25 cache found")
            return
        
        try:
            with open(self.bm25_cache_path, 'rb') as f:
                cache_data = pickle.load(f)
            
            self.bm25_index = cache_data["bm25_index"]
            self.document_texts = cache_data["document_texts"]
            self.document_ids = cache_data["document_ids"]
            self.document_metadatas = cache_data["document_metadatas"]
            
            logger.info(f"BM25 index loaded from cache with {len(self.document_texts)} documents")
        except Exception as e:
            logger.warning(f"Failed to load BM25 index cache: {e}")
            self.bm25_index = None
    
    def clear_cache(self):
        """Clear BM25 cache file and in-memory index"""
        if self.bm25_cache_path.exists():
            self.bm25_cache_path.unlink()
        
        self.bm25_index = None
        self.document_texts = []
        self.document_ids = []
        self.document_metadatas = []
        
        logger.info("BM25 cache cleared")