"""
Face Recognition Service using DeepFace + FAISS (FaceNet512)
Local, free, production-ready replacement for AWS Rekognition
"""

import os
import json
import uuid
import base64
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

import cv2
import numpy as np
from deepface import DeepFace

from .faiss_store import FaissStore

# ------------------------------------------------------------------
# Logging Setup
# ------------------------------------------------------------------
logging.basicConfig(
    level=logging.DEBUG,  # 🔥 change to INFO in production
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

logger = logging.getLogger(__name__)


class FaceRecognitionService:
    """
    Face Recognition Service
    - Face detection
    - Face embedding (FaceNet512)
    - FAISS indexing & search
    """

    def __init__(self):
        logger.info("🚀 Initializing FaceRecognitionService")

        self.model_name = "Facenet512"
        self.detector_backend = "retinaface"

        logger.debug(f"Model={self.model_name}, Detector={self.detector_backend}")

        # Base storage
        self.base_path = Path("./face_data")
        self.images_path = self.base_path / "images"
        self.temp_path = self.base_path / "temp"
        self.debug_path = self.base_path / "debug"

        # Create directories
        for p in [
            self.images_path,
            self.temp_path,
            self.debug_path,
            self.debug_path / "raw",
            self.debug_path / "crops",
            self.debug_path / "boxes",
            self.debug_path / "search",
        ]:
            p.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Directory ready: {p}")

        self.faiss = FaissStore()
        logger.info("✅ FAISS store initialized")

        self._warmup_model()

        logger.info("✅ FaceRecognitionService ready")

    # ------------------------------------------------------------------
    # Utils
    # ------------------------------------------------------------------

    def _cleanup_temp_file(self, path: Optional[str]):
        try:
            if path and os.path.exists(path):
                os.remove(path)
                logger.debug(f"Temp file deleted: {path}")
        except Exception:
            logger.warning("Temp cleanup failed", exc_info=True)

    def _warmup_model(self):
        """Load DeepFace model once (first call is slow)"""
        logger.info("🔥 Warming up DeepFace model")

        try:
            dummy = np.zeros((224, 224, 3), dtype=np.uint8)
            path = self.temp_path / "warmup.jpg"
            cv2.imwrite(str(path), dummy)

            DeepFace.represent(
                img_path=str(path),
                model_name=self.model_name,
                detector_backend=self.detector_backend,
                enforce_detection=False,
            )

            path.unlink(missing_ok=True)
            logger.info("✅ Model warmup completed")

        except Exception:
            logger.warning("Model warmup failed (non-critical)", exc_info=True)

    def _decode_base64_image(self, image_base64: str) -> str:
        logger.debug("Decoding base64 image")

        if "," in image_base64:
            image_base64 = image_base64.split(",")[1]

        img_bytes = base64.b64decode(image_base64)
        filename = f"{uuid.uuid4().hex}.jpg"
        path = self.temp_path / filename

        with open(path, "wb") as f:
            f.write(img_bytes)

        logger.debug(f"Image written to temp path: {path}")
        return str(path)

    # ------------------------------------------------------------------
    # Face Embedding
    # ------------------------------------------------------------------

    def get_face_embedding(self, image_base64: str) -> Optional[List[float]]:
        logger.info("🧠 Extracting face embedding")

        temp_path = None
        try:
            temp_path = self._decode_base64_image(image_base64)

            reps = DeepFace.represent(
                img_path=temp_path,
                model_name=self.model_name,
                detector_backend=self.detector_backend,
                enforce_detection=True,
            )

            if not reps:
                logger.warning("No embeddings returned")
                return None

            logger.info("✅ Embedding extracted")
            return reps[0]["embedding"]

        except Exception:
            logger.error("Embedding extraction failed", exc_info=True)
            return None

        finally:
            self._cleanup_temp_file(temp_path)

    # ------------------------------------------------------------------
    # Index Face
    # ------------------------------------------------------------------

    def index_face(
        self,
        image_base64: str,
        person_id: str,
        person_type: str = "visitor",
        person_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        logger.info(f"📦 Indexing face | person_id={person_id}, type={person_type}")

        try:
            if person_type not in {"visitor", "resident", "watchlist"}:
                raise ValueError("Invalid person_type")

            face_id = f"{person_type}_{uuid.uuid4().hex}"
            logger.debug(f"Generated face_id={face_id}")

            image_dir = self.images_path / f"{person_type}s"
            image_dir.mkdir(parents=True, exist_ok=True)

            image_path = image_dir / f"{face_id}.jpg"

            img_bytes = base64.b64decode(image_base64.split(",")[-1])
            with open(image_path, "wb") as f:
                f.write(img_bytes)

            logger.debug(f"Image saved: {image_path}")

            faces = self.extract_faces_with_boxes(str(image_path))
            logger.info(f"Faces detected: {len(faces)}")

            if not faces:
                return {"success": False, "error": "No face detected"}

            self.save_debug_faces(face_id, str(image_path), faces)

            embedding_obj = DeepFace.represent(
                img_path=str(image_path),
                model_name=self.model_name,
                detector_backend=self.detector_backend,
                align=True,
                enforce_detection=True,
            )

            embedding = embedding_obj[0]["embedding"]

            self.faiss.add_face(
                face_id=face_id,
                embedding=embedding,
                meta={
                    "face_id": face_id,
                    "person_id": person_id,
                    "person_name": person_name,
                    "person_type": person_type,
                    "image_path": str(image_path),
                    "created_at": datetime.utcnow().isoformat(),
                    "active": True,
                    **(metadata or {}),
                },
            )

            logger.info(f"✅ Face indexed successfully: {face_id}")

            return {
                "success": True,
                "face_id": face_id,
                "image_path": str(image_path),
                "faces_detected": len(faces),
            }

        except Exception:
            logger.error("Face indexing failed", exc_info=True)
            return {"success": False, "error": "Indexing failed"}

    # ------------------------------------------------------------------
    # Search Face
    # ------------------------------------------------------------------

    def search_face(self, image_base64: str, person_types=None, top_k=5):
        logger.info("🔍 Face search started")

        temp_path = None
        try:
            temp_path = self._decode_base64_image(image_base64)

            faces = self.extract_faces_with_boxes(temp_path)
            logger.info(f"Faces detected: {len(faces)}")

            if not faces:
                return {"success": False, "error": "No face detected"}

            best_face = max(faces, key=lambda x: x["confidence"])
            x, y, w, h = best_face["box"].values()

            img = cv2.imread(temp_path)
            crop = img[y:y + h, x:x + w]

            crop_path = self.debug_path / "search" / f"search_{uuid.uuid4().hex}.jpg"
            cv2.imwrite(str(crop_path), crop)

            logger.debug(f"Search crop saved: {crop_path}")

            embedding_obj = DeepFace.represent(
                img_path=str(crop_path),
                model_name=self.model_name,
                detector_backend=self.detector_backend,
                align=True,
                enforce_detection=True,
            )

            embedding = embedding_obj[0]["embedding"]

            results = self.faiss.search(embedding, top_k=top_k)
            logger.info(f"FAISS matches found: {len(results)}")

            if person_types:
                results = [r for r in results if r.get("person_type") in person_types]

            if not results:
                return {"success": True, "matches": []}

            best_match = max(results, key=lambda x: x["score"])

            return {
                "success": True,
                "matches": results,
                "best_match": best_match,
                "confidence": best_match["score"],
            }

        except Exception:
            logger.error("Face search failed", exc_info=True)
            return {"success": False, "error": "Search failed"}

        finally:
            self._cleanup_temp_file(temp_path)

    # ------------------------------------------------------------------
    # Face Detection
    # ------------------------------------------------------------------

    def extract_faces_with_boxes(self, image_path: str):
        logger.debug(f"Detecting faces in: {image_path}")

        faces = DeepFace.extract_faces(
            img_path=image_path,
            detector_backend=self.detector_backend,
            align=True,
            enforce_detection=True
        )

        img = cv2.imread(image_path)
        results = []

        for i, face in enumerate(faces):
            area = face["facial_area"]
            logger.debug(f"Face {i}: {area}")

            x, y, w, h = area["x"], area["y"], area["w"], area["h"]
            crop = img[y:y + h, x:x + w]

            results.append({
                "index": i,
                "confidence": float(face.get("confidence", 0)),
                "box": {"x": x, "y": y, "w": w, "h": h},
                "crop": crop
            })

        return results

    # ------------------------------------------------------------------
    # Debug Save
    # ------------------------------------------------------------------

    def save_debug_faces(self, face_id, image_path, faces):
        logger.debug(f"Saving debug artifacts for {face_id}")

        raw_dir = self.debug_path / "raw"
        crop_dir = self.debug_path / "crops"
        box_dir = self.debug_path / "boxes"

        shutil.copy(image_path, raw_dir / f"{face_id}.jpg")

        box_data = []

        for f in faces:
            idx = f["index"]
            crop_path = crop_dir / f"{face_id}_{idx}.jpg"
            cv2.imwrite(str(crop_path), f["crop"])

            box_data.append({
                "index": idx,
                "confidence": f["confidence"],
                "box": f["box"],
                "crop_path": str(crop_path)
            })

        with open(box_dir / f"{face_id}.json", "w") as fp:
            json.dump(box_data, fp, indent=2)

        logger.debug("Debug artifacts saved")

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self):
        stats = self.faiss.stats()
        logger.info("Stats fetched")

        return {
            "total_faces": stats["active_faces"],
            "total_vectors": stats["total_vectors"],
            "by_type": stats["by_type"],
        }
    
        # ------------------------------------------------------------------
    # Watchlist Search
    # ------------------------------------------------------------------

    def search_watchlist(self, image_base64: str) -> Dict[str, Any]:
        """
        Search specifically in watchlist faces
        """

        logger.info("🚨 Watchlist search started")

        result = self.search_face(
            image_base64=image_base64,
            person_types=["watchlist"],
            top_k=3
        )

        if not result.get("success"):
            logger.warning("Watchlist search failed")
            return {
                "watchlist_match": False,
                "error": result.get("error")
            }

        matches = result.get("matches", [])

        if not matches:
            logger.info("No watchlist matches found")
            return {
                "watchlist_match": False
            }

        # Best watchlist hit
        best_match = max(matches, key=lambda x: x["score"])

        logger.warning(
            f"🚨 WATCHLIST MATCH FOUND | person_id={best_match.get('person_id')} "
            f"| confidence={best_match.get('score')}"
        )

        return {
            "watchlist_match": True,
            "alert_person_id": best_match.get("person_id"),
            "confidence": best_match.get("score"),
            "details": best_match
        }


# ------------------------------------------------------------------
# Singleton Instance
# ------------------------------------------------------------------
face_service = FaceRecognitionService()
