
# #  Microphone input using PyAudio.
# #  Yields 30ms chunks of int16 PCM audio at 16kHz.
# #
# #  Usage:
# #      cap = AudioCapture()
# #      cap.start()
# #      chunk = cap.read()   # numpy int16 array of 480 samples
# #      cap.stop()

# import logging
# import queue
# import threading
# import numpy as np
# from typing import Optional

# from config import SAMPLE_RATE, CHUNK_SAMPLES, CHANNELS

# logger = logging.getLogger(__name__)


# class AudioCapture:
#     """
#     Non-blocking microphone capture.
#     Audio is read in a background thread and put into a queue.
#     Call read() to get the next chunk without blocking the main thread.
#     """

#     def __init__(self, device_index: Optional[int] = None,
#                  queue_maxsize: int = 50):
#         """
#         Args:
#             device_index: PyAudio device index. None = system default mic.
#             queue_maxsize: max chunks buffered (50 × 30ms = 1.5s buffer)
#         """
#         self._device_index = device_index
#         self._queue        = queue.Queue(maxsize=queue_maxsize)
#         self._stream       = None
#         self._pa           = None
#         self._thread       = None
#         self._running      = False

#     def start(self):
#         """Open microphone and start background capture thread."""
#         try:
#             import pyaudio
#         except ImportError:
#             raise ImportError(
#                 "PyAudio not installed.\n"
#                 "Windows: pip install pyaudio\n"
#                 "Linux:   sudo apt install portaudio19-dev && pip install pyaudio"
#             )

#         import pyaudio

#         self._pa     = pyaudio.PyAudio()
#         self._stream = self._pa.open(
#             format            = pyaudio.paInt16,
#             channels          = CHANNELS,
#             rate              = SAMPLE_RATE,
#             input             = True,
#             input_device_index= self._device_index,
#             frames_per_buffer = CHUNK_SAMPLES,
#         )
#         self._running = True
#         self._thread  = threading.Thread(
#             target=self._capture_loop, daemon=True, name="audio_capture"
#         )
#         self._thread.start()
#         logger.info(
#             "AudioCapture started | device=%s  rate=%d  chunk=%dms",
#             self._device_index or "default", SAMPLE_RATE,
#             int(CHUNK_SAMPLES * 1000 / SAMPLE_RATE),
#         )

#     def _capture_loop(self):
#         while self._running:
#             try:
#                 raw = self._stream.read(CHUNK_SAMPLES, exception_on_overflow=False)
#                 chunk = np.frombuffer(raw, dtype=np.int16)
#                 # Drop oldest if queue full (keep real-time, discard stale)
#                 if self._queue.full():
#                     try:
#                         self._queue.get_nowait()
#                     except queue.Empty:
#                         pass
#                 self._queue.put_nowait(chunk)
#             except Exception as e:
#                 if self._running:
#                     logger.error("Audio capture error: %s", e)

#     def read(self, timeout: float = 0.1) -> Optional[np.ndarray]:
#         """
#         Get next audio chunk (480 int16 samples = 30ms).
#         Returns None if no chunk available within timeout.
#         """
#         try:
#             return self._queue.get(timeout=timeout)
#         except queue.Empty:
#             return None

#     def read_seconds(self, seconds: float) -> np.ndarray:
#         """
#         Collect `seconds` worth of audio and return as one array.
#         Blocks until enough audio is collected.
#         """
#         n_chunks = int(seconds * 1000 / (CHUNK_SAMPLES * 1000 / SAMPLE_RATE))
#         chunks   = []
#         while len(chunks) < n_chunks:
#             chunk = self.read(timeout=1.0)
#             if chunk is not None:
#                 chunks.append(chunk)
#         return np.concatenate(chunks)

#     def stop(self):
#         """Stop capture and release resources."""
#         self._running = False
#         if self._stream:
#             try:
#                 self._stream.stop_stream()
#                 self._stream.close()
#             except Exception:
#                 pass
#         if self._pa:
#             try:
#                 self._pa.terminate()
#             except Exception:
#                 pass
#         logger.info("AudioCapture stopped.")

#     @staticmethod
#     def list_devices():
#         """Print available audio input devices."""
#         try:
#             import pyaudio
#             pa = pyaudio.PyAudio()
#             print("\nAvailable audio input devices:")
#             for i in range(pa.get_device_count()):
#                 info = pa.get_device_info_by_index(i)
#                 if info["maxInputChannels"] > 0:
#                     print(f"  [{i}] {info['name']}")
#             pa.terminate()
#         except ImportError:
#             print("PyAudio not installed.")



#  Auto-detects microphone. NO adaptive gain normalization.
#  Normalization caused false positives — removed entirely.


import logging
import queue
import threading
import numpy as np
from typing import Optional

from config import SAMPLE_RATE, CHUNK_SAMPLES, CHANNELS

