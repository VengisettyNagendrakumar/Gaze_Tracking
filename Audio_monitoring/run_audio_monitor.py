
# import argparse
# import logging
# import sys
# import os
# import time

# sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s  %(levelname)-7s  %(message)s",
# )
# logger = logging.getLogger(__name__)


# def run(device_index=None, duration=None):
#     from audio_monitor import AudioMonitor
#     from audio_capture import AudioCapture
#     from config import (
#         STATE_SILENT, STATE_SPEECH_NORMAL,
#         STATE_NOISE_LOUD, STATE_MULTIPLE_SPEAKERS, STATE_WHISPERING,
#     )

#     # Color codes for terminal
#     COLORS = {
#         STATE_SILENT:            "\033[90m",   # grey
#         STATE_SPEECH_NORMAL:     "\033[32m",   # green
#         STATE_NOISE_LOUD:        "\033[33m",   # yellow
#         STATE_MULTIPLE_SPEAKERS: "\033[31m",   # red
#         STATE_WHISPERING:        "\033[35m",   # magenta
#     }
#     RESET = "\033[0m"

#     monitor    = AudioMonitor("TEST_STUDENT", device_index=device_index)
#     risk_events = []

#     logger.info("=" * 60)
#     logger.info("  Audio Monitor  |  Ctrl+C to stop")
#     logger.info("  Monitoring: voice activity, noise, multiple speakers")
#     logger.info("=" * 60)

#     monitor.start()

#     start_time  = time.time()
#     last_print  = time.time()
#     PRINT_EVERY = 1.0   # print state every 1 second

#     try:
#         while True:
#             # Check duration limit
#             if duration and (time.time() - start_time) >= duration:
#                 break

#             # Print current state every second
#             if time.time() - last_print >= PRINT_EVERY:
#                 state = monitor.current_state
#                 rms   = monitor.current_rms
#                 color = COLORS.get(state, "")
#                 print(f"\r{color}State: {state:<22}{RESET}  rms={rms:>6.0f}", end="", flush=True)
#                 last_print = time.time()

#             # Drain any risk events
#             events = monitor.get_all_events()
#             for event in events:
#                 risk_events.append(event)
#                 print()  # newline before event
#                 logger.warning(
#                     "RISK EVENT  event=%-30s  severity=%.2f  reason=%s",
#                     event["event"], event["severity"], event["risk_reason"],
#                 )

#             time.sleep(0.05)

#     except KeyboardInterrupt:
#         print()
#         logger.info("Stopping ...")

#     summary = monitor.stop()

#     print("\n" + "=" * 60)
#     print("  SESSION SUMMARY")
#     print("=" * 60)
#     print(f"  Student ID      : {summary['student_id']}")
#     print(f"  Violation rate  : {summary['violation_rate'] * 100:.1f}%")
#     print(f"  Total events    : {len(risk_events)}")
#     if risk_events:
#         print("\n  Events fired:")
#         for e in risk_events:
#             print(f"    [{e['event']}]  severity={e['severity']}  reason={e['risk_reason']}")
#     print("=" * 60)


# if __name__ == "__main__":
#     parser = argparse.ArgumentParser(description="Audio Monitor")
#     parser.add_argument("--device",       type=int,   default=None,
#                         help="Microphone device index")
#     parser.add_argument("--list-devices", action="store_true",
#                         help="List available microphones and exit")
#     parser.add_argument("--duration",     type=int,   default=None,
#                         help="Run for N seconds then stop")
#     args = parser.parse_args()

#     if args.list_devices:
#         from audio_capture import AudioCapture
#         AudioCapture.list_devices()
#         sys.exit(0)

#     run(device_index=args.device, duration=args.duration)



import argparse
import logging
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
)
logger = logging.getLogger(__name__)


def run(device_index="auto", duration=None):
    from audio_monitor import AudioMonitor
    from audio_capture import AudioCapture
    from config import (
        STATE_SILENT, STATE_SPEECH_NORMAL,
        STATE_NOISE_LOUD, STATE_MULTIPLE_SPEAKERS,
        STATE_WHISPERING, STATE_BACKGROUND_AUDIO,
    )

    # Color codes for terminal
    COLORS = {
        STATE_SILENT:            "\033[90m",   # grey
        STATE_SPEECH_NORMAL:     "\033[32m",   # green
        STATE_NOISE_LOUD:        "\033[33m",   # yellow
        STATE_MULTIPLE_SPEAKERS: "\033[31m",   # red
        STATE_WHISPERING:        "\033[35m",   # magenta
        "background_audio":      "\033[36m",   # cyan
    }
    RESET = "\033[0m"

    monitor    = AudioMonitor("TEST_STUDENT", device_index=device_index)
    risk_events = []

    logger.info("=" * 60)
    logger.info("  Audio Monitor  |  Ctrl+C to stop")
    logger.info("  Monitoring: voice activity, noise, multiple speakers")
    logger.info("=" * 60)
    print("\n[INFO] Loading models (first run may take 5-10 sec) ...")
    print("[INFO] Then mic calibrates for 3 sec — stay silent during calibration.\n")

    monitor.start()

    start_time  = time.time()
    last_print  = time.time()
    PRINT_EVERY = 0.5

    try:
        while True:
            # Check duration limit
            if duration and (time.time() - start_time) >= duration:
                break

            # Print current state every 300ms
            if time.time() - last_print >= PRINT_EVERY:
                state    = monitor.current_state
                rms      = monitor.current_rms
                vad_score= monitor._vad._last_score if hasattr(monitor._vad, '_last_score') else 0.0
                color    = COLORS.get(state, "")
                print(f"\r{color}state={state:<20}{RESET}  rms={rms:>6.0f}  vad={vad_score:.2f}", end="", flush=True)
                last_print = time.time()

            # Drain any risk events
            events = monitor.get_all_events()
            for event in events:
                risk_events.append(event)
                print()  # newline before event
                logger.warning(
                    "RISK EVENT  event=%-30s  severity=%.2f  reason=%s",
                    event["event"], event["severity"], event["risk_reason"],
                )

            time.sleep(0.05)

    except KeyboardInterrupt:
        print()
        logger.info("Stopping ...")

    summary = monitor.stop()

    print("\n" + "=" * 60)
    print("  SESSION SUMMARY")
    print("=" * 60)
    print(f"  Student ID      : {summary['student_id']}")
    print(f"  Violation rate  : {summary['violation_rate'] * 100:.1f}%")
    print(f"  Total events    : {len(risk_events)}")
    if risk_events:
        print("\n  Events fired:")
        for e in risk_events:
            print(f"    [{e['event']}]  severity={e['severity']}  reason={e['risk_reason']}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audio Monitor")
    parser.add_argument("--device",       type=int,   default=None,
                        help="Mic device index (optional — auto-detected if not given)")
    parser.add_argument("--list-devices", action="store_true",
                        help="List available microphones and exit")
    parser.add_argument("--duration",     type=int,   default=None,
                        help="Run for N seconds then stop")
    args = parser.parse_args()

    if args.list_devices:
        from audio_capture import AudioCapture
        AudioCapture.list_devices()
        sys.exit(0)

    # Use specified device or auto-detect
    device = args.device if args.device is not None else "auto"
    run(device_index=device, duration=args.duration)