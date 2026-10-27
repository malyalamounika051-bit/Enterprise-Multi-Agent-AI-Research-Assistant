import os
import json
import math
import re
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np
from pydantic import BaseModel
import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings
from ..config import settings

class LocalDenseEmbeddingFunction(EmbeddingFunction):
    """
    100% offline, deterministic, zero-download embedding function.
    Computes a 384-dimensional dense semantic projection using token hashing,
    subword n-grams, and L2 normalization. Perfectly calibrated for ChromaDB cosine similarity.
    """
    def __init__(self, dim: int = 384):
        self.dim = dim

    def _embed_text(self, text: str) -> List[float]:
        vec = np.zeros(self.dim, dtype=np.float32)
        words = re.findall(r"\w+|[\$0-9\-\.\_]+", text.lower())
        for w in words:
            # Word token projection
            h = int(hashlib.md5(w.encode("utf-8")).hexdigest()[:8], 16)
            idx = h % self.dim
            sign = 1.0 if (h // self.dim) % 2 == 0 else -1.0
            vec[idx] += sign * 2.0

            # 3-gram subword features for typo and stem tolerance
            if len(w) >= 3:
                for i in range(len(w) - 2):
                    sub = w[i:i+3]
                    sub_h = int(hashlib.sha256(sub.encode("utf-8")).hexdigest()[:8], 16)
                    sub_idx = sub_h % self.dim
                    sub_sign = 1.0 if (sub_h // self.dim) % 2 == 0 else -1.0
                    vec[sub_idx] += sub_sign * 0.5

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def __call__(self, input: Documents) -> Embeddings:
        return [self._embed_text(doc) for doc in input]

class ChunkDocument(BaseModel):
    chunk_id: str
    doc_id: str
    title: str
    category: str
    owner: str
    source_url: str
    published: str
    version: str
    text: str
    score: Optional[float] = 0.0
    match_type: Optional[str] = "hybrid"

class VectorStoreManager:
    def __init__(self, persist_directory: Optional[Path] = None):
        self.persist_dir = str(persist_directory or settings.CHROMA_PERSIST_DIR)
        os.makedirs(self.persist_dir, exist_ok=True)
        
        # Persistent Chroma client
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        self.embedding_fn = LocalDenseEmbeddingFunction()
        
        # Get or create collection with versioned name to prevent function conflict
        coll_name = "asterline_corpus_v1"
        try:
            self.collection = self.client.get_or_create_collection(
                name=coll_name,
                embedding_function=self.embedding_fn,
                metadata={"hnsw:space": "cosine", "description": "Asterline Labs Knowledge Base 75 chunks"}
            )
        except Exception:
            try:
                self.client.delete_collection(coll_name)
            except Exception:
                pass
            self.collection = self.client.create_collection(
                name=coll_name,
                embedding_function=self.embedding_fn,
                metadata={"hnsw:space": "cosine", "description": "Asterline Labs Knowledge Base 75 chunks"}
            )
        
        self.raw_chunks: List[Dict[str, Any]] = []
        self._load_and_index_corpus()

    def _load_and_index_corpus(self):
        corpus_path = settings.CORPUS_PATH
        if not corpus_path.exists():
            fallback = settings.BASE_DIR.parent / "corpus.jsonl"
            if fallback.exists():
                corpus_path = fallback

        if not corpus_path.exists():
            print(f"[VectorStore] Warning: Corpus file not found at {corpus_path}")
            return

        with open(corpus_path, "r", encoding="utf-8") as f:
            self.raw_chunks = [json.loads(line) for line in f if line.strip()]

        current_count = self.collection.count()
        if current_count < len(self.raw_chunks):
            print(f"[VectorStore] Indexing {len(self.raw_chunks)} chunks into ChromaDB...")
            ids = []
            documents = []
            metadatas = []
            
            for chunk in self.raw_chunks:
                ids.append(chunk["chunk_id"])
                embed_text = f"Title: {chunk['title']}\nCategory: {chunk['category']}\nDoc: {chunk['doc_id']}\nContent: {chunk['text']}"
                documents.append(embed_text)
                metadatas.append({
                    "chunk_id": chunk["chunk_id"],
                    "doc_id": chunk["doc_id"],
                    "title": chunk["title"],
                    "category": chunk["category"],
                    "owner": chunk["owner"],
                    "source_url": chunk["source_url"],
                    "published": str(chunk["published"]),
                    "version": str(chunk["version"]),
                    "raw_text": chunk["text"]
                })
            
            # Upsert into Chroma in batches
            batch_size = 50
            for i in range(0, len(ids), batch_size):
                end = min(i + batch_size, len(ids))
                self.collection.upsert(
                    ids=ids[i:end],
                    documents=documents[i:end],
                    metadatas=metadatas[i:end]
                )
            print(f"[VectorStore] Successfully indexed {self.collection.count()} chunks.")
        else:
            print(f"[VectorStore] Collection already verified ({current_count} chunks).")

    def _keyword_search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        tokens = [t.lower() for t in re.findall(r"\w+|[\$0-9\-\.\_]+", query) if len(t) > 1]
        if not tokens:
            return []

        results = []
        for chunk in self.raw_chunks:
            searchable = (
                chunk["chunk_id"].lower() + " " +
                chunk["doc_id"].lower() + " " +
                chunk["title"].lower() + " " +
                chunk["category"].lower() + " " +
                chunk["text"].lower()
            )
            score = 0.0
            
            # Exact phrase bonus
            q_lower = query.lower()
            if q_lower in searchable:
                score += 8.0
                
            # Token match
            for t in tokens:
                if t in searchable:
                    if t in chunk["chunk_id"].lower():
                        score += 5.0
                    elif t in chunk["title"].lower():
                        score += 3.0
                    else:
                        score += 1.0

            if score > 0:
                results.append((score, chunk))

        results.sort(key=lambda x: x[0], reverse=True)
        return [{"score": score, "chunk": c} for score, c in results[:top_k]]

    def hybrid_search(
        self,
        query: str,
        top_k: int = 5,
        category_filter: Optional[str] = None,
        doc_id_filter: Optional[str] = None
    ) -> List[ChunkDocument]:
        where_filter = {}
        if category_filter:
            where_filter["category"] = category_filter
        if doc_id_filter:
            where_filter["doc_id"] = doc_id_filter
        where_clause = where_filter if where_filter else None

        # 1. Vector Search
        dense_results: List[Dict[str, Any]] = []
        try:
            n_results = min(top_k * 3, max(self.collection.count(), 1))
            query_kwargs = {
                "query_texts": [query],
                "n_results": n_results
            }
            if where_clause:
                query_kwargs["where"] = where_clause

            vector_res = self.collection.query(**query_kwargs)
            if vector_res and vector_res["ids"] and vector_res["ids"][0]:
                for idx, cid in enumerate(vector_res["ids"][0]):
                    dist = vector_res["distances"][0][idx] if "distances" in vector_res and vector_res["distances"] else 0.5
                    meta = vector_res["metadatas"][0][idx]
                    dense_results.append({
                        "chunk_id": cid,
                        "metadata": meta,
                        "distance": dist,
                        "rank": idx + 1
                    })
        except Exception as e:
            print(f"[VectorStore] Dense retrieval error: {e}")

        # 2. Keyword Search
        keyword_hits = self._keyword_search(query, top_k=top_k * 3)

        # 3. Reciprocal Rank Fusion (RRF)
        rrf_k = 60
        scores: Dict[str, float] = {}
        chunk_map: Dict[str, Dict[str, Any]] = {c["chunk_id"]: c for c in self.raw_chunks}

        for item in dense_results:
            cid = item["chunk_id"]
            scores[cid] = scores.get(cid, 0.0) + (1.0 / (rrf_k + item["rank"]))

        for rank, item in enumerate(keyword_hits, 1):
            cid = item["chunk"]["chunk_id"]
            if category_filter and item["chunk"].get("category") != category_filter:
                continue
            if doc_id_filter and item["chunk"].get("doc_id") != doc_id_filter:
                continue
            scores[cid] = scores.get(cid, 0.0) + (1.0 / (rrf_k + rank))

        sorted_cids = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        final_chunks: List[ChunkDocument] = []
        for cid, score in sorted_cids:
            raw = chunk_map.get(cid)
            if raw:
                final_chunks.append(ChunkDocument(
                    chunk_id=raw["chunk_id"],
                    doc_id=raw["doc_id"],
                    title=raw["title"],
                    category=raw["category"],
                    owner=raw["owner"],
                    source_url=raw["source_url"],
                    published=str(raw["published"]),
                    version=str(raw["version"]),
                    text=raw["text"],
                    score=round(score, 4),
                    match_type="hybrid"
                ))

        return final_chunks

# Singleton instance
_vector_store_instance: Optional[VectorStoreManager] = None

def get_vector_store() -> VectorStoreManager:
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = VectorStoreManager()
    return _vector_store_instance
