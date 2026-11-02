from __future__ import annotations

from enum import Enum


class Badge(str, Enum):
    """Valid badge values and their IHC display colors.

    Semantics (IHC guideline):
    - NATIVE  = success, teal — recompiled native binary
    - EMU     = informative, yellow — emulated (not an error)
    - BUILDING = in-progress, blue — build running
    - BUILD_ERROR = error, red — action required
    """

    NATIVE = "NATIVE"
    EMU = "EMU"
    BUILDING = "BUILDING"
    BUILD_ERROR = "BUILD ERROR"


BADGE_COLORS: dict[Badge, str] = {
    Badge.NATIVE: "#4ecdc4",
    Badge.EMU: "#f5a623",
    Badge.BUILDING: "#4a9eff",
    Badge.BUILD_ERROR: "#e94560",
}
