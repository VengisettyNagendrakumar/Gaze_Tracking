
# #  Aggregates 30ms chunks into 1-second windows, then scores.
# #  Returns None until window is complete — callers must handle None.


# import time
# import logging
# from typing import Optional
# from dataclasses import dataclass
# from collections import deque

# from config import (
#     SCORING_WINDOW_SEC, CHUNK_MS,
#     CONSECUTIVE_VIOLATION_WINDOWS,
#     ESCALATION_COUNT, ESCALATION_WINDOW_CHECKS,
#     RISK_SCORE_NOISE_LOUD, RISK_SCORE_MULTIPLE_SPEAKERS,
#     RISK_SCORE_WHISPERING, RISK_SCORE_BACKGROUND_AUDIO,
#     RISK_SCORE_SUSTAINED, RISK_SCORE_ESCALATION,
#     STATE_SILENT, STATE_SPEECH_NORMAL, STATE_NOISE_LOUD,
#     STATE_MULTIPLE_SPEAKERS, STATE_WHISPERING, STATE_BACKGROUND_AUDIO,
# )

# logger = logging.getLogger(__name__)

# _VIOLATION_STATES = {
#     STATE_NOISE_LOUD, STATE_MULTIPLE_SPEAKERS,
#     STATE_WHISPERING, STATE_BACKGROUND_AUDIO,
# }

# _RISK_MAP = {
#     STATE_NOISE_LOUD:        RISK_SCORE_NOISE_LOUD,
#     STATE_MULTIPLE_SPEAKERS: RISK_SCORE_MULTIPLE_SPEAKERS,
#     STATE_WHISPERING:        RISK_SCORE_WHISPERING,
#     STATE_BACKGROUND_AUDIO:  RISK_SCORE_BACKGROUND_AUDIO,
# }

# _REASON_MAP = {
#     STATE_NOISE_LOUD:        "loud_background_noise",
#     STATE_MULTIPLE_SPEAKERS: "multiple_speakers_detected",
#     STATE_WHISPERING:        "whispering_detected",
#     STATE_BACKGROUND_AUDIO:  "background_audio_detected",
# }

# _CHUNKS_PER_WINDOW = max(1, int(SCORING_WINDOW_SEC * 1000 / CHUNK_MS))  # ~31


# @dataclass
# class AudioScore:
#     state:               str
#     risk_score:          float
#     risk_reason:         str
#     consecutive:         int     # consecutive violation windows
#     violations_in_window:int
#     emit_sustained:      bool = False
#     emit_escalation:     bool = False


# class AudioScorer:
#     """
#     Aggregates 30ms chunks into 1-second windows.
#     update() returns AudioScore when a window completes, else None.
#     """

#     def __init__(self, student_id: str):
#         self.student_id = student_id
#         self._window_states: list  = []
#         self._window_count         = 0
#         self._consec               = 0   # consecutive violation windows
#         self._total_windows        = 0
#         self._violation_windows    = 0
#         self._sustained_window: deque = deque(maxlen=ESCALATION_WINDOW_CHECKS)

#     def update(self, state: str, base_risk: float,
#                reason: str) -> Optional[AudioScore]:
#         """
#         Feed one chunk state.
#         Returns AudioScore on window completion (~1 sec), else None.
#         """
#         self._window_states.append(state)
#         self._window_count += 1

#         if self._window_count < _CHUNKS_PER_WINDOW:
#             return None   # window not complete yet

#         # ── Window complete ───────────────────────────────────
#         window_state = max(set(self._window_states),
#                            key=self._window_states.count)
#         self._window_states = []
#         self._window_count  = 0
#         self._total_windows += 1

#         is_violation = window_state in _VIOLATION_STATES
#         if is_violation:
#             self._consec            += 1
#             self._violation_windows += 1
#         else:
#             self._consec = 0

#         emit_sustained  = False
#         emit_escalation = False

#         if self._consec == CONSECUTIVE_VIOLATION_WINDOWS:
#             emit_sustained = True
#             self._sustained_window.append(1)
#             logger.info("[Audio] student=%s SUSTAINED %s (%d sec)",
#                         self.student_id, window_state, self._consec)

#         recent = sum(self._sustained_window)
#         if recent >= ESCALATION_COUNT and emit_sustained:
#             emit_escalation = True
#             logger.warning("[Audio] student=%s ESCALATION — %d violations",
#                            self.student_id, recent)

#         # Risk
#         if emit_escalation:
#             risk = RISK_SCORE_ESCALATION
#         elif emit_sustained:
#             risk = RISK_SCORE_SUSTAINED
#         else:
#             risk = _RISK_MAP.get(window_state, 0.0)

