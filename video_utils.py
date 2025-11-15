import math
import time
from typing import Optional

import numpy as np


class FrameRateController:
    """Keeps recorded footage aligned with real elapsed time by padding or dropping frames."""

    def __init__(self, target_fps: float):
        self.target_fps = max(1.0, float(target_fps))
        self.start_time = time.time()
        self.frames_written = 0

    def _writes_needed(self, elapsed: float) -> int:
        expected_total = max(self.frames_written + 1, int(math.floor(elapsed * self.target_fps)))
        return max(0, expected_total - self.frames_written)

    def write(self, writer, frame: np.ndarray):
        elapsed = time.time() - self.start_time
        writes_needed = self._writes_needed(elapsed)
        if writes_needed == 0:
            return
        for _ in range(writes_needed):
            writer.write(frame)
            self.frames_written += 1

    def finalize(self, writer, frame: Optional[np.ndarray], total_duration: float):
        if frame is None:
            return
        total_duration = max(0.0, total_duration)
        expected_total = max(self.frames_written, int(round(total_duration * self.target_fps)))
        while self.frames_written < expected_total:
            writer.write(frame)
            self.frames_written += 1

