"""
Face Recognition Service using DeepFace + FAISS (FaceNet512)
Local, free, production-ready replacement for AWS Rekognition

FIXED VERSION - Consistent embedding extraction between index and search
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
# Confidence Thresholds (Cosine Similarity)
# ------------------------------------------------------------------
# LOWERED thresholds - the previous ones were too strict
# FaceNet512 + FAISS Inner Product after normalization:
# - Same person (good conditions): 0.5 - 0.9
# - Same person (varying conditions): 0.3 - 0.6  
# - Different person: 0.0 - 0.3

WATCHLIST_THRESHOLD = 0.40      # Lowered from 0.55
VISITOR_THRESHOLD = 0.35        # Lowered from 0.50
RESIDENT_THRESHOLD = 0.35       # Lowered from 0.50
HIGH_CONFIDENCE_THRESHOLD = 0.55  # Lowered from 0.70


class FaceRecognitionService:
    """
    Face Recognition Service with CONSISTENT embedding extraction
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
        logger.info(f"Thresholds: watchlist={self.watchlist_threshold}, visitor={self.visitor_threshold}")

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
            pass

    def _warmup_model(self):
        """Load DeepFace model once"""
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
            logger.warning("Model warmup failed (non-critical)")

    def _decode_base64_image(self, image_base64: str) -> str:
        """Decode base64 to temp file"""
        if "," in image_base64:
            image_base64 = image_base64.split(",")[1]

        img_bytes = base64.b64decode(image_base64)
        filename = f"{uuid.uuid4().hex}.jpg"
        path = self.temp_path / filename

        with open(path, "wb") as f:
            f.write(img_bytes)

        logger.debug(f"Image decoded to: {path}")
        return str(path)

    def _get_threshold_for_type(self, person_type: str) -> float:
        """Get the appropriate confidence threshold for a person type"""
        thresholds = {
            "watchlist": self.watchlist_threshold,
            "visitor": self.visitor_threshold,
            "resident": self.resident_threshold,
        }
        return thresholds.get(person_type, self.visitor_threshold)

    # ------------------------------------------------------------------
    # CORE: Get embedding from image (SINGLE METHOD FOR CONSISTENCY)
    # ------------------------------------------------------------------
    
    def _get_embedding_from_image(self, image_path: str) -> Optional[Dict[str, Any]]:
        """
        Extract face embedding from image.
        
        THIS IS THE SINGLE SOURCE OF TRUTH FOR EMBEDDING EXTRACTION.
        Both indexing and search use this method to ensure consistency.
        
        Returns:
            Dict with 'embedding', 'facial_area', etc. or None if failed
        """
        try:
            result = DeepFace.represent(
                img_path=image_path,
                model_name=self.model_name,
                detector_backend=self.detector_backend,
                align=True,
                enforce_detection=True,
            )
            
            if result and len(result) > 0:
                return result[0]
            return None
            
        except Exception as e:
            logger.error(f"Embedding extraction failed: {e}")
            return None

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

        logger.info(f"📦 Indexing face | person_id={person_id}, type={person_type}, name={person_name}")

        try:
            if person_type not in {"visitor", "resident", "watchlist"}:
                raise ValueError("Invalid person_type")

            face_id = f"{person_type}_{uuid.uuid4().hex}"
            logger.debug(f"Generated face_id={face_id}")

            # Save image
            image_dir = self.images_path / f"{person_type}s"
            image_dir.mkdir(parents=True, exist_ok=True)
            image_path = image_dir / f"{face_id}.jpg"

            img_bytes = base64.b64decode(image_base64.split(",")[-1])
            with open(image_path, "wb") as f:
                f.write(img_bytes)

            logger.debug(f"Image saved: {image_path}")

            # Get embedding using THE SAME METHOD as search
            embedding_result = self._get_embedding_from_image(str(image_path))
            
            if not embedding_result:
                logger.error("No face detected in image")
                return {"success": False, "error": "No face detected"}

            embedding = embedding_result["embedding"]
            facial_area = embedding_result.get("facial_area", {})
            
            logger.debug(f"Face detected at: {facial_area}")
            logger.debug(f"Embedding extracted, length: {len(embedding)}")

            # Save debug info
            self._save_debug_info(face_id, str(image_path), facial_area)

            # Add to FAISS
            self.faiss.add_face(
                face_id=face_id,
                embedding=embedding,
                meta={
                    "face_id": face_id,
                    "person_id": person_id,
                    "person_name": person_name,
                    "person_type": person_type,
                    "image_path": str(image_path),
                    "facial_area": facial_area,
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
                "facial_area": facial_area,
            }

        except Exception as e:
            logger.error(f"Face indexing failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def _save_debug_info(self, face_id: str, image_path: str, facial_area: dict):
        """Save debug images"""
        try:
            # Copy raw image
            raw_dir = self.debug_path / "raw"
            shutil.copy(image_path, raw_dir / f"{face_id}.jpg")
            
            # Save crop if we have facial area
            if facial_area:
                img = cv2.imread(image_path)
                x = facial_area.get('x', 0)
                y = facial_area.get('y', 0)
                w = facial_area.get('w', img.shape[1])
                h = facial_area.get('h', img.shape[0])
                
                crop = img[y:y+h, x:x+w]
                crop_path = self.debug_path / "crops" / f"{face_id}.jpg"
                cv2.imwrite(str(crop_path), crop)
                
            logger.debug(f"Debug info saved for {face_id}")
        except Exception as e:
            logger.warning(f"Failed to save debug info: {e}")

    # ------------------------------------------------------------------
    # Search Face - NOW USES SAME METHOD AS INDEXING
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
        Uses THE SAME embedding extraction as indexing for consistency.
        """
        logger.info("🔍 Face search started")

        temp_path = None
        try:
            # Decode image
            temp_path = self._decode_base64_image(image_base64)

            # Get embedding using THE SAME METHOD as indexing
            embedding_result = self._get_embedding_from_image(temp_path)
            
            if not embedding_result:
                logger.warning("No face detected in search image")
                return {"success": False, "error": "No face detected"}

            embedding = embedding_result["embedding"]
            facial_area = embedding_result.get("facial_area", {})
            
            logger.debug(f"Search face detected at: {facial_area}")

            # Save debug crop
            self._save_search_debug(temp_path, facial_area)

            # Search FAISS
            results = self.faiss.search(embedding, top_k=top_k)
            logger.info(f"FAISS matches found: {len(results)}")

            # Log ALL results for debugging
            for i, r in enumerate(results):
                logger.debug(f"  Match {i}: score={r.get('score', 0):.4f}, "
                           f"name={r.get('person_name')}, type={r.get('person_type')}")

            # Filter by person_types if specified
            if person_types:
                original_count = len(results)
                results = [r for r in results if r.get("person_type") in person_types]
                logger.debug(f"After type filter ({person_types}): {len(results)}/{original_count}")

            # Filter out inactive faces
            results = [r for r in results if r.get("active", True)]

            if not results:
                logger.info("No matches found after filtering")
                return {"success": True, "matches": [], "match_found": False}

            # Determine threshold
            if threshold is None:
                if person_types:
                    threshold = self._get_threshold_for_type(person_types[0])
                else:
                    threshold = self.visitor_threshold

            # Filter by threshold
            valid_matches = [r for r in results if r.get("score", 0) >= threshold]
            best_score = max(r.get("score", 0) for r in results) if results else 0
            
            logger.info(f"Matches above threshold ({threshold}): {len(valid_matches)}/{len(results)}, best_score={best_score:.4f}")

            if not valid_matches:
                return {
                    "success": True,
                    "matches": results,
                    "match_found": False,
                    "threshold": threshold,
                    "best_score": best_score
                }

            # Get best match
            best_match = max(valid_matches, key=lambda x: x["score"])
            best_match_normalized = dict(best_match)
            best_match_normalized["confidence"] = best_match_normalized.get("score")

            logger.info(f"✅ Best match: {best_match_normalized.get('person_name')} "
                       f"with confidence {best_match_normalized.get('confidence'):.4f}")

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
            return {"success": False, "error": str(e)}

        finally:
            self._cleanup_temp_file(temp_path)

    def _save_search_debug(self, image_path: str, facial_area: dict):
        """Save search debug image"""
        try:
            if facial_area:
                img = cv2.imread(image_path)
                x = facial_area.get('x', 0)
                y = facial_area.get('y', 0)
                w = facial_area.get('w', img.shape[1])
                h = facial_area.get('h', img.shape[0])
                
                crop = img[y:y+h, x:x+w]
                crop_path = self.debug_path / "search" / f"search_{uuid.uuid4().hex}.jpg"
                cv2.imwrite(str(crop_path), crop)
                logger.debug(f"Search crop saved: {crop_path}")
        except Exception as e:
            logger.warning(f"Failed to save search debug: {e}")

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
            return {"watchlist_match": False, "error": result.get("error")}

        if not result.get("match_found"):
            logger.info("No watchlist matches found")
            return {
                "watchlist_match": False,
                "threshold": threshold,
                "best_score": result.get("best_score", 0)
            }

        best_match = result.get("best_match")
        logger.warning(f"🚨 WATCHLIST MATCH: {best_match.get('person_name')} "
                      f"confidence={best_match.get('confidence'):.3f}")

        return {
            "watchlist_match": True,
            "best_match": best_match,
            "confidence": best_match.get("confidence"),
            "threshold": threshold,
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

        return self.search_face(
            image_base64=image_base64,
            person_types=["visitor", "resident"],
            top_k=5,
            threshold=threshold
        )

    # ------------------------------------------------------------------
    # Delete Face
    # ------------------------------------------------------------------

    def delete_face(self, face_id: str) -> bool:
        """Mark face as inactive in FAISS"""
        logger.info(f"🗑️ Deleting face: {face_id}")
        try:
            for idx, meta in self.faiss.metadata.items():
                if meta.get("face_id") == face_id:
                    meta["active"] = False
                    self.faiss._save()
                    logger.info(f"✅ Face marked inactive: {face_id}")
                    return True
            logger.warning(f"Face not found: {face_id}")
            return False
        except Exception as e:
            logger.error(f"Face deletion failed: {e}")
            return False

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self):
        stats = self.faiss.stats()
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
        """Save evidence image"""
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
    # Legacy method for compatibility
    # ------------------------------------------------------------------
    
    def extract_faces_with_boxes(self, image_path: str):
        """Extract faces with bounding boxes (legacy compatibility)"""
        try:
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
                x, y, w, h = area["x"], area["y"], area["w"], area["h"]
                crop = img[y:y + h, x:x + w]

                results.append({
                    "index": i,
                    "confidence": float(face.get("confidence", 0)),
                    "box": {"x": x, "y": y, "w": w, "h": h},
                    "crop": crop
                })

            return results
        except Exception as e:
            logger.error(f"Face extraction failed: {e}")
            return []


# ------------------------------------------------------------------
# Singleton Instance
# ------------------------------------------------------------------
face_service = FaceRecognitionService()