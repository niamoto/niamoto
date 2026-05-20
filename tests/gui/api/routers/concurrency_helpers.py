"""Helpers for deterministic concurrency regression tests."""

from __future__ import annotations

import threading


class TrackingRLock:
    """RLock wrapper that records when another thread contends for the lock."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._state_lock = threading.Lock()
        self._owner: int | None = None
        self._depth = 0
        self.contended_acquire = threading.Event()

    def acquire(self, blocking: bool = True, timeout: float = -1) -> bool:
        current_thread = threading.get_ident()
        with self._state_lock:
            if self._owner is not None and self._owner != current_thread:
                self.contended_acquire.set()

        acquired = self._lock.acquire(blocking, timeout)
        if acquired:
            with self._state_lock:
                if self._owner == current_thread:
                    self._depth += 1
                else:
                    self._owner = current_thread
                    self._depth = 1
        return acquired

    def release(self) -> None:
        current_thread = threading.get_ident()
        with self._state_lock:
            if self._owner == current_thread:
                self._depth -= 1
                if self._depth == 0:
                    self._owner = None
        self._lock.release()

    def __enter__(self) -> "TrackingRLock":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.release()
