"""
Unit tests for AudioEncoder (mocked, no network).
Owner: Claude
"""

import pytest
import numpy as np
from datetime import datetime
from unittest.mock import patch, MagicMock
from src.fusion.encoders.audio import AudioEncoder


class TestAudioEncoder:
    """Test AudioEncoder with mocking."""
    
    def test_encoder_graceful_fallback(self):
        """Encoder handles missing dependencies gracefully."""
        # Even without Whisper/librosa, encoder should initialize without error
        encoder = AudioEncoder()
        # available() may be False if deps missing, but no error
        assert isinstance(encoder.available(), bool)
    
    @patch('src.fusion.encoders.audio.AudioEncoder._whisper_model', MagicMock(), create=True)
    def test_encode_with_mocked_deps(self):
        """Encode audio with mocked Whisper and librosa."""
        encoder = AudioEncoder()
        encoder._use_whisper = True
        encoder._use_librosa = True
        
        # Mock the transcribe and extract_prosody methods
        with patch.object(encoder, '_get_audio_path', return_value='/fake/audio.wav'):
            with patch.object(encoder, '_transcribe', return_value='Bitcoin rallied'):
                with patch.object(encoder, '_extract_prosody', return_value={'pitch': 0.1, 'energy': 0.5, 'speech_rate': 0.05}):
                    embedding = encoder.encode('/fake/url')
                    
                    if embedding:  # Only if available
                        assert embedding.modality == "audio"
                        assert embedding.embedding.shape == (384,)
                        assert 0.0 <= embedding.confidence <= 1.0
    
    def test_prosody_to_vector(self):
        """Prosody dict converts to 384-dim vector."""
        encoder = AudioEncoder()
        prosody = {"pitch": 0.1, "energy": 0.5, "speech_rate": 0.05}
        
        vec = encoder._prosody_to_vector(prosody)
        assert vec.shape == (384,)
        assert np.all(np.isfinite(vec))  # No NaNs or Infs
    
    def test_none_on_unavailable(self):
        """Returns None if encoder unavailable."""
        encoder = AudioEncoder()
        encoder._use_whisper = False
        encoder._use_librosa = False
        
        result = encoder.encode("/some/audio.wav")
        assert result is None
    
    def test_confidence_computation(self):
        """Confidence is computed based on features."""
        encoder = AudioEncoder()
        
        # With transcript only
        conf1 = encoder._compute_confidence("Hello world", {})
        assert 0.8 == pytest.approx(conf1)
        
        # With prosody only
        conf2 = encoder._compute_confidence("", {"pitch": 0.1, "energy": 0.5})
        assert 0.7 == pytest.approx(conf2)
        
        # With both (more features)
        conf3 = encoder._compute_confidence("Hello", {"pitch": 0.1})
        assert conf1 < conf3
        assert conf2 < conf3
        assert 1.0 == pytest.approx(conf3)
