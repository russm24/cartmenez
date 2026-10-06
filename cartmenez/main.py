"""Run the kiosk: camera loop on the main thread, conversation on a worker thread.

    python -m cartmenez.main                 # webcam + mic + speaker
    python -m cartmenez.main --preview       # also show the camera window
    python -m cartmenez.main --no-camera     # press Enter to simulate a visitor
    python -m cartmenez.main --text          # type instead of talking
"""

import argparse
import threading
import time

from .brain import CartmanBrain, Reply
from .config import Config
from .detector import PresenceTracker
from .listener import Listener, TypedListener
from .sounds import SoundLibrary
from .voice import Voice


def perform(reply: Reply, voice: Voice, sounds: SoundLibrary) -> None:
    clip = reply.sound if reply.sound != "none" else None
    if clip and reply.sound_timing == "before":
        sounds.play(clip)
    voice.say(reply.say)
    if clip and reply.sound_timing == "after":
        sounds.play(clip)


def conversation_loop(cfg, tracker, brain, voice, listener, sounds, stop: threading.Event, once=False):
    while not stop.is_set():
        if not tracker.arrived.wait(timeout=0.5):
            continue

        brain.reset()
        n = tracker.count
        who = "A person" if n <= 1 else f"A group of {n} people"
        reply = brain.respond(f"[{who} just walked up to the camera. Greet them in character.]")
        perform(reply, voice, sounds)

        turns, silences = 0, 0
        while not reply.end_conversation and turns < cfg.max_turns and not stop.is_set():
            if not tracker.present:
                reply = brain.respond("[The visitor walked away mid-conversation. One short parting shot.]")
                perform(reply, voice, sounds)
                break

            heard = listener.listen(cfg.listen_timeout, cfg.phrase_limit)
            if heard is None:
                silences += 1
                if silences >= 2:
                    reply = brain.respond("[The visitor has gone quiet. Wrap it up.]")
                    perform(reply, voice, sounds)
                    break
                reply = brain.respond("[The visitor didn't say anything.]")
            else:
                print(f"visitor> {heard}")
                silences = 0
                reply = brain.respond(heard)
            perform(reply, voice, sounds)
            turns += 1

        if once:
            return

        # Don't re-greet the same person: wait until they leave, then cool down.
        while tracker.present and not stop.is_set():
            time.sleep(0.5)
        tracker.arrived.clear()
        time.sleep(cfg.cooldown_seconds)


def run_camera(cfg: Config, tracker: PresenceTracker, preview: bool, stop: threading.Event):
    import cv2

    from .detector import PersonDetector, draw

    det = PersonDetector(cfg.camera_index)
    try:
        while not stop.is_set():
            frame, d = det.read()
            if frame is None:
                time.sleep(0.1)
                continue
            tracker.update(d)
            if preview:
                status = f"present ({tracker.count})" if tracker.present else "waiting"
                cv2.imshow("cartmenez", draw(frame, d, status))
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    stop.set()
    finally:
        det.release()
        if preview:
            cv2.destroyAllWindows()


def run_simulated(tracker: PresenceTracker, stop: threading.Event):
    print("No camera: press Enter to toggle a visitor arriving/leaving, Ctrl+C to quit.")
    while not stop.is_set():
        input()
        tracker.force(not tracker.present)
        print("[sim] visitor", "arrived" if tracker.present else "left")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--preview", action="store_true", help="show the camera feed with detections")
    ap.add_argument("--no-camera", action="store_true", help="simulate visitors with the Enter key")
    ap.add_argument("--text", action="store_true", help="type replies instead of using the mic")
    ap.add_argument("--mute", action="store_true", help="print replies instead of speaking them")
    args = ap.parse_args()

    cfg = Config()
    if args.mute:
        cfg.tts_backend = "print"

    sounds = SoundLibrary(cfg.sounds_dir)
    print(f"[sounds] {len(sounds.names)} clip(s): {', '.join(sounds.names) or '-'}")
    brain = CartmanBrain(cfg, sounds.names, sounds.catalog())
    voice = Voice(cfg)
    listener = TypedListener() if args.text else Listener(cfg.stt_backend, cfg.whisper_model)
    tracker = PresenceTracker(cfg.arrive_frames, cfg.leave_seconds)
    stop = threading.Event()

    worker = threading.Thread(
        target=conversation_loop,
        args=(cfg, tracker, brain, voice, listener, sounds, stop, args.no_camera and args.text),
        daemon=True,
    )
    worker.start()

    try:
        if args.no_camera:
            if args.text:
                # stdin is shared with the typed listener, so just start one visitor.
                tracker.force(True)
                worker.join()
            else:
                run_simulated(tracker, stop)
        else:
            run_camera(cfg, tracker, args.preview, stop)
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()


if __name__ == "__main__":
    main()
