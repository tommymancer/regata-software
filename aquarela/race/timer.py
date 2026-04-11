"""Race timer — countdown/countup state machine.

States:
  idle      — no race active
  countdown — counting down to gun (5/4/3/2/1 min start sequence)
  racing    — counting up from gun
"""

import time
from typing import Optional

from ..pipeline.state import BoatState


class RaceTimer:
    """Race start sequence timer.

    Controlled via REST API, state broadcast over WebSocket.
    Called once per pipeline step to update BoatState fields.
    """

    def __init__(self) -> None:
        self.state: str = "idle"
        self._start_mono: float = 0.0
        self._countdown_secs: float = 300.0  # default 5 min

    # ── Controls ───────────────────────────────────────────────────

    def start(self, minutes: int = 5) -> None:
        """Begin countdown from *minutes* (typical: 5, 3, or 1)."""
        self._countdown_secs = minutes * 60
        self._start_mono = time.monotonic()
        self.state = "countdown"

    def sync_up(self) -> None:
        """Add 1 minute to the countdown (synchronise to flag signal)."""
        if self.state == "countdown":
            self._countdown_secs += 60

    def sync_down(self) -> None:
        """Remove 1 minute from the countdown."""
        if self.state == "countdown":
            self._countdown_secs = max(0, self._countdown_secs - 60)

    def stop(self) -> None:
        """Stop the timer (back to idle)."""
        self.state = "idle"

    def reset(self) -> None:
        """Full reset."""
        self.state = "idle"
        self._start_mono = 0.0
        self._countdown_secs = 300.0

    # ── Pipeline integration ──────────────────────────────────────

    def get_seconds(self) -> Optional[float]:
        """Current timer value in seconds.

        - countdown: positive = seconds remaining until gun
        - racing:    positive = seconds elapsed since gun
        - idle:      None
        """
        if self.state == "idle":
            return None

        now = time.monotonic()
        elapsed = now - self._start_mono

        if self.state == "countdown":
            remaining = self._countdown_secs - elapsed
            if remaining <= 0:
                # Gun! Transition to racing.
                self.state = "racing"
                # Adjust start so elapsed counts from the exact gun moment
                self._start_mono = self._start_mono + self._countdown_secs
                return now - self._start_mono
            return remaining

        # racing
        return elapsed

    def update(self, state: BoatState) -> None:
        """Set race fields on *state* (called once per pipeline step)."""
        state.race_state = self.state
        state.race_timer_secs = self.get_seconds()
