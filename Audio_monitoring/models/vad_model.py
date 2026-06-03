#silero vad loader


import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

logger = logging.getLogger(__name__)

_model = None
_utils = None


def get_vad_model():
    """
    Returns (model, utils) Silero VAD.
    Downloads model automatically on first call.
    Thread-safe for inference.
    """
    global _model, _utils
    if _model is not None:
        return _model, _utils

    try:
        import torch
        logger.info("Loading Silero VAD model ...")
        _model, _utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            force_reload=False,
            trust_repo=True,
        )
        logger.info("Silero VAD loaded.")
    except Exception as e:
        raise RuntimeError(
            f"Failed to load Silero VAD: {e}\n"
            "Run: pip install torch torchaudio"
        )

    return _model, _utils