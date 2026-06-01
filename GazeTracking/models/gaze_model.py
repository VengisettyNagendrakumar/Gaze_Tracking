
#  MediaPipe FaceMesh singleton.
#  Returns the same FaceMesh instance across the whole app.
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import (
    MAX_NUM_FACES,
    DETECTION_CONFIDENCE,
    TRACKING_CONFIDENCE,
    REFINE_LANDMARKS,
)

logger = logging.getLogger(__name__)

_face_mesh = None


def get_face_mesh():
    """
    Returns a cached MediaPipe FaceMesh instance.
    Downloads model weights on first call (~4 MB, automatic).
    Thread-safe for read-only inference.
    """
    global _face_mesh
    if _face_mesh is not None:
        return _face_mesh

    try:
        import mediapipe as mp
        _face_mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=MAX_NUM_FACES,
            refine_landmarks=REFINE_LANDMARKS,
            min_detection_confidence=0.3,   # lower = detects more, fewer misses
            min_tracking_confidence=0.3,    # lower = holds tracking better at 2 FPS
        )
        logger.info("MediaPipe FaceMesh loaded (refine_landmarks=%s)", REFINE_LANDMARKS)
    except ImportError:
        raise ImportError(
            "MediaPipe not installed. Run: pip install mediapipe"
        )

    return _face_mesh


def close_face_mesh():
    """Release MediaPipe resources. Call when exam session ends."""
    global _face_mesh
    if _face_mesh is not None:
        _face_mesh.close()
        _face_mesh = None
        logger.info("MediaPipe FaceMesh released.")