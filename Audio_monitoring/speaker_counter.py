
# import logging
# import numpy as np
# from dataclasses import dataclass
# from typing import List, Optional
# from collections import deque

# from config import (
#     SAMPLE_RATE,
#     SPEAKER_SIMILARITY_THRESHOLD,
#     SPEAKER_CHECK_WINDOW_SEC,
#     MIN_VOICE_RATIO,
#     STATE_MULTIPLE_SPEAKERS,
#     STATE_SPEECH_NORMAL,
# )

# logger = logging.getLogger(__name__)


# @dataclass
# class SpeakerResult:
#     multiple_speakers: bool    # True = more than one speaker detected
#     num_speakers:      int     # estimated number of speakers (1 or 2+)
#     confidence:        float   # how confident (0.0–1.0)
#     similarity:        float   # embedding cosine similarity between segments
#     state:             str     # STATE_MULTIPLE_SPEAKERS or STATE_SPEECH_NORMAL


# class SpeakerCounter:
#     """
#     Buffers incoming audio and periodically checks for multiple speakers.
#     Call update() with each voice-active chunk.
#     Returns SpeakerResult when enough audio is buffered for a check.
#     Returns None otherwise (still collecting).
#     """

#     def __init__(self):
#         self._encoder      = None
#         self._loaded       = False
#         self._buffer:  List[np.ndarray] = []
#         self._buffer_sec   = 0.0
#         self._chunk_sec    = 0.032   # 32ms per chunk (matches CHUNK_MS in config)

#     def _load(self):
#         if self._loaded:
#             return
#         from models.speaker_model import get_speaker_encoder
#         self._encoder = get_speaker_encoder()
#         self._loaded  = True

#     def _load(self):
#         if self._loaded:
#             return
#         from models.speaker_model import get_speaker_encoder
#         self._encoder = get_speaker_encoder()
#         self._loaded  = True

#     def update(self, chunk_int16: np.ndarray,
#                is_voice: bool) -> Optional[SpeakerResult]:
#         """
#         Add a chunk to the buffer. Returns SpeakerResult when
#         SPEAKER_CHECK_WINDOW_SEC of voice audio is accumulated,
#         then resets the buffer.

#         Args:
#             chunk_int16: 30ms int16 audio chunk
#             is_voice:    True if VAD detected speech in this chunk

#         Returns:
#             SpeakerResult if check was performed, else None
#         """
#         if is_voice:
#             self._buffer.append(chunk_int16)
#             self._buffer_sec += self._chunk_sec

#         if self._buffer_sec >= SPEAKER_CHECK_WINDOW_SEC:
#             result = self._check_speakers()
#             self._buffer     = []
#             self._buffer_sec = 0.0
#             return result

#         return None

#     def _check_speakers(self) -> SpeakerResult:
#         """
#         Check if multiple speakers are present in the buffered audio.
#         """
#         self._load()

#         audio = np.concatenate(self._buffer).astype(np.float32) / 32768.0
#         total_samples = len(audio)

#         if total_samples < SAMPLE_RATE:
#             # Not enough audio — assume single speaker
#             return SpeakerResult(
#                 multiple_speakers=False,
#                 num_speakers=1,
#                 confidence=0.5,
#                 similarity=1.0,
#                 state=STATE_SPEECH_NORMAL,
#             )

#         # ── Split into two halves ─────────────────────────────
#         # Compare first half vs second half embeddings.
#         # If same speaker: high similarity.
#         # If different speakers talked in each half: low similarity.
#         mid   = total_samples // 2
#         seg_a = audio[:mid]
#         seg_b = audio[mid:]

#         try:
#             emb_a = self._encoder.embed_utterance(seg_a)
#             emb_b = self._encoder.embed_utterance(seg_b)

#             similarity = float(np.dot(emb_a, emb_b) /
#                                (np.linalg.norm(emb_a) * np.linalg.norm(emb_b) + 1e-8))

#             multiple = similarity < SPEAKER_SIMILARITY_THRESHOLD
#             n_speakers = 2 if multiple else 1

#             # Confidence: how far from threshold
#             confidence = abs(similarity - SPEAKER_SIMILARITY_THRESHOLD) / SPEAKER_SIMILARITY_THRESHOLD
#             confidence = float(np.clip(confidence, 0.0, 1.0))

#             state = STATE_MULTIPLE_SPEAKERS if multiple else STATE_SPEECH_NORMAL

#             logger.info(
#                 "Speaker check: similarity=%.3f  threshold=%.2f  multiple=%s",
#                 similarity, SPEAKER_SIMILARITY_THRESHOLD, multiple
#             )

#         except Exception as e:
#             logger.warning("Speaker embedding failed: %s", e)
#             similarity = 1.0
#             multiple   = False
#             n_speakers = 1
#             confidence = 0.0
#             state      = STATE_SPEECH_NORMAL

#         return SpeakerResult(
#             multiple_speakers = multiple,
#             num_speakers      = n_speakers,
#             confidence        = confidence,
#             similarity        = similarity,
#             state             = state,
#         )

