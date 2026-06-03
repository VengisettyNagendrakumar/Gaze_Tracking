

# import logging
# import queue
# import threading
# import time
# from typing import Optional
# from collections import deque

# from config import (
#     RISK_SCORE_NOISE_LOUD, RISK_SCORE_MULTIPLE_SPEAKERS,
#     RISK_SCORE_WHISPERING, RISK_SCORE_BACKGROUND_AUDIO,
#     STATE_SILENT, STATE_SPEECH_NORMAL,
#     STATE_NOISE_LOUD, STATE_MULTIPLE_SPEAKERS,
#     STATE_WHISPERING, STATE_BACKGROUND_AUDIO,
# )
# from audio_capture   import AudioCapture
# from vad_detector    import VADDetector
# from speaker_counter import SpeakerCounter
# from event_generator import AudioScorer, build_event

# logger = logging.getLogger(__name__)


# class AudioMonitor:

#     def __init__(self, student_id: str, device_index="auto"):
#         self.student_id = student_id
#         self._capture   = AudioCapture(device_index=device_index)
#         self._vad       = VADDetector()
#         self._speakers  = SpeakerCounter()
#         self._scorer    = AudioScorer(student_id)

#         self._event_queue: queue.Queue = queue.Queue(maxsize=100)
#         self._monitor_thread: Optional[threading.Thread] = None
#         self._running    = False
#         self._last_state = STATE_SILENT
#         self._last_rms   = 0.0

#         # Multiple speaker rolling window
#         # Fire when 1 in last 3 checks is True
#         self._multi_window    = deque(maxlen=3)
#         self._MULTI_THRESHOLD = 1

#     def start(self):
#         self._capture.start()
#         logger.info("Loading VAD model before calibration ...")
#         self._vad._load()
#         logger.info("Loading speaker encoder before calibration ...")
#         self._speakers._load()
#         logger.info("All models ready. Starting 3-sec silence calibration ...")
#         self._running = True
#         self._monitor_thread = threading.Thread(
#             target=self._monitor_loop, daemon=True, name="audio_monitor"
#         )
#         self._monitor_thread.start()
#         logger.info("AudioMonitor started for student=%s", self.student_id)

#     def get_event(self) -> Optional[dict]:
#         try:
#             return self._event_queue.get_nowait()
#         except queue.Empty:
#             return None

#     def get_all_events(self) -> list:
#         events = []
#         while True:
#             try:
#                 events.append(self._event_queue.get_nowait())
#             except queue.Empty:
#                 break
#         return events

#     @property
#     def current_state(self) -> str:
#         return self._last_state

#     @property
#     def current_rms(self) -> float:
#         return self._last_rms

#     def stop(self) -> dict:
#         self._running = False
#         self._capture.stop()
#         if self._monitor_thread:
#             self._monitor_thread.join(timeout=2.0)
#         summary = {
#             "student_id":     self.student_id,
#             "violation_rate": self._scorer.violation_rate,
#         }
#         logger.info("AudioMonitor stopped | %s", summary)
#         return summary

#     def _monitor_loop(self):
#         while self._running:
#             try:
#                 chunk = self._capture.read(timeout=0.1)
#                 if chunk is None:
#                     continue

#                 # VAD per chunk
#                 vad = self._vad.process_chunk(chunk)
#                 self._last_rms   = vad.rms
#                 self._last_state = vad.state

#                 # Speaker check (returns result every 3 sec, else None)
#                 speaker_result = self._speakers.update(
#                     chunk_int16=chunk,
#                     is_voice=vad.vad_score >= 0.5,
#                 )

#                 # Handle multiple speaker detection separately
#                 # — fires its own events immediately, not through window scorer
#                 if speaker_result is not None:
#                     self._multi_window.append(
#                         1 if speaker_result.multiple_speakers else 0
#                     )
#                     logger.info(
#                         "Speaker check: similarity=%.3f  multiple=%s  window=%s",
#                         speaker_result.similarity,
#                         speaker_result.multiple_speakers,
#                         list(self._multi_window),
#                     )
#                     if sum(self._multi_window) >= self._MULTI_THRESHOLD:
#                         self._multi_window.clear()
#                         self._fire_event("audio_multiple_speakers",
#                                          RISK_SCORE_MULTIPLE_SPEAKERS,
#                                          "multiple_speakers_detected")
#                         self._fire_event("audio_background_noise",
#                                          0.0,
#                                          "background_noise_detected")

