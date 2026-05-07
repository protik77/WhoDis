"""ImageHash-based detection engine using perceptual hashing."""

import io
import pickle

import imagehash
from PIL import Image

from whodis.config import IMAGEHASH_THRESHOLD, MAX_IMAGE_DIMENSION
from whodis.engines.base import DetectionEngine, DetectionResult


class ImageHashEngine(DetectionEngine):
    """
    Detection engine using image perceptual hashing.
    
    Uses a combination of average hash and perceptual hash for robust matching.
    """
    
    name = "imagehash"
    
    def __init__(self, threshold: int = None):
        self.threshold = threshold or IMAGEHASH_THRESHOLD
    
    def _resize_image(self, img: Image.Image) -> Image.Image:
        """Resize image if too large while maintaining aspect ratio."""
        width, height = img.size
        max_dim = MAX_IMAGE_DIMENSION
        
        if width > max_dim or height > max_dim:
            ratio = min(max_dim / width, max_dim / height)
            new_size = (int(width * ratio), int(height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        return img
    
    def _compute_hashes(self, img: Image.Image) -> dict:
        """Compute multiple hash types for an image."""
        # Convert to RGB if necessary
        if img.mode != "RGB":
            img = img.convert("RGB")
        
        # Resize if needed
        img = self._resize_image(img)
        
        return {
            "average": imagehash.average_hash(img),
            "perceptual": imagehash.phash(img),
            "difference": imagehash.dhash(img),
        }
    
    async def compute_embedding(self, image_data: bytes) -> bytes:
        """Compute hash embedding for an image."""
        img = Image.open(io.BytesIO(image_data))
        hashes = self._compute_hashes(img)
        # Serialize with pickle
        return pickle.dumps(hashes)
    
    def compare_embeddings(self, emb1: bytes, emb2: bytes) -> float:
        """
        Compare two hash embeddings.
        
        Returns similarity as a float between 0.0 and 1.0.
        Uses weighted combination of hash differences.
        """
        try:
            hashes1 = pickle.loads(emb1)
            hashes2 = pickle.loads(emb2)
        except Exception:
            return 0.0
        
        # Compute hamming distances
        avg_dist = hashes1["average"] - hashes2["average"]
        perc_dist = hashes1["perceptual"] - hashes2["perceptual"]
        diff_dist = hashes1["difference"] - hashes2["difference"]
        
        # Max possible distance for 64-bit hashes is 64
        max_dist = 64.0
        
        # Normalize distances (0 = identical, 1 = completely different)
        avg_sim = 1.0 - (avg_dist / max_dist)
        perc_sim = 1.0 - (perc_dist / max_dist)
        diff_sim = 1.0 - (diff_dist / max_dist)
        
        # Weighted combination (perceptual hash is most important)
        similarity = (0.2 * avg_sim) + (0.5 * perc_sim) + (0.3 * diff_sim)
        
        # Ensure in valid range
        return max(0.0, min(1.0, similarity))
    
    async def detect(self, image_data: bytes, db_session) -> DetectionResult:
        """
        Detect a person using image hashing.
        
        Returns the best match if similarity exceeds threshold.
        """
        matches = await self.find_matches(
            image_data, 
            db_session, 
            threshold=(1.0 - (self.threshold / 64.0))  # Convert threshold to similarity
        )
        
        if not matches:
            return DetectionResult(
                person_id=None,
                person_name=None,
                confidence=0.0,
                matched=False
            )
        
        best_match = matches[0]
        return DetectionResult(
            person_id=best_match.person_id,
            person_name=best_match.person_name,
            confidence=best_match.similarity,
            matched=True
        )
    
    def compute_hash_distance(self, emb1: bytes, emb2: bytes) -> int:
        """Compute combined hash distance (for debugging)."""
        try:
            hashes1 = pickle.loads(emb1)
            hashes2 = pickle.loads(emb2)
        except Exception:
            return float("inf")
        
        avg_dist = hashes1["average"] - hashes2["average"]
        perc_dist = hashes1["perceptual"] - hashes2["perceptual"]
        diff_dist = hashes1["difference"] - hashes2["difference"]
        
        # Weighted combination
        return int(0.2 * avg_dist + 0.5 * perc_dist + 0.3 * diff_dist)
