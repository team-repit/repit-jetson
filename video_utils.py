import math
import time
from typing import Optional

import numpy as np
import cv2


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


def create_browser_compatible_video_writer(output_path: str, fps: float, frame_width: int, frame_height: int):
    """
    브라우저 호환 H.264 코덱으로 VideoWriter 생성
    h264 또는 x264 코덱을 시도하고, 실패하면 기본 코덱(mp4v)으로 폴백
    
    Args:
        output_path: 출력 비디오 파일 경로
        fps: 프레임 레이트
        frame_width: 프레임 너비
        frame_height: 프레임 높이
    
    Returns:
        VideoWriter 객체 또는 None (모두 실패 시)
    """
    # h264 또는 x264 코덱 시도
    h264_codecs = ['h264', 'x264']
    for codec_str in h264_codecs:
        try:
            fourcc = cv2.VideoWriter_fourcc(*codec_str)
            out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))
            if out.isOpened():
                print(f"[VideoWriter] {codec_str} 코덱 사용 성공")
                return out
            else:
                out.release()
        except Exception as e:
            print(f"[VideoWriter] {codec_str} 코덱 시도 실패: {e}")
            continue
    
    # h264/x264 실패 시 기본 코덱(mp4v)으로 폴백
    try:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))
        if out.isOpened():
            print("[VideoWriter] 기본 코덱(mp4v) 사용")
            return out
        else:
            out.release()
    except Exception as e:
        print(f"[VideoWriter] 기본 코덱(mp4v)도 실패: {e}")
    
    return None