#                 # Window scorer handles: noise_loud, whispering, background_audio
#                 # Maps STATE_BACKGROUND_AUDIO → background_noise event after 5 sec
#                 vad_state = vad.state

#                 # Collapse background_audio → use it in scorer but only
#                 # if rms is above whisper threshold (prevent chunk-level spam
#                 # from being counted — majority vote in 1-sec window handles it)
#                 score = self._scorer.update(vad_state,
#                                             self._risk_for(vad_state),
#                                             self._reason_for(vad_state))
#                 result = build_event(self.student_id, score)
#                 if result:
#                     evts = result if isinstance(result, list) else [result]
#                     for evt in evts:
#                         try:
#                             self._event_queue.put_nowait(evt)
#                         except queue.Full:
#                             pass

#             except Exception as e:
#                 logger.error("Monitor loop error: %s", e, exc_info=True)

#     def _fire_event(self, event_name: str, severity: float, reason: str):
#         evt = {
#             "event":               event_name,
#             "severity":            severity,
#             "timestamp":           time.time(),
#             "student_id":          self.student_id,
#             "audio_state":         event_name,
#             "consecutive_windows": 0,
#             "violations_in_window":0,
#             "risk_reason":         reason,
#         }
#         logger.warning("RISK EVENT  event=%-30s  severity=%.2f  reason=%s",
#                        event_name, severity, reason)
#         try:
#             self._event_queue.put_nowait(evt)
#         except queue.Full:
#             pass

#     def _risk_for(self, state: str) -> float:
#         return {
#             STATE_NOISE_LOUD:       RISK_SCORE_NOISE_LOUD,
#             STATE_WHISPERING:       RISK_SCORE_WHISPERING,
#             STATE_BACKGROUND_AUDIO: RISK_SCORE_BACKGROUND_AUDIO,
#         }.get(state, 0.0)

#     def _reason_for(self, state: str) -> str:
#         return {
#             STATE_NOISE_LOUD:       "loud_background_noise",
#             STATE_WHISPERING:       "whispering_detected",
#             STATE_BACKGROUND_AUDIO: "background_audio_detected",
#         }.get(state, "")




import logging
import queue
import threading
import time
from typing import Optional
from collections import deque

from config import (
    RISK_SCORE_NOISE_LOUD, RISK_SCORE_MULTIPLE_SPEAKERS,
    RISK_SCORE_WHISPERING, RISK_SCORE_BACKGROUND_AUDIO,
    STATE_SILENT, STATE_SPEECH_NORMAL,
    STATE_NOISE_LOUD, STATE_MULTIPLE_SPEAKERS,
    STATE_WHISPERING, STATE_BACKGROUND_AUDIO,
)
from audio_capture   import AudioCapture
from vad_detector    import VADDetector
from speaker_counter import SpeakerCounter
from event_generator import AudioScorer, build_event

logger = logging.getLogger(__name__)


