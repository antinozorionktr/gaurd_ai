import faiss
import os
import json
import threading
import numpy as np
from typing import Dict, Any, List

FAISS_DIR = "./faiss"
INDEX_PATH = f"{FAISS_DIR}/faces.index"
META_PATH = f"{FAISS_DIR}/faces_meta.json"
EMBEDDING_DIM = 512  # FaceNet512


class FaissStore:
    def __init__(self, dim: int = 512):
        self.dim = dim
        self.index = faiss.IndexFlatIP(dim)  # cosine similarity
        self.lock = threading.Lock()
        self.metadata = {}  # face_id -> meta
        os.makedirs(FAISS_DIR, exist_ok=True)

        if os.path.exists(INDEX_PATH):
            self.index = faiss.read_index(INDEX_PATH)
        else:
            self.index = faiss.IndexFlatIP(EMBEDDING_DIM)

        if os.path.exists(META_PATH):
            with open(META_PATH, "r") as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {}

    def _save(self):
        faiss.write_index(self.index, INDEX_PATH)
        with open(META_PATH, "w") as f:
            json.dump(self.metadata, f)

    @staticmethod
    def normalize(vec: List[float]) -> np.ndarray:
        vec = np.array(vec).astype("float32")
        return vec / np.linalg.norm(vec)

    def add_face(self, face_id: str, embedding: List[float], meta: Dict[str, Any]):
        vec = self.normalize(embedding).reshape(1, -1)
        self.index.add(vec)

        faiss_id = self.index.ntotal - 1
        self.metadata[str(faiss_id)] = {
            "face_id": face_id,
            **meta
        }

        self._save()

    def search(self, embedding: List[float], top_k: int = 5):
        if self.index.ntotal == 0:
            return []

        vec = self.normalize(embedding).reshape(1, -1)
        scores, ids = self.index.search(vec, top_k)

        results = []
        for score, idx in zip(scores[0], ids[0]):
            if idx == -1:
                continue
            results.append({
                "score": float(score),
                **self.metadata.get(str(idx), {})
            })
        return results
    
    def stats(self) -> Dict[str, Any]:
        by_type = {}

        for meta in self.metadata.values():
            person_type = meta.get("person_type", "unknown")
            by_type[person_type] = by_type.get(person_type, 0) + 1

        return {
            "total_vectors": self.index.ntotal,
            "active_faces": len(self.metadata),
            "by_type": by_type
        }
    