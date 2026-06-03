
import logging
import numpy as np
from dataclasses import dataclass
from typing import Optional

from config import (
    SAMPLE_RATE, VAD_THRESHOLD,
    STATE_SILENT, STATE_SPEECH_NORMAL, STATE_NOISE_LOUD,
    STATE_WHISPERING, STATE_BACKGROUND_AUDIO,
)

logger = logging.getLogger(__name__)

# Calibration: measure silence for this many seconds on startup
CALIBRATION_SEC    = 3.0
CALIBRATION_CHUNKS = int(CALIBRATION_SEC * 1000 / 32)   # ~93 chunks

WHISPER_MULT = 2.5
SPEECH_MULT  = 5.0
LOUD_MULT    = 40.0   

# Minimum absolute RMS values — prevents calibrating to 0
MIN_SILENCE_RMS  = 20
MIN_SPEECH_RMS   = 200


@dataclass
class VADResult:
    is_speech:   bool
    vad_score:   float
    rms:         float
    noise_level: str
    state:       str


class VADDetector:

    def __init__(self):
        self._model      = None
        self._loaded     = False
        self._last_score = 0.0

        # Smoothing history
        self._rms_history = []
        self._vad_history = []
        self._SMOOTH = 8

        # Calibration state
        self._calibrated      = False
        self._calib_samples   = []
        self._silence_rms     = 50.0    # default before calibration

        # Thresholds (set after calibration)
        self._thresh_whisper  = 150
        self._thresh_speech   = 280
        self._thresh_loud     = 900

    def _load(self):
        if self._loaded:
            return
        from models.vad_model import get_vad_model
        self._model, _ = get_vad_model()
        self._loaded = True

    def _calibrate(self, rms: float):
        """Collect silence samples and compute thresholds."""
        self._calib_samples.append(rms)
        if len(self._calib_samples) >= CALIBRATION_CHUNKS:
            silence = float(np.percentile(self._calib_samples, 20))
            
            silence = max(min(silence, 100), MIN_SILENCE_RMS)

            self._silence_rms    = silence
            self._thresh_whisper = max(silence * WHISPER_MULT, 80)
            self._thresh_speech  = max(silence * SPEECH_MULT,  MIN_SPEECH_RMS)
            self._thresh_loud    = silence * LOUD_MULT
            self._calibrated     = True

            if silence > 100:
                logger.warning(
                    "Calibration may be inaccurate — detected sound during "
                    "silence window (rms=%.0f). Stay completely silent during "
                    "the 3-second calibration.", silence)

            logger.info(
                "Mic calibrated | silence_rms=%.0f  "
                "whisper>%.0f  speech>%.0f  loud>%.0f",
                silence,
                self._thresh_whisper,
                self._thresh_speech,
                self._thresh_loud,
            )

    def process_chunk(self, chunk_int16: np.ndarray) -> VADResult:
        self._load()

        # Smoothed RMS 
        raw_rms = float(np.sqrt(np.mean(chunk_int16.astype(np.float32) ** 2)))
        self._rms_history.append(raw_rms)
        if len(self._rms_history) > self._SMOOTH:
            self._rms_history.pop(0)
        rms = float(np.mean(self._rms_history))

        #Calibration (first CALIBRATION_SEC seconds) 
        if not self._calibrated:
            self._calibrate(raw_rms)
            # During calibration always return silent
            return VADResult(is_speech=False, vad_score=0.0,
                             rms=rms, noise_level="silent",
                             state=STATE_SILENT)

        # Silero VAD (smoothed) 
        raw_vad = 0.0
        try:
            import torch
            audio_f32 = chunk_int16.astype(np.float32) / 32768.0
            tensor    = torch.from_numpy(audio_f32)
            raw_vad   = float(self._model(tensor, SAMPLE_RATE).item())
        except Exception as e:
            logger.debug("VAD error: %s", e)

        self._vad_history.append(raw_vad)
        if len(self._vad_history) > self._SMOOTH:
            self._vad_history.pop(0)
        vad_score        = float(np.mean(self._vad_history))
        self._last_score = vad_score

        # Noise level label 
        if rms < self._thresh_whisper:
            noise_level = "silent"
        elif rms < self._thresh_speech:
            noise_level = "medium"
        else:
            noise_level = "loud"

        # Classify 
        is_speech = False

        if rms < self._thresh_whisper:
            # Very low energy — silent or distant background
            if vad_score >= 0.50 and rms > self._silence_rms * 2:
                state = STATE_BACKGROUND_AUDIO
            else:
                state = STATE_SILENT

        elif rms >= self._thresh_loud and vad_score < 0.40:
            # Very high RMS + low VAD = external loud noise (music, TV)
            state = STATE_NOISE_LOUD

        elif vad_score >= VAD_THRESHOLD:
            # Clear speech signal — normal speech regardless of volume
            state     = STATE_SPEECH_NORMAL
            is_speech = True

        elif vad_score >= 0.40:
            # Moderate VAD = whispering
            state     = STATE_WHISPERING
            is_speech = True

        elif rms >= self._thresh_speech and vad_score < 0.25:
            # Medium-high RMS but very low VAD = background noise/music
            state = STATE_BACKGROUND_AUDIO

        else:
            state = STATE_SILENT

        logger.debug("rms=%.0f (thresh: w=%.0f s=%.0f l=%.0f) vad=%.2f → %s",
                     rms, self._thresh_whisper, self._thresh_speech,
                     self._thresh_loud, vad_score, state)

        return VADResult(
            is_speech   = is_speech,
            vad_score   = vad_score,
            rms         = rms,
            noise_level = noise_level,
            state       = state,
        )

    def reset(self):
        self._rms_history   = []
        self._vad_history   = []
        self._calibrated    = False
        self._calib_samples = []
        if self._model and hasattr(self._model, "reset_states"):
            self._model.reset_states()