"""
Audio Encoder — Whisper transcription + prosody features.
Owner: Claude

Graceful fallback: returns None if dependencies unavailable.
Downloads audio from YouTube/TikTok URLs via yt-dlp.
"""

import numpy as np
from typing import Optional
from datetime import datetime

from ..types import ModalityEmbedding


class AudioEncoder:
    """Encode audio to 384-dimensional embeddings via Whisper + prosody."""
    
    def __init__(self):
        """Initialize with optional Whisper and librosa."""
        self._whisper_model = None
        self._use_whisper = False
        self._use_librosa = False
        self._try_load_whisper()
        self._try_load_librosa()
    
    def _try_load_whisper(self) -> None:
        """Try to load Whisper (tiny, 39MB)."""
        try:
            import whisper
            self._whisper_model = whisper.load_model("tiny")
            self._use_whisper = True
        except (ImportError, Exception):
            pass
    
    def _try_load_librosa(self) -> None:
        """Try to load librosa for prosody."""
        try:
            import librosa
            self._use_librosa = True
        except ImportError:
            pass
    
    def available(self) -> bool:
        """Check if audio encoding is available."""
        return self._use_whisper or self._use_librosa
    
    def encode(
        self,
        audio_source: str,
        timestamp: Optional[datetime] = None,
    ) -> Optional[ModalityEmbedding]:
        """
        Encode audio to 384-dimensional embedding.
        
        Args:
            audio_source: File path, URL, or raw audio data
            timestamp: Optional timestamp for the embedding
        
        Returns:
            ModalityEmbedding or None if unavailable
        """
        if not self.available():
            return None
        
        try:
            # Download audio from URL if needed
            audio_path = self._get_audio_path(audio_source)
            if not audio_path:
                return None
            
            # Extract transcription and prosody features
            transcript = self._transcribe(audio_path)
            prosody_features = self._extract_prosody(audio_path)
            
            # Combine into 384-dim embedding
            embedding = self._combine_features(transcript, prosody_features)
            
            return ModalityEmbedding(
                modality="audio",
                embedding=embedding,
                confidence=self._compute_confidence(transcript, prosody_features),
                timestamp=timestamp or datetime.now(),
            )
        except Exception:
            return None
    
    def _get_audio_path(self, source: str) -> Optional[str]:
        """Get local audio path, downloading from URL if needed."""
        # If local file, return path
        try:
            import os
            if os.path.isfile(source):
                return source
        except:
            pass
        
        # Try to download from URL
        if source.startswith(("http://", "https://")):
            try:
                import yt_dlp
                import tempfile
                
                temp_dir = tempfile.gettempdir()
                ydl_opts = {
                    "format": "m4a/bestaudio/best",
                    "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "m4a"}],
                    "outtmpl": f"{temp_dir}/%(title)s",
                    "quiet": True,
                    "no_warnings": True,
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(source, download=True)
                    # Try to find the audio file
                    for ext in [".m4a", ".mp3", ".wav"]:
                        path = f"{temp_dir}/{info['title']}{ext}"
                        try:
                            import os
                            if os.path.isfile(path):
                                return path
                        except:
                            pass
            except (ImportError, Exception):
                pass
        
        return None
    
    def _transcribe(self, audio_path: str) -> str:
        """Transcribe audio to text using Whisper."""
        if not self._use_whisper or not self._whisper_model:
            return ""
        
        try:
            result = self._whisper_model.transcribe(audio_path, language="en", fp16=False)
            return result.get("text", "").strip()
        except Exception:
            return ""
    
    def _extract_prosody(self, audio_path: str) -> dict:
        """Extract prosody features: pitch, energy, speech rate."""
        prosody = {"pitch": [], "energy": [], "speech_rate": 0.0}
        
        if not self._use_librosa:
            return prosody
        
        try:
            import librosa
            
            y, sr = librosa.load(audio_path, sr=None)
            
            # Pitch estimation (using zero-crossing rate as proxy)
            zcr = librosa.feature.zero_crossing_rate(y)[0]
            prosody["pitch"] = float(np.mean(zcr))
            
            # Energy (RMS)
            rms = librosa.feature.rms(y=y)[0]
            prosody["energy"] = float(np.mean(rms))
            
            # Speech rate (using spectral centroid as proxy)
            spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
            prosody["speech_rate"] = float(np.mean(spectral_centroids) / sr)
            
        except Exception:
            pass
        
        return prosody
    
    def _combine_features(self, transcript: str, prosody: dict) -> np.ndarray:
        """Combine transcription and prosody into 384-dim embedding."""
        embedding = np.zeros(384, dtype=np.float32)
        
        # Use transcript to seed embedding (if we have text encoder available)
        if transcript:
            try:
                from .text import TextEncoder
                text_encoder = TextEncoder()
                text_emb = text_encoder.encode(transcript).embedding
                # Weight transcript embedding (50%)
                embedding[:384] = text_emb * 0.5
            except Exception:
                pass
        
        # Add prosody features (50%)
        prosody_vec = self._prosody_to_vector(prosody)
        embedding += prosody_vec * 0.5
        
        # Normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        
        return embedding
    
    def _prosody_to_vector(self, prosody: dict) -> np.ndarray:
        """Convert prosody dict to 384-dim vector."""
        vec = np.zeros(384, dtype=np.float32)
        
        # Repeat prosody features across dimensions
        pitch = prosody.get("pitch", 0.0)
        energy = prosody.get("energy", 0.0)
        speech_rate = prosody.get("speech_rate", 0.0)
        
        # Map to 384 dimensions
        vec[0:128] = pitch
        vec[128:256] = energy
        vec[256:384] = speech_rate
        
        # Normalize to [-1, 1]
        vec = np.clip(vec / 100.0, -1.0, 1.0)
        
        return vec
    
    def _compute_confidence(self, transcript: str, prosody: dict) -> float:
        """Compute confidence based on available features."""
        confidence = 0.5  # Base confidence
        
        if transcript:
            confidence += 0.3  # +30% for transcription
        
        if prosody.get("pitch") or prosody.get("energy"):
            confidence += 0.2  # +20% for prosody
        
        return min(1.0, confidence)
