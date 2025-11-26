import math
import time
import subprocess
import shlex
import platform
from typing import Optional

import numpy as np
import cv2


class FFmpegVideoWriter:
    """FFmpeg 파이프를 사용하는 VideoWriter 래퍼 클래스 (젯슨 전용)"""
    
    def __init__(self, output_path: str, fps: float, frame_width: int, frame_height: int):
        self.output_path = output_path
        self.fps = fps
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.process = None
        self.stdin = None
        self._closed = False
        
        # FFmpeg 프로세스 시작
        # -f rawvideo: 입력 데이터가 가공되지 않은 이미지
        # -pix_fmt bgr24: OpenCV 기본 컬러 포맷 매칭
        # -c:v libx264: 소프트웨어 H.264 인코더 사용 (호환성 100%)
        # -preset ultrafast: 인코딩 속도 최우선 (Jetson CPU 부하 최소화 필수)
        # -pix_fmt yuv420p: 웹/모바일 재생 호환성을 위한 픽셀 포맷 변환
        ffmpeg_cmd = (
            f"ffmpeg -y -f rawvideo -vcodec rawvideo "
            f"-s {frame_width}x{frame_height} -pix_fmt bgr24 -r {fps} "
            f"-i - -c:v libx264 -pix_fmt yuv420p "
            f"-preset ultrafast {output_path}"
        )
        
        try:
            self.process = subprocess.Popen(
                shlex.split(ffmpeg_cmd), stdin=subprocess.PIPE
            )
            self.stdin = self.process.stdin
            print(f"[FFmpegVideoWriter] FFmpeg 파이프 초기화 성공 ({output_path})")
        except Exception as e:
            print(f"[FFmpegVideoWriter] FFmpeg 프로세스 시작 실패: {e}")
            self._closed = True
    
    def isOpened(self) -> bool:
        """VideoWriter가 열려있는지 확인"""
        return self.process is not None and not self._closed
    
    def write(self, frame: np.ndarray) -> bool:
        """프레임을 FFmpeg 파이프에 쓰기"""
        if self._closed:
            return False
        
        try:
            # 프레임을 바이트로 변환하여 FFmpeg 파이프에 쓰기
            self.stdin.write(frame.tobytes())
            return True
        except Exception as e:
            print(f"[FFmpegVideoWriter] 프레임 쓰기 실패: {e}")
            return False
    
    def release(self):
        """리소스 정리"""
        if self.stdin:
            self.stdin.close()  # 파이프 입구 닫기
        
        if self.process:
            self.process.wait()  # 인코딩 완료 대기
        
        self._closed = True


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


def _is_jetson_platform() -> bool:
    """
    현재 플랫폼이 Jetson인지 감지
    
    Returns:
        Jetson 플랫폼이면 True, 아니면 False
    """
    system = platform.system()
    machine = platform.machine().lower()
    
    # 젯슨 감지 (ARM64 + Linux)
    if system == "Linux" and any(arch in machine for arch in ("aarch64", "arm64")):
        # 추가 확인: Jetson 특정 파일이나 환경 변수 확인
        try:
            with open("/proc/device-tree/model", "r") as f:
                model = f.read().lower()
                if "jetson" in model or "tegra" in model:
                    return True
        except (FileNotFoundError, IOError):
            pass
        
        # aarch64/arm64 Linux는 Jetson일 가능성이 높음
        return True
    
    return False


def create_browser_compatible_video_writer(output_path: str, fps: float, frame_width: int, frame_height: int):
    """
    브라우저 호환 H.264 코덱으로 VideoWriter 생성
    
    젯슨에서는 FFmpeg 파이프 방식을 사용하여 H.264 인코딩을 보장합니다.
    일반 플랫폼에서는 h264/x264 코덱을 시도하고, 실패하면 기본 코덱(mp4v)으로 폴백합니다.
    
    Args:
        output_path: 출력 비디오 파일 경로
        fps: 프레임 레이트
        frame_width: 프레임 너비
        frame_height: 프레임 높이
    
    Returns:
        VideoWriter 객체 또는 None (모두 실패 시)
    """
    # 젯슨 플랫폼 감지
    is_jetson = _is_jetson_platform()
    
    if is_jetson:
        # 젯슨에서는 FFmpeg 파이프 방식 사용
        try:
            writer = FFmpegVideoWriter(output_path, fps, frame_width, frame_height)
            if writer.isOpened():
                print("[VideoWriter] 젯슨 환경: FFmpeg 파이프 방식 사용")
                return writer
            else:
                writer.release()
                print("[VideoWriter] FFmpeg 파이프 초기화 실패 - OpenCV로 폴백")
        except Exception as e:
            print(f"[VideoWriter] FFmpeg 파이프 방식 실패: {e} - OpenCV로 폴백")
    
    # 일반 플랫폼 또는 FFmpeg 실패 시 OpenCV VideoWriter 사용
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
