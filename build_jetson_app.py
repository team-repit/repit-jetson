#!/usr/bin/env python3
"""
Jetson (Ubuntu 22.04) 전용 리눅스 앱 패키징 스크립트

- PyInstaller onedir 빌드를 수행
- 결과물을 지정된 설치 경로에 복사
- .desktop 런처를 생성하여 GUI 아이콘으로 실행 가능하도록 설정
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent
DIST_DIR = BASE_DIR / "dist"
PYINSTALLER_NAME = "RePiT-Jetson"


def ensure_jetson() -> None:
    system = platform.system()
    machine = platform.machine().lower()
    if system != "Linux" or not any(arch in machine for arch in ("aarch64", "arm64")):
        raise RuntimeError(f"Jetson 빌드는 Linux aarch64 환경에서만 지원됩니다. 현재: {system}/{machine}")


def ensure_pyinstaller(python_exe: str) -> str:
    try:
        subprocess.check_call(
            [python_exe, "-m", "PyInstaller", "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return python_exe
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️  PyInstaller가 설치되지 않았습니다. 설치를 진행합니다...")
        subprocess.check_call([python_exe, "-m", "pip", "install", "pyinstaller"])
        return python_exe


def run_pyinstaller(python_exe: str, name: str) -> Path:
    cmd = [
        python_exe,
        "-m",
        "PyInstaller",
        "--name",
        name,
        "--onedir",
        "--windowed",
        "--icon=ui_pyside6/logo.png",
        "--add-data=ui_pyside6/logo.png:ui_pyside6",
        "--hidden-import=PySide6.QtCore",
        "--hidden-import=PySide6.QtGui",
        "--hidden-import=PySide6.QtWidgets",
        "--hidden-import=cv2",
        "--hidden-import=mediapipe",
        "--hidden-import=numpy",
        "--hidden-import=gtts",
        "--hidden-import=pydub",
        "--hidden-import=api_client",
        "--hidden-import=squat_real_tts",
        "--hidden-import=lunge_realtime",
        "--hidden-import=plank",
        "--collect-all=cv2",
        "--collect-all=mediapipe",
        "--exclude-module=jax",
        "--exclude-module=jaxlib",
        "--clean",
        "--noconfirm",
        "main_pyside6.py",
    ]

    print("🛠️  PyInstaller 명령:", " ".join(cmd))
    subprocess.check_call(cmd, cwd=BASE_DIR)

    built_path = DIST_DIR / name
    if not built_path.exists():
        raise FileNotFoundError(f"PyInstaller 빌드 결과를 찾을 수 없습니다: {built_path}")
    return built_path


def copy_to_install(built_dir: Path, install_dir: Path) -> Path:
    if install_dir.exists():
        shutil.rmtree(install_dir)
    shutil.copytree(built_dir, install_dir)

    app_binary = install_dir / PYINSTALLER_NAME
    if app_binary.exists():
        app_binary.chmod(0o755)

    return install_dir


def ensure_icon_available(install_dir: Path) -> Path:
    """Jetson 빌드 시 PyInstaller 데이터 경로 차이를 보정한다."""

    root_icon = install_dir / "ui_pyside6" / "logo.png"
    internal_icon = install_dir / "_internal" / "ui_pyside6" / "logo.png"

    if root_icon.exists():
        return root_icon

    if internal_icon.exists():
        root_icon.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(internal_icon, root_icon)
        return root_icon

    raise FileNotFoundError(
        f"아이콘 파일을 찾을 수 없습니다: {root_icon} 또는 {internal_icon}"
    )


def create_desktop_file(install_dir: Path, desktop_path: Path, launcher_name: str) -> Path:
    app_binary = install_dir / PYINSTALLER_NAME
    icon_path = ensure_icon_available(install_dir)

    desktop_contents = f"""[Desktop Entry]
Type=Application
Name={launcher_name}
Comment=RePiT posture analysis
Exec={app_binary}
Icon={icon_path}
Terminal=false
Categories=Education;Sports;
"""

    desktop_path.write_text(desktop_contents, encoding="utf-8")
    desktop_path.chmod(0o755)
    return desktop_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Jetson용 RePiT 앱 빌드 스크립트")
    parser.add_argument(
        "--install-dir",
        type=Path,
        default=Path.home() / "RePiT-Jetson",
        help="빌드 결과 설치 위치 (기본값: ~/RePiT-Jetson)",
    )
    parser.add_argument(
        "--desktop-path",
        type=Path,
        default=Path.home() / "Desktop" / "RePiT.desktop",
        help="생성할 .desktop 파일 경로 (기본값: ~/Desktop/RePiT.desktop)",
    )
    parser.add_argument(
        "--launcher-name",
        type=str,
        default="RePiT",
        help="런처에 표시될 이름 (기본값: RePiT)",
    )
    return parser.parse_args()


def main() -> None:
    ensure_jetson()
    args = parse_args()

    python_exe = ensure_pyinstaller(sys.executable)
    built_dir = run_pyinstaller(python_exe, PYINSTALLER_NAME)

    install_dir = copy_to_install(built_dir, args.install_dir)
    print(f"✅ 설치 폴더: {install_dir}")

    desktop_path = create_desktop_file(install_dir, args.desktop_path, args.launcher_name)
    print(f"✅ Desktop 런처 생성: {desktop_path}")

    print("\n사용 방법:")
    print(f"  1) {desktop_path} 더블클릭 → '신뢰/실행' 허용")
    print("  2) 또는, 메뉴에 등록하려면 .desktop 파일을 ~/.local/share/applications/ 로 옮기세요.")
    print("\n앱 실행: ", install_dir / PYINSTALLER_NAME)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pylint: disable=broad-except
        print(f"\n❌ 빌드 실패: {exc}")
        sys.exit(1)

