"""Webcam presence detection with OpenCV.

Uses two cheap detectors and treats a frame as "someone's there" if either fires:
  * Haar frontal-face cascade: good when someone is close and facing the laptop.
  * HOG pedestrian detector: good for full bodies walking past further away.

A small state machine debounces the result into ARRIVED / LEFT events so a
single noisy frame doesn't trigger a greeting.
"""

import threading
import time
from dataclasses import dataclass

import cv2


@dataclass
class Detection:
    faces: int
    bodies: int
    boxes: list

    @property
    def present(self) -> bool:
        return self.faces > 0 or self.bodies > 0

    @property
    def count(self) -> int:
        return max(self.faces, self.bodies)


class PersonDetector:
    def __init__(self, camera_index: int = 0, width: int = 640):
        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            raise RuntimeError(f"Could not open camera {camera_index}")
        self.width = width
        self.face = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

    def read(self):
        ok, frame = self.cap.read()
        if not ok:
            return None, None
        scale = self.width / frame.shape[1]
        frame = cv2.resize(frame, (self.width, int(frame.shape[0] * scale)))
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        faces = self.face.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(60, 60))
        bodies, weights = self.hog.detectMultiScale(gray, winStride=(8, 8), padding=(8, 8), scale=1.05)
        bodies = [b for b, w in zip(bodies, weights) if float(w) > 0.5]

        boxes = [tuple(f) for f in faces] + [tuple(b) for b in bodies]
        return frame, Detection(faces=len(faces), bodies=len(bodies), boxes=boxes)

    def release(self):
        self.cap.release()


class PresenceTracker:
    """Turns per-frame detections into arrive/leave events (thread-safe)."""

    def __init__(self, arrive_frames: int, leave_seconds: float):
        self.arrive_frames = arrive_frames
        self.leave_seconds = leave_seconds
        self._streak = 0
        self._last_seen = 0.0
        self._present = False
        self.count = 0
        self.arrived = threading.Event()
        self._lock = threading.Lock()

    def update(self, det: Detection) -> None:
        now = time.monotonic()
        with self._lock:
            if det.present:
                self._streak += 1
                self._last_seen = now
                self.count = det.count
                if not self._present and self._streak >= self.arrive_frames:
                    self._present = True
                    self.arrived.set()
            else:
                self._streak = 0
                if self._present and now - self._last_seen > self.leave_seconds:
                    self._present = False
                    self.count = 0
                    self.arrived.clear()

    @property
    def present(self) -> bool:
        with self._lock:
            return self._present

    def force(self, present: bool, count: int = 1) -> None:
        """Simulate a visitor (used by --no-camera mode)."""
        with self._lock:
            self._present = present
            self.count = count if present else 0
            self._last_seen = time.monotonic()
            if present:
                self.arrived.set()
            else:
                self.arrived.clear()


def draw(frame, det: Detection, status: str):
    for (x, y, w, h) in det.boxes:
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 200, 255), 2)
    cv2.putText(frame, status, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    return frame