class AudioMonitor:

    def __init__(self, student_id: str, device_index="auto"):
        self.student_id = student_id
        self._capture   = AudioCapture(device_index=device_index)
        self._vad       = VADDetector()
        self._speakers  = SpeakerCounter()
        self._scorer    = AudioScorer(student_id)

        self._event_queue: queue.Queue = queue.Queue(maxsize=100)
        self._monitor_thread: Optional[threading.Thread] = None
        self._running    = False
        self._last_state = STATE_SILENT
        self._last_rms   = 0.0

        # Multiple speaker rolling window
        # Fire when 1 in last 3 checks is True
        self._multi_window    = deque(maxlen=3)
        self._MULTI_THRESHOLD = 1

    def start(self):
        self._capture.start()
        logger.info("Loading VAD model before calibration ...")
        self._vad._load()
        logger.info("Loading speaker encoder before calibration ...")
        self._speakers._load()
        logger.info("All models ready. Starting 3-sec silence calibration ...")
        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, daemon=True, name="audio_monitor"
        )
        self._monitor_thread.start()
        logger.info("AudioMonitor started for student=%s", self.student_id)

    def get_event(self) -> Optional[dict]:
        try:
            return self._event_queue.get_nowait()
        except queue.Empty:
            return None

    def get_all_events(self) -> list:
        events = []
        while True:
            try:
                events.append(self._event_queue.get_nowait())
            except queue.Empty:
                break
        return events

    @property
    def current_state(self) -> str:
        return self._last_state

    @property
    def current_rms(self) -> float:
        return self._last_rms

    def stop(self) -> dict:
        self._running = False
        self._capture.stop()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
        summary = {
            "student_id":     self.student_id,
            "violation_rate": self._scorer.violation_rate,
        }
        logger.info("AudioMonitor stopped | %s", summary)
        return summary

    def _monitor_loop(self):
        while self._running:
            try:
                chunk = self._capture.read(timeout=0.1)
                if chunk is None:
                    continue

                # VAD per chunk
                vad = self._vad.process_chunk(chunk)
                self._last_rms   = vad.rms
                self._last_state = vad.state

                # Speaker check (returns result every 3 sec, else None)
                speaker_result = self._speakers.update(
                    chunk_int16=chunk,
                    is_voice=vad.vad_score >= 0.5,
                )

                # Handle multiple speaker detection separately
                # — fires its own events immediately, not through window scorer
                if speaker_result is not None:
                    self._multi_window.append(
                        1 if speaker_result.multiple_speakers else 0
                    )
                    logger.info(
                        "Speaker check: similarity=%.3f  multiple=%s  window=%s",
                        speaker_result.similarity,
                        speaker_result.multiple_speakers,
                        list(self._multi_window),
                    )
                    if sum(self._multi_window) >= self._MULTI_THRESHOLD:
                        self._multi_window.clear()  # clear BEFORE firing
                        self._fire_event("audio_multiple_speakers",
                                         RISK_SCORE_MULTIPLE_SPEAKERS,
                                         "multiple_speakers_detected")
                        self._fire_event("audio_background_noise",
                                         0.0,
                                         "background_noise_detected")

                # Window scorer handles: noise_loud, whispering, background_audio
                # Maps STATE_BACKGROUND_AUDIO → background_noise event after 5 sec
                vad_state = vad.state

                # Collapse background_audio → use it in scorer but only
                # if rms is above whisper threshold (prevent chunk-level spam
                # from being counted — majority vote in 1-sec window handles it)
                score = self._scorer.update(vad_state,
                                            self._risk_for(vad_state),
                                            self._reason_for(vad_state))
                result = build_event(self.student_id, score)
                if result:
                    evts = result if isinstance(result, list) else [result]
                    for evt in evts:
                        try:
                            self._event_queue.put_nowait(evt)
                        except queue.Full:
                            pass

            except Exception as e:
                logger.error("Monitor loop error: %s", e, exc_info=True)

    def _fire_event(self, event_name: str, severity: float, reason: str):
        evt = {
            "event":               event_name,
            "severity":            severity,
            "timestamp":           time.time(),
            "student_id":          self.student_id,
            "audio_state":         event_name,
            "consecutive_windows": 0,
            "violations_in_window":0,
            "risk_reason":         reason,
        }
        logger.warning("RISK EVENT  event=%-30s  severity=%.2f  reason=%s",
                       event_name, severity, reason)
        try:
            self._event_queue.put_nowait(evt)
        except queue.Full:
            pass

    def _risk_for(self, state: str) -> float:
        return {
            STATE_NOISE_LOUD:       RISK_SCORE_NOISE_LOUD,
            STATE_WHISPERING:       RISK_SCORE_WHISPERING,
            STATE_BACKGROUND_AUDIO: RISK_SCORE_BACKGROUND_AUDIO,
        }.get(state, 0.0)

    def _reason_for(self, state: str) -> str:
        return {
            STATE_NOISE_LOUD:       "loud_background_noise",
            STATE_WHISPERING:       "whispering_detected",
            STATE_BACKGROUND_AUDIO: "background_audio_detected",
        }.get(state, "")