#         return AudioScore(
#             state                = window_state,
#             risk_score           = risk,
#             risk_reason          = _REASON_MAP.get(window_state, ""),
#             consecutive          = self._consec,
#             violations_in_window = recent,
#             emit_sustained       = emit_sustained,
#             emit_escalation      = emit_escalation,
#         )

#     def reset(self):
#         self._window_states          = []
#         self._window_count           = 0
#         self._consec                 = 0
#         self._total_windows          = 0
#         self._violation_windows      = 0
#         self._sustained_window.clear()

#     @property
#     def violation_rate(self) -> float:
#         if self._total_windows == 0:
#             return 0.0
#         return round(self._violation_windows / self._total_windows, 4)


# def build_event(student_id: str,
#                 score: Optional[AudioScore],
#                 force: bool = False) -> Optional[dict]:
#     if score is None:
#         return None

#     should_emit = (
#         force
#         or score.emit_sustained
#         or score.emit_escalation
#         or score.state == STATE_MULTIPLE_SPEAKERS
#     )
#     if not should_emit:
#         return None

#     event = {
#         "event":               _event_name(score),
#         "severity":            round(score.risk_score, 4),
#         "timestamp":           time.time(),
#         "student_id":          student_id,
#         "audio_state":         score.state,
#         "consecutive_windows": score.consecutive,
#         "violations_in_window":score.violations_in_window,
#         "risk_reason":         score.risk_reason,
#     }
#     logger.info("[Event] student=%s  event=%-30s  severity=%.2f",
#                 student_id, event["event"], event["severity"])
#     return event


# def _event_name(score: AudioScore) -> str:
#     if score.emit_escalation:      return "audio_repeated_violation"
#     if score.emit_sustained:       return "audio_sustained_violation"
#     if score.state == STATE_MULTIPLE_SPEAKERS: return "audio_multiple_speakers"
#     if score.state == STATE_NOISE_LOUD:        return "audio_loud_noise"
#     if score.state == STATE_WHISPERING:        return "audio_whispering"
#     if score.state == STATE_BACKGROUND_AUDIO:  return "audio_background_detected"
#     return "audio_violation"

#  Aggregates 30ms chunks into 1-second windows, then scores.
#  Returns None until window is complete — callers must handle None.


import time
import logging
from typing import Optional
from dataclasses import dataclass
from collections import deque

from config import (
    STATE_BACKGROUND_NOISE,
    SCORING_WINDOW_SEC, CHUNK_MS,
    CONSECUTIVE_VIOLATION_WINDOWS,
    ESCALATION_COUNT, ESCALATION_WINDOW_CHECKS,
    RISK_SCORE_NOISE_LOUD, RISK_SCORE_MULTIPLE_SPEAKERS,
    RISK_SCORE_WHISPERING, RISK_SCORE_BACKGROUND_AUDIO,
    RISK_SCORE_SUSTAINED, RISK_SCORE_ESCALATION,
    STATE_SILENT, STATE_SPEECH_NORMAL, STATE_NOISE_LOUD,
    STATE_MULTIPLE_SPEAKERS, STATE_WHISPERING, STATE_BACKGROUND_AUDIO,
)

logger = logging.getLogger(__name__)

_VIOLATION_STATES = {
    STATE_NOISE_LOUD, STATE_MULTIPLE_SPEAKERS,
    STATE_WHISPERING, STATE_BACKGROUND_AUDIO,
    "background_noise",   # unified state from audio_monitor
}

_RISK_MAP = {
    STATE_NOISE_LOUD:        RISK_SCORE_NOISE_LOUD,
    STATE_MULTIPLE_SPEAKERS: RISK_SCORE_MULTIPLE_SPEAKERS,
    STATE_WHISPERING:        RISK_SCORE_WHISPERING,
    STATE_BACKGROUND_AUDIO:  RISK_SCORE_BACKGROUND_AUDIO,
    "background_noise":      RISK_SCORE_BACKGROUND_AUDIO,
}

_REASON_MAP = {
    STATE_NOISE_LOUD:        "loud_background_noise",
    STATE_MULTIPLE_SPEAKERS: "multiple_speakers_detected",
    STATE_WHISPERING:        "whispering_detected",
    STATE_BACKGROUND_AUDIO:  "background_audio_detected",
    "background_noise":      "background_noise_detected",
}

_CHUNKS_PER_WINDOW = max(1, int(SCORING_WINDOW_SEC * 1000 / CHUNK_MS))  # ~31


@dataclass
class AudioScore:
    state:               str
    risk_score:          float
    risk_reason:         str
    consecutive:         int     # consecutive violation windows
    violations_in_window:int
    emit_sustained:      bool = False
    emit_escalation:     bool = False


class AudioScorer:
    """
    Aggregates 30ms chunks into 1-second windows.
    update() returns AudioScore when a window completes, else None.
    """

    def __init__(self, student_id: str):
        self.student_id = student_id
        self._window_states: list  = []
        self._window_count         = 0
        self._consec               = 0   # consecutive violation windows
        self._total_windows        = 0
        self._violation_windows    = 0
        self._sustained_window: deque = deque(maxlen=ESCALATION_WINDOW_CHECKS)

    def update(self, state: str, base_risk: float,
               reason: str) -> Optional[AudioScore]:
        """
        Feed one chunk state.
        Returns AudioScore on window completion (~1 sec), else None.
        """
        self._window_states.append(state)
        self._window_count += 1

        if self._window_count < _CHUNKS_PER_WINDOW:
            return None   # window not complete yet

        # ── Window complete ───────────────────────────────────
        window_state = max(set(self._window_states),
                           key=self._window_states.count)
        self._window_states = []
        self._window_count  = 0
        self._total_windows += 1

        is_violation = window_state in _VIOLATION_STATES
        if is_violation:
            self._consec            += 1
            self._violation_windows += 1
        else:
            self._consec = 0

        emit_sustained  = False
        emit_escalation = False

        if self._consec == CONSECUTIVE_VIOLATION_WINDOWS and self._consec % CONSECUTIVE_VIOLATION_WINDOWS == 0:
            emit_sustained = True
            self._sustained_window.append(1)
            logger.info("[Audio] student=%s SUSTAINED %s (%d sec)",
                        self.student_id, window_state, self._consec)

        recent = sum(self._sustained_window)
        if recent >= ESCALATION_COUNT and emit_sustained:
            emit_escalation = True
            logger.warning("[Audio] student=%s ESCALATION — %d violations",
                           self.student_id, recent)

        # Risk
        if emit_escalation:
            risk = RISK_SCORE_ESCALATION
        elif emit_sustained:
            risk = RISK_SCORE_SUSTAINED
        else:
            risk = _RISK_MAP.get(window_state, 0.0)

        return AudioScore(
            state                = window_state,
            risk_score           = risk,
            risk_reason          = _REASON_MAP.get(window_state, ""),
            consecutive          = self._consec,
            violations_in_window = recent,
            emit_sustained       = emit_sustained,
            emit_escalation      = emit_escalation,
        )

    def reset(self):
        self._window_states          = []
        self._window_count           = 0
        self._consec                 = 0
        self._total_windows          = 0
        self._violation_windows      = 0
        self._sustained_window.clear()

    @property
    def violation_rate(self) -> float:
        if self._total_windows == 0:
            return 0.0
        return round(self._violation_windows / self._total_windows, 4)


def build_event(student_id: str,
                score: Optional[AudioScore],
                force: bool = False):
    """
    Returns a single event dict, OR a list of two dicts when
    multiple speakers sustained (fires both multiple_speakers
    AND background_noise events with one shared risk score).
    """
    if score is None:
        return None

    should_emit = (
        force
        or score.emit_sustained
        or score.emit_escalation
    )
    if not should_emit:
        return None

    base_event = {
        "severity":            round(score.risk_score, 4),
        "timestamp":           time.time(),
        "student_id":          student_id,
        "audio_state":         score.state,
        "consecutive_windows": score.consecutive,
        "violations_in_window":score.violations_in_window,
        "risk_reason":         score.risk_reason,
    }

    event_name = _event_name(score)
    main_event = {**base_event, "event": event_name}

    logger.info("[Event] student=%s  event=%-30s  severity=%.2f",
                student_id, event_name, score.risk_score)

    # When multiple speakers sustained — also fire background_noise event
    # Background noise event has severity=0 so it doesn't double-count score
    if score.state == "background_noise" and score.emit_sustained:
        bg_event = {**base_event,
                    "event":    "audio_background_noise",
                    "severity": 0.0,   # zero — score already counted above
                    "risk_reason": "background_noise_detected"}
        logger.info("[Event] student=%s  event=%-30s  severity=0.0 (no extra score)",
                    student_id, "audio_background_noise")
        return [main_event, bg_event]   # return list of two events

    return main_event


def _event_name(score: AudioScore) -> str:
    if score.emit_escalation:                    return "audio_repeated_violation"
    if score.emit_sustained:                     return "audio_sustained_violation"
    if score.state == STATE_MULTIPLE_SPEAKERS:   return "audio_multiple_speakers"
    if score.state == STATE_NOISE_LOUD:          return "audio_loud_noise"
    if score.state == STATE_WHISPERING:          return "audio_whispering"
    if score.state == STATE_BACKGROUND_AUDIO:    return "audio_background_noise"
    if score.state == "background_noise":        return "audio_background_noise"
    return "audio_violation"