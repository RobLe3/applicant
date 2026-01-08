import hashlib
import json
import math
import os
import re


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "is", "it", "of", "on", "or", "that", "the", "to", "with",
}


def tokenize(text):
    tokens = re.findall(r"[a-zA-Z0-9+#]+", (text or "").lower())
    return {t for t in tokens if t not in STOPWORDS and len(t) > 1}


def jaccard_similarity(text_a, text_b):
    set_a = tokenize(text_a or "")
    set_b = tokenize(text_b or "")
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def _cosine_similarity(vec_a, vec_b):
    if not vec_a or not vec_b:
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _hash_embedding(text, dims=256):
    tokens = tokenize(text)
    if not tokens:
        return [0.0] * dims
    vec = [0.0] * dims
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        idx = int(digest[:8], 16) % dims
        sign = 1.0 if int(digest[8:10], 16) % 2 == 0 else -1.0
        vec[idx] += sign
    return vec


class EmbeddingCache:
    def __init__(self, path=None):
        self.path = path
        self._cache = {}
        if path and os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    self._cache = data
            except Exception:
                self._cache = {}

    def get(self, text):
        if text in self._cache:
            return self._cache[text]
        return None

    def set(self, text, vector):
        self._cache[text] = vector

    def save(self):
        if not self.path:
            return
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._cache, f)


class SemanticEmbedder:
    def __init__(self, backend="hash", model_path=None, cache_path=None):
        self.backend = backend
        self.model_path = model_path
        self.cache = EmbeddingCache(cache_path)
        self.model = None
        self.available = False
        self.reason = ""
        self._init_model()

    def _init_model(self):
        if self.backend == "hash":
            self.available = True
            self.reason = "hash"
            return
        if self.backend != "sbert":
            self.available = False
            self.reason = "unsupported_backend"
            return
        if not self.model_path:
            self.available = False
            self.reason = "missing_model_path"
            return
        if not os.path.exists(self.model_path):
            self.available = False
            self.reason = "model_path_not_found"
            return
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore

            self.model = SentenceTransformer(self.model_path)
            self.available = True
            self.reason = "sbert_loaded"
        except Exception as exc:
            self.available = False
            self.reason = f"load_failed:{exc}"

    def embed(self, text):
        if not text:
            return []
        cached = self.cache.get(text)
        if cached is not None:
            return cached
        if self.backend == "hash":
            vec = _hash_embedding(text)
        elif self.backend == "sbert" and self.model:
            try:
                vec = self.model.encode([text])[0]
                vec = vec.tolist() if hasattr(vec, "tolist") else list(vec)
            except Exception:
                vec = _hash_embedding(text)
        else:
            vec = _hash_embedding(text)
        self.cache.set(text, vec)
        return vec


def semantic_similarity(text_a, text_b, embedder=None):
    if not embedder or not embedder.available:
        return jaccard_similarity(text_a, text_b)
    vec_a = embedder.embed(text_a or "")
    vec_b = embedder.embed(text_b or "")
    return _cosine_similarity(vec_a, vec_b)


def cluster_texts(texts, embedder=None, threshold=0.85):
    if not texts:
        return [], []
    vectors = []
    for text in texts:
        if embedder and embedder.available:
            vectors.append(embedder.embed(text or ""))
        else:
            vectors.append(_hash_embedding(text or ""))

    cluster_ids = []
    cluster_vectors = []
    cluster_texts_ref = []

    for idx, vec in enumerate(vectors):
        assigned = None
        for cluster_idx, rep_vec in enumerate(cluster_vectors):
            if embedder and embedder.available:
                sim = _cosine_similarity(vec, rep_vec)
            else:
                sim = jaccard_similarity(texts[idx], cluster_texts_ref[cluster_idx])
            if sim >= threshold:
                assigned = cluster_idx
                break
        if assigned is None:
            cluster_vectors.append(vec)
            cluster_texts_ref.append(texts[idx])
            assigned = len(cluster_vectors) - 1
        cluster_ids.append(assigned + 1)

    cluster_sizes = {}
    for cluster_id in cluster_ids:
        cluster_sizes[cluster_id] = cluster_sizes.get(cluster_id, 0) + 1

    return cluster_ids, cluster_sizes
