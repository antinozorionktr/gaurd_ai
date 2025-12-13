"""
Face Recognition Service using DeepFace + FAISS (FaceNet512)
Local, free, production-ready replacement for AWS Rekognition

FIXES APPLIED:
1. Consistent face cropping during both indexing and search
2. Adjusted thresholds based on actual FaceNet512 + cosine similarity behavior
3. Better debug logging for score analysis
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
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Confidence Thresholds (Cosine Similarity: -1.0 to 1.0, typically 0.0 to 1.0 for faces)
# ------------------------------------------------------------------
# FaceNet512 + Cosine similarity typical ranges after normalization:
# - Same person (good quality): 0.5 - 0.9
# - Same person (varying conditions): 0.3 - 0.6
# - Different person: -0.1 - 0.3
#
# LOWERED thresholds to account for:
# - Different lighting conditions
# - Different angles
# - Different image quality (webcam vs photo)

WATCHLIST_THRESHOLD = 0.35      # Lowered from 0.55 - still secure but allows for variation
VISITOR_THRESHOLD = 0.30        # Lowered from 0.50 - allows webcam/photo matching
RESIDENT_THRESHOLD = 0.30       # Lowered from 0.50
HIGH_CONFIDENCE_THRESHOLD = 0.50  # Lowered from 0.70 - auto-approve threshold


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

        # Thresholds (can be overridden via environment variables)
        self.watchlist_threshold = float(os.getenv("WATCHLIST_THRESHOLD", WATCHLIST_THRESHOLD))
        self.visitor_threshold = float(os.getenv("VISITOR_THRESHOLD", VISITOR_THRESHOLD))
        self.resident_threshold = float(os.getenv("RESIDENT_THRESHOLD", RESIDENT_THRESHOLD))
        self.high_confidence_threshold = float(os.getenv("HIGH_CONFIDENCE_THRESHOLD", HIGH_CONFIDENCE_THRESHOLD))

        logger.info(f"Model={self.model_name}, Detector={self.detector_backend}")
        logger.info(f"Thresholds: watchlist={self.watchlist_threshold}, visitor={self.visitor_threshold}, resident={self.resident_threshold}")

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
            self.debug_path / "indexed_crops",  # NEW: Store the actual crops used for indexing
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

    def _get_threshold_for_type(self, person_type: str) -> float:
        """Get the appropriate confidence threshold for a person type"""
        thresholds = {
            "watchlist": self.watchlist_threshold,
            "visitor": self.visitor_threshold,
            "resident": self.resident_threshold,
        }
        return thresholds.get(person_type, self.visitor_threshold)

    def _crop_best_face(self, image_path: str) -> Optional[str]:
        """
        Detect faces in image and return path to cropped best face.
        This ensures consistent preprocessing for both indexing and search.
        """
        try:
            faces = DeepFace.extract_faces(
                img_path=image_path,
                detector_backend=self.detector_backend,
                align=True,
                enforce_detection=True
            )

            if not faces:
                return None

            img = cv2.imread(image_path)
            
            # Find the largest/most confident face
            best_face = max(faces, key=lambda x: x.get("confidence", 0) * x["facial_area"]["w"] * x["facial_area"]["h"])
            area = best_face["facial_area"]
            
            x, y, w, h = area["x"], area["y"], area["w"], area["h"]
            
            # Add padding around the face (10% on each side)
            pad_x = int(w * 0.1)
            pad_y = int(h * 0.1)
            
            # Ensure we don't go out of bounds
            x1 = max(0, x - pad_x)
            y1 = max(0, y - pad_y)
            x2 = min(img.shape[1], x + w + pad_x)
            y2 = min(img.shape[0], y + h + pad_y)
            
            crop = img[y1:y2, x1:x2]
            
            # Save cropped face
            crop_path = self.temp_path / f"crop_{uuid.uuid4().hex}.jpg"
            cv2.imwrite(str(crop_path), crop)
            
            logger.debug(f"Face cropped: {crop_path} (box: x={x}, y={y}, w={w}, h={h})")
            
            return str(crop_path)
            
        except Exception as e:
            logger.error(f"Face cropping failed: {e}", exc_info=True)
            return None

    # ------------------------------------------------------------------
    # Face Embedding
    # ------------------------------------------------------------------

    def get_face_embedding(self, image_base64: str) -> Optional[List[float]]:
        logger.info("🧠 Extracting face embedding")

        temp_path = None
        crop_path = None
        try:
            temp_path = self._decode_base64_image(image_base64)
            
            # Crop the face first for consistent embedding
            crop_path = self._crop_best_face(temp_path)
            if not crop_path:
                logger.warning("No face detected for embedding")
                return None

            reps = DeepFace.represent(
                img_path=crop_path,
                model_name=self.model_name,
                detector_backend="skip",  # Already cropped, skip detection
                enforce_detection=False,
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
            self._cleanup_temp_file(crop_path)

    # ------------------------------------------------------------------
    # Index Face - FIXED: Now uses cropped face for embedding
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

        temp_path = None
        crop_path = None
        try:
            if person_type not in {"visitor", "resident", "watchlist"}:
                raise ValueError("Invalid person_type")

            face_id = f"{person_type}_{uuid.uuid4().hex}"
            logger.debug(f"Generated face_id={face_id}")

            # Save original image
            image_dir = self.images_path / f"{person_type}s"
            image_dir.mkdir(parents=True, exist_ok=True)
            image_path = image_dir / f"{face_id}.jpg"

            img_bytes = base64.b64decode(image_base64.split(",")[-1])
            with open(image_path, "wb") as f:
                f.write(img_bytes)

            logger.debug(f"Original image saved: {image_path}")

            # Detect and extract faces for debug info
            faces = self.extract_faces_with_boxes(str(image_path))
            logger.info(f"Faces detected: {len(faces)}")

            if not faces:
                return {"success": False, "error": "No face detected"}

            # Save debug artifacts
            self.save_debug_faces(face_id, str(image_path), faces)

            # CRITICAL FIX: Crop the best face and use that for embedding
            crop_path = self._crop_best_face(str(image_path))
            if not crop_path:
                return {"success": False, "error": "Failed to crop face"}

            # Save the indexed crop for debugging
            indexed_crop_path = self.debug_path / "indexed_crops" / f"{face_id}.jpg"
            shutil.copy(crop_path, indexed_crop_path)
            logger.debug(f"Indexed crop saved: {indexed_crop_path}")

            # Get embedding from CROPPED face (not full image)
            embedding_obj = DeepFace.represent(
                img_path=crop_path,
                model_name=self.model_name,
                detector_backend="skip",  # Already cropped, skip detection
                align=False,  # Already aligned during crop
                enforce_detection=False,
            )

            if not embedding_obj:
                return {"success": False, "error": "Failed to extract embedding"}

            embedding = embedding_obj[0]["embedding"]
            
            # Log embedding stats for debugging
            emb_array = np.array(embedding)
            logger.debug(f"Embedding stats: min={emb_array.min():.4f}, max={emb_array.max():.4f}, mean={emb_array.mean():.4f}, norm={np.linalg.norm(emb_array):.4f}")

            self.faiss.add_face(
                face_id=face_id,
                embedding=embedding,
                meta={
                    "face_id": face_id,
                    "person_id": person_id,
                    "person_name": person_name,
                    "person_type": person_type,
                    "image_path": str(image_path),
                    "crop_path": str(indexed_crop_path),
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
                "crop_path": str(indexed_crop_path),
                "faces_detected": len(faces),
            }

        except Exception as e:
            logger.error(f"Face indexing failed: {e}", exc_info=True)
            return {"success": False, "error": f"Indexing failed: {str(e)}"}

        finally:
            self._cleanup_temp_file(crop_path)

    # ------------------------------------------------------------------
    # Search Face - FIXED: Consistent cropping and better logging
    # ------------------------------------------------------------------

    def search_face(
        self,
        image_base64: str,
        person_types: Optional[List[str]] = None,
        top_k: int = 5,
        threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Search for a face in the FAISS index.
        """
        logger.info("🔍 Face search started")

        temp_path = None
        crop_path = None
        try:
            temp_path = self._decode_base64_image(image_base64)

            # Crop the face (consistent with indexing)
            crop_path = self._crop_best_face(temp_path)
            if not crop_path:
                return {"success": False, "error": "No face detected"}

            # Save search crop for debugging
            debug_crop_path = self.debug_path / "search" / f"search_{uuid.uuid4().hex}.jpg"
            shutil.copy(crop_path, debug_crop_path)
            logger.debug(f"Search crop saved: {debug_crop_path}")

            # Get embedding from cropped face
            embedding_obj = DeepFace.represent(
                img_path=crop_path,
                model_name=self.model_name,
                detector_backend="skip",  # Already cropped
                align=False,
                enforce_detection=False,
            )

            if not embedding_obj:
                return {"success": False, "error": "Failed to extract embedding"}

            embedding = embedding_obj[0]["embedding"]
            
            # Log embedding stats
            emb_array = np.array(embedding)
            logger.debug(f"Search embedding stats: min={emb_array.min():.4f}, max={emb_array.max():.4f}, mean={emb_array.mean():.4f}, norm={np.linalg.norm(emb_array):.4f}")

            results = self.faiss.search(embedding, top_k=top_k)
            logger.info(f"FAISS matches found: {len(results)}")

            # Log ALL results for debugging
            for i, r in enumerate(results):
                logger.debug(f"  Match {i}: score={r.get('score', 0):.4f}, person_id={r.get('person_id')}, type={r.get('person_type')}, name={r.get('person_name')}")

            # Filter by person_types if specified
            if person_types:
                results = [r for r in results if r.get("person_type") in person_types]
                logger.debug(f"After type filter ({person_types}): {len(results)} matches")

            # Filter out inactive faces
            results = [r for r in results if r.get("active", True)]

            if not results:
                return {"success": True, "matches": [], "match_found": False}

            # Determine threshold to use
            if threshold is None:
                if person_types:
                    threshold = self._get_threshold_for_type(person_types[0])
                else:
                    threshold = self.visitor_threshold

            # Filter results by threshold
            valid_matches = [r for r in results if r.get("score", 0) >= threshold]
            
            logger.info(f"Matches above threshold ({threshold}): {len(valid_matches)} / {len(results)}")

            if not valid_matches:
                best_score = max(r.get("score", 0) for r in results) if results else 0
                logger.info(f"No matches above threshold {threshold} (best score: {best_score:.4f})")
                return {
                    "success": True,
                    "matches": results,
                    "match_found": False,
                    "threshold": threshold,
                    "best_score": best_score
                }

            best_match = max(valid_matches, key=lambda x: x["score"])

            # Normalize keys
            best_match_normalized = dict(best_match)
            best_match_normalized["confidence"] = best_match_normalized.get("score")

            logger.info(f"✅ Best match: {best_match_normalized.get('person_name')} with score {best_match_normalized.get('confidence'):.4f}")

            return {
                "success": True,
                "matches": valid_matches,
                "best_match": best_match_normalized,
                "match_found": True,
                "confidence": best_match_normalized["confidence"],
                "threshold": threshold,
            }

        except Exception as e:
            logger.error(f"Face search failed: {e}", exc_info=True)
            return {"success": False, "error": f"Search failed: {str(e)}"}

        finally:
            self._cleanup_temp_file(temp_path)
            self._cleanup_temp_file(crop_path)

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
    # Delete Face
    # ------------------------------------------------------------------

    def delete_face(self, face_id: str) -> bool:
        """Delete a face from the index (mark as inactive)."""
        logger.info(f"🗑️ Deleting face: {face_id}")
        
        try:
            for idx, meta in self.faiss.metadata.items():
                if meta.get("face_id") == face_id:
                    meta["active"] = False
                    self.faiss._save()
                    logger.info(f"✅ Face marked as inactive: {face_id}")
                    return True
            
            logger.warning(f"Face not found: {face_id}")
            return False
            
        except Exception:
            logger.error("Face deletion failed", exc_info=True)
            return False

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
            "thresholds": {
                "watchlist": self.watchlist_threshold,
                "visitor": self.visitor_threshold,
                "resident": self.resident_threshold,
                "high_confidence": self.high_confidence_threshold,
            }
        }

    # ------------------------------------------------------------------
    # Evidence Image Save (for incidents)
    # ------------------------------------------------------------------

    def save_evidence_image(self, image_base64: str, folder: str) -> Optional[str]:
        """Save evidence image and return path"""
        try:
            evidence_dir = self.base_path / "evidence" / folder
            evidence_dir.mkdir(parents=True, exist_ok=True)
            
            filename = f"{uuid.uuid4().hex}.jpg"
            path = evidence_dir / filename
            
            if "," in image_base64:
                image_base64 = image_base64.split(",")[1]
            
            img_bytes = base64.b64decode(image_base64)
            with open(path, "wb") as f:
                f.write(img_bytes)
            
            return str(path)
        except Exception as e:
            logger.error(f"Failed to save evidence: {e}")
            return None

    # ------------------------------------------------------------------
    # Watchlist Search
    # ------------------------------------------------------------------

    def search_watchlist(
        self,
        image_base64: str,
        threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """Search specifically in watchlist faces."""
        logger.info("🚨 Watchlist search started")

        if threshold is None:
            threshold = self.watchlist_threshold

        result = self.search_face(
            image_base64=image_base64,
            person_types=["watchlist"],
            top_k=3,
            threshold=threshold
        )

        if not result.get("success"):
            logger.warning("Watchlist search failed")
            return {
                "watchlist_match": False,
                "error": result.get("error")
            }

        if not result.get("match_found"):
            best_score = result.get("best_score", 0)
            logger.info(f"No watchlist matches above threshold {threshold} (best score: {best_score:.3f})")
            return {
                "watchlist_match": False,
                "threshold": threshold,
                "best_score": best_score
            }

        best_match = result.get("best_match")
        confidence = best_match.get("confidence", 0)

        logger.warning(
            f"🚨 WATCHLIST MATCH FOUND | person_id={best_match.get('person_id')} "
            f"| confidence={confidence:.3f} | threshold={threshold}"
        )

        return {
            "watchlist_match": True,
            "best_match": best_match,
            "alert_person_id": best_match.get("person_id"),
            "confidence": confidence,
            "threshold": threshold,
            "details": best_match,
        }

    # ------------------------------------------------------------------
    # Visitor/Resident Search
    # ------------------------------------------------------------------

    def search_visitor(
        self,
        image_base64: str,
        threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """Search for visitor/resident faces."""
        logger.info("👤 Visitor/Resident search started")

        if threshold is None:
            threshold = self.visitor_threshold

        result = self.search_face(
            image_base64=image_base64,
            person_types=["visitor", "resident"],
            top_k=5,
            threshold=threshold
        )

        if not result.get("success"):
            return {
                "match_found": False,
                "error": result.get("error")
            }

        if not result.get("match_found"):
            best_score = result.get("best_score", 0)
            logger.info(f"No visitor/resident matches above threshold {threshold} (best score: {best_score:.3f})")
            return {
                "match_found": False,
                "threshold": threshold,
                "best_score": best_score,
                "matches": result.get("matches", [])
            }

        best_match = result.get("best_match")
        logger.info(
            f"✅ Visitor/Resident match found | person_id={best_match.get('person_id')} "
            f"| confidence={best_match.get('confidence', 0):.3f}"
        )

        return {
            "match_found": True,
            "best_match": best_match,
            "confidence": best_match.get("confidence"),
            "threshold": threshold,
            "matches": result.get("matches", [])
        }


# ------------------------------------------------------------------
# Singleton Instance
# ------------------------------------------------------------------
face_service = FaceRecognitionService()