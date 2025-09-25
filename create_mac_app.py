#!/usr/bin/env python3
"""
맥북에서 GUI 앱으로 실행하기 위한 macOS 앱 번들 생성 스크립트
"""

import os
import sys
import shutil
import stat
import subprocess

def create_mac_app():
    """macOS 앱 번들 생성"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    app_name = "Re:PiT"
    app_bundle_path = os.path.join(current_dir, f"{app_name}.app")
    
    # 기존 앱 번들 삭제
    if os.path.exists(app_bundle_path):
        shutil.rmtree(app_bundle_path)
        print(f"✅ 기존 앱 번들 삭제됨: {app_bundle_path}")
    
    # 앱 번들 구조 생성
    contents_path = os.path.join(app_bundle_path, "Contents")
    macos_path = os.path.join(contents_path, "MacOS")
    resources_path = os.path.join(contents_path, "Resources")
    
    os.makedirs(macos_path, exist_ok=True)
    os.makedirs(resources_path, exist_ok=True)
    
    # Info.plist 생성
    info_plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>{app_name}</string>
    <key>CFBundleIdentifier</key>
    <string>com.repit.exercise-analyzer</string>
    <key>CFBundleName</key>
    <string>{app_name}</string>
    <key>CFBundleDisplayName</key>
    <string>{app_name}</string>
    <key>CFBundleVersion</key>
    <string>2.0.0</string>
    <key>CFBundleShortVersionString</key>
    <string>2.0.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleSignature</key>
    <string>????</string>
    <key>CFBundleIconFile</key>
    <string>icon.icns</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>LSUIElement</key>
    <false/>
</dict>
</plist>"""
    
    info_plist_path = os.path.join(contents_path, "Info.plist")
    with open(info_plist_path, 'w', encoding='utf-8') as f:
        f.write(info_plist_content)
    
    # 실행 스크립트 생성
    launcher_script = f"""#!/bin/bash
# Re:PiT macOS 런처 스크립트

# 스크립트가 있는 디렉토리 (앱 번들 내부)
# APP_DIR은 본인의 앱 py 파일이 있는 디렉토리의 절대 경로를 입력해주세요.(ex. "/Users/repit/ai/application")
APP_DIR=

# 프로젝트 디렉토리로 이동
cd "$APP_DIR"

# 가상환경 활성화 (있는 경우)
if [ -d "app-env-pyside6" ]; then
    source app-env-pyside6/bin/activate
    echo "✅ PySide6 가상환경 활성화됨"
elif [ -d "app-env" ]; then
    source app-env/bin/activate
    echo "✅ 기본 가상환경 활성화됨"
fi

# Re:PiT 앱 실행
echo "🚀 {app_name} 시작 중..."
python3 main_pyside6.py

echo "👋 {app_name}이 종료되었습니다."
"""
    
    launcher_path = os.path.join(macos_path, app_name)
    with open(launcher_path, 'w', encoding='utf-8') as f:
        f.write(launcher_script)
    
    # 실행 권한 부여
    os.chmod(launcher_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IROTH)
    
    # 아이콘 복사 (PNG를 ICO로 변환하거나 그대로 사용)
    icon_source = os.path.join(current_dir, "ui_pyside6", "logo.png")
    if os.path.exists(icon_source):
        # PNG 아이콘을 그대로 복사 (macOS에서 PNG도 지원)
        icon_dest = os.path.join(resources_path, "icon.png")
        shutil.copy2(icon_source, icon_dest)
        print(f"✅ 아이콘 복사됨: {icon_dest}")
        
        # Info.plist에서 아이콘 파일명 수정
        with open(info_plist_path, 'r', encoding='utf-8') as f:
            content = f.read()
        content = content.replace('icon.icns', 'icon.png')
        with open(info_plist_path, 'w', encoding='utf-8') as f:
            f.write(content)
    else:
        print(f"⚠️  아이콘 파일을 찾을 수 없습니다: {icon_source}")
    
    print(f"✅ macOS 앱 번들 생성 완료: {app_bundle_path}")
    return app_bundle_path

def create_launcher_script():
    """터미널용 런처 스크립트 생성"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    launcher_path = os.path.join(current_dir, "launch_repit_mac.sh")
    
    launcher_content = f"""#!/bin/bash
# Re:PiT 맥북 런처 스크립트

# 프로젝트 디렉토리로 이동
cd "{current_dir}"

# 가상환경 활성화 (있는 경우)
if [ -d "app-env-pyside6" ]; then
    source app-env-pyside6/bin/activate
    echo "✅ PySide6 가상환경 활성화됨"
elif [ -d "app-env" ]; then
    source app-env/bin/activate
    echo "✅ 기본 가상환경 활성화됨"
fi

# Re:PiT 앱 실행
echo "🚀 Re:PiT 시작 중..."
python3 main_pyside6.py

echo "👋 Re:PiT이 종료되었습니다."
"""
    
    try:
        with open(launcher_path, 'w', encoding='utf-8') as f:
            f.write(launcher_content)
        
        # 실행 권한 부여
        os.chmod(launcher_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IROTH)
        
        print(f"✅ 맥북 런처 스크립트 생성됨: {launcher_path}")
        return True
        
    except Exception as e:
        print(f"❌ 런처 스크립트 생성 실패: {e}")
        return False

def create_desktop_shortcut():
    """데스크톱 바로가기 생성 (macOS)"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    desktop_path = os.path.expanduser("~/Desktop")
    app_bundle_path = os.path.join(current_dir, "Re:PiT.app")
    
    if os.path.exists(app_bundle_path):
        shortcut_path = os.path.join(desktop_path, "Re:PiT.app")
        
        # 데스크톱에 심볼릭 링크 생성
        try:
            if os.path.exists(shortcut_path):
                os.remove(shortcut_path)
            
            os.symlink(app_bundle_path, shortcut_path)
            print(f"✅ 데스크톱 바로가기 생성됨: {shortcut_path}")
            return True
        except Exception as e:
            print(f"❌ 데스크톱 바로가기 생성 실패: {e}")
            return False
    else:
        print("❌ 앱 번들을 먼저 생성해야 합니다.")
        return False

def main():
    """메인 함수"""
    print("🍎 Re:PiT 맥북 GUI 앱 설정 시작...")
    print("=" * 50)
    
    # macOS 앱 번들 생성
    app_bundle = create_mac_app()
    if app_bundle:
        print("✅ macOS 앱 번들 생성 완료")
    else:
        print("❌ macOS 앱 번들 생성 실패")
        return False
    
    # 런처 스크립트 생성
    if create_launcher_script():
        print("✅ 런처 스크립트 생성 완료")
    else:
        print("❌ 런처 스크립트 생성 실패")
    
    # 데스크톱 바로가기 생성
    if create_desktop_shortcut():
        print("✅ 데스크톱 바로가기 생성 완료")
    else:
        print("⚠️  데스크톱 바로가기 생성 실패 (수동으로 가능)")
    
    print("\n" + "=" * 50)
    print("🎉 Re:PiT 맥북 GUI 앱 설정이 완료되었습니다!")
    print("\n실행 방법:")
    print("1. 데스크톱의 'Re:PiT.app' 더블클릭")
    print("2. Finder에서 'Re:PiT.app' 더블클릭")
    print("3. 터미널에서: ./launch_repit_mac.sh")
    print("4. Spotlight에서 'Re:PiT' 검색 후 실행")
    
    return True

if __name__ == "__main__":
    main()