#     def reset(self):
#         self._buffer     = []
#         self._buffer_sec = 0.0





import logging
import numpy as np
from dataclasses import dataclass
from typing import List, Optional
from collections import deque

from config import (
    SAMPLE_RATE,
    SPEAKER_SIMILARITY_THRESHOLD,
    SPEAKER_CHECK_WINDOW_SEC,
    MIN_VOICE_RATIO,
    STATE_MULTIPLE_SPEAKERS,
    STATE_SPEECH_NORMAL,
)

logger = logging.getLogger(__name__)


@dataclass
class SpeakerResult:
    multiple_speakers: bool    # True = more than one speaker detected
    num_speakers:      int     # estimated number of speakers (1 or 2+)
    confidence:        float   # how confident (0.0–1.0)
    similarity:        float   # embedding cosine similarity between segments
    state:             str     # STATE_MULTIPLE_SPEAKERS or STATE_SPEECH_NORMAL


class SpeakerCounter:
    """
    Buffers incoming audio and periodically checks for multiple speakers.
    Call update() with each voice-active chunk.
    Returns SpeakerResult when enough audio is buffered for a check.
    Returns None otherwise (still collecting).
    """

    def __init__(self):
        self._encoder      = None
        self._loaded       = False
        self._buffer:  List[np.ndarray] = []
        self._buffer_sec   = 0.0
        self._chunk_sec    = 0.032   # 32ms per chunk (matches CHUNK_MS in config)

    def _load(self):
        if self._loaded:
            return
        from models.speaker_model import get_speaker_encoder
        self._encoder = get_speaker_encoder()
        self._loaded  = True

    def _load(self):
        if self._loaded:
            return
        from models.speaker_model import get_speaker_encoder
        self._encoder = get_speaker_encoder()
        self._loaded  = True

    def update(self, chunk_int16: np.ndarray,
               is_voice: bool) -> Optional[SpeakerResult]:
        """
        Add a chunk to the buffer. Returns SpeakerResult when
        SPEAKER_CHECK_WINDOW_SEC of voice audio is accumulated,
        then resets the buffer.

        Args:
            chunk_int16: 30ms int16 audio chunk
            is_voice:    True if VAD detected speech in this chunk

        Returns:
            SpeakerResult if check was performed, else None
        """
        if is_voice:
            self._buffer.append(chunk_int16)
            self._buffer_sec += self._chunk_sec

        if self._buffer_sec >= SPEAKER_CHECK_WINDOW_SEC:
            result           = self._check_speakers()
            self._buffer     = []
            self._buffer_sec = 0.0   # hard reset — no carryover
            return result

        return None
    def _check_speakers(self) -> SpeakerResult:
        """
        Check if multiple speakers are present in the buffered audio.
        """
        self._load()

        audio = np.concatenate(self._buffer).astype(np.float32) / 32768.0
        total_samples = len(audio)

        if total_samples < SAMPLE_RATE:
            # Not enough audio — assume single speaker
            return SpeakerResult(
                multiple_speakers=False,
                num_speakers=1,
                confidence=0.5,
                similarity=1.0,
                state=STATE_SPEECH_NORMAL,
            )

        # ── Split into two halves ─────────────────────────────
        # Compare first half vs second half embeddings.
        # If same speaker: high similarity.
        # If different speakers talked in each half: low similarity.
        mid   = total_samples // 2
        seg_a = audio[:mid]
        seg_b = audio[mid:]

        try:
            emb_a = self._encoder.embed_utterance(seg_a)
            emb_b = self._encoder.embed_utterance(seg_b)

            similarity = float(np.dot(emb_a, emb_b) /
                               (np.linalg.norm(emb_a) * np.linalg.norm(emb_b) + 1e-8))

            multiple = similarity < SPEAKER_SIMILARITY_THRESHOLD
            n_speakers = 2 if multiple else 1

            # Confidence: how far from threshold
            confidence = abs(similarity - SPEAKER_SIMILARITY_THRESHOLD) / SPEAKER_SIMILARITY_THRESHOLD
            confidence = float(np.clip(confidence, 0.0, 1.0))

            state = STATE_MULTIPLE_SPEAKERS if multiple else STATE_SPEECH_NORMAL

            logger.info(
                "Speaker check: similarity=%.3f  threshold=%.2f  multiple=%s",
                similarity, SPEAKER_SIMILARITY_THRESHOLD, multiple
            )

        except Exception as e:
            logger.warning("Speaker embedding failed: %s", e)
            similarity = 1.0
            multiple   = False
            n_speakers = 1
            confidence = 0.0
            state      = STATE_SPEECH_NORMAL

        return SpeakerResult(
            multiple_speakers = multiple,
            num_speakers      = n_speakers,
            confidence        = confidence,
            similarity        = similarity,
            state             = state,
        )

    def reset(self):
        self._buffer     = []
        self._buffer_sec = 0.0