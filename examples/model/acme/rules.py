from __future__ import annotations

from .models import Decision


def choose(flag: bool, first: Decision, second: Decision) -> Decision:
    if flag:
        return first
    else:
        return second
