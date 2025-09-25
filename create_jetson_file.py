#!/usr/bin/env python3
"""
젯슨에서 GUI 앱으로 실행하기 위한 데스크톱 파일 생성 스크립트
"""

import os
import sys
import shutil
import stat

def create_desktop_file():
    """데스크톱 파일 생성"""
    # 현재 디렉토리 경로
    current_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(current_dir, "main_pyside6.py")
    icon_path = os.path.join(current_dir, "ui_pyside6", "logo.png")
    
    # 데스크톱 파일 내용
    desktop_content = f"""[Desktop Entry]
Version=1.0
Type=Application
Name=Re:PiT
Comment=운동 자세 분석 GUI 애플리케이션
Exec=python3 {script_path}
Icon={icon_path}
Terminal=false
StartupNotify=true
Categories=Education;Sports;
Keywords=exercise;fitness;squat;analysis;re:pit;
"""
    
    # 데스크톱 파일 경로
    desktop_file = os.path.join(current_dir, "repit.desktop")
    
    try:
        # 데스크톱 파일 생성
        with open(desktop_file, 'w', encoding='utf-8') as f:
            f.write(desktop_content)
        
        # 실행 권한 부여
        os.chmod(desktop_file, stat.S_IRWXU | stat.S_IRGRP | stat.S_IROTH)
        
        print(f"✅ 데스크톱 파일 생성됨: {desktop_file}")
        
        # 사용자 데스크톱 디렉토리에 복사
        home_dir = os.path.expanduser("~")
        user_desktop = os.path.join(home_dir, "Desktop")
        user_applications = os.path.join(home_dir, ".local", "share", "applications")
        
        # 데스크톱에 복사
        if os.path.exists(user_desktop):
            desktop_dest = os.path.join(user_desktop, "repit.desktop")
            shutil.copy2(desktop_file, desktop_dest)
            os.chmod(desktop_dest, stat.S_IRWXU | stat.S_IRGRP | stat.S_IROTH)
            print(f"✅ 데스크톱에 복사됨: {desktop_dest}")
        
        # 애플리케이션 메뉴에 복사
        os.makedirs(user_applications, exist_ok=True)
        app_dest = os.path.join(user_applications, "repit.desktop")
        shutil.copy2(desktop_file, app_dest)
        os.chmod(app_dest, stat.S_IRWXU | stat.S_IRGRP | stat.S_IROTH)
        print(f"✅ 애플리케이션 메뉴에 복사됨: {app_dest}")
        
        print("\n🎉 설정 완료!")
        print("이제 다음 방법으로 앱을 실행할 수 있습니다:")
        print("1. 데스크톱의 'Re:PiT' 아이콘 더블클릭")
        print("2. 애플리케이션 메뉴에서 'Re:PiT' 검색 후 실행")
        print("3. 파일 매니저에서 .desktop 파일 더블클릭")
        
        return True
        
    except Exception as e:
        print(f"❌ 데스크톱 파일 생성 실패: {e}")
        return False

def create_launcher_script():
    """런처 스크립트 생성"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    launcher_path = os.path.join(current_dir, "launch_repit.sh")
    
    launcher_content = f"""#!/bin/bash
# Re:PiT 런처 스크립트

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
        
        print(f"✅ 런처 스크립트 생성됨: {launcher_path}")
        return True
        
    except Exception as e:
        print(f"❌ 런처 스크립트 생성 실패: {e}")
        return False

def main():
    """메인 함수"""
    print("🔧 젯슨 GUI 앱 설정 시작...")
    print("=" * 50)
    
    # 데스크톱 파일 생성
    if create_desktop_file():
        print("✅ 데스크톱 파일 설정 완료")
    else:
        print("❌ 데스크톱 파일 설정 실패")
        return False
    
    # 런처 스크립트 생성
    if create_launcher_script():
        print("✅ 런처 스크립트 생성 완료")
    else:
        print("❌ 런처 스크립트 생성 실패")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 Re:PiT GUI 앱 설정이 완료되었습니다!")
    print("\n실행 방법:")
    print("1. 데스크톱 아이콘 더블클릭")
    print("2. 애플리케이션 메뉴에서 'Re:PiT' 검색")
    print("3. 터미널에서: ./launch_repit.sh")
    
    return True

if __name__ == "__main__":
    main()
