"""
Video Encoder — CLIP ViT-B/32 frame analysis.
Owner: Claude

Samples 5 frames, extracts features, projects to 384-dim.
Falls back to thumbnail from metadata.
"""

import numpy as np
from typing import Optional
from datetime import datetime

from ..types import ModalityEmbedding


class VideoEncoder:
    """Encode video to 384-dimensional embeddings via CLIP."""
    
    def __init__(self):
        """Initialize with optional CLIP."""
        self._clip_model = None
        self._clip_processor = None
        self._use_clip = False
        self._try_load_clip()
    
    def _try_load_clip(self) -> None:
        """Try to load CLIP ViT-B/32."""
        try:
            from PIL import Image
            import clip
            import torch
            
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self._clip_model, self._clip_processor = clip.load("ViT-B/32", device=device)
            self._use_clip = True
        except (ImportError, Exception):
            pass
    
    def available(self) -> bool:
        """Check if video encoding is available."""
        return self._use_clip
    
    def encode(
        self,
        video_source: str,
        metadata: Optional[dict] = None,
        num_frames: int = 5,
        timestamp: Optional[datetime] = None,
    ) -> Optional[ModalityEmbedding]:
        """
        Encode video to 384-dimensional embedding.
        
        Args:
            video_source: File path or URL
            metadata: Optional metadata dict (may contain 'thumbnail')
            num_frames: Number of frames to sample
            timestamp: Optional timestamp for the embedding
        
        Returns:
            ModalityEmbedding or None if unavailable
        """
        if self._use_clip:
            # Try to extract frames and encode
            frames = self._extract_frames(video_source, num_frames)
            if frames:
                embedding = self._encode_frames(frames)
                if embedding is not None:
                    return ModalityEmbedding(
                        modality="video",
                        embedding=embedding,
                        confidence=0.8,
                        timestamp=timestamp or datetime.now(),
                    )
        
        # Fallback: use thumbnail from metadata
        if metadata and "thumbnail" in metadata:
            embedding = self._encode_thumbnail(metadata["thumbnail"])
            if embedding is not None:
                return ModalityEmbedding(
                    modality="video",
                    embedding=embedding,
                    confidence=0.5,
                    timestamp=timestamp or datetime.now(),
                )
        
        return None
    
    def _extract_frames(self, video_source: str, num_frames: int) -> Optional[list]:
        """Extract frames from video file or URL."""
        try:
            import cv2
            
            # Try to open video
            cap = cv2.VideoCapture(video_source)
            if not cap.isOpened():
                return None
            
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if total_frames <= 0:
                return None
            
            # Sample frames evenly
            frame_indices = np.linspace(0, total_frames - 1, num_frames, dtype=int)
            frames = []
            
            for idx in frame_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ret, frame = cap.read()
                if ret:
                    frames.append(frame)
            
            cap.release()
            return frames if frames else None
        except (ImportError, Exception):
            return None
    
    def _encode_frames(self, frames: list) -> Optional[np.ndarray]:
        """Encode list of frames using CLIP."""
        if not self._use_clip or not self._clip_model:
            return None
        
        try:
            from PIL import Image
            import torch
            
            embeddings = []
            
            for frame in frames:
                # Convert BGR to RGB for PIL
                frame_rgb = frame[:, :, ::-1]
                img = Image.fromarray(frame_rgb)
                
                # Process and encode
                img_tensor = self._clip_processor(images=img, return_tensors="pt")
                with torch.no_grad():
                    img_features = self._clip_model.encode_image(img_tensor["pixel_values"])
                
                embeddings.append(img_features.cpu().numpy().flatten())
            
            # Average embeddings across frames
            avg_embedding = np.mean(embeddings, axis=0).astype(np.float32)
            
            # Project to 384-dim
            embedding_384 = self._project_to_384(avg_embedding)
            return embedding_384
        except Exception:
            return None
    
    def _encode_thumbnail(self, thumbnail_path: str) -> Optional[np.ndarray]:
        """Encode a single thumbnail image using CLIP."""
        if not self._use_clip or not self._clip_model:
            return None
        
        try:
            from PIL import Image
            import torch
            
            img = Image.open(thumbnail_path)
            img_tensor = self._clip_processor(images=img, return_tensors="pt")
            
            with torch.no_grad():
                img_features = self._clip_model.encode_image(img_tensor["pixel_values"])
            
            # Project to 384-dim
            embedding = img_features.cpu().numpy().flatten()
            return self._project_to_384(embedding)
        except Exception:
            return None
    
    def _project_to_384(self, embedding: np.ndarray) -> np.ndarray:
        """Project embedding to 384 dimensions."""
        embedding = embedding.astype(np.float32)
        
        if len(embedding) == 384:
            return embedding
        elif len(embedding) < 384:
            # Pad with zeros
            return np.pad(embedding, (0, 384 - len(embedding)))
        else:
            # Truncate
            return embedding[:384]
