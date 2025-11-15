#!/usr/bin/env python3
"""
실행 파일(.exe/.app) 생성 스크립트
PyInstaller를 사용하여 가상환경 없이 실행 가능한 단일 실행 파일 생성
"""

import os
import sys
import subprocess
import shutil
import platform

def activate_venv_if_exists():
    """가상환경 자동 감지 및 활성화"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    venv_paths = [
        os.path.join(base_dir, "app-env-pyside6"),
        os.path.join(base_dir, "app-env"),
    ]
    
    for venv_path in venv_paths:
        if os.path.exists(venv_path):
            # 가상환경의 Python 경로 확인
            if platform.system() == "Windows":
                python_exe = os.path.join(venv_path, "Scripts", "python.exe")
            else:
                python_exe = os.path.join(venv_path, "bin", "python")
            
            if os.path.exists(python_exe):
                print(f"✅ 가상환경 발견: {os.path.basename(venv_path)}")
                print(f"   Python 경로: {python_exe}")
                # sys.executable 업데이트 (실제로는 환경 변수로 처리)
                return python_exe
    
    print("ℹ️  가상환경을 찾을 수 없습니다. 시스템 Python을 사용합니다.")
    return sys.executable

def check_pyinstaller():
    """PyInstaller 설치 확인 및 설치"""
    # 가상환경 확인
    python_exe = activate_venv_if_exists()
    
    try:
        # 가상환경의 PyInstaller 확인
        result = subprocess.run(
            [python_exe, "-c", "import PyInstaller; print(PyInstaller.__version__)"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"✅ PyInstaller 설치됨: {version}")
            return True, python_exe
    except:
        pass
    
    print("⚠️  PyInstaller가 설치되지 않았습니다.")
    response = input("PyInstaller를 설치하시겠습니까? (y/n, 기본값: y): ").strip()
    if response.lower() != 'n':
        print("📦 PyInstaller 설치 중...")
        subprocess.check_call([python_exe, "-m", "pip", "install", "pyinstaller"])
        print("✅ PyInstaller 설치 완료")
        return True, python_exe
    else:
        print("❌ PyInstaller가 필요합니다.")
        return False, python_exe

def get_icon_path():
    """아이콘 파일 경로 반환"""
    icon_path = os.path.join(os.path.dirname(__file__), "ui_pyside6", "logo.png")
    if os.path.exists(icon_path):
        # PyInstaller는 .ico (Windows) 또는 .icns (macOS) 파일을 선호
        # PNG도 사용 가능하지만 변환이 필요할 수 있음
        return icon_path
    return None

def build_windows_exe(python_exe=None):
    """Windows용 .exe 파일 생성"""
    print("\n🪟 Windows용 실행 파일 생성 중...")
    print("=" * 60)
    
    if python_exe is None:
        python_exe = sys.executable
    
    # PyInstaller 명령어 구성
    cmd = [
        python_exe, "-m", "PyInstaller",
        "--name=RePiT",
        "--onedir",  # 또는 --onefile (단일 파일)
        "--windowed",  # 콘솔 창 없이 실행
        "--icon=ui_pyside6/logo.png",
        "--add-data=ui_pyside6/logo.png;ui_pyside6",  # Windows는 ; 구분자 사용
        "--hidden-import=PySide6.QtCore",
        "--hidden-import=PySide6.QtGui",
        "--hidden-import=PySide6.QtWidgets",
        "--hidden-import=cv2",
        "--hidden-import=mediapipe",
        "--hidden-import=numpy",
        "--hidden-import=gtts",
        "--hidden-import=pydub",
        "--collect-all=PySide6",
        "--collect-all=cv2",
        "main_pyside6.py"
    ]
    
    # onefile 옵션 (선택사항 - 더 느리지만 단일 파일)
    use_onefile = input("단일 파일(.exe)로 생성하시겠습니까? (y/n, 기본값: n): ").lower() == 'y'
    if use_onefile:
        cmd[cmd.index("--onedir")] = "--onefile"
        print("📦 단일 파일 모드: 모든 의존성이 하나의 .exe 파일에 포함됩니다")
    else:
        print("📦 폴더 모드: dist/RePiT/ 폴더에 모든 파일이 포함됩니다")
    
    try:
        subprocess.check_call(cmd)
        print("\n✅ Windows 실행 파일 생성 완료!")
        print(f"📁 출력 위치: dist/RePiT/")
        if use_onefile:
            print(f"📄 실행 파일: dist/RePiT.exe")
        else:
            print(f"📄 실행 파일: dist/RePiT/RePiT.exe")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 빌드 실패: {e}")
        return False

def create_dmg(app_path, dmg_name="RePiT"):
    """macOS용 DMG 파일 생성"""
    print("\n💿 DMG 파일 생성 중...")
    print("=" * 60)
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(base_dir, "dist")
    dmg_path = os.path.join(dist_dir, f"{dmg_name}.dmg")
    
    # 기존 DMG 파일 삭제
    if os.path.exists(dmg_path):
        os.remove(dmg_path)
        print(f"🗑️  기존 DMG 파일 삭제됨: {dmg_path}")
    
    # 임시 DMG 마운트 폴더 생성
    temp_dmg_dir = os.path.join(dist_dir, "dmg_temp")
    if os.path.exists(temp_dmg_dir):
        shutil.rmtree(temp_dmg_dir)
    os.makedirs(temp_dmg_dir, exist_ok=True)
    
    try:
        # 앱 복사
        app_name = "RePiT.app"
        dest_app = os.path.join(temp_dmg_dir, app_name)
        if os.path.exists(dest_app):
            shutil.rmtree(dest_app)
        shutil.copytree(app_path, dest_app)
        print(f"✅ 앱 복사 완료: {dest_app}")
        
        # Applications 폴더로의 심볼릭 링크 생성 (선택사항)
        applications_link = os.path.join(temp_dmg_dir, "Applications")
        if not os.path.exists(applications_link):
            os.symlink("/Applications", applications_link)
            print("✅ Applications 링크 생성 완료")
        
        # DMG 생성 (hdiutil 사용)
        print("\n📦 DMG 이미지 생성 중...")
        create_cmd = [
            "hdiutil", "create",
            "-volname", dmg_name,
            "-srcfolder", temp_dmg_dir,
            "-ov",  # 덮어쓰기
            "-format", "UDZO",  # 압축된 읽기 전용 형식
            dmg_path
        ]
        
        subprocess.check_call(create_cmd)
        print(f"\n✅ DMG 파일 생성 완료!")
        print(f"📁 DMG 위치: {dmg_path}")
        
        # 임시 폴더 정리
        shutil.rmtree(temp_dmg_dir)
        
        # DMG 파일 크기 표시
        dmg_size = os.path.getsize(dmg_path) / (1024 * 1024)  # MB
        print(f"📊 DMG 크기: {dmg_size:.2f} MB")
        
        return dmg_path
        
    except Exception as e:
        # 임시 폴더 정리
        if os.path.exists(temp_dmg_dir):
            shutil.rmtree(temp_dmg_dir)
        print(f"❌ DMG 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return None

def build_macos_app(python_exe=None):
    """macOS용 .app 번들 생성"""
    print("\n🍎 macOS용 앱 번들 생성 중...")
    print("=" * 60)
    
    if python_exe is None:
        python_exe = sys.executable
    
    # PyInstaller 명령어 구성
    cmd = [
        python_exe, "-m", "PyInstaller",
        "--name=RePiT",
        "--onedir",  # macOS에서는 onedir 권장 (QtWebEngine 충돌 방지)
        "--windowed",  # 콘솔 창 없이 실행
        "--icon=ui_pyside6/logo.png",
        "--add-data=ui_pyside6/logo.png:ui_pyside6",  # macOS는 : 구분자 사용
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
        "--collect-all=mediapipe",  # MediaPipe 모델 파일 포함
        "--exclude-module=PySide6.QtWebEngineCore",
        "--exclude-module=PySide6.QtWebEngineWidgets",
        "--exclude-module=PySide6.QtWebEngineQuick",
        "--exclude-module=PySide6.Qt3DAnimation",
        "--exclude-module=PySide6.Qt3DCore",
        "--exclude-module=PySide6.Qt3DRender",
        "--exclude-module=PySide6.Qt3DExtras",
        "--exclude-module=PySide6.Qt3DInput",
        "--exclude-module=PySide6.Qt3DLogic",
        "--exclude-module=jax",  # jaxlib 처리 문제 방지
        "--exclude-module=jaxlib",  # jaxlib 처리 문제 방지
        "--clean",  # 이전 빌드 파일 정리
        "--noconfirm",  # 기존 파일 덮어쓰기
        "main_pyside6.py"
    ]
    
    # PySide6는 collect-all 대신 필요한 모듈만 hidden-import로 추가
    # 이렇게 하면 Qt 프레임워크 충돌 문제를 피할 수 있음
    
    # QtWebEngine 문제 해결을 위한 추가 옵션
    # QtWebEngine은 프레임워크 심볼릭 링크 문제로 제외
    # --onedir 모드에서는 QtWebEngine이 제대로 작동함
    
    # onefile 옵션 (macOS에서는 onedir 권장 - QtWebEngine 문제로)
    print("⚠️  macOS에서는 --onedir 모드를 권장합니다 (--onefile는 QtWebEngine 충돌 발생 가능)")
    # 비대화형 모드 지원: 기본값 n (onedir 권장)
    try:
        use_onefile = input("단일 파일(.app)로 생성하시겠습니까? (y/n, 기본값: n): ").lower() == 'y'
    except (EOFError, KeyboardInterrupt):
        use_onefile = False
        print("기본값 사용: --onedir 모드 (권장)")
    if use_onefile:
        cmd[cmd.index("--onedir")] = "--onefile"
        print("📦 단일 파일 모드: 모든 의존성이 하나의 .app 파일에 포함됩니다")
        print("⚠️  경고: QtWebEngine 관련 오류가 발생할 수 있습니다")
    else:
        print("📦 폴더 모드: dist/RePiT.app/ 폴더에 모든 파일이 포함됩니다 (권장)")
    
    try:
        subprocess.check_call(cmd)
        app_path = os.path.join("dist", "RePiT.app")
        
        # Finder에서 실행할 수 있도록 런처 스크립트 생성
        macos_path = os.path.join(app_path, "Contents", "MacOS")
        binary_path = os.path.join(macos_path, "RePiT")
        binary_backup = os.path.join(macos_path, "RePiT_bin")
        
        # 바이너리가 존재하는지 확인
        if os.path.exists(binary_path):
            # 바이너리를 백업
            if os.path.exists(binary_backup):
                os.remove(binary_backup)
            shutil.move(binary_path, binary_backup)
            
            # 런처 스크립트 생성
            launcher_script = '''#!/bin/bash
# RePiT macOS 런처 - Finder 실행 시 올바른 경로에서 실행
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
exec "$SCRIPT_DIR/RePiT_bin" "$@"
'''
            with open(binary_path, 'w') as f:
                f.write(launcher_script)
            os.chmod(binary_path, 0o755)
            print("✅ Finder 실행을 위한 런처 스크립트 생성 완료")
        
        # Info.plist에 카메라 권한 설명 추가 (macOS 개인정보 보호 필수)
        info_plist_path = os.path.join(app_path, "Contents", "Info.plist")
        if os.path.exists(info_plist_path):
            import plistlib
            try:
                # Info.plist 읽기
                with open(info_plist_path, 'rb') as f:
                    plist = plistlib.load(f)
                
                # 카메라 권한 설명 추가
                if 'NSCameraUsageDescription' not in plist:
                    plist['NSCameraUsageDescription'] = '운동 자세 분석을 위해 카메라가 필요합니다. 실시간으로 자세를 감지하고 분석합니다.'
                    print("✅ Info.plist에 카메라 권한 설명 추가됨")
                
                # 마이크 권한도 필요할 수 있으므로 추가 (TTS 사용 시)
                if 'NSMicrophoneUsageDescription' not in plist:
                    plist['NSMicrophoneUsageDescription'] = '음성 피드백을 제공하기 위해 마이크가 필요할 수 있습니다.'
                
                # Info.plist 저장
                with open(info_plist_path, 'wb') as f:
                    plistlib.dump(plist, f)
                print("✅ Info.plist 업데이트 완료")
            except Exception as e:
                print(f"⚠️  Info.plist 업데이트 실패: {e}")
                print("   수동으로 NSCameraUsageDescription을 추가해야 할 수 있습니다.")
        
        print("\n✅ macOS 앱 번들 생성 완료!")
        print(f"📁 출력 위치: {app_path}")
        print("\n⚠️  macOS 보안 설정:")
        print("   1. System Preferences > Security & Privacy")
        print("   2. 'Open Anyway' 버튼 클릭 (첫 실행 시)")
        print("   3. 또는: xattr -cr dist/RePiT.app (터미널)")
        
        # DMG 생성 옵션
        # 비대화형 모드 지원: 기본값 y
        try:
            create_dmg_option = input("\nDMG 파일을 생성하시겠습니까? (y/n, 기본값: y): ").lower()
        except (EOFError, KeyboardInterrupt):
            create_dmg_option = 'y'
            print("기본값 사용: DMG 파일 생성")
        if create_dmg_option != 'n':
            dmg_path = create_dmg(app_path)
            if dmg_path:
                print("\n" + "=" * 60)
                print("🎉 DMG 생성 완료!")
                print(f"📦 배포 파일: {dmg_path}")
                print("\n사용 방법:")
                print("1. DMG 파일을 더블클릭하여 마운트")
                print("2. RePiT.app을 Applications 폴더로 드래그")
                print("3. Applications에서 RePiT.app 실행")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 빌드 실패: {e}")
        return False

def build_linux_executable(python_exe=None):
    """Linux용 실행 파일 생성"""
    print("\n🐧 Linux용 실행 파일 생성 중...")
    print("=" * 60)
    
    if python_exe is None:
        python_exe = sys.executable
    
    cmd = [
        python_exe, "-m", "PyInstaller",
        "--name=RePiT",
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
        "--collect-all=PySide6",
        "--collect-all=cv2",
        "main_pyside6.py"
    ]
    
    use_onefile = input("단일 파일로 생성하시겠습니까? (y/n, 기본값: n): ").lower() == 'y'
    if use_onefile:
        cmd[cmd.index("--onedir")] = "--onefile"
    
    try:
        subprocess.check_call(cmd)
        print("\n✅ Linux 실행 파일 생성 완료!")
        print(f"📁 출력 위치: dist/RePiT/")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 빌드 실패: {e}")
        return False

def cleanup_build_files():
    """빌드 중간 파일 정리"""
    cleanup_dirs = ["build", "__pycache__"]
    cleanup_files = ["*.spec"]
    
    for dir_name in cleanup_dirs:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"🗑️  정리됨: {dir_name}/")
    
    # .spec 파일은 유지 (사용자가 수정할 수 있음)

def main():
    """메인 함수"""
    print("🚀 Re:PiT 실행 파일 생성 스크립트")
    print("=" * 60)
    print("\n이 스크립트는 PyInstaller를 사용하여")
    print("가상환경 없이 실행 가능한 실행 파일을 생성합니다.\n")
    print("💡 가상환경을 자동으로 감지하여 사용합니다.\n")
    
    # PyInstaller 확인 (가상환경 자동 감지 포함)
    result = check_pyinstaller()
    if isinstance(result, tuple):
        pyinstaller_ok, python_exe = result
        if not pyinstaller_ok:
            return False
    else:
        if not result:
            return False
        python_exe = sys.executable
    
    # 현재 플랫폼 확인
    current_platform = platform.system()
    print(f"\n현재 플랫폼: {current_platform}")
    
    # 플랫폼별 빌드
    success = False
    if current_platform == "Windows":
        success = build_windows_exe(python_exe)
    elif current_platform == "Darwin":  # macOS
        success = build_macos_app(python_exe)
    elif current_platform == "Linux":
        success = build_linux_executable(python_exe)
    else:
        print(f"❌ 지원하지 않는 플랫폼: {current_platform}")
        print("수동으로 PyInstaller 명령어를 실행하세요.")
        return False
    
    if success:
        # 정리 옵션
        # 비대화형 모드 지원: 기본값 n
        try:
            cleanup = input("\n빌드 중간 파일을 정리하시겠습니까? (y/n): ").lower() == 'y'
        except (EOFError, KeyboardInterrupt):
            cleanup = False
            print("기본값 사용: 빌드 중간 파일 유지")
        if cleanup:
            cleanup_build_files()
        
        print("\n" + "=" * 60)
        print("🎉 빌드 완료!")
        print("\n중요 사항:")
        print("1. 생성된 실행 파일은 가상환경 없이 실행 가능합니다")
        print("2. 실행 파일 크기가 크면 정상입니다 (모든 의존성 포함)")
        print("3. 첫 실행 시 안티바이러스가 경고할 수 있습니다 (정상)")
        print("4. Windows/macOS는 서로 다른 파일 형식이므로 각각 빌드해야 합니다")
        print("\n⚠️  iOS는 모바일 OS이므로 Python 실행 파일을 직접 실행할 수 없습니다")
        print("   macOS와 iOS는 다른 플랫폼입니다!")
    
    return success

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ 사용자가 취소했습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