logger = logging.getLogger(__name__)


def find_best_microphone() -> Optional[int]:
    """
    Auto-detect the best working microphone.
    Tests each device to confirm it actually opens successfully.
    Returns the first working input device index.
    """
    try:
        import pyaudio
        pa = pyaudio.PyAudio()

        # Build list of all input devices
        devices = []
        default_idx = None
        try:
            default_idx = int(pa.get_default_input_device_info()["index"])
        except Exception:
            pass

        for i in range(pa.get_device_count()):
            try:
                info = pa.get_device_info_by_index(i)
                if info["maxInputChannels"] > 0:
                    devices.append(i)
            except Exception:
                pass

        pa.terminate()

        # Try default first, then others
        if default_idx is not None and default_idx in devices:
            devices.insert(0, devices.pop(devices.index(default_idx)))

        # Test each device — return first one that actually opens
        for idx in devices:
            if _test_device(idx):
                import pyaudio as pa2
                p = pa2.PyAudio()
                try:
                    name = p.get_device_info_by_index(idx)["name"]
                finally:
                    p.terminate()
                logger.info("Auto-detected mic: [%d] %s", idx, name)
                return idx

    except Exception as e:
        logger.warning("Device detection failed: %s", e)

    logger.warning("No working mic found — using system default")
    return None


def _test_device(device_index: int) -> bool:
    """Try opening a device briefly to confirm it works."""
    try:
        import pyaudio
        pa     = pyaudio.PyAudio()
        stream = pa.open(
            format             = pyaudio.paInt16,
            channels           = 1,
            rate               = SAMPLE_RATE,
            input              = True,
            input_device_index = device_index,
            frames_per_buffer  = CHUNK_SAMPLES,
        )
        stream.read(CHUNK_SAMPLES, exception_on_overflow=False)
        stream.stop_stream()
        stream.close()
        pa.terminate()
        return True
    except Exception:
        try:
            pa.terminate()
        except Exception:
            pass
        return False


class AudioCapture:
    """
    Non-blocking microphone capture.
    Raw audio — no normalization (was causing false positives).
    """

    def __init__(self, device_index="auto", queue_maxsize: int = 50):
        if device_index == "auto":
            self._device_index = find_best_microphone()
        else:
            self._device_index = device_index

        self._queue   = queue.Queue(maxsize=queue_maxsize)
        self._stream  = None
        self._pa      = None
        self._thread  = None
        self._running = False

    def start(self):
        try:
            import pyaudio
        except ImportError:
            raise ImportError("Run: pip install pyaudio")

        import pyaudio
        self._pa     = pyaudio.PyAudio()
        self._stream = self._pa.open(
            format             = pyaudio.paInt16,
            channels           = CHANNELS,
            rate               = SAMPLE_RATE,
            input              = True,
            input_device_index = self._device_index,
            frames_per_buffer  = CHUNK_SAMPLES,
        )
        self._running = True
        self._thread  = threading.Thread(
            target=self._capture_loop, daemon=True, name="audio_capture"
        )
        self._thread.start()
        logger.info("AudioCapture started | device=%s  rate=%d",
                    self._device_index or "default", SAMPLE_RATE)

    def _capture_loop(self):
        while self._running:
            try:
                raw   = self._stream.read(CHUNK_SAMPLES,
                                          exception_on_overflow=False)
                chunk = np.frombuffer(raw, dtype=np.int16)
                if self._queue.full():
                    try:
                        self._queue.get_nowait()
                    except queue.Empty:
                        pass
                self._queue.put_nowait(chunk)
            except Exception as e:
                if self._running:
                    logger.error("Capture error: %s", e)

    def read(self, timeout: float = 0.1) -> Optional[np.ndarray]:
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def read_seconds(self, seconds: float) -> np.ndarray:
        n = int(seconds * 1000 / (CHUNK_SAMPLES * 1000 / SAMPLE_RATE))
        chunks = []
        while len(chunks) < n:
            c = self.read(timeout=1.0)
            if c is not None:
                chunks.append(c)
        return np.concatenate(chunks)

    def stop(self):
        self._running = False
        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
        if self._pa:
            try:
                self._pa.terminate()
            except Exception:
                pass
        logger.info("AudioCapture stopped.")

    @staticmethod
    def list_devices():
        try:
            import pyaudio
            pa = pyaudio.PyAudio()
            print("\nAvailable audio input devices:")
            for i in range(pa.get_device_count()):
                info = pa.get_device_info_by_index(i)
                if info["maxInputChannels"] > 0:
                    tag = ""
                    try:
                        if pa.get_default_input_device_info()["index"] == i:
                            tag = " ← DEFAULT"
                    except Exception:
                        pass
                    print(f"  [{i}] {info['name']}{tag}")
            pa.terminate()
        except ImportError:
            print("PyAudio not installed.")