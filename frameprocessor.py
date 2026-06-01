
#  Each AI module runs in its own thread on the same frame.
#  
#  Who owns what:
#    Gaze Tracking    → your module   (GazeTracking/)
#    Face Detection   → friend 1      (their module)
#    Face Verification→ friend 2      (their module)
#
#  This file is the ONLY integration point between all 3.
#  Each person only edits their own section (marked below).

import sys, os, time, logging, threading
from dataclasses import dataclass, field
from typing import Optional, Any

import numpy as np

logger = logging.getLogger(__name__)

# Module paths 
_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_ROOT, "GazeTracking"))
sys.path.insert(0, os.path.join(_ROOT, "Face_verification"))
# sys.path.insert(0, os.path.join(_ROOT, "Face_detection"))


#Shared result for one frame
@dataclass
class FrameResult:
    timestamp:        float = 0.0
    gaze_event:       Optional[dict] = None   # → Risk Engine
    gaze_state:       str = "unknown"
    verify_result:    Any = None              # → Risk Engine
    detection_result: Any = None              # → Risk Engine
    gaze_ms:          float = 0.0
    verify_ms:        float = 0.0
    detect_ms:        float = 0.0
    errors:           list = field(default_factory=list)



#  FrameProcessor

class FrameProcessor:
    """
    Runs all 3 AI modules in parallel on the same camera frame.
    One instance per student session.
    """

    def __init__(self, student_id: str):
        self.student_id    = student_id
        self._gaze_tracker = None
        self._started      = False

    def start(self):
        if self._started:
            return

        #YOUR MODULE (Gaze) 
        from GazeTracking.gaze_tracker import GazeTracker
        self._gaze_tracker = GazeTracker(self.student_id)
        logger.info("GazeTracker ready")

        # ─(Detection) — uncomment when ready ───────
        # from face_detector import FaceDetector
        # self._detector = FaceDetector()

        # ──  (Verification) — uncomment when ready ────
        # from verification import verify
        # self._verify_fn = verify

        self._started = True
        logger.info("FrameProcessor started for student=%s", self.student_id)

    def process(self,
                frame_bgr: np.ndarray,
                face_crop: Optional[np.ndarray] = None) -> FrameResult:
        """
        Process one frame through all modules simultaneously.

        Args:
            frame_bgr:  Full BGR frame from camera
            face_crop:  Cropped face BGR array (for verification).
                        Pass this when friend 1's detector gives a crop.

        Returns:
            FrameResult — all outputs filled in once all threads finish.
        """
        if not self._started:
            self.start()

        result  = FrameResult(timestamp=time.time())
        threads = []
        lock    = threading.Lock()

        # ── Thread: Gaze
        def _gaze():
            t0 = time.perf_counter()
            try:
                event = self._gaze_tracker.process_frame(frame_bgr)
                g     = self._gaze_tracker.last_gaze
                with lock:
                    result.gaze_event = event
                    result.gaze_state = g.state if g else "unknown"
                    result.gaze_ms    = (time.perf_counter() - t0) * 1000
            except Exception as e:
                with lock:
                    result.errors.append(f"gaze: {e}")
                logger.error("Gaze error: %s", e, exc_info=True)

        threads.append(threading.Thread(target=_gaze, name="gaze", daemon=True))

        #Thread: Detection
        # Uncomment this entire block when friend 1 is ready:
        #
        # def _detect():
        #     t0 = time.perf_counter()
        #     try:
        #         dr = self._detector.detect(frame_bgr)
        #         with lock:
        #             result.detection_result = dr
        #             result.detect_ms = (time.perf_counter() - t0) * 1000
        #     except Exception as e:
        #         with lock:
        #             result.errors.append(f"detect: {e}")
        #         logger.error("Detection error: %s", e, exc_info=True)
        #
        # threads.append(threading.Thread(target=_detect, name="detect", daemon=True))

        # Thread: Verification (FRIEND 2) 
        # Uncomment this entire block when friend 2 is ready:
        #
        # def _verify():
        #     t0 = time.perf_counter()
        #     try:
        #         if face_crop is not None:
        #             vr = self._verify_fn(self.student_id, face_crop)
        #             with lock:
        #                 result.verify_result = vr
        #                 result.verify_ms = (time.perf_counter() - t0) * 1000
        #     except Exception as e:
        #         with lock:
        #             result.errors.append(f"verify: {e}")
        #         logger.error("Verification error: %s", e, exc_info=True)
        #
        # threads.append(threading.Thread(target=_verify, name="verify", daemon=True))

        # Run all threads and wait 
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=2.0)

        for t in threads:
            if t.is_alive():
                logger.warning("Thread '%s' timed out", t.name)

        logger.debug("Frame done | gaze=%.1fms  verify=%.1fms  detect=%.1fms",
                     result.gaze_ms, result.verify_ms, result.detect_ms)
        return result

    def stop(self):
        """Call when exam session ends."""
        if self._gaze_tracker:
            summary = self._gaze_tracker.end_session()
            logger.info("Gaze summary: %s", summary)
        try:
            from GazeTracking.gaze_tracker import shutdown
            shutdown()
        except Exception:
            pass
        self._started = False
        logger.info("FrameProcessor stopped for student=%s", self.student_id)