
# #  Converts AttentionScore → structured Risk Engine event dict.
# #  Matches the event schema from architecture doc:
# #    { "event": ..., "severity": ..., "timestamp": ... }
# #
# #  Only emits events when something noteworthy happens —
# #  NOT on every focused frame (to avoid flooding the Risk Engine).


# import time
# import logging
# from typing import Optional

# from attention_scorer import AttentionScore

# logger = logging.getLogger(__name__)


# def build_event(
#     student_id: str,
#     score: AttentionScore,
#     force: bool = False,
# ) -> Optional[dict]:
#     """
#     Build a Risk Engine event from an AttentionScore.

#     Events are only emitted when:
#       - A sustained look-away is detected  (emit_sustained_event=True)
#       - An escalation pattern is detected  (emit_escalation_event=True)
#       - Face is not visible
#       - force=True (use for periodic heartbeat checks)

#     Returns None if nothing notable happened this frame.

#     Args:
#         student_id: student being tracked
#         score:      AttentionScore from AttentionScorer.update()
#         force:      always emit (useful for periodic sampling)

#     Returns:
#         dict ready for Risk Engine, or None
#     """
#     should_emit = (
#         force
#         or score.emit_sustained_event
#         or score.emit_escalation_event
#         or score.current_state == "no_face"
#     )

#     if not should_emit:
#         return None

#     event = {
#         #Required by Risk Engine
#         "event":      _event_name(score),
#         "severity":   round(score.risk_score, 4),   # attention_risk × 0.10 in Risk Engine
#         "timestamp":  time.time(),

#         #Gaze-specific context 
#         "student_id":          student_id,
#         "gaze_state":          score.current_state,
#         "consecutive_away":    score.consecutive_away,
#         "violations_in_window":score.violations_in_window,
#         "risk_reason":         score.risk_reason,
#         "is_attentive":        score.is_attentive,
#     }

#     logger.info(
#         "[Event] student=%s  event=%s  severity=%.2f  state=%s",
#         student_id, event["event"], event["severity"], score.current_state,
#     )
#     return event


# def _event_name(score: AttentionScore) -> str:
#     if score.emit_escalation_event:
#         return "gaze_repeated_violation"
#     if score.emit_sustained_event:
#         return "gaze_sustained_away"
#     if score.current_state == "no_face":
#         return "gaze_face_missing"
#     return "gaze_away"




#  Converts AttentionScore → Risk Engine event dict.
#  Emits events only when something notable happens.
#  No_face events are throttled — only on sustained absence.

import time
import logging
from typing import Optional

from attention_scorer import AttentionScore

logger = logging.getLogger(__name__)


def build_event(student_id: str,
                score: AttentionScore,
                force: bool = False) -> Optional[dict]:
    """
    Returns a Risk Engine event dict, or None if nothing notable.

    Events emitted only for:
      - Sustained gaze look-away    (not every single away frame)
      - Sustained no-face           (not every missing frame)
      - Escalation pattern
      - Pupil-only deviation        (subtle cheating)
      - force=True                  (periodic heartbeat)

    Single away frames or brief no_face → returns None (not spammy).
    """
    should_emit = (
        force
        or score.emit_gaze_sustained
        or score.emit_no_face_sustained
        or score.emit_escalation
        or score.emit_pupil_away
    )

    if not should_emit:
        return None

    event = {
        # Required by Risk Engine
        "event":     _event_name(score),
        "severity":  round(score.risk_score, 4),
        "timestamp": time.time(),

        # Gaze context
        "student_id":           student_id,
        "gaze_state":           score.current_state,
        "consecutive_away":     score.consecutive_gaze_away,
        "violations_in_window": score.violations_in_window,
        "risk_reason":          score.risk_reason,
        "is_attentive":         score.is_attentive,
    }

    logger.info("[Event] student=%s  event=%-28s  severity=%.2f",
                student_id, event["event"], event["severity"])
    return event


def _event_name(score: AttentionScore) -> str:
    if score.emit_escalation:
        return "gaze_repeated_violation"
    if score.emit_gaze_sustained:
        return "gaze_sustained_away"
    if score.emit_no_face_sustained:
        return "gaze_face_missing_sustained"
    if score.emit_pupil_away:
        return "gaze_pupil_deviation"
    return "gaze_away"