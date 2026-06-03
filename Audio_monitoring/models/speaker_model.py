#resemblyzer loader
#  Resemblyzer speaker encoder — auto-downloads on first run.
#  Used to check if more than one speaker is present.

import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

logger = logging.getLogger(__name__)

_encoder = None


def get_speaker_encoder():
    """
    Returns a cached Resemblyzer VoiceEncoder.
    Downloads pretrained weights (~17MB) on first call.
    """
    global _encoder
    if _encoder is not None:
        return _encoder

    try:
        from resemblyzer import VoiceEncoder
        logger.info("Loading Resemblyzer speaker encoder ...")
        _encoder = VoiceEncoder(device="cpu")
        logger.info("Speaker encoder loaded.")
    except ImportError:
        raise ImportError(
            "Resemblyzer not installed.\n"
            "Run: pip install resemblyzer"
        )

    return _encoder