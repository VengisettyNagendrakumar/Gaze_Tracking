

import sys, os, time, logging, threading
from dataclasses import dataclass, field
from typing import Optional, Any, List

import numpy as np

logger = logging.getLogger(__name__)

# Module paths 
_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_ROOT, "GazeTracking"))
sys.path.insert(0, os.path.join(_ROOT, "Audio_monitoring"))
sys.path.insert(0, os.path.join(_ROOT, "Face_verification"))
# sys.path.insert(0, os.path.join(_ROOT, "Face_detection"))


# Shared result for one processed frame 

@dataclass
class FrameResult:
    timestamp:        float = 0.0

    # Gaze output (your module)
    gaze_event:       Optional[dict] = None
    gaze_state:       str = "unknown"
    gaze_ms:          float = 0.0

    # Audio output 
    audio_events:     List[dict] = field(default_factory=list)

    # Face detection output 
    detection_result: Any = None
    detect_ms:        float = 0.0

    # Face verification output 
    verify_result:    Any = None
    verify_ms:        float = 0.0

    errors:           List[str] = field(default_factory=list)


#Main coordinator 

class FrameProcessor:
    """
    Runs all AI modules for one student exam session.

    - Gaze + Face modules: per-frame (called every 500ms)
    - Audio: continuous background thread (started once, runs until stop())
    """

    def __init__(self, student_id: str):
        self.student_id      = student_id
        self._gaze_tracker   = None
        self._audio_monitor  = None
        self._started        = False

    def start(self):
        if self._started:
            return

        # Gaze Tracking 
        from GazeTracking.gaze_tracker import GazeTracker
        self._gaze_tracker = GazeTracker(self.student_id)
        logger.info("GazeTracker ready")

        #Audio Monitoring 
        # Runs in its own background thread automatically.
        # Call get_all_events() to drain events each second.
        from Audio_monitoring.audio_monitor import AudioMonitor
        self._audio_monitor = AudioMonitor(self.student_id)
        self._audio_monitor.start()
        logger.info("AudioMonitor ready")

        # Face Detection — uncomment when ready 
        # from face_detector import FaceDetector
        # self._detector = FaceDetector()
        # logger.info("FaceDetector ready")

        # Face Verification 
        # from verification import verify
        # self._verify_fn = verify
        # logger.info("FaceVerification ready")

        self._started = True
        logger.info("FrameProcessor started for student=%s", self.student_id)

    def process(self,
                frame_bgr: np.ndarray,
                face_crop: Optional[np.ndarray] = None) -> FrameResult:
        """
        Process one camera frame through all vision modules in parallel.
        Also drains any pending audio events from the background thread.

        Call at 2 FPS (every 500ms).

        Args:
            frame_bgr:  Full BGR frame from camera
            face_crop:  Cropped face (from friend 1's detector)

        Returns:
            FrameResult with all outputs.
        """
        if not self._started:
            self.start()

        result  = FrameResult(timestamp=time.time())
        threads = []
        lock    = threading.Lock()

        # Thread: Gaze 
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

        # Face Detection
       
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

        #Thread: Face Verification
        # Uncomment when friend 2 is ready:
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

        #Run all vision threads 
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=2.0)
        for t in threads:
            if t.is_alive():
                logger.warning("Thread '%s' timed out", t.name)

        # Drain audio events (non-blocking) 
        # Audio runs in its own background thread.
        # We just collect whatever events it has ready.
        if self._audio_monitor:
            result.audio_events = self._audio_monitor.get_all_events()

        logger.debug(
            "Frame done | gaze=%.1fms  detect=%.1fms  verify=%.1fms  audio_events=%d",
            result.gaze_ms, result.detect_ms, result.verify_ms,
            len(result.audio_events),
        )
        return result

    def stop(self) -> dict:
        """
        Stop all modules. Call when exam session ends.
        Returns session summary.
        """
        summary = {"student_id": self.student_id}

        if self._gaze_tracker:
            gaze_summary = self._gaze_tracker.end_session()
            summary["gaze"] = gaze_summary
            logger.info("Gaze summary: %s", gaze_summary)

        if self._audio_monitor:
            audio_summary = self._audio_monitor.stop()
            summary["audio"] = audio_summary
            logger.info("Audio summary: %s", audio_summary)

        try:
            from GazeTracking.gaze_tracker import shutdown
            shutdown()
        except Exception:
            pass

        self._started = False
        logger.info("FrameProcessor stopped for student=%s", self.student_id)
        return summary