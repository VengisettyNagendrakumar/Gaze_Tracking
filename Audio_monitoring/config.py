

SAMPLE_RATE   = 16000
CHUNK_MS      = 32      # 32ms = 512 samples (Silero VAD minimum)
CHUNK_SAMPLES = int(SAMPLE_RATE * CHUNK_MS / 1000)   # 512
CHANNELS      = 1
AUDIO_FORMAT  = "int16"

# VAD 
VAD_THRESHOLD         = 0.50   # smoothed VAD threshold for speech detection
VAD_MIN_SPEECH_CHUNKS = 5

# RMS thresholds (normalized — same for all mic types) 
NOISE_LEVEL_QUIET   = 30     # below = truly silent
NOISE_LEVEL_WHISPER = 150    # below = background noise
NOISE_LEVEL_MEDIUM  = 280    # below = whisper, above = normal speech
NOISE_LEVEL_LOUD    = 900    # above = loud background noise

# Whisper: needs VAD confirmation to avoid false positives
WHISPER_VAD_MIN    = 0.55

# Background audio detection
BACKGROUND_VAD_MAX = 0.40    # low VAD in grey zone = background audio

# Scoring window 
SCORING_WINDOW_SEC            = 1.0   # 1 second per scoring window
CONSECUTIVE_VIOLATION_WINDOWS = 5     # 5 sec sustained → event

# Multiple speaker detection 
SPEAKER_SIMILARITY_THRESHOLD = 0.75   # below = different speakers
SPEAKER_CHECK_WINDOW_SEC     = 3.0    # 3 sec voice window
MIN_VOICE_RATIO              = 0.3

# Audio states 
STATE_SILENT            = "silent"
STATE_SPEECH_NORMAL     = "speech_normal"
STATE_NOISE_LOUD        = "noise_loud"
STATE_MULTIPLE_SPEAKERS = "multiple_speakers"
STATE_WHISPERING        = "whispering"
STATE_BACKGROUND_AUDIO  = "background_audio"
STATE_BACKGROUND_NOISE  = "background_noise"   # unified: music + multiple speakers

# Risk scores (audio_risk × 0.10 weight in Risk Engine)
RISK_SCORE_SILENT            = 0.0
RISK_SCORE_SPEECH_NORMAL     = 0.0
RISK_SCORE_NOISE_LOUD        = 0.3
RISK_SCORE_MULTIPLE_SPEAKERS = 0.7
RISK_SCORE_WHISPERING        = 0.4
RISK_SCORE_BACKGROUND_AUDIO  = 0.3
RISK_SCORE_SUSTAINED         = 0.6
RISK_SCORE_ESCALATION        = 0.9

# Escalation 
ESCALATION_COUNT         = 3
ESCALATION_WINDOW_CHECKS = 20