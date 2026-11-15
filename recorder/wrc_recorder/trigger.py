# WRC - WoW Record Combat | Ionity (Pty) Ltd | Author: Johan Wilhelm van Antwerp
"""Decides when a recording starts and stops. Pure logic, no I/O."""

START, STOP, SPLIT = "start", "stop", "split"


def wanted(beacon, mode):
    """Does this beacon reading ask for a recording under the chosen trigger mode?"""
    if beacon is None or not beacon.trusted:
        return False
    if beacon.manual:
        return True
    if mode == "pvp_combat":
        return beacon.pvp_combat
    if mode == "any_combat":
        return beacon.combat or beacon.pvp_combat
    return beacon.enemy or beacon.pvp_combat          # "enemy" (default)


class Trigger:
    """Feed update(signal, now) every tick; it returns START, STOP, SPLIT or None.

    start_confirm : consecutive positive readings needed before starting
    linger        : seconds to keep recording after the signal goes away
    max_clip      : seconds after which a long recording is split into a new file
    """

    def __init__(self, start_confirm=2, linger=10.0, max_clip=1800.0):
        self.start_confirm = max(1, int(start_confirm))
        self.linger = float(linger)
        self.max_clip = float(max_clip)
        self.recording = False
        self._streak = 0
        self._last_signal = 0.0
        self._started = 0.0

    def reset(self):
        self.recording = False
        self._streak = 0

    def force_stop(self):
        """End the current recording now, without the linger (manual Stop)."""
        if not self.recording:
            return None
        self.reset()
        return STOP

    def update(self, signal, now):
        if signal:
            self._streak += 1
            self._last_signal = now
        else:
            self._streak = 0

        if not self.recording:
            if self._streak >= self.start_confirm:
                self.recording = True
                self._started = now
                return START
            return None

        if now - self._last_signal >= self.linger:
            self.recording = False
            self._streak = 0
            return STOP
        if self.max_clip > 0 and now - self._started >= self.max_clip:
            self._started = now
            return SPLIT
        return None